"""Adaptador HTTP del rate limit con una app Flask mínima (sin base de datos)."""

from functools import wraps
from types import SimpleNamespace

import pytest
from flask import Flask, g, request

from orderhub.adapters.inbound.http.rate_limiter import InMemoryRateLimiter
from orderhub.adapters.inbound.http.rate_limiting import (
    install_rate_limiting,
    rate_limit_by_ip,
    rate_limit_by_user,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def _limiter(clock, maximo):
    return InMemoryRateLimiter(maximo, 60, clock=clock)


def _con_identidad_opcional(view):
    """Hace de @jwt_required: deja g.current_user si llega X-Test-User."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        user_id = request.headers.get("X-Test-User")
        if user_id is not None:
            g.current_user = SimpleNamespace(user_id=int(user_id))
        return view(*args, **kwargs)

    return wrapper


def _app(global_limiter, hops=0, ip_limiter=None, user_limiter=None) -> Flask:
    app = Flask(__name__)
    app.testing = True
    install_rate_limiting(app, global_limiter, trusted_proxy_hops=hops)

    @app.route("/")
    def raiz():
        return "ok"

    @app.route("/api")
    def api():
        return "ok"

    if ip_limiter is not None:

        @app.route("/por-ip", methods=["POST"])
        @rate_limit_by_ip(ip_limiter)
        def por_ip():
            return "ok"

    if user_limiter is not None:

        @app.route("/por-usuario", methods=["POST"])
        @_con_identidad_opcional
        @rate_limit_by_user(user_limiter)
        def por_usuario():
            return "ok"

    return app


# --- Formato del 429 ----------------------------------------------------------


def test_un_429_es_json_con_el_formato_de_error_y_retry_after(clock):
    client = _app(_limiter(clock, 1)).test_client()
    client.get("/api")

    response = client.get("/api")

    assert response.status_code == 429
    assert response.get_json() == {
        "status": "error",
        "message": "Demasiadas peticiones. Intenta de nuevo en 60 s",
    }
    assert response.headers["Retry-After"] == "60"


def test_el_retry_after_baja_con_el_paso_del_tiempo(clock):
    client = _app(_limiter(clock, 1)).test_client()
    client.get("/api")
    clock.advance(45)

    response = client.get("/api")

    assert response.headers["Retry-After"] == "15"
    assert "en 15 s" in response.get_json()["message"]


def test_tras_la_ventana_la_ruta_vuelve_a_responder(clock):
    client = _app(_limiter(clock, 1)).test_client()
    client.get("/api")
    assert client.get("/api").status_code == 429

    clock.advance(60)

    assert client.get("/api").status_code == 200


# --- Límite global: qué cuenta y qué no ---------------------------------------


def test_la_raiz_no_cuenta_para_el_limite_global(clock):
    client = _app(_limiter(clock, 1)).test_client()

    assert all(client.get("/").status_code == 200 for _ in range(20))
    assert client.get("/api").status_code == 200  # el contador sigue en cero


def test_los_estaticos_no_cuentan_para_el_limite_global(clock):
    client = _app(_limiter(clock, 1)).test_client()

    # Ni siquiera existe el fichero: se excluye la ruta, no la respuesta.
    codigos = {client.get("/static/inexistente.js").status_code for _ in range(20)}

    assert codigos == {404}
    assert client.get("/api").status_code == 200


def test_una_ruta_inexistente_si_cuenta_para_el_limite_global(clock):
    client = _app(_limiter(clock, 2)).test_client()
    client.get("/no-existe")
    client.get("/no-existe")

    assert client.get("/no-existe").status_code == 429


# --- Decoradores por IP y por usuario -----------------------------------------


def test_rate_limit_by_ip_bloquea_a_la_misma_ip_y_no_a_otra(clock):
    app = _app(_limiter(clock, 100), ip_limiter=_limiter(clock, 1))
    client = app.test_client()

    primera = client.post("/por-ip", environ_overrides={"REMOTE_ADDR": "9.9.9.1"})
    repetida = client.post("/por-ip", environ_overrides={"REMOTE_ADDR": "9.9.9.1"})
    otra = client.post("/por-ip", environ_overrides={"REMOTE_ADDR": "9.9.9.2"})

    assert (primera.status_code, repetida.status_code, otra.status_code) == (
        200,
        429,
        200,
    )


def test_rate_limit_by_user_cuenta_por_user_id_y_no_por_ip(clock):
    app = _app(_limiter(clock, 100), user_limiter=_limiter(clock, 1))
    client = app.test_client()

    uno = client.post("/por-usuario", headers={"X-Test-User": "1"})
    uno_otra_ip = client.post(
        "/por-usuario",
        headers={"X-Test-User": "1"},
        environ_overrides={"REMOTE_ADDR": "9.9.9.9"},
    )
    dos = client.post("/por-usuario", headers={"X-Test-User": "2"})

    assert (uno.status_code, uno_otra_ip.status_code, dos.status_code) == (
        200,
        429,
        200,
    )


def test_rate_limit_by_user_sin_identidad_cae_a_la_ip(clock):
    app = _app(_limiter(clock, 100), user_limiter=_limiter(clock, 1))
    client = app.test_client()

    primera = client.post("/por-usuario")
    segunda = client.post("/por-usuario")

    assert (primera.status_code, segunda.status_code) == (200, 429)


def test_sin_remote_addr_se_usa_una_clave_comun(clock):
    client = _app(_limiter(clock, 1)).test_client()

    client.get("/api", environ_overrides={"REMOTE_ADDR": ""})
    response = client.get("/api", environ_overrides={"REMOTE_ADDR": ""})

    assert response.status_code == 429


# --- Proxy: X-Forwarded-For -----------------------------------------------------


def test_sin_proxies_de_confianza_x_forwarded_for_se_ignora(clock):
    """Falsificar la cabecera no da un contador nuevo."""
    client = _app(_limiter(clock, 1), hops=0).test_client()

    primera = client.get("/api", headers={"X-Forwarded-For": "1.1.1.1"})
    falsificada = client.get("/api", headers={"X-Forwarded-For": "2.2.2.2"})

    assert (primera.status_code, falsificada.status_code) == (200, 429)


def test_con_un_proxy_de_confianza_se_usa_la_ip_que_anade_el_proxy(clock):
    client = _app(_limiter(clock, 1), hops=1).test_client()

    a = client.get("/api", headers={"X-Forwarded-For": "1.1.1.1"})
    b = client.get("/api", headers={"X-Forwarded-For": "2.2.2.2"})
    repetida = client.get("/api", headers={"X-Forwarded-For": "2.2.2.2"})

    assert (a.status_code, b.status_code, repetida.status_code) == (200, 200, 429)


def test_con_un_salto_un_cliente_no_puede_elegir_su_ip_con_la_cabecera(clock):
    """El cliente envía 'falsa'; el proxy añade la real al final. Con N=1 solo
    cuenta la última entrada, así que cambiar la primera no sirve."""
    client = _app(_limiter(clock, 1), hops=1).test_client()

    client.get("/api", headers={"X-Forwarded-For": "10.0.0.1, 7.7.7.7"})
    cambiada = client.get("/api", headers={"X-Forwarded-For": "10.0.0.2, 7.7.7.7"})

    assert cambiada.status_code == 429


def test_con_dos_saltos_se_usa_la_penultima_entrada(clock):
    client = _app(_limiter(clock, 1), hops=2).test_client()

    client.get("/api", headers={"X-Forwarded-For": "1.1.1.1, 5.5.5.5"})
    mismo_cliente = client.get("/api", headers={"X-Forwarded-For": "1.1.1.1, 6.6.6.6"})
    otro_cliente = client.get("/api", headers={"X-Forwarded-For": "3.3.3.3, 5.5.5.5"})

    assert (mismo_cliente.status_code, otro_cliente.status_code) == (429, 200)

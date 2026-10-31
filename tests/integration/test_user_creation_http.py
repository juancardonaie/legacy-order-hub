"""POST /users de extremo a extremo: SQLite real, bcrypt real, JWT real.

Cubre la creación solo por admin, la validación de entrada y el rate limit
(con reloj falso, sin dormir). El rate limit usa `make_app` con límites bajos;
el resto de la suite usa los límites altos de `integration_app`.
"""

import bcrypt
import pytest

from orderhub.adapters.inbound.http.rate_limiter import RateLimitConfig

VALIDO = {"username": "ana", "password": "clave-segura-1"}


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _contar_usuarios(connection) -> int:
    return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]


@pytest.fixture
def admin_headers(login, admin_password):
    return _auth(login("admin", admin_password))


@pytest.fixture
def client_headers(login, client_password):
    return _auth(login("juan", client_password))


# --- Creación y login posterior ---------------------------------------------


def test_admin_crea_un_client_y_ese_usuario_puede_iniciar_sesion(
    http, admin_headers, login, connection
):
    response = http.post("/users", json=VALIDO, headers=admin_headers)

    assert response.status_code == 201
    user = response.get_json()["user"]
    assert user["username"] == "ana"
    assert user["role"] == "client"
    token = login("ana", "clave-segura-1")
    assert http.get("/products", headers=_auth(token)).status_code == 200


def test_el_usuario_creado_con_role_client_no_puede_crear_usuarios(
    http, admin_headers, login
):
    http.post("/users", json=VALIDO, headers=admin_headers)

    token = login("ana", "clave-segura-1")

    assert http.post("/users", json=VALIDO, headers=_auth(token)).status_code == 403


def test_un_admin_creado_puede_crear_productos_y_usuarios(http, admin_headers, login):
    body = {"username": "adm2", "password": "clave-segura-2", "role": "admin"}
    assert http.post("/users", json=body, headers=admin_headers).status_code == 201

    headers = _auth(login("adm2", "clave-segura-2"))

    producto = {"name": "Nuevo", "price": 5.0, "stock": 1}
    assert http.post("/products", json=producto, headers=headers).status_code == 201
    otro = {"username": "otro", "password": "clave-segura-3"}
    assert http.post("/users", json=otro, headers=headers).status_code == 201


def test_se_guarda_solo_el_hash_y_nunca_la_contrasena(http, admin_headers, connection):
    http.post("/users", json=VALIDO, headers=admin_headers)

    fila = connection.execute(
        "SELECT password, password_hash FROM users WHERE username = 'ana'"
    ).fetchone()

    assert fila["password"] is None
    assert fila["password_hash"] != "clave-segura-1"
    assert bcrypt.checkpw(b"clave-segura-1", fila["password_hash"].encode("utf-8"))


def test_la_respuesta_nunca_incluye_contrasena_ni_hash(http, admin_headers):
    response = http.post("/users", json=VALIDO, headers=admin_headers)

    texto = response.get_data(as_text=True)
    assert "clave-segura-1" not in texto
    assert "$2b$" not in texto
    assert "password" not in texto


# --- Seguridad: quién puede crear -----------------------------------------------


def test_sin_token_da_401_y_no_crea_nada(http, connection):
    antes = _contar_usuarios(connection)

    assert http.post("/users", json=VALIDO).status_code == 401
    assert _contar_usuarios(connection) == antes


def test_un_token_invalido_da_401(http):
    assert http.post("/users", json=VALIDO, headers=_auth("falso")).status_code == 401


def test_un_client_recibe_403_aunque_pida_role_admin(http, client_headers, connection):
    antes = _contar_usuarios(connection)
    body = {**VALIDO, "role": "admin"}

    response = http.post("/users", json=body, headers=client_headers)

    assert response.status_code == 403
    assert _contar_usuarios(connection) == antes


# --- Validación ---------------------------------------------------------------


@pytest.mark.parametrize("body", [[1], "abc", 5, [], None])
def test_un_body_que_no_es_un_objeto_da_400(http, admin_headers, connection, body):
    antes = _contar_usuarios(connection)

    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert _contar_usuarios(connection) == antes


@pytest.mark.parametrize(
    "body",
    [
        {"username": "ana", "password": 12345678},
        {"username": ["ana"], "password": "clave-segura-1"},
        {"username": "ana", "password": "clave-segura-1", "role": False},
        {"username": "ana", "password": "clave-segura-1", "role": None},
    ],
)
def test_los_tipos_incorrectos_dan_400(http, admin_headers, connection, body):
    antes = _contar_usuarios(connection)

    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert _contar_usuarios(connection) == antes


@pytest.mark.parametrize("role", ["false", "ADMIN", "", "root"])
def test_un_role_invalido_da_400_y_no_crea_el_usuario(
    http, admin_headers, connection, role
):
    antes = _contar_usuarios(connection)

    response = http.post("/users", json={**VALIDO, "role": role}, headers=admin_headers)

    assert response.status_code == 400
    assert _contar_usuarios(connection) == antes


@pytest.mark.parametrize(
    "body",
    [
        {"username": "Ana", "password": "clave-segura-1"},
        {"username": "ab", "password": "clave-segura-1"},
        {"username": "con espacio", "password": "clave-segura-1"},
        {"username": "ana", "password": "corta"},
        {"username": "ana", "password": "ñ" * 37},
    ],
)
def test_las_reglas_de_username_y_contrasena_dan_400(
    http, admin_headers, connection, body
):
    antes = _contar_usuarios(connection)

    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert _contar_usuarios(connection) == antes


def test_un_username_repetido_da_409(http, admin_headers, connection):
    body = {"username": "juan", "password": "clave-segura-1"}
    antes = _contar_usuarios(connection)

    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 409
    assert _contar_usuarios(connection) == antes


def test_crear_el_mismo_usuario_dos_veces_da_201_y_luego_409(http, admin_headers):
    primera = http.post("/users", json=VALIDO, headers=admin_headers)
    segunda = http.post("/users", json=VALIDO, headers=admin_headers)

    assert (primera.status_code, segunda.status_code) == (201, 409)


# --- Rate limit: /users ----------------------------------------------------------


def test_users_devuelve_429_con_retry_after_al_superar_el_limite(
    make_app, admin_password
):
    clock = FakeClock()
    app = make_app(RateLimitConfig(users_max=2, clock=clock))
    http = app.test_client()
    headers = _auth(login_con(http, "admin", admin_password))

    http.post("/users", json={**VALIDO, "username": "usr1"}, headers=headers)
    http.post("/users", json={**VALIDO, "username": "usr2"}, headers=headers)
    response = http.post("/users", json={**VALIDO, "username": "usr3"}, headers=headers)

    assert response.status_code == 429
    assert response.get_json() == {
        "status": "error",
        "message": "Demasiadas peticiones. Intenta de nuevo en 60 s",
    }
    assert response.headers["Retry-After"] == "60"


def test_el_429_de_users_llega_antes_de_validar_hashear_o_consultar(
    make_app, admin_password, connection
):
    app = make_app(RateLimitConfig(users_max=1, clock=FakeClock()))
    http = app.test_client()
    headers = _auth(login_con(http, "admin", admin_password))
    http.post("/users", json=[1], headers=headers)  # consume el único permitido
    antes = _contar_usuarios(connection)

    bloqueada = http.post("/users", json=VALIDO, headers=headers)

    assert bloqueada.status_code == 429  # no 201: no se creó el usuario
    assert _contar_usuarios(connection) == antes


def test_el_limite_de_users_es_por_usuario_y_no_por_ip(
    make_app, admin_password, client_password
):
    app = make_app(RateLimitConfig(users_max=1, clock=FakeClock()))
    http = app.test_client()
    admin = _auth(login_con(http, "admin", admin_password))
    http.post("/users", json={**VALIDO, "username": "usr1"}, headers=admin)
    http.post("/users", json={**VALIDO, "username": "usr2"}, headers=admin)  # 429

    # Mismo cliente HTTP e IP, pero otro user_id (juan): su contador es propio.
    juan = _auth(login_con(http, "juan", client_password))
    respuesta = http.post("/users", json=VALIDO, headers=juan)

    assert respuesta.status_code == 403


def test_pasada_la_ventana_users_vuelve_a_responder(make_app, admin_password):
    clock = FakeClock()
    app = make_app(RateLimitConfig(users_max=1, clock=clock))
    http = app.test_client()
    headers = _auth(login_con(http, "admin", admin_password))
    http.post("/users", json={**VALIDO, "username": "usr1"}, headers=headers)
    assert (
        http.post("/users", json={**VALIDO, "username": "usr2"}, headers=headers)
    ).status_code == 429

    clock.advance(60)

    assert (
        http.post("/users", json={**VALIDO, "username": "usr2"}, headers=headers)
    ).status_code == 201


# --- Rate limit: /login -----------------------------------------------------------


def login_con(http, username, password) -> str:
    response = http.post("/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_json()
    return response.get_json()["token"]


def _login_fallido(http, **kwargs):
    return http.post("/login", json={"username": "x", "password": "y"}, **kwargs)


def test_login_devuelve_429_con_retry_after_al_superar_el_limite(make_app):
    app = make_app(RateLimitConfig(login_max=3, clock=FakeClock()))
    http = app.test_client()

    codigos = [_login_fallido(http).status_code for _ in range(3)]
    bloqueado = _login_fallido(http)

    assert codigos == [401, 401, 401]
    assert bloqueado.status_code == 429
    assert bloqueado.headers["Retry-After"] == "60"
    assert bloqueado.get_json()["status"] == "error"
    assert "Demasiadas peticiones" in bloqueado.get_json()["message"]


def test_con_el_limite_superado_ni_el_login_correcto_pasa(make_app, admin_password):
    app = make_app(RateLimitConfig(login_max=1, clock=FakeClock()))
    http = app.test_client()
    _login_fallido(http)

    response = http.post(
        "/login", json={"username": "admin", "password": admin_password}
    )

    assert response.status_code == 429


def test_el_limite_de_login_es_por_ip(make_app):
    app = make_app(RateLimitConfig(login_max=1, clock=FakeClock()))
    http = app.test_client()
    _login_fallido(http, environ_overrides={"REMOTE_ADDR": "9.9.9.1"})

    misma = _login_fallido(http, environ_overrides={"REMOTE_ADDR": "9.9.9.1"})
    otra = _login_fallido(http, environ_overrides={"REMOTE_ADDR": "9.9.9.2"})

    assert (misma.status_code, otra.status_code) == (429, 401)


def test_un_429_no_afecta_a_otras_rutas_con_su_propio_contador(make_app):
    app = make_app(RateLimitConfig(login_max=1, clock=FakeClock()))
    http = app.test_client()
    _login_fallido(http)
    assert _login_fallido(http).status_code == 429

    assert http.get("/products").status_code == 401  # no 429


# --- Rate limit: global ------------------------------------------------------------


def test_la_raiz_y_los_estaticos_no_cuentan_para_el_limite_global(make_app):
    app = make_app(RateLimitConfig(global_max=3, clock=FakeClock()))
    http = app.test_client()

    raiz = {http.get("/").status_code for _ in range(10)}
    estaticos = {http.get("/static/js/main.js").status_code for _ in range(10)} | {
        http.get("/static/endpoints.json").status_code for _ in range(10)
    }

    assert raiz == {200}
    assert estaticos == {200}
    assert http.get("/products").status_code == 401  # el contador sigue en cero


def test_el_limite_global_bloquea_la_api_con_429(make_app):
    app = make_app(RateLimitConfig(global_max=3, clock=FakeClock()))
    http = app.test_client()

    codigos = [http.get("/products").status_code for _ in range(3)]
    bloqueada = http.get("/get_all_orders_legacy")

    assert codigos == [401, 401, 401]
    assert bloqueada.status_code == 429
    assert bloqueada.headers["Retry-After"] == "60"
    assert bloqueada.get_json()["status"] == "error"


def test_con_el_limite_global_superado_la_raiz_sigue_respondiendo(make_app):
    app = make_app(RateLimitConfig(global_max=1, clock=FakeClock()))
    http = app.test_client()
    http.get("/products")
    assert http.get("/products").status_code == 429

    assert http.get("/").status_code == 200


def test_rate_limit_desactivado_no_bloquea_nunca(make_app):
    app = make_app(
        RateLimitConfig(
            enabled=False, login_max=1, users_max=1, global_max=1, clock=FakeClock()
        )
    )
    http = app.test_client()

    codigos = {_login_fallido(http).status_code for _ in range(20)}

    assert codigos == {401}


# --- Proxy -------------------------------------------------------------------------


def test_x_forwarded_for_falsificado_no_cambia_la_clave_sin_proxy_de_confianza(
    make_app,
):
    app = make_app(RateLimitConfig(login_max=1, clock=FakeClock()))
    http = app.test_client()

    _login_fallido(http, headers={"X-Forwarded-For": "1.1.1.1"})
    falsificado = _login_fallido(http, headers={"X-Forwarded-For": "2.2.2.2"})

    assert falsificado.status_code == 429


def test_con_un_proxy_de_confianza_cada_ip_real_tiene_su_contador(make_app):
    app = make_app(
        RateLimitConfig(login_max=1, clock=FakeClock()), trusted_proxy_hops=1
    )
    http = app.test_client()

    uno = _login_fallido(http, headers={"X-Forwarded-For": "1.1.1.1"})
    otro = _login_fallido(http, headers={"X-Forwarded-For": "2.2.2.2"})
    repetido = _login_fallido(http, headers={"X-Forwarded-For": "2.2.2.2"})

    assert (uno.status_code, otro.status_code, repetido.status_code) == (401, 401, 429)

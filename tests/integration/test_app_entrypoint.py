"""Punto de entrada real: `app.py` y `gunicorn.conf.py`.

`app.py` ejecuta `init_db()` al importarse (DT-06). Aquí se importa con
`database.init_db` sustituido por un espía, así se prueba el cableado real sin
escribir en orderhub.db.
"""

import importlib
import json
import pathlib
import runpy
import sys

import pytest

import database
from orderhub import settings

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
CATALOG = json.loads((PROJECT_ROOT / "static/endpoints.json").read_text("utf-8"))

VARIABLES = ("APP_DEBUG", "APP_HOST", "PORT", "ADMIN_USERNAME", "ADMIN_PASSWORD")


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for nombre in VARIABLES:
        monkeypatch.delenv(nombre, raising=False)


@pytest.fixture
def llamadas_init_db(monkeypatch):
    llamadas = []

    def espia(*args, **kwargs):
        llamadas.append((args, kwargs))

    monkeypatch.setattr(database, "init_db", espia)
    return llamadas


@pytest.fixture
def app_module(llamadas_init_db, monkeypatch):
    monkeypatch.delitem(sys.modules, "app", raising=False)
    return importlib.import_module("app")


# --- Arranque ----------------------------------------------------------------


def test_al_importarse_inicializa_la_base_con_el_entorno_de_settings(
    llamadas_init_db, app_module
):
    assert llamadas_init_db == [
        (
            (settings.DATABASE_PATH,),
            {
                "app_env": settings.APP_ENV,
                "admin_username": None,
                "admin_password": None,
            },
        )
    ]


def test_pasa_las_variables_admin_a_init_db(llamadas_init_db, monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "operaciones")
    monkeypatch.setenv("ADMIN_PASSWORD", "clave-de-prueba")
    monkeypatch.delitem(sys.modules, "app", raising=False)

    importlib.import_module("app")

    _, kwargs = llamadas_init_db[0]
    assert kwargs["admin_username"] == "operaciones"
    assert kwargs["admin_password"] == "clave-de-prueba"


def test_las_rutas_reales_coinciden_con_el_catalogo_del_explorador(app_module):
    reales = {
        (metodo, regla.rule)
        for regla in app_module.app.url_map.iter_rules()
        if regla.endpoint != "static" and regla.rule != "/"
        for metodo in regla.methods - {"HEAD", "OPTIONS"}
    }

    assert reales == {(e["method"], e["path"]) for e in CATALOG}


def test_la_ruta_raiz_entrega_la_interfaz(app_module):
    response = app_module.app.test_client().get("/")

    assert response.status_code == 200
    assert b"Legacy OrderHub" in response.data
    response.close()


# --- Rate limit ---------------------------------------------------------------


LIMITE_GLOBAL_DE_PRUEBA = 5


@pytest.fixture
def app_con_limite_global(llamadas_init_db, monkeypatch):
    """`app.py` importado con límites fijados aquí, sin depender del entorno
    ni de un .env local: settings se lee al construir el Container."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_GLOBAL_MAX", LIMITE_GLOBAL_DE_PRUEBA)
    monkeypatch.setattr(settings, "RATE_LIMIT_GLOBAL_WINDOW", 60)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 0)
    monkeypatch.delitem(sys.modules, "app", raising=False)
    return importlib.import_module("app")


def test_app_py_instala_el_limite_global_pero_no_cuenta_la_raiz(
    app_con_limite_global,
):
    cliente = app_con_limite_global.app.test_client()

    for _ in range(LIMITE_GLOBAL_DE_PRUEBA + 5):
        assert cliente.get("/").status_code == 200

    for _ in range(LIMITE_GLOBAL_DE_PRUEBA):
        assert cliente.get("/ruta-que-no-existe").status_code == 404
    bloqueada = cliente.get("/ruta-que-no-existe")
    assert bloqueada.status_code == 429
    assert "Retry-After" in bloqueada.headers


def test_app_py_registra_post_users_con_login_y_rate_limit(app_module):
    reglas = {
        (metodo, regla.rule)
        for regla in app_module.app.url_map.iter_rules()
        for metodo in regla.methods
    }

    assert ("POST", "/users") in reglas
    assert ("POST", "/login") in reglas


# --- Debug y servidor de desarrollo ------------------------------------------


@pytest.mark.parametrize("valor", ["1", "true", "TRUE", " yes "])
def test_debug_se_activa_solo_con_valores_explicitos(app_module, monkeypatch, valor):
    monkeypatch.setenv("APP_DEBUG", valor)

    assert app_module._debug_enabled() is True


@pytest.mark.parametrize("valor", ["", "0", "false", "no", "si"])
def test_debug_queda_apagado_por_defecto(app_module, monkeypatch, valor):
    monkeypatch.setenv("APP_DEBUG", valor)

    assert app_module._debug_enabled() is False


def test_por_defecto_el_servidor_solo_escucha_en_loopback_y_sin_debug(app_module):
    assert app_module._server_options() == {
        "host": "127.0.0.1",
        "port": 5001,
        "debug": False,
    }


def test_port_y_app_host_se_leen_del_entorno(app_module, monkeypatch):
    monkeypatch.setenv("PORT", "8080")
    monkeypatch.setenv("APP_HOST", "0.0.0.0")

    assert app_module._server_options() == {
        "host": "0.0.0.0",
        "port": 8080,
        "debug": False,
    }


def test_variables_vacias_equivalen_a_los_valores_por_defecto(app_module, monkeypatch):
    monkeypatch.setenv("PORT", "  ")
    monkeypatch.setenv("APP_HOST", "")

    assert app_module._server_options()["host"] == "127.0.0.1"
    assert app_module._server_options()["port"] == 5001


def test_un_puerto_no_numerico_falla_claro(app_module, monkeypatch):
    monkeypatch.setenv("PORT", "abc")

    with pytest.raises(RuntimeError, match="PORT debe ser un entero"):
        app_module._server_options()


def test_debug_con_host_expuesto_se_rechaza(app_module, monkeypatch):
    monkeypatch.setenv("APP_DEBUG", "1")
    monkeypatch.setenv("APP_HOST", "0.0.0.0")

    with pytest.raises(RuntimeError, match="APP_DEBUG solo se permite en loopback"):
        app_module._server_options()


def test_debug_con_host_loopback_se_permite(app_module, monkeypatch):
    monkeypatch.setenv("APP_DEBUG", "1")
    monkeypatch.setenv("APP_HOST", "localhost")

    assert app_module._server_options()["debug"] is True


# --- gunicorn ----------------------------------------------------------------


def _gunicorn_conf():
    return runpy.run_path(str(PROJECT_ROOT / "gunicorn.conf.py"))


def test_gunicorn_usa_un_solo_worker():
    assert _gunicorn_conf()["workers"] == 1


def test_gunicorn_escucha_por_defecto_en_todas_las_interfaces_puerto_5001():
    assert _gunicorn_conf()["bind"] == "0.0.0.0:5001"


def test_gunicorn_toma_puerto_y_host_del_entorno(monkeypatch):
    monkeypatch.setenv("PORT", "10000")
    monkeypatch.setenv("APP_HOST", "127.0.0.1")

    assert _gunicorn_conf()["bind"] == "127.0.0.1:10000"


def test_gunicorn_ignora_variables_vacias(monkeypatch):
    monkeypatch.setenv("PORT", "")
    monkeypatch.setenv("APP_HOST", " ")

    assert _gunicorn_conf()["bind"] == "0.0.0.0:5001"

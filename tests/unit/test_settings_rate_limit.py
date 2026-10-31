"""Configuración del rate limit en settings.py (valores por defecto y errores)."""

import importlib

import dotenv
import pytest

from orderhub import settings as settings_module

VARIABLES = (
    "RATE_LIMIT_ENABLED",
    "RATE_LIMIT_LOGIN_MAX",
    "RATE_LIMIT_LOGIN_WINDOW",
    "RATE_LIMIT_USERS_MAX",
    "RATE_LIMIT_USERS_WINDOW",
    "RATE_LIMIT_GLOBAL_MAX",
    "RATE_LIMIT_GLOBAL_WINDOW",
    "TRUSTED_PROXY_HOPS",
)


@pytest.fixture
def load_settings(monkeypatch):
    def _load(**entorno):
        for variable in VARIABLES:
            monkeypatch.delenv(variable, raising=False)
        for nombre, valor in entorno.items():
            monkeypatch.setenv(nombre, valor)
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
        return importlib.reload(settings_module)

    yield _load

    monkeypatch.undo()
    importlib.reload(settings_module)


def test_los_valores_por_defecto_son_holgados_y_el_proxy_no_es_de_confianza(
    load_settings,
):
    settings = load_settings()

    assert settings.RATE_LIMIT_ENABLED is True
    assert (settings.RATE_LIMIT_LOGIN_MAX, settings.RATE_LIMIT_LOGIN_WINDOW) == (30, 60)
    assert (settings.RATE_LIMIT_USERS_MAX, settings.RATE_LIMIT_USERS_WINDOW) == (30, 60)
    assert (settings.RATE_LIMIT_GLOBAL_MAX, settings.RATE_LIMIT_GLOBAL_WINDOW) == (
        300,
        60,
    )
    assert settings.TRUSTED_PROXY_HOPS == 0


def test_las_variables_son_configurables(load_settings):
    settings = load_settings(
        RATE_LIMIT_LOGIN_MAX="3",
        RATE_LIMIT_LOGIN_WINDOW="10",
        RATE_LIMIT_USERS_MAX="4",
        RATE_LIMIT_USERS_WINDOW="20",
        RATE_LIMIT_GLOBAL_MAX="5",
        RATE_LIMIT_GLOBAL_WINDOW="30",
        TRUSTED_PROXY_HOPS="2",
    )

    assert (settings.RATE_LIMIT_LOGIN_MAX, settings.RATE_LIMIT_LOGIN_WINDOW) == (3, 10)
    assert (settings.RATE_LIMIT_USERS_MAX, settings.RATE_LIMIT_USERS_WINDOW) == (4, 20)
    assert (settings.RATE_LIMIT_GLOBAL_MAX, settings.RATE_LIMIT_GLOBAL_WINDOW) == (
        5,
        30,
    )
    assert settings.TRUSTED_PROXY_HOPS == 2


def test_una_variable_vacia_equivale_a_no_definida(load_settings):
    settings = load_settings(
        RATE_LIMIT_ENABLED="", RATE_LIMIT_LOGIN_MAX="  ", TRUSTED_PROXY_HOPS=""
    )

    assert settings.RATE_LIMIT_ENABLED is True
    assert settings.RATE_LIMIT_LOGIN_MAX == 30
    assert settings.TRUSTED_PROXY_HOPS == 0


@pytest.mark.parametrize("valor", ["0", "false", "FALSE", "no", " off "])
def test_el_interruptor_se_apaga_con_valores_explicitos(load_settings, valor):
    assert load_settings(RATE_LIMIT_ENABLED=valor).RATE_LIMIT_ENABLED is False


@pytest.mark.parametrize("valor", ["1", "true", "yes", "ON"])
def test_el_interruptor_se_enciende_con_valores_explicitos(load_settings, valor):
    assert load_settings(RATE_LIMIT_ENABLED=valor).RATE_LIMIT_ENABLED is True


def test_un_valor_ambiguo_del_interruptor_aborta_el_arranque(load_settings):
    with pytest.raises(ValueError, match="RATE_LIMIT_ENABLED"):
        load_settings(RATE_LIMIT_ENABLED="quizas")


def test_un_entero_invalido_aborta_el_arranque_con_el_nombre_de_la_variable(
    load_settings,
):
    with pytest.raises(ValueError, match="RATE_LIMIT_LOGIN_MAX debe ser un entero"):
        load_settings(RATE_LIMIT_LOGIN_MAX="muchas")


@pytest.mark.parametrize(
    "nombre", [n for n in VARIABLES if n not in ("RATE_LIMIT_ENABLED",)]
)
def test_los_negativos_se_rechazan(load_settings, nombre):
    with pytest.raises(ValueError, match=nombre):
        load_settings(**{nombre: "-1"})


def test_un_maximo_o_ventana_en_cero_se_rechaza_pero_cero_proxies_se_admite(
    load_settings,
):
    with pytest.raises(ValueError, match="RATE_LIMIT_GLOBAL_WINDOW"):
        load_settings(RATE_LIMIT_GLOBAL_WINDOW="0")

    assert load_settings(TRUSTED_PROXY_HOPS="0").TRUSTED_PROXY_HOPS == 0

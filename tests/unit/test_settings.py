"""Tests de la configuración leída del entorno (RNF-02.1, DT-01 y DT-02).

`settings` resuelve sus valores en el cuerpo del módulo, así que cada caso
prepara el entorno y **recarga** el módulo con importlib. Se restaura al
final para no contaminar al resto de la suite.

`load_dotenv` se neutraliza en todos los casos: si no, un `.env` presente en
la máquina de quien ejecuta los tests cambiaría el resultado y la suite
dejaría de ser reproducible.

El parcheo se hace sobre `dotenv.load_dotenv`, el módulo de origen, y **no**
sobre `settings.load_dotenv`: al recargar, `settings` vuelve a ejecutar
`from dotenv import load_dotenv` y recuperaría la función real, deshaciendo un
parcheo hecho sobre su propio espacio de nombres.
"""

import importlib

import dotenv
import pytest

from orderhub import settings as settings_module

VARIABLES = (
    "APP_ENV",
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "JWT_EXPIRATION_MINUTES",
    "FLASK_SECRET_KEY",
    "DATABASE_PATH",
)


@pytest.fixture
def load_settings(monkeypatch):
    """Recarga `settings` con el entorno que indique el test."""

    def _load(**entorno):
        for variable in VARIABLES:
            monkeypatch.delenv(variable, raising=False)
        for nombre, valor in entorno.items():
            monkeypatch.setenv(nombre, valor)
        monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
        return importlib.reload(settings_module)

    yield _load

    # Se deshace el parcheo ANTES de recargar: si no, la última recarga vería
    # todavía el entorno del test y podría volver a fallar.
    monkeypatch.undo()
    importlib.reload(settings_module)


def test_en_desarrollo_arranca_sin_configuracion(load_settings):
    settings = load_settings()

    assert settings.APP_ENV == "development"
    assert settings.JWT_SECRET_KEY == settings.DEV_FALLBACK_JWT_SECRET
    assert settings.FLASK_SECRET_KEY == settings.DEV_FALLBACK_FLASK_SECRET


def test_las_variables_del_entorno_ganan_sobre_los_respaldos(load_settings):
    settings = load_settings(
        JWT_SECRET_KEY="secreto-jwt-real",
        FLASK_SECRET_KEY="secreto-flask-real",
    )

    assert settings.JWT_SECRET_KEY == "secreto-jwt-real"
    assert settings.FLASK_SECRET_KEY == "secreto-flask-real"


@pytest.mark.parametrize("entorno", ["production", "staging"])
@pytest.mark.parametrize("faltante", ["JWT_SECRET_KEY", "FLASK_SECRET_KEY"])
def test_fuera_de_desarrollo_falta_un_secreto_es_error_fatal(
    load_settings, entorno, faltante
):
    """DT-02: el fallo debe ser ruidoso al arrancar, nunca silencioso."""
    presentes = {
        nombre: "valor-configurado"
        for nombre in ("JWT_SECRET_KEY", "FLASK_SECRET_KEY")
        if nombre != faltante
    }

    # Se espera RuntimeError y no `settings_module.MissingConfigurationError`
    # a propósito: cada importlib.reload() crea una clase nueva, así que la
    # referencia leída antes de recargar ya no sería la que se lanza.
    with pytest.raises(RuntimeError) as excinfo:
        load_settings(APP_ENV=entorno, **presentes)

    assert type(excinfo.value).__name__ == "MissingConfigurationError"
    assert excinfo.value.name == faltante
    assert faltante in str(excinfo.value)
    assert entorno in str(excinfo.value)


def test_fuera_de_desarrollo_con_todo_configurado_arranca(load_settings):
    settings = load_settings(
        APP_ENV="production",
        JWT_SECRET_KEY="secreto-jwt-real",
        FLASK_SECRET_KEY="secreto-flask-real",
    )

    assert settings.APP_ENV == "production"
    assert settings.JWT_SECRET_KEY == "secreto-jwt-real"


def test_un_secreto_vacio_cuenta_como_ausente(load_settings):
    """`.env.example` deja las claves vacías: eso no es una configuración."""
    with pytest.raises(RuntimeError) as excinfo:
        load_settings(
            APP_ENV="production",
            JWT_SECRET_KEY="",
            FLASK_SECRET_KEY="secreto-flask-real",
        )

    assert type(excinfo.value).__name__ == "MissingConfigurationError"


def test_en_desarrollo_un_secreto_vacio_cae_al_respaldo(load_settings):
    settings = load_settings(JWT_SECRET_KEY="")

    assert settings.JWT_SECRET_KEY == settings.DEV_FALLBACK_JWT_SECRET


def test_los_valores_no_secretos_tienen_defecto_y_son_configurables(load_settings):
    por_defecto = load_settings()

    assert por_defecto.JWT_ALGORITHM == "HS256"
    assert por_defecto.JWT_EXPIRATION_MINUTES == 60
    assert por_defecto.DATABASE_PATH == "orderhub.db"

    configurado = load_settings(
        JWT_ALGORITHM="HS512",
        JWT_EXPIRATION_MINUTES="15",
        DATABASE_PATH="/tmp/otra.db",
    )

    assert configurado.JWT_ALGORITHM == "HS512"
    assert configurado.JWT_EXPIRATION_MINUTES == 15
    assert configurado.DATABASE_PATH == "/tmp/otra.db"


def test_los_dos_respaldos_de_desarrollo_son_distintos(load_settings):
    """Reutilizar la misma clave para Flask y para los JWT sería un error."""
    settings = load_settings()

    assert settings.DEV_FALLBACK_JWT_SECRET != settings.DEV_FALLBACK_FLASK_SECRET

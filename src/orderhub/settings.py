"""Configuración de infraestructura leída del entorno (RNF-02.1).

Vive junto al Composition Root porque es él quien decide con qué valores se
construyen los adaptadores. Ni el dominio ni la capa de aplicación importan
este módulo.

Este módulo es la **única** fuente de configuración del proyecto. El antiguo
`config.py` de la raíz, que declaraba secretos como literales, fue eliminado
al resolverse DT-01: no existe ningún otro sitio donde leer configuración.

Cero secretos literales: todo valor sensible se lee del entorno, que se puede
poblar con un archivo `.env` local (ver `.env.example`). `.env` está excluido
del control de versiones.
"""

import os

from dotenv import load_dotenv

# Carga el .env de la raíz del proyecto si existe. `override=False` (defecto)
# hace que las variables ya presentes en el entorno real ganen sobre el
# fichero: en producción manda el entorno del contenedor, no un .env olvidado.
load_dotenv()

# Entorno de ejecución. Es lo que distingue "estoy en local sin configurar"
# de "me desplegaron sin configurar" (DT-02).
DEVELOPMENT = "development"
APP_ENV = os.environ.get("APP_ENV", DEVELOPMENT)


class MissingConfigurationError(RuntimeError):
    """Falta una variable de entorno obligatoria fuera de desarrollo."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"La variable de entorno {name} es obligatoria cuando "
            f"APP_ENV != '{DEVELOPMENT}' (APP_ENV actual: '{APP_ENV}'). "
            "Defínela en el entorno o en un archivo .env; ver .env.example."
        )
        self.name = name


def _required_secret(name: str, development_fallback: str) -> str:
    """Lee un secreto del entorno.

    En desarrollo cae a un valor de respaldo para que el proyecto arranque sin
    configuración previa. En cualquier otro entorno su ausencia es un error
    fatal al arrancar, y no un fallo silencioso que dejaría el sistema firmando
    tokens con una clave pública (DT-02).
    """
    value = os.environ.get(name)
    if value:
        return value
    if APP_ENV == DEVELOPMENT:
        return development_fallback
    raise MissingConfigurationError(name)


# Respaldos de desarrollo. No son secretos de producción: son valores
# deliberadamente marcados como inseguros que solo se usan con
# APP_ENV=development.
DEV_FALLBACK_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"
DEV_FALLBACK_FLASK_SECRET = "dev-only-insecure-flask-secret-change-me"

# Clave de firma de los JWT (HS256).
JWT_SECRET_KEY = _required_secret("JWT_SECRET_KEY", DEV_FALLBACK_JWT_SECRET)

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# Tiempo de vida del token en minutos. Configurable por entorno para no dejar
# un número mágico repartido por el código.
DEFAULT_JWT_EXPIRATION_MINUTES = 60

JWT_EXPIRATION_MINUTES = int(
    os.environ.get("JWT_EXPIRATION_MINUTES", DEFAULT_JWT_EXPIRATION_MINUTES)
)

# Clave de sesión de Flask. Antes vivía hardcodeada en config.py (DT-01).
FLASK_SECRET_KEY = _required_secret("FLASK_SECRET_KEY", DEV_FALLBACK_FLASK_SECRET)

# Ruta del fichero SQLite. No es un secreto, pero sí configuración de
# despliegue: antes estaba cableada en app.py.
DEFAULT_DATABASE_PATH = "orderhub.db"

DATABASE_PATH = os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH)

"""Configuración de infraestructura leída del entorno.

Vive junto al Composition Root porque es él quien decide con qué valores se
construyen los adaptadores. Ni el dominio ni la capa de aplicación importan
este módulo.

Nota: config.py (raíz del proyecto legado) tiene secretos hardcodeados; eso es
deuda técnica conocida y no se replica aquí.
"""

import os

# Clave de firma de los JWT. En desarrollo cae a un valor por defecto para que
# el proyecto arranque sin configuración; en despliegue real debe venir del
# entorno.
DEFAULT_DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", DEFAULT_DEV_JWT_SECRET)

JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# Tiempo de vida del token en minutos. Configurable por entorno para no dejar
# un número mágico repartido por el código.
DEFAULT_JWT_EXPIRATION_MINUTES = 60

JWT_EXPIRATION_MINUTES = int(
    os.environ.get("JWT_EXPIRATION_MINUTES", DEFAULT_JWT_EXPIRATION_MINUTES)
)

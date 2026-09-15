"""Fixtures compartidas por los tests unitarios y los de integración.

Se exponen como fixtures (y no como constantes importables) porque pytest las
hereda automáticamente en los subdirectorios, sin tocar sys.path ni convertir
tests/ en un paquete.

Aquí solo vive lo común a ambas suites: las identidades de prueba y el helper
de cabecera Bearer. Los dobles en memoria son propios de la suite unitaria y
la infraestructura real, de la de integración.
"""

import pytest

from orderhub.domain.entities.user import User

# HS256 pide al menos 32 bytes de clave (RFC 7518); por debajo PyJWT avisa.
JWT_TEST_SECRET = "secreto-de-pruebas-con-32-bytes-o-mas"

ADMIN_PASSWORD = "admin123"
CLIENT_PASSWORD = "123456"


@pytest.fixture
def jwt_test_secret() -> str:
    return JWT_TEST_SECRET


@pytest.fixture
def admin_user() -> User:
    return User(id=1, username="admin", password_hash="irrelevante", role="admin")


@pytest.fixture
def client_user() -> User:
    return User(id=2, username="juan", password_hash="irrelevante", role="client")


@pytest.fixture
def bearer():
    """Devuelve un helper que construye la cabecera Authorization."""

    def _bearer(token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    return _bearer

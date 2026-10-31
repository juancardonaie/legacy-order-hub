import re
from dataclasses import dataclass
from typing import Optional

from orderhub.domain.exceptions import (
    InvalidPasswordError,
    InvalidRoleError,
    InvalidUsernameError,
)

ROLE_ADMIN = "admin"
ROLE_CLIENT = "client"
VALID_ROLES = frozenset({ROLE_ADMIN, ROLE_CLIENT})

# Sin normalizar: las mayúsculas se rechazan en vez de pasarse a minúsculas.
_USERNAME_PATTERN = re.compile(r"[a-z0-9._-]{3,32}")

MIN_PASSWORD_LENGTH = 8
# Límite de bcrypt, el algoritmo de hashing actual: más allá de 72 bytes la
# librería rechaza la entrada. Se valida aquí para devolver un error de
# negocio claro antes de llegar al adaptador.
MAX_PASSWORD_BYTES = 72


def validate_username(username: object) -> None:
    if not isinstance(username, str) or not _USERNAME_PATTERN.fullmatch(username):
        raise InvalidUsernameError(username)


def validate_role(role: object) -> None:
    if not isinstance(role, str) or role not in VALID_ROLES:
        raise InvalidRoleError(role)


def validate_password(password: object) -> None:
    """Política de contraseña: 8 caracteres como mínimo y 72 bytes UTF-8 como
    máximo. Los errores no incluyen la contraseña recibida."""
    if not isinstance(password, str):
        raise InvalidPasswordError("La contraseña debe ser un texto")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise InvalidPasswordError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
        )
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise InvalidPasswordError(
            f"La contraseña no puede superar {MAX_PASSWORD_BYTES} bytes"
        )


@dataclass
class User:
    """Usuario del sistema. La verificación de contraseña es responsabilidad
    del adaptador de hashing (PasswordHasher), no de esta entidad."""

    id: Optional[int]
    username: str
    password_hash: str
    role: str

    @classmethod
    def create(cls, username: str, password_hash: str, role: str) -> "User":
        """Crea un usuario nuevo validando username y rol.

        Recibe el hash y nunca la contraseña en claro: la política de
        contraseña (`validate_password`) se aplica antes de hashear.
        """
        validate_username(username)
        validate_role(role)
        return cls(id=None, username=username, password_hash=password_hash, role=role)

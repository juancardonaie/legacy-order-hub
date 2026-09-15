from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """Usuario del sistema. La verificación de contraseña es responsabilidad
    del adaptador de hashing (PasswordHasher), no de esta entidad."""

    id: Optional[int]
    username: str
    password_hash: str
    role: str

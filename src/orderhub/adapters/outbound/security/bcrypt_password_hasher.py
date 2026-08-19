import bcrypt

from orderhub.application.ports.password_hasher import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    """Implementación del puerto de hashing usando bcrypt."""

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

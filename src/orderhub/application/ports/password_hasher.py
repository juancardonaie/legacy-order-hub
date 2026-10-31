from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    """Puerto de salida hacia el algoritmo de hashing de contraseñas."""

    @abstractmethod
    def verify(self, plain_password: str, password_hash: str) -> bool:
        """Indica si la contraseña en texto plano corresponde al hash dado."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Devuelve el hash de la contraseña en texto plano."""

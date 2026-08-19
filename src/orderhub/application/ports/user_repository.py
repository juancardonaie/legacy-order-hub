from abc import ABC, abstractmethod
from typing import Optional

from orderhub.domain.entities.user import User


class UserRepository(ABC):
    """Puerto de salida hacia el almacenamiento de usuarios."""

    @abstractmethod
    def find_by_username(self, username: str) -> Optional[User]:
        """Devuelve el usuario o None si no existe."""

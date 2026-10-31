from abc import ABC, abstractmethod
from typing import Optional

from orderhub.domain.entities.user import User


class UserRepository(ABC):
    """Puerto de salida hacia el almacenamiento de usuarios."""

    @abstractmethod
    def find_by_username(self, username: str) -> Optional[User]:
        """Devuelve el usuario o None si no existe."""

    @abstractmethod
    def add(self, user: User) -> User:
        """Persiste un usuario nuevo y lo devuelve con su id asignado.

        Lanza UsernameAlreadyExistsError si el username ya está en uso, también
        cuando dos altas coinciden a la vez: la unicidad la garantiza el
        almacenamiento, no una consulta previa.
        """

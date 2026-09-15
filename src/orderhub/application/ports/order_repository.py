from abc import ABC, abstractmethod
from typing import List

from orderhub.domain.entities.order import Order


class OrderRepository(ABC):
    """Puerto de salida hacia el almacenamiento de órdenes."""

    @abstractmethod
    def save(self, order: Order) -> Order:
        """Persiste la orden y devuelve la entidad con su id asignado."""

    @abstractmethod
    def find_all(self) -> List[Order]:
        """Devuelve todas las órdenes registradas."""

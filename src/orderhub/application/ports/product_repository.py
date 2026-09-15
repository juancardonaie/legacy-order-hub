from abc import ABC, abstractmethod
from typing import List, Optional

from orderhub.domain.entities.product import Product


class ProductRepository(ABC):
    """Puerto de salida hacia el almacenamiento de productos.

    Lo define la capa de aplicación y lo implementa la de adaptadores: así el
    caso de uso depende de esta abstracción y nunca de SQLite.
    """

    @abstractmethod
    def find_by_id(self, product_id: int) -> Optional[Product]:
        """Devuelve el producto o None si no existe."""

    @abstractmethod
    def find_all(self) -> List[Product]:
        """Devuelve todos los productos del catálogo (RF-02.1)."""

    @abstractmethod
    def update_stock(self, product: Product) -> None:
        """Persiste el stock actual de la entidad."""

    @abstractmethod
    def save(self, product: Product) -> Product:
        """Persiste un producto nuevo y lo devuelve con su id asignado."""

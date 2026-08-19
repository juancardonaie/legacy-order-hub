from dataclasses import dataclass
from typing import Optional

from orderhub.domain.exceptions import InsufficientStockError, InvalidQuantityError


@dataclass
class Product:
    """Producto del catálogo. Concentra las reglas de disponibilidad de stock."""

    id: Optional[int]
    name: str
    price: float
    stock: int

    def has_stock_for(self, quantity: int) -> bool:
        return self.stock >= quantity

    def decrease_stock(self, quantity: int) -> None:
        """Descuenta unidades del stock validando las reglas de negocio."""
        if quantity <= 0:
            raise InvalidQuantityError(quantity)
        if not self.has_stock_for(quantity):
            raise InsufficientStockError(self.id, quantity, self.stock)
        self.stock -= quantity

    def price_for(self, quantity: int) -> float:
        if quantity <= 0:
            raise InvalidQuantityError(quantity)
        return self.price * quantity

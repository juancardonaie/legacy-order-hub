from dataclasses import dataclass
from typing import Optional

from orderhub.domain.exceptions import (
    InsufficientStockError,
    InvalidProductNameError,
    InvalidProductPriceError,
    InvalidQuantityError,
    InvalidStockError,
)


@dataclass
class Product:
    """Producto del catálogo. Concentra las reglas de disponibilidad de stock."""

    id: Optional[int]
    name: str
    price: float
    stock: int

    @classmethod
    def create(cls, name: str, price: float, stock: int = 0) -> "Product":
        """Crea un producto nuevo validando sus invariantes.

        Las reglas viven aquí y no en el controller: un producto sin nombre o
        con precio no positivo es inválido venga de HTTP, de un script o de una
        importación masiva. Mismo criterio que Order.create().
        """
        if not isinstance(name, str) or not name.strip():
            raise InvalidProductNameError(name)
        if price is None or price <= 0:
            raise InvalidProductPriceError(price)
        if stock < 0:
            raise InvalidStockError(stock)

        return cls(id=None, name=name.strip(), price=price, stock=stock)

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

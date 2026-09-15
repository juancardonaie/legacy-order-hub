from dataclasses import dataclass
from typing import Optional

from orderhub.domain.entities.product import Product
from orderhub.domain.exceptions import InvalidQuantityError

STATUS_PENDING = "PENDING"


@dataclass
class Order:
    """Orden de compra. El total es una regla del dominio, no del handler HTTP."""

    id: Optional[int]
    user_id: int
    product_id: int
    quantity: int
    total: float
    status: str

    @classmethod
    def create(cls, user_id: int, product: Product, quantity: int) -> "Order":
        """Crea una orden pendiente calculando el total a partir del producto."""
        if quantity <= 0:
            raise InvalidQuantityError(quantity)
        return cls(
            id=None,
            user_id=user_id,
            product_id=product.id,
            quantity=quantity,
            total=product.price_for(quantity),
            status=STATUS_PENDING,
        )

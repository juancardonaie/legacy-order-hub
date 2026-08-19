from orderhub.application.ports.order_repository import OrderRepository
from orderhub.application.ports.product_repository import ProductRepository
from orderhub.domain.entities.order import Order
from orderhub.domain.exceptions import InsufficientStockError, ProductNotFoundError


class CreateOrder:
    """Caso de uso: registrar una orden y descontar el stock del producto.

    Orquesta dominio y puertos. No contiene SQL ni conoce Flask.
    """

    def __init__(
        self,
        product_repository: ProductRepository,
        order_repository: OrderRepository,
    ) -> None:
        self._product_repository = product_repository
        self._order_repository = order_repository

    def execute(self, user_id: int, product_id: int, quantity: int) -> Order:
        product = self._product_repository.find_by_id(product_id)
        if product is None:
            raise ProductNotFoundError(product_id)

        if not product.has_stock_for(quantity):
            raise InsufficientStockError(product_id, quantity, product.stock)

        order = Order.create(user_id=user_id, product=product, quantity=quantity)
        saved_order = self._order_repository.save(order)

        product.decrease_stock(quantity)
        self._product_repository.update_stock(product)

        return saved_order

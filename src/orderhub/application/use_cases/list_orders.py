from typing import List

from orderhub.application.ports.order_repository import OrderRepository
from orderhub.domain.entities.order import Order


class ListOrders:
    """Caso de uso: consultar todas las órdenes registradas."""

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self) -> List[Order]:
        return self._order_repository.find_all()

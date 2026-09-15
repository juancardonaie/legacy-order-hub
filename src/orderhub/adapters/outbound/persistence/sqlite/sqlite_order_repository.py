import sqlite3
from dataclasses import replace
from typing import Callable, List

from orderhub.application.ports.order_repository import OrderRepository
from orderhub.domain.entities.order import Order


class SQLiteOrderRepository(OrderRepository):
    """Implementación del puerto de órdenes sobre SQLite."""

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def save(self, order: Order) -> Order:
        connection = self._connection_factory()
        try:
            cursor = connection.execute(
                "INSERT INTO orders (user_id, product_id, quantity, total, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    order.user_id,
                    order.product_id,
                    order.quantity,
                    order.total,
                    order.status,
                ),
            )
            connection.commit()
            return replace(order, id=cursor.lastrowid)
        finally:
            connection.close()

    def find_all(self) -> List[Order]:
        connection = self._connection_factory()
        try:
            rows = connection.execute(
                "SELECT id, user_id, product_id, quantity, total, status FROM orders"
            ).fetchall()
        finally:
            connection.close()

        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(row: sqlite3.Row) -> Order:
        return Order(
            id=row["id"],
            user_id=row["user_id"],
            product_id=row["product_id"],
            quantity=row["quantity"],
            total=row["total"],
            status=row["status"],
        )

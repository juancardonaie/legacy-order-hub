import sqlite3
from typing import Callable, Optional

from orderhub.application.ports.product_repository import ProductRepository
from orderhub.domain.entities.product import Product


class SQLiteProductRepository(ProductRepository):
    """Implementación del puerto de productos sobre SQLite.

    Todas las consultas son parametrizadas (RNF-02.2).
    """

    def __init__(self, connection_factory: Callable[[], sqlite3.Connection]) -> None:
        self._connection_factory = connection_factory

    def find_by_id(self, product_id: int) -> Optional[Product]:
        connection = self._connection_factory()
        try:
            row = connection.execute(
                "SELECT id, name, price, stock FROM products WHERE id = ?",
                (product_id,),
            ).fetchone()
        finally:
            connection.close()

        return self._to_entity(row) if row is not None else None

    def update_stock(self, product: Product) -> None:
        connection = self._connection_factory()
        try:
            connection.execute(
                "UPDATE products SET stock = ? WHERE id = ?",
                (product.stock, product.id),
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _to_entity(row: sqlite3.Row) -> Product:
        return Product(
            id=row["id"],
            name=row["name"],
            price=row["price"],
            stock=row["stock"],
        )

"""Tests unitarios de CreateOrder.

No se importa Flask ni sqlite3: los puertos se sustituyen por dobles en
memoria, lo que demuestra que el caso de uso está desacoplado de la
infraestructura.
"""

from dataclasses import replace
from typing import Dict, List, Optional

import pytest

from orderhub.application.ports.order_repository import OrderRepository
from orderhub.application.ports.product_repository import ProductRepository
from orderhub.application.use_cases.create_order import CreateOrder
from orderhub.domain.entities.order import STATUS_PENDING, Order
from orderhub.domain.entities.product import Product
from orderhub.domain.exceptions import InsufficientStockError, ProductNotFoundError


class InMemoryProductRepository(ProductRepository):
    def __init__(self, products: Optional[List[Product]] = None) -> None:
        self._products: Dict[int, Product] = {p.id: p for p in (products or [])}

    def find_by_id(self, product_id: int) -> Optional[Product]:
        return self._products.get(product_id)

    def update_stock(self, product: Product) -> None:
        self._products[product.id] = product


class InMemoryOrderRepository(OrderRepository):
    def __init__(self) -> None:
        self.orders: List[Order] = []
        self._next_id = 1

    def save(self, order: Order) -> Order:
        saved = replace(order, id=self._next_id)
        self._next_id += 1
        self.orders.append(saved)
        return saved

    def find_all(self) -> List[Order]:
        return list(self.orders)


@pytest.fixture
def product() -> Product:
    return Product(id=1, name="Laptop Legada", price=1200.0, stock=5)


@pytest.fixture
def product_repository(product: Product) -> InMemoryProductRepository:
    return InMemoryProductRepository([product])


@pytest.fixture
def order_repository() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()


@pytest.fixture
def create_order(product_repository, order_repository) -> CreateOrder:
    return CreateOrder(
        product_repository=product_repository,
        order_repository=order_repository,
    )


def test_crea_la_orden_y_la_persiste(create_order, order_repository):
    order = create_order.execute(user_id=7, product_id=1, quantity=2)

    assert order.id == 1
    assert order.user_id == 7
    assert order.product_id == 1
    assert order.quantity == 2
    assert order_repository.orders == [order]


def test_rechaza_la_orden_si_el_producto_no_existe(create_order, order_repository):
    with pytest.raises(ProductNotFoundError):
        create_order.execute(user_id=7, product_id=999, quantity=1)

    assert order_repository.orders == []


def test_rechaza_la_orden_si_el_stock_es_insuficiente(
    create_order, order_repository, product
):
    with pytest.raises(InsufficientStockError):
        create_order.execute(user_id=7, product_id=1, quantity=6)

    assert order_repository.orders == []
    assert product.stock == 5


def test_descuenta_el_stock_del_producto(create_order, product_repository):
    create_order.execute(user_id=7, product_id=1, quantity=3)

    assert product_repository.find_by_id(1).stock == 2


def test_calcula_el_total_de_la_orden(create_order):
    order = create_order.execute(user_id=7, product_id=1, quantity=3)

    assert order.total == 3600.0


def test_la_orden_nace_en_estado_pending(create_order):
    order = create_order.execute(user_id=7, product_id=1, quantity=1)

    assert order.status == STATUS_PENDING
    assert order.status == "PENDING"

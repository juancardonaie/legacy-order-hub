"""Integración de SQLiteOrderRepository contra una BD SQLite real."""

import pytest

from orderhub.adapters.outbound.persistence.sqlite.connection import (
    SQLiteConnectionFactory,
)
from orderhub.adapters.outbound.persistence.sqlite.sqlite_order_repository import (
    SQLiteOrderRepository,
)
from orderhub.domain.entities.order import STATUS_PENDING, Order
from orderhub.domain.entities.product import Product

PRODUCTO = Product(id=1, name="Laptop Legada", price=1200.00, stock=5)


@pytest.fixture
def repository(database_path) -> SQLiteOrderRepository:
    return SQLiteOrderRepository(SQLiteConnectionFactory(database_path))


def test_una_bd_recien_sembrada_no_tiene_ordenes(repository):
    assert repository.find_all() == []


def test_guarda_una_orden_y_le_asigna_id(repository):
    order = Order.create(user_id=2, product=PRODUCTO, quantity=2)
    assert order.id is None

    saved = repository.save(order)

    assert saved.id == 1
    assert saved.user_id == 2
    assert saved.total == 2400.00


def test_find_all_devuelve_la_orden_guardada_con_todos_sus_campos(repository):
    saved = repository.save(Order.create(user_id=2, product=PRODUCTO, quantity=3))

    recuperadas = repository.find_all()

    assert recuperadas == [saved]
    assert recuperadas[0].status == STATUS_PENDING
    assert recuperadas[0].quantity == 3
    assert recuperadas[0].total == 3600.00


def test_guarda_varias_ordenes_con_ids_correlativos(repository):
    primera = repository.save(Order.create(user_id=1, product=PRODUCTO, quantity=1))
    segunda = repository.save(Order.create(user_id=2, product=PRODUCTO, quantity=2))

    assert [primera.id, segunda.id] == [1, 2]
    assert len(repository.find_all()) == 2


def test_el_total_conserva_los_decimales_al_ir_y_volver_de_sqlite(repository):
    barato = Product(id=2, name="Mouse USB", price=15.50, stock=50)

    saved = repository.save(Order.create(user_id=1, product=barato, quantity=3))

    assert repository.find_all()[0].total == saved.total == 46.50


def test_el_estado_de_la_bd_no_se_filtra_entre_tests(repository):
    """Si otro test hubiera contaminado la BD, aquí habría órdenes."""
    assert repository.find_all() == []

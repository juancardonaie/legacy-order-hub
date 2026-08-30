"""Integración de SQLiteProductRepository contra una BD SQLite real."""

import pytest

from orderhub.adapters.outbound.persistence.sqlite.connection import (
    SQLiteConnectionFactory,
)
from orderhub.adapters.outbound.persistence.sqlite.sqlite_product_repository import (
    SQLiteProductRepository,
)
from orderhub.domain.entities.product import Product


@pytest.fixture
def repository(database_path) -> SQLiteProductRepository:
    return SQLiteProductRepository(SQLiteConnectionFactory(database_path))


def test_recupera_un_producto_sembrado_con_todos_sus_campos(repository):
    product = repository.find_by_id(1)

    assert product == Product(id=1, name="Laptop Legada", price=1200.00, stock=5)


def test_un_producto_inexistente_devuelve_none(repository):
    assert repository.find_by_id(9999) is None


def test_guarda_un_producto_y_lo_recupera_igual(repository):
    saved = repository.save(Product.create(name="Teclado", price=99.99, stock=7))

    assert saved.id is not None
    recuperado = repository.find_by_id(saved.id)
    assert recuperado == saved
    assert recuperado.price == 99.99
    assert recuperado.stock == 7


def test_cada_producto_guardado_recibe_un_id_distinto(repository):
    primero = repository.save(Product.create(name="Uno", price=1.0))
    segundo = repository.save(Product.create(name="Dos", price=2.0))

    assert primero.id != segundo.id
    assert repository.find_by_id(primero.id).name == "Uno"
    assert repository.find_by_id(segundo.id).name == "Dos"


def test_update_stock_persiste_el_nuevo_stock(repository):
    product = repository.find_by_id(1)
    product.decrease_stock(2)

    repository.update_stock(product)

    assert repository.find_by_id(1).stock == 3


def test_el_sql_parametrizado_acepta_comillas_simples_en_el_nombre(repository):
    """Con concatenación de strings esto rompería la consulta o inyectaría."""
    nombre = "Teclado 'Pro' de O'Brien; DROP TABLE products;--"

    saved = repository.save(Product.create(name=nombre, price=10.0))

    assert repository.find_by_id(saved.id).name == nombre
    # La tabla sigue viva y el producto sembrado sigue ahí.
    assert repository.find_by_id(1) is not None


def test_los_cambios_de_un_test_no_se_ven_en_otro(repository):
    """La BD se recrea por test: solo están los 2 productos sembrados."""
    assert repository.find_by_id(3) is None

"""Reglas de negocio de la entidad Product.

Caminos de error del dominio puro: sin Flask, sin sqlite3, sin bcrypt.
"""

import pytest

from orderhub.domain.entities.order import Order
from orderhub.domain.entities.product import Product
from orderhub.domain.exceptions import (
    InsufficientStockError,
    InvalidQuantityError,
)


@pytest.fixture
def product() -> Product:
    return Product(id=1, name="Laptop", price=100.0, stock=5)


@pytest.mark.parametrize("quantity", [0, -1, -10])
def test_no_se_puede_descontar_una_cantidad_no_positiva(product, quantity):
    with pytest.raises(InvalidQuantityError) as error:
        product.decrease_stock(quantity)

    assert error.value.quantity == quantity
    assert product.stock == 5  # el stock queda intacto


def test_no_se_puede_descontar_mas_stock_del_disponible(product):
    with pytest.raises(InsufficientStockError) as error:
        product.decrease_stock(6)

    assert error.value.requested == 6
    assert error.value.available == 5
    assert product.stock == 5


def test_descontar_exactamente_todo_el_stock_es_valido(product):
    product.decrease_stock(5)

    assert product.stock == 0
    assert product.has_stock_for(1) is False


@pytest.mark.parametrize("quantity", [0, -3])
def test_no_se_puede_calcular_el_precio_de_una_cantidad_no_positiva(product, quantity):
    with pytest.raises(InvalidQuantityError):
        product.price_for(quantity)


def test_el_precio_se_calcula_por_unidades(product):
    assert product.price_for(3) == 300.0


@pytest.mark.parametrize("quantity", [0, -1])
def test_no_se_puede_crear_una_orden_con_cantidad_no_positiva(product, quantity):
    with pytest.raises(InvalidQuantityError) as error:
        Order.create(user_id=1, product=product, quantity=quantity)

    assert error.value.quantity == quantity

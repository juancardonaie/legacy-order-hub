"""Tests unitarios de CreateProduct.

Repositorio en memoria: ni sqlite3 ni Flask. Comprueban que el caso de uso
delega las reglas de negocio en el dominio y persiste por el puerto.
"""

from dataclasses import replace
from typing import Dict, Optional

import pytest

from orderhub.application.ports.product_repository import ProductRepository
from orderhub.application.use_cases.create_product import CreateProduct
from orderhub.domain.entities.product import Product
from orderhub.domain.exceptions import (
    InvalidProductNameError,
    InvalidProductPriceError,
    InvalidStockError,
)


class InMemoryProductRepository(ProductRepository):
    def __init__(self) -> None:
        self.products: Dict[int, Product] = {}
        self._next_id = 1

    def find_by_id(self, product_id: int) -> Optional[Product]:
        return self.products.get(product_id)

    def update_stock(self, product: Product) -> None:
        self.products[product.id] = product

    def save(self, product: Product) -> Product:
        saved = replace(product, id=self._next_id)
        self.products[self._next_id] = saved
        self._next_id += 1
        return saved


@pytest.fixture
def product_repository() -> InMemoryProductRepository:
    return InMemoryProductRepository()


@pytest.fixture
def create_product(product_repository) -> CreateProduct:
    return CreateProduct(product_repository=product_repository)


def test_crea_el_producto_y_lo_persiste(create_product, product_repository):
    product = create_product.execute(name="Teclado", price=99.5, stock=10)

    assert product.id == 1
    assert product.name == "Teclado"
    assert product.price == 99.5
    assert product.stock == 10
    assert product_repository.products[1] == product


def test_el_stock_por_defecto_es_cero(create_product):
    assert create_product.execute(name="Monitor", price=250.0).stock == 0


def test_normaliza_los_espacios_del_nombre(create_product):
    assert create_product.execute(name="  Mouse  ", price=20.0).name == "Mouse"


@pytest.mark.parametrize("name", ["", "   ", None])
def test_rechaza_un_nombre_vacio(create_product, product_repository, name):
    with pytest.raises(InvalidProductNameError):
        create_product.execute(name=name, price=10.0)

    assert product_repository.products == {}


@pytest.mark.parametrize("price", [0, -1, -99.9])
def test_rechaza_un_precio_no_positivo(create_product, product_repository, price):
    with pytest.raises(InvalidProductPriceError):
        create_product.execute(name="Teclado", price=price)

    assert product_repository.products == {}


def test_rechaza_un_stock_negativo(create_product, product_repository):
    with pytest.raises(InvalidStockError):
        create_product.execute(name="Teclado", price=10.0, stock=-1)

    assert product_repository.products == {}

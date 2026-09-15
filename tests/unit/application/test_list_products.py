"""Tests unitarios de ListProducts (RF-02.1).

Repositorio en memoria: ni sqlite3 ni Flask. Comprueban que el caso de uso
delega en el puerto y devuelve entidades de dominio, no diccionarios.
"""

from dataclasses import replace
from typing import Dict, List, Optional

import pytest

from orderhub.application.ports.product_repository import ProductRepository
from orderhub.application.use_cases.list_products import ListProducts
from orderhub.domain.entities.product import Product


class InMemoryProductRepository(ProductRepository):
    def __init__(self, products: Optional[List[Product]] = None) -> None:
        self.products: Dict[int, Product] = {p.id: p for p in (products or [])}

    def find_by_id(self, product_id: int) -> Optional[Product]:
        return self.products.get(product_id)

    def find_all(self) -> List[Product]:
        return [self.products[key] for key in sorted(self.products)]

    def update_stock(self, product: Product) -> None:
        self.products[product.id] = product

    def save(self, product: Product) -> Product:
        new_id = max(self.products, default=0) + 1
        saved = replace(product, id=new_id)
        self.products[new_id] = saved
        return saved


CATALOGO = [
    Product(id=1, name="Laptop", price=1200.0, stock=5),
    Product(id=2, name="Mouse USB", price=15.5, stock=50),
]


@pytest.fixture
def product_repository() -> InMemoryProductRepository:
    return InMemoryProductRepository(list(CATALOGO))


@pytest.fixture
def list_products(product_repository) -> ListProducts:
    return ListProducts(product_repository=product_repository)


def test_devuelve_el_catalogo_completo(list_products):
    assert list_products.execute() == CATALOGO


def test_cada_producto_lleva_precio_y_stock_actual(list_products):
    laptop, mouse = list_products.execute()

    assert (laptop.price, laptop.stock) == (1200.0, 5)
    assert (mouse.price, mouse.stock) == (15.5, 50)


def test_un_catalogo_vacio_devuelve_una_lista_vacia():
    assert ListProducts(product_repository=InMemoryProductRepository()).execute() == []


def test_devuelve_entidades_de_dominio_no_diccionarios(list_products):
    """La serialización es responsabilidad del adaptador, no del caso de uso."""
    assert all(isinstance(product, Product) for product in list_products.execute())


def test_refleja_el_stock_despues_de_descontarlo(list_products, product_repository):
    """RF-02.1 pide el stock *actual*, no el inicial."""
    laptop = product_repository.find_by_id(1)
    laptop.decrease_stock(2)
    product_repository.update_stock(laptop)

    assert list_products.execute()[0].stock == 3


def test_ve_los_productos_dados_de_alta_despues(list_products, product_repository):
    product_repository.save(Product.create(name="Teclado", price=99.0, stock=7))

    nombres = [product.name for product in list_products.execute()]
    assert "Teclado" in nombres

"""Fixtures de la suite unitaria del adaptador inbound.

Se monta una app Flask real con los blueprints y el decorador de
autenticación reales, pero con repositorios en memoria: no hay servidor ni
base de datos. El TokenServicePort sí es el JWTTokenService real, para que los
tokens de los tests recorran el mismo camino de firma y verificación que en
producción.

Las identidades de prueba (admin_user, client_user) y el helper `bearer`
vienen del conftest superior, compartidos con la suite de integración.
"""

from dataclasses import replace
from typing import Dict, List, Optional

import pytest
from flask import Flask

from orderhub.adapters.inbound.http.jwt_required import create_jwt_required
from orderhub.adapters.inbound.http.order_controller import create_order_blueprint
from orderhub.adapters.inbound.http.product_controller import create_product_blueprint
from orderhub.adapters.outbound.security.jwt_token_service import JWTTokenService
from orderhub.application.ports.order_repository import OrderRepository
from orderhub.application.ports.product_repository import ProductRepository
from orderhub.application.use_cases.create_order import CreateOrder
from orderhub.application.use_cases.create_product import CreateProduct
from orderhub.application.use_cases.list_orders import ListOrders
from orderhub.domain.entities.order import Order
from orderhub.domain.entities.product import Product


class InMemoryProductRepository(ProductRepository):
    def __init__(self, products: Optional[List[Product]] = None) -> None:
        self.products: Dict[int, Product] = {p.id: p for p in (products or [])}

    def find_by_id(self, product_id: int) -> Optional[Product]:
        return self.products.get(product_id)

    def update_stock(self, product: Product) -> None:
        self.products[product.id] = product

    def save(self, product: Product) -> Product:
        new_id = max(self.products, default=0) + 1
        saved = replace(product, id=new_id)
        self.products[new_id] = saved
        return saved


class InMemoryOrderRepository(OrderRepository):
    def __init__(self) -> None:
        self.orders: List[Order] = []

    def save(self, order: Order) -> Order:
        saved = replace(order, id=len(self.orders) + 1)
        self.orders.append(saved)
        return saved

    def find_all(self) -> List[Order]:
        return list(self.orders)


@pytest.fixture
def product_repository() -> InMemoryProductRepository:
    return InMemoryProductRepository(
        [Product(id=1, name="Laptop", price=100.0, stock=5)]
    )


@pytest.fixture
def order_repository() -> InMemoryOrderRepository:
    return InMemoryOrderRepository()


@pytest.fixture
def token_service(jwt_test_secret) -> JWTTokenService:
    return JWTTokenService(secret_key=jwt_test_secret, expiration_minutes=15)


@pytest.fixture
def client(product_repository, order_repository, token_service):
    app = Flask(__name__)
    app.testing = True

    jwt_required = create_jwt_required(token_service)

    app.register_blueprint(
        create_order_blueprint(
            create_order=CreateOrder(
                product_repository=product_repository,
                order_repository=order_repository,
            ),
            list_orders=ListOrders(order_repository=order_repository),
            jwt_required=jwt_required,
        )
    )
    app.register_blueprint(
        create_product_blueprint(
            create_product=CreateProduct(product_repository=product_repository),
            jwt_required=jwt_required,
        )
    )

    return app.test_client()


@pytest.fixture
def admin_headers(token_service, admin_user, bearer):
    return bearer(token_service.generate(admin_user))


@pytest.fixture
def client_headers(token_service, client_user, bearer):
    return bearer(token_service.generate(client_user))

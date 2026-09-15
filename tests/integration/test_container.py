"""Tests del Composition Root.

Verifican que el Container arma el grafo completo de dependencias y que cada
pieza concreta cumple el puerto que la capa de aplicación espera: es la
comprobación de que la inversión de dependencias está bien cableada.
"""

from orderhub.application.ports.order_repository import OrderRepository
from orderhub.application.ports.password_hasher import PasswordHasher
from orderhub.application.ports.product_repository import ProductRepository
from orderhub.application.ports.token_service import TokenServicePort
from orderhub.application.ports.user_repository import UserRepository
from orderhub.application.use_cases.authenticate_user import AuthenticateUser
from orderhub.application.use_cases.create_order import CreateOrder
from orderhub.application.use_cases.create_product import CreateProduct
from orderhub.application.use_cases.list_orders import ListOrders
from orderhub.application.use_cases.list_products import ListProducts
from orderhub.container import Container


def test_los_adaptadores_cumplen_sus_puertos(container):
    assert isinstance(container.product_repository, ProductRepository)
    assert isinstance(container.order_repository, OrderRepository)
    assert isinstance(container.user_repository, UserRepository)
    assert isinstance(container.password_hasher, PasswordHasher)
    assert isinstance(container.token_service, TokenServicePort)


def test_construye_todos_los_casos_de_uso(container):
    assert isinstance(container.create_order, CreateOrder)
    assert isinstance(container.list_orders, ListOrders)
    assert isinstance(container.create_product, CreateProduct)
    assert isinstance(container.authenticate_user, AuthenticateUser)


def test_los_casos_de_uso_funcionan_contra_la_bd_real(container, admin_password):
    """No basta con que se instancien: deben tener las dependencias correctas."""
    user = container.authenticate_user.execute(
        username="admin", password=admin_password
    )

    assert user.username == "admin"
    assert container.list_orders.execute() == []
    assert container.product_repository.find_by_id(1).name == "Laptop Legada"


def test_el_token_del_container_se_verifica_con_su_propio_servicio(
    container, admin_password
):
    user = container.authenticate_user.execute(
        username="admin", password=admin_password
    )

    payload = container.token_service.verify(container.token_service.generate(user))

    assert payload.user_id == user.id
    assert payload.role == "admin"


def test_los_repositorios_comparten_la_misma_base_de_datos(container):
    """product_repository y create_order deben ver el mismo catálogo."""
    creado = container.create_product.execute(name="Compartido", price=5.0, stock=2)

    assert container.product_repository.find_by_id(creado.id).name == "Compartido"


def test_construir_el_container_no_abre_la_base_de_datos(tmp_path):
    """La fábrica de conexiones es perezosa: no toca el fichero al construirse."""
    inexistente = tmp_path / "todavia-no-existe.db"

    Container(database_path=str(inexistente))

    assert not inexistente.exists()


def test_construye_el_caso_de_uso_de_catalogo(container):
    assert isinstance(container.list_products, ListProducts)


def test_list_products_lee_el_catalogo_real(container):
    assert [p.name for p in container.list_products.execute()] == [
        "Laptop Legada",
        "Mouse USB",
    ]


def test_list_products_y_create_product_comparten_repositorio(container):
    container.create_product.execute(name="Webcam", price=45.0, stock=3)

    assert "Webcam" in [p.name for p in container.list_products.execute()]

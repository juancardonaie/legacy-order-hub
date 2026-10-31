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
from orderhub.application.use_cases.create_user import CreateUser
from orderhub.application.use_cases.list_orders import ListOrders
from orderhub.application.use_cases.list_products import ListProducts
from orderhub.adapters.inbound.http.rate_limiter import (
    InMemoryRateLimiter,
    NoRateLimiter,
    RateLimitConfig,
)
from orderhub.container import Container
from orderhub import settings


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
    assert isinstance(container.create_user, CreateUser)


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


def test_create_user_crea_un_usuario_que_el_repositorio_encuentra(container):
    creado = container.create_user.execute(
        username="ana", password="clave-segura-1", role="client"
    )

    assert container.user_repository.find_by_username("ana") == creado
    assert container.password_hasher.verify("clave-segura-1", creado.password_hash)


def test_sin_configuracion_explicita_los_limitadores_salen_de_settings(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_MAX", 2)
    container = Container(database_path=str(tmp_path / "x.db"))

    assert isinstance(container.rate_limiters.login, InMemoryRateLimiter)
    assert container.rate_limiters.login.hit("k") == 0
    assert container.rate_limiters.login.hit("k") == 0
    assert container.rate_limiters.login.hit("k") > 0


def test_settings_con_rate_limit_apagado_da_limitadores_neutros(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)

    container = Container(database_path=str(tmp_path / "x.db"))

    assert isinstance(container.rate_limiters.login, NoRateLimiter)


def test_los_limites_se_pueden_fijar_al_construir_el_container(tmp_path):
    config = RateLimitConfig(login_max=1, users_max=1, global_max=1)
    container = Container(database_path=str(tmp_path / "x.db"), rate_limits=config)

    assert container.rate_limiters.login.hit("k") == 0
    assert container.rate_limiters.login.hit("k") > 0
    assert container.rate_limiters.users.hit("k") == 0
    assert container.rate_limiters.users.hit("k") > 0
    assert container.rate_limiters.global_.hit("k") == 0
    assert container.rate_limiters.global_.hit("k") > 0


def test_el_container_con_rate_limit_desactivado_usa_limitadores_neutros(tmp_path):
    config = RateLimitConfig(enabled=False, login_max=1)
    container = Container(database_path=str(tmp_path / "x.db"), rate_limits=config)

    assert all(container.rate_limiters.login.hit("k") == 0 for _ in range(5))

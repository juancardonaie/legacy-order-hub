"""Composition Root.

Único lugar de la aplicación donde se instancian clases concretas y se inyectan
por constructor. Cambiar SQLite por otra persistencia solo debería tocar aquí y
los adaptadores correspondientes.
"""

from typing import Optional

from orderhub.adapters.inbound.http.rate_limiter import (
    RateLimitConfig,
    create_rate_limiters,
)
from orderhub.adapters.outbound.persistence.sqlite.connection import (
    SQLiteConnectionFactory,
)
from orderhub.adapters.outbound.persistence.sqlite.sqlite_order_repository import (
    SQLiteOrderRepository,
)
from orderhub.adapters.outbound.persistence.sqlite.sqlite_product_repository import (
    SQLiteProductRepository,
)
from orderhub.adapters.outbound.persistence.sqlite.sqlite_user_repository import (
    SQLiteUserRepository,
)
from orderhub.adapters.outbound.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)
from orderhub.adapters.outbound.security.jwt_token_service import JWTTokenService
from orderhub.application.use_cases.authenticate_user import AuthenticateUser
from orderhub.application.use_cases.create_order import CreateOrder
from orderhub.application.use_cases.create_product import CreateProduct
from orderhub.application.use_cases.create_user import CreateUser
from orderhub.application.use_cases.list_orders import ListOrders
from orderhub.application.use_cases.list_products import ListProducts
from orderhub import settings


def _rate_limits_from_settings() -> RateLimitConfig:
    return RateLimitConfig(
        enabled=settings.RATE_LIMIT_ENABLED,
        login_max=settings.RATE_LIMIT_LOGIN_MAX,
        login_window=settings.RATE_LIMIT_LOGIN_WINDOW,
        users_max=settings.RATE_LIMIT_USERS_MAX,
        users_window=settings.RATE_LIMIT_USERS_WINDOW,
        global_max=settings.RATE_LIMIT_GLOBAL_MAX,
        global_window=settings.RATE_LIMIT_GLOBAL_WINDOW,
    )


class Container:
    def __init__(
        self,
        database_path: str,
        rate_limits: Optional[RateLimitConfig] = None,
    ) -> None:
        connection_factory = SQLiteConnectionFactory(database_path)

        self.product_repository = SQLiteProductRepository(connection_factory)
        self.order_repository = SQLiteOrderRepository(connection_factory)
        self.user_repository = SQLiteUserRepository(connection_factory)
        self.password_hasher = BcryptPasswordHasher()
        self.token_service = JWTTokenService(
            secret_key=settings.JWT_SECRET_KEY,
            expiration_minutes=settings.JWT_EXPIRATION_MINUTES,
            algorithm=settings.JWT_ALGORITHM,
        )

        self.create_order = CreateOrder(
            product_repository=self.product_repository,
            order_repository=self.order_repository,
        )
        self.list_orders = ListOrders(order_repository=self.order_repository)
        self.create_product = CreateProduct(
            product_repository=self.product_repository,
        )
        self.list_products = ListProducts(
            product_repository=self.product_repository,
        )
        self.authenticate_user = AuthenticateUser(
            user_repository=self.user_repository,
            password_hasher=self.password_hasher,
        )
        self.create_user = CreateUser(
            user_repository=self.user_repository,
            password_hasher=self.password_hasher,
        )

        # Los limitadores no dependen de Flask: el cableado HTTP está en
        # rate_limiting.install_rate_limiting. `rate_limits` permite a los tests
        # fijar límites propios sin tocar el entorno.
        self.rate_limiters = create_rate_limiters(
            rate_limits or _rate_limits_from_settings()
        )

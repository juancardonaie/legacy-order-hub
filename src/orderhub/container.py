"""Composition Root.

Único lugar de la aplicación donde se instancian clases concretas y se inyectan
por constructor. Cambiar SQLite por otra persistencia solo debería tocar aquí y
los adaptadores correspondientes.
"""

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
from orderhub.application.use_cases.authenticate_user import AuthenticateUser
from orderhub.application.use_cases.create_order import CreateOrder
from orderhub.application.use_cases.list_orders import ListOrders


class Container:
    def __init__(self, database_path: str) -> None:
        connection_factory = SQLiteConnectionFactory(database_path)

        self.product_repository = SQLiteProductRepository(connection_factory)
        self.order_repository = SQLiteOrderRepository(connection_factory)
        self.user_repository = SQLiteUserRepository(connection_factory)
        self.password_hasher = BcryptPasswordHasher()

        self.create_order = CreateOrder(
            product_repository=self.product_repository,
            order_repository=self.order_repository,
        )
        self.list_orders = ListOrders(order_repository=self.order_repository)
        self.authenticate_user = AuthenticateUser(
            user_repository=self.user_repository,
            password_hasher=self.password_hasher,
        )

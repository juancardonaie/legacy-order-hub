"""Fixtures de la suite de integración: infraestructura real, aislada.

BASE DE DATOS: cada test recibe un fichero SQLite propio bajo tmp_path, creado
y sembrado desde cero. Nunca se abre orderhub.db.

Por qué un fichero temporal y no ":memory:": SQLiteConnectionFactory abre una
conexión nueva en cada llamada y la cierra al terminar. Con ":memory:" cada
conexión sería una base distinta y vacía, así que los repositorios no verían
nada de lo que escribieron. Un fichero por test da el mismo aislamiento y sí
sobrevive entre conexiones.

El esquema se replica aquí en vez de llamar a database.init_db() porque esa
función tiene "orderhub.db" cableado dentro y escribiría en la BD de
desarrollo. Es duplicación conocida: si cambia el esquema real, hay que
actualizar SCHEMA.
"""

import sqlite3

import bcrypt
import pytest
from flask import Flask, render_template

from orderhub.adapters.inbound.http.auth_controller import create_auth_blueprint
from orderhub.adapters.inbound.http.jwt_required import create_jwt_required
from orderhub.adapters.inbound.http.order_controller import create_order_blueprint
from orderhub.adapters.inbound.http.product_controller import create_product_blueprint
from orderhub.container import Container

# Mismo esquema que database.init_db(), incluida la columna legada `password`
# en texto plano: es justo la que el repositorio NO debe leer.
SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    password_hash TEXT,
    role TEXT
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL,
    stock INTEGER
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    total REAL,
    status TEXT
);
"""

ADMIN_PASSWORD = "admin123"
CLIENT_PASSWORD = "123456"


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# bcrypt es deliberadamente lento; se calcula una sola vez por sesión en vez de
# en cada test.
ADMIN_HASH = _hash(ADMIN_PASSWORD)
CLIENT_HASH = _hash(CLIENT_PASSWORD)

SEED_PRODUCTS = [
    ("Laptop Legada", 1200.00, 5),
    ("Mouse USB", 15.50, 50),
]


@pytest.fixture
def admin_password() -> str:
    return ADMIN_PASSWORD


@pytest.fixture
def client_password() -> str:
    return CLIENT_PASSWORD


@pytest.fixture
def admin_password_hash() -> str:
    return ADMIN_HASH


@pytest.fixture
def database_path(tmp_path) -> str:
    """Crea una BD SQLite nueva y sembrada para un único test."""
    path = str(tmp_path / "orderhub_test.db")

    connection = sqlite3.connect(path)
    try:
        connection.executescript(SCHEMA)
        connection.executemany(
            "INSERT INTO users (username, password, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            [
                # La columna `password` guarda un valor distinto del hash a
                # propósito: si el repositorio la leyera por error, se notaría.
                ("admin", "texto-plano-legado", ADMIN_HASH, "admin"),
                ("juan", "texto-plano-legado", CLIENT_HASH, "client"),
            ],
        )
        connection.executemany(
            "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
            SEED_PRODUCTS,
        )
        connection.commit()
    finally:
        connection.close()

    return path


@pytest.fixture
def connection(database_path):
    """Conexión directa para comprobar el estado real de la BD desde el test."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


@pytest.fixture
def container(database_path) -> Container:
    """Composition Root real apuntando a la BD temporal."""
    return Container(database_path=database_path)


@pytest.fixture
def integration_app(container) -> Flask:
    """App Flask cableada igual que app.py, pero contra la BD temporal.

    No se importa app.py porque su cuerpo de módulo llama a init_db() sobre
    orderhub.db. El cableado se replica aquí; ver nota en el resumen del paso.
    """
    import os

    templates = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "templates",
    )
    app = Flask(__name__, template_folder=templates)
    app.testing = True

    jwt_required = create_jwt_required(container.token_service)

    app.register_blueprint(
        create_order_blueprint(
            create_order=container.create_order,
            list_orders=container.list_orders,
            jwt_required=jwt_required,
        )
    )
    app.register_blueprint(
        create_auth_blueprint(
            authenticate_user=container.authenticate_user,
            token_service=container.token_service,
        )
    )
    app.register_blueprint(
        create_product_blueprint(
            create_product=container.create_product,
            jwt_required=jwt_required,
        )
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


@pytest.fixture
def http(integration_app):
    return integration_app.test_client()


@pytest.fixture
def login(http):
    """Devuelve un helper que hace login real y entrega el token."""

    def _login(username: str, password: str) -> str:
        response = http.post(
            "/login", json={"username": username, "password": password}
        )
        assert response.status_code == 200, response.get_json()
        return response.get_json()["token"]

    return _login

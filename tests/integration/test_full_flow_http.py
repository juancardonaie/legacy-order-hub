"""Flujo completo de extremo a extremo con Container real y SQLite real.

login → token → operación protegida → verificación del estado en la BD.
Incluye los caminos de error: sin token, token vencido, rol insuficiente.
"""

from datetime import datetime, timedelta, timezone

import pytest

from orderhub import settings
from orderhub.adapters.outbound.security.jwt_token_service import JWTTokenService
from orderhub.domain.entities.user import User


def test_flujo_admin_login_crear_producto_comprar_y_listar(
    http, login, bearer, admin_password, connection
):
    token = login("admin", admin_password)

    creado = http.post(
        "/products",
        json={"name": "Teclado mecánico", "price": 99.99, "stock": 10},
        headers=bearer(token),
    )
    assert creado.status_code == 201
    product_id = creado.get_json()["product"]["id"]

    # El producto está de verdad en la tabla, no solo en la respuesta.
    fila = connection.execute(
        "SELECT name, price, stock FROM products WHERE id = ?", (product_id,)
    ).fetchone()
    assert (fila["name"], fila["price"], fila["stock"]) == (
        "Teclado mecánico",
        99.99,
        10,
    )

    comprado = http.post(
        "/create_order",
        json={"product_id": product_id, "quantity": 2},
        headers=bearer(token),
    )
    assert comprado.status_code == 201
    assert comprado.get_json()["total"] == 199.98

    listado = http.get("/get_all_orders_legacy", headers=bearer(token))
    assert listado.status_code == 200
    ordenes = listado.get_json()
    assert len(ordenes) == 1
    assert ordenes[0]["user_id"] == 1
    assert ordenes[0]["product_id"] == product_id
    assert ordenes[0]["status"] == "PENDING"

    # La compra descontó el stock en la BD.
    assert (
        connection.execute(
            "SELECT stock FROM products WHERE id = ?", (product_id,)
        ).fetchone()["stock"]
        == 8
    )


def test_un_client_hace_login_compra_pero_no_crea_productos(
    http, login, bearer, client_password, connection
):
    token = login("juan", client_password)

    comprado = http.post(
        "/create_order", json={"product_id": 1, "quantity": 1}, headers=bearer(token)
    )
    assert comprado.status_code == 201

    prohibido = http.post(
        "/products", json={"name": "Pirata", "price": 1.0}, headers=bearer(token)
    )
    assert prohibido.status_code == 403

    # Nada se creó en el catálogo: siguen los 2 productos sembrados.
    assert connection.execute("SELECT COUNT(*) c FROM products").fetchone()["c"] == 2


def test_la_orden_se_registra_a_nombre_del_dueno_del_token(
    http, login, bearer, client_password, connection
):
    token = login("juan", client_password)

    http.post(
        "/create_order",
        json={"product_id": 1, "quantity": 1, "user_id": 9999},
        headers=bearer(token),
    )

    assert connection.execute("SELECT user_id FROM orders").fetchone()["user_id"] == 2


@pytest.mark.parametrize("ruta", ["/create_order", "/products"])
def test_los_endpoints_protegidos_rechazan_peticiones_sin_token(http, ruta, connection):
    response = http.post(ruta, json={"product_id": 1, "quantity": 1})

    assert response.status_code == 401
    assert connection.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"] == 0


def test_un_token_vencido_se_rechaza_con_401(http, bearer):
    """Token firmado con la clave real de la app pero ya expirado."""
    pasado = datetime.now(timezone.utc) - timedelta(hours=2)
    emisor_vencido = JWTTokenService(
        secret_key=settings.JWT_SECRET_KEY,
        expiration_minutes=settings.JWT_EXPIRATION_MINUTES,
        algorithm=settings.JWT_ALGORITHM,
        clock=lambda: pasado,
    )
    token = emisor_vencido.generate(
        User(id=1, username="admin", password_hash="x", role="admin")
    )

    response = http.get("/get_all_orders_legacy", headers=bearer(token))

    assert response.status_code == 401
    assert response.get_json()["message"] == "Token expirado"


def test_un_token_firmado_con_otra_clave_se_rechaza_con_401(
    http, bearer, jwt_test_secret
):
    intruso = JWTTokenService(secret_key=jwt_test_secret, expiration_minutes=15)
    token = intruso.generate(
        User(id=1, username="admin", password_hash="x", role="admin")
    )

    response = http.get("/get_all_orders_legacy", headers=bearer(token))

    assert response.status_code == 401
    assert response.get_json()["message"] == "Token inválido"


def test_comprar_mas_stock_del_disponible_devuelve_400_y_no_crea_la_orden(
    http, login, bearer, admin_password, connection
):
    token = login("admin", admin_password)

    response = http.post(
        "/create_order", json={"product_id": 1, "quantity": 999}, headers=bearer(token)
    )

    assert response.status_code == 400
    assert connection.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"] == 0
    assert (
        connection.execute("SELECT stock FROM products WHERE id = 1").fetchone()[
            "stock"
        ]
        == 5
    )


def test_comprar_un_producto_inexistente_devuelve_404(
    http, login, bearer, admin_password
):
    token = login("admin", admin_password)

    response = http.post(
        "/create_order", json={"product_id": 4040, "quantity": 1}, headers=bearer(token)
    )

    assert response.status_code == 404


def test_crear_un_producto_con_datos_invalidos_devuelve_400_y_no_toca_la_bd(
    http, login, bearer, admin_password, connection
):
    token = login("admin", admin_password)

    response = http.post(
        "/products", json={"name": "  ", "price": -3}, headers=bearer(token)
    )

    assert response.status_code == 400
    assert connection.execute("SELECT COUNT(*) c FROM products").fetchone()["c"] == 2


def test_el_panel_html_responde_200_sin_token(http):
    response = http.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]

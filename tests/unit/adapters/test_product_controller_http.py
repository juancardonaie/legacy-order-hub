"""Tests HTTP de POST /products (RF-01.4).

Operación administrativa: 201 con token admin, 403 con token de rol client,
401 sin token, 400 con datos que violan las reglas del dominio.
"""

import pytest

NUEVO_PRODUCTO = {"name": "Teclado mecánico", "price": 99.99, "stock": 10}


def test_admin_crea_el_producto_y_recibe_201(client, admin_headers, product_repository):
    response = client.post("/products", json=NUEVO_PRODUCTO, headers=admin_headers)

    assert response.status_code == 201
    body = response.get_json()
    assert body["status"] == "success"
    assert body["product"]["name"] == "Teclado mecánico"
    assert body["product"]["id"] is not None
    assert product_repository.products[body["product"]["id"]].price == 99.99


def test_un_client_recibe_403_y_no_crea_nada(
    client, client_headers, product_repository
):
    antes = dict(product_repository.products)

    response = client.post("/products", json=NUEVO_PRODUCTO, headers=client_headers)

    assert response.status_code == 403
    assert product_repository.products == antes


def test_sin_token_recibe_401(client, product_repository):
    antes = dict(product_repository.products)

    response = client.post("/products", json=NUEVO_PRODUCTO)

    assert response.status_code == 401
    assert product_repository.products == antes


def test_con_token_invalido_recibe_401(client):
    response = client.post(
        "/products",
        json=NUEVO_PRODUCTO,
        headers={"Authorization": "Bearer no-es-un-token"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload, esperado",
    [
        ({"name": "", "price": 10.0}, "nombre"),
        ({"name": "   ", "price": 10.0}, "nombre"),
        ({"name": "Teclado", "price": 0}, "precio"),
        ({"name": "Teclado", "price": -5}, "precio"),
        ({"name": "Teclado", "price": 10.0, "stock": -1}, "stock"),
    ],
)
def test_datos_invalidos_devuelven_400(client, admin_headers, payload, esperado):
    response = client.post("/products", json=payload, headers=admin_headers)

    assert response.status_code == 400
    assert esperado in response.get_json()["message"].lower()


def test_precio_no_numerico_devuelve_400(client, admin_headers):
    response = client.post(
        "/products",
        json={"name": "Teclado", "price": "carísimo"},
        headers=admin_headers,
    )

    assert response.status_code == 400
    assert "numérico" in response.get_json()["message"]


def test_body_vacio_devuelve_400_y_no_500(client, admin_headers):
    response = client.post("/products", json={}, headers=admin_headers)

    assert response.status_code == 400


def test_la_autenticacion_se_evalua_antes_que_el_rol(client):
    """Sin token debe ser 401 aunque el endpoint también exija rol admin."""
    response = client.post("/products", json={}, headers={})

    assert response.status_code == 401

"""Tests HTTP del inventario: RF-02.2 (descuento de stock) y RF-02.3 (rechazo).

Cubren el contrato que ve el cliente al comprar, no las reglas de dominio:
esas ya están probadas en tests/unit/domain/test_product_rules.py.
"""

import pytest


def test_una_compra_descuenta_el_stock(client, admin_headers, product_repository):
    """RF-02.2: el stock se actualiza al procesar la orden."""
    response = client.post(
        "/create_order", json={"product_id": 1, "quantity": 2}, headers=admin_headers
    )

    assert response.status_code == 201
    assert product_repository.products[1].stock == 3


def test_compras_sucesivas_acumulan_el_descuento(
    client, admin_headers, product_repository
):
    for _ in range(3):
        client.post(
            "/create_order",
            json={"product_id": 1, "quantity": 1},
            headers=admin_headers,
        )

    assert product_repository.products[1].stock == 2


def test_comprar_todo_el_stock_lo_deja_en_cero(
    client, admin_headers, product_repository
):
    response = client.post(
        "/create_order", json={"product_id": 1, "quantity": 5}, headers=admin_headers
    )

    assert response.status_code == 201
    assert product_repository.products[1].stock == 0


@pytest.mark.parametrize("quantity", [6, 100])
def test_pedir_mas_del_stock_disponible_devuelve_400(
    client, admin_headers, product_repository, quantity
):
    """RF-02.3: rechazo con error claro, no una excepción cruda (500)."""
    response = client.post(
        "/create_order",
        json={"product_id": 1, "quantity": quantity},
        headers=admin_headers,
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Stock insuficiente"
    assert body["requested"] == quantity
    assert body["available"] == 5
    assert body["product_id"] == 1


def test_una_compra_rechazada_no_toca_el_stock(
    client, admin_headers, product_repository, order_repository
):
    client.post(
        "/create_order", json={"product_id": 1, "quantity": 99}, headers=admin_headers
    )

    assert product_repository.products[1].stock == 5
    assert order_repository.orders == []


def test_agotado_el_stock_la_siguiente_compra_se_rechaza(
    client, admin_headers, product_repository
):
    """El rechazo se calcula sobre la disponibilidad real, ya descontada."""
    client.post(
        "/create_order", json={"product_id": 1, "quantity": 5}, headers=admin_headers
    )

    response = client.post(
        "/create_order", json={"product_id": 1, "quantity": 1}, headers=admin_headers
    )

    assert response.status_code == 400
    assert response.get_json()["available"] == 0


def test_un_producto_inexistente_devuelve_404(client, admin_headers):
    response = client.post(
        "/create_order", json={"product_id": 9999, "quantity": 1}, headers=admin_headers
    )

    assert response.status_code == 404

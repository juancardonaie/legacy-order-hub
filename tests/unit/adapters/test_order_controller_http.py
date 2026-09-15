"""Tests HTTP de /create_order y /get_all_orders_legacy tras aplicar
@jwt_required (RF-01.3 / RF-01.4).

Comprar NO exige rol admin: un usuario con rol 'client' debe poder crear su
orden. Lo que se exige es estar autenticado.
"""

ORDEN = {"product_id": 1, "quantity": 2}


def test_create_order_sin_token_devuelve_401(client, order_repository):
    response = client.post("/create_order", json=ORDEN)

    assert response.status_code == 401
    assert order_repository.orders == []


def test_get_all_orders_legacy_sin_token_devuelve_401(client):
    assert client.get("/get_all_orders_legacy").status_code == 401


def test_un_client_autenticado_si_puede_comprar(client, client_headers):
    """Crear una orden es comprar, no es una operación administrativa."""
    response = client.post("/create_order", json=ORDEN, headers=client_headers)

    assert response.status_code == 201
    assert response.get_json()["total"] == 200.0


def test_un_admin_tambien_puede_comprar(client, admin_headers):
    assert (
        client.post("/create_order", json=ORDEN, headers=admin_headers).status_code
        == 201
    )


def test_el_user_id_sale_del_token_y_no_del_body(
    client, client_headers, order_repository, client_user
):
    """Aunque el cliente mienta en el body, la orden se registra a su nombre."""
    response = client.post(
        "/create_order",
        json={**ORDEN, "user_id": 9999},
        headers=client_headers,
    )

    assert response.status_code == 201
    assert order_repository.orders[0].user_id == client_user.id


def test_get_all_orders_legacy_con_token_valido_devuelve_las_ordenes(
    client, client_headers
):
    client.post("/create_order", json=ORDEN, headers=client_headers)

    response = client.get("/get_all_orders_legacy", headers=client_headers)

    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_token_invalido_devuelve_401(client):
    response = client.post(
        "/create_order", json=ORDEN, headers={"Authorization": "Bearer roto"}
    )

    assert response.status_code == 401


def test_stock_insuficiente_sigue_devolviendo_400(client, client_headers):
    response = client.post(
        "/create_order", json={"product_id": 1, "quantity": 99}, headers=client_headers
    )

    assert response.status_code == 400


def test_producto_inexistente_sigue_devolviendo_404(client, client_headers):
    response = client.post(
        "/create_order", json={"product_id": 404, "quantity": 1}, headers=client_headers
    )

    assert response.status_code == 404


def test_una_cantidad_no_numerica_devuelve_400(client, client_headers):
    response = client.post(
        "/create_order",
        json={"product_id": 1, "quantity": "muchas"},
        headers=client_headers,
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Cantidad inválida"


def test_una_cantidad_cero_devuelve_400(client, client_headers, order_repository):
    response = client.post(
        "/create_order", json={"product_id": 1, "quantity": 0}, headers=client_headers
    )

    assert response.status_code == 400
    assert order_repository.orders == []

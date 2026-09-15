"""Tests HTTP de GET /products (RF-02.1).

Consultar el catálogo exige token válido, pero NO rol admin: es lo que hace
cualquier comprador antes de crear una orden. App Flask real con repositorio
en memoria; no hay servidor ni base de datos.
"""

from orderhub.domain.entities.product import Product


def test_devuelve_200_y_el_catalogo_con_precio_y_stock(client, admin_headers):
    response = client.get("/products", headers=admin_headers)

    assert response.status_code == 200
    assert response.get_json() == [
        {"id": 1, "name": "Laptop", "price": 100.0, "stock": 5}
    ]


def test_un_client_tambien_puede_consultar_el_catalogo(client, client_headers):
    """No es una operación administrativa: 200, no 403."""
    response = client.get("/products", headers=client_headers)

    assert response.status_code == 200


def test_sin_token_recibe_401(client):
    response = client.get("/products")

    assert response.status_code == 401
    assert "id" not in response.get_data(as_text=True)


def test_con_token_invalido_recibe_401(client, bearer):
    response = client.get("/products", headers=bearer("no-es-un-token"))

    assert response.status_code == 401


def test_un_catalogo_vacio_devuelve_una_lista_vacia(
    client, admin_headers, product_repository
):
    product_repository.products.clear()

    response = client.get("/products", headers=admin_headers)

    assert response.status_code == 200
    assert response.get_json() == []


def test_lista_todos_los_productos_ordenados_por_id(
    client, admin_headers, product_repository
):
    product_repository.products[2] = Product(
        id=2, name="Mouse USB", price=15.5, stock=50
    )

    ids = [
        product["id"]
        for product in client.get("/products", headers=admin_headers).get_json()
    ]

    assert ids == [1, 2]


def test_refleja_el_stock_despues_de_una_compra(client, admin_headers):
    """RF-02.1 + RF-02.2: el catálogo muestra el stock ya descontado."""
    client.post(
        "/create_order", json={"product_id": 1, "quantity": 2}, headers=admin_headers
    )

    catalogo = client.get("/products", headers=admin_headers).get_json()

    assert catalogo[0]["stock"] == 3


def test_la_respuesta_no_expone_campos_internos(client, admin_headers):
    producto = client.get("/products", headers=admin_headers).get_json()[0]

    assert set(producto) == {"id", "name", "price", "stock"}

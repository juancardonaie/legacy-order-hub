"""Flujo completo de catálogo e inventario contra infraestructura real (RF-02).

Recorre login → GET /products → POST /create_order → GET /products con la app
Flask cableada como app.py, el Container real y una BD SQLite temporal. Lo que
comprueban estos tests y no los unitarios es que el stock descontado llega
realmente al disco.
"""


def test_el_catalogo_expone_precio_y_stock_de_los_productos_sembrados(http, login):
    """RF-02.1 de extremo a extremo."""
    token = login("juan", "123456")

    response = http.get("/products", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.get_json() == [
        {"id": 1, "name": "Laptop Legada", "price": 1200.00, "stock": 5},
        {"id": 2, "name": "Mouse USB", "price": 15.50, "stock": 50},
    ]


def test_el_catalogo_exige_token(http):
    assert http.get("/products").status_code == 401


def test_comprar_descuenta_el_stock_en_la_base_de_datos(http, login, connection):
    """RF-02.2: la actualización se persiste, no se queda en memoria."""
    token = login("juan", "123456")
    headers = {"Authorization": f"Bearer {token}"}

    respuesta = http.post(
        "/create_order", json={"product_id": 1, "quantity": 2}, headers=headers
    )

    assert respuesta.status_code == 201
    fila = connection.execute(
        "SELECT stock FROM products WHERE id = ?", (1,)
    ).fetchone()
    assert fila["stock"] == 3
    assert http.get("/products", headers=headers).get_json()[0]["stock"] == 3


def test_pedir_mas_del_stock_disponible_se_rechaza_sin_tocar_la_bd(
    http, login, connection
):
    """RF-02.3: 400 con detalle, y ni orden ni descuento en la base."""
    headers = {"Authorization": f"Bearer {login('juan', '123456')}"}

    respuesta = http.post(
        "/create_order", json={"product_id": 1, "quantity": 6}, headers=headers
    )

    assert respuesta.status_code == 400
    cuerpo = respuesta.get_json()
    assert cuerpo["error"] == "Stock insuficiente"
    assert (cuerpo["requested"], cuerpo["available"]) == (6, 5)

    assert (
        connection.execute("SELECT stock FROM products WHERE id = ?", (1,)).fetchone()[
            "stock"
        ]
        == 5
    )
    assert connection.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"] == 0


def test_un_producto_creado_por_admin_aparece_en_el_catalogo(http, login):
    """POST /products (RF-01.4) y GET /products (RF-02.1) ven el mismo catálogo."""
    admin_headers = {"Authorization": f"Bearer {login('admin', 'admin123')}"}

    creado = http.post(
        "/products",
        json={"name": "Monitor 27", "price": 320.0, "stock": 4},
        headers=admin_headers,
    ).get_json()["product"]

    catalogo = http.get("/products", headers=admin_headers).get_json()

    assert {"id": creado["id"], "name": "Monitor 27", "price": 320.0, "stock": 4} in (
        catalogo
    )


def test_agotar_el_stock_y_volver_a_comprar(http, login, connection):
    headers = {"Authorization": f"Bearer {login('juan', '123456')}"}

    assert (
        http.post(
            "/create_order", json={"product_id": 1, "quantity": 5}, headers=headers
        ).status_code
        == 201
    )

    rechazo = http.post(
        "/create_order", json={"product_id": 1, "quantity": 1}, headers=headers
    )

    assert rechazo.status_code == 400
    assert rechazo.get_json()["available"] == 0
    assert http.get("/products", headers=headers).get_json()[0]["stock"] == 0

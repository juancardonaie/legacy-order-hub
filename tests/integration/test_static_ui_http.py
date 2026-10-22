"""La UI estática (static/) se sirve sin token y desde el mismo origen."""

import pytest

ASSETS = [
    ("/static/js/main.js", "javascript"),
    ("/static/js/api.js", "javascript"),
    ("/static/js/auth.js", "javascript"),
    ("/static/js/session.js", "javascript"),
    ("/static/js/ui.js", "javascript"),
    ("/static/css/styles.css", "css"),
]


@pytest.mark.parametrize("ruta, tipo", ASSETS)
def test_los_assets_de_la_ui_se_sirven_sin_token(http, ruta, tipo):
    response = http.get(ruta)

    assert response.status_code == 200
    assert tipo in response.headers["Content-Type"]
    response.close()


def test_la_pagina_de_entrada_referencia_assets_que_existen(http):
    response = http.get("/")
    html = response.get_data(as_text=True)
    response.close()

    assert "/static/js/main.js" in html
    assert "/static/css/styles.css" in html


def test_la_api_sigue_protegida_aunque_la_ui_sea_publica(http):
    assert http.get("/products").status_code == 401
    assert http.get("/get_all_orders_legacy").status_code == 401


def test_la_ui_puede_completar_un_login_real(http):
    response = http.post("/login", json={"username": "admin", "password": "admin123"})

    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == "success"
    assert set(body["user"]) == {"id", "username", "role"}

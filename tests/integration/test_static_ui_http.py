"""La UI estática (static/) se sirve sin token y desde el mismo origen."""

import pathlib

import pytest

STATIC_DIR = pathlib.Path(__file__).resolve().parents[2] / "static"

TIPOS = {".js": "javascript", ".css": "css", ".json": "json", ".html": "html"}

# Se recorre static/ en vez de mantener una lista a mano: un asset nuevo queda
# cubierto sin tocar este archivo.
ASSETS = sorted(
    (f"/static/{path.relative_to(STATIC_DIR).as_posix()}", TIPOS[path.suffix])
    for path in STATIC_DIR.rglob("*")
    if path.suffix in TIPOS
)


def test_el_recorrido_de_static_encuentra_los_assets_esperados():
    rutas = {ruta for ruta, _ in ASSETS}

    assert "/static/endpoints.json" in rutas
    assert "/static/js/explorer.js" in rutas
    assert "/static/js/main.js" in rutas
    assert "/static/css/styles.css" in rutas


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
    assert 'id="explorer"' in html


def test_el_catalogo_del_explorador_se_sirve_como_json_valido(http):
    response = http.get("/static/endpoints.json")

    catalogo = response.get_json()
    response.close()
    assert isinstance(catalogo, list)
    assert len(catalogo) == 6


def test_la_api_sigue_protegida_aunque_la_ui_sea_publica(http):
    assert http.get("/products").status_code == 401
    assert http.get("/get_all_orders_legacy").status_code == 401


def test_la_ui_puede_completar_un_login_real(http):
    response = http.post("/login", json={"username": "admin", "password": "admin123"})

    body = response.get_json()
    assert response.status_code == 200
    assert body["status"] == "success"
    assert set(body["user"]) == {"id", "username", "role"}

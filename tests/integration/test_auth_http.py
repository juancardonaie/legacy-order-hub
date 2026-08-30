"""Integración de POST /login: HTTP → caso de uso → bcrypt → SQLite real.

Cubre auth_controller.py de extremo a extremo, sin dobles.
"""

import jwt


def test_login_correcto_devuelve_200_y_un_token(http, admin_password):
    response = http.post(
        "/login", json={"username": "admin", "password": admin_password}
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "success"
    assert body["user"] == {"id": 1, "username": "admin", "role": "admin"}
    assert body["token"]


def test_el_token_emitido_lleva_la_identidad_y_una_expiracion(http, admin_password):
    token = http.post(
        "/login", json={"username": "admin", "password": admin_password}
    ).get_json()["token"]

    claims = jwt.decode(token, options={"verify_signature": False})

    assert claims["user_id"] == 1
    assert claims["username"] == "admin"
    assert claims["role"] == "admin"
    assert claims["exp"] > claims["iat"]


def test_la_respuesta_de_login_nunca_incluye_el_hash_ni_la_contrasena(
    http, admin_password
):
    response = http.post(
        "/login", json={"username": "admin", "password": admin_password}
    )

    cuerpo = response.get_data(as_text=True)
    assert "password" not in cuerpo
    assert admin_password not in cuerpo


def test_contrasena_incorrecta_devuelve_401(http):
    response = http.post("/login", json={"username": "admin", "password": "mala"})

    assert response.status_code == 401
    assert response.get_json()["message"] == "Credenciales inválidas"
    assert "token" not in response.get_json()


def test_usuario_inexistente_devuelve_401(http):
    response = http.post("/login", json={"username": "fantasma", "password": "x"})

    assert response.status_code == 401
    assert response.get_json()["message"] == "Credenciales inválidas"


def test_el_mensaje_no_revela_si_el_usuario_existe(http):
    """Mismo mensaje para usuario inexistente y contraseña mala: no permite
    enumerar usuarios."""
    inexistente = http.post("/login", json={"username": "fantasma", "password": "x"})
    mala = http.post("/login", json={"username": "admin", "password": "x"})

    assert inexistente.get_json() == mala.get_json()


def test_body_vacio_devuelve_401_y_no_500(http):
    assert http.post("/login", json={}).status_code == 401


def test_sin_body_json_devuelve_401_y_no_500(http):
    assert http.post("/login").status_code == 401


def test_un_intento_de_inyeccion_en_el_username_no_autentica(http):
    response = http.post(
        "/login", json={"username": "' OR '1'='1", "password": "loquesea"}
    )

    assert response.status_code == 401


def test_el_usuario_client_tambien_puede_autenticarse(http, client_password):
    response = http.post(
        "/login", json={"username": "juan", "password": client_password}
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "client"

"""Tests del decorador @jwt_required.

Se monta una app Flask mínima en memoria y se usa el test client: no hace
falta servidor ni base de datos. El TokenServicePort se sustituye por un doble,
así que estos tests no dependen de PyJWT.
"""

import pytest
from flask import Flask, g, jsonify

from orderhub.adapters.inbound.http.jwt_required import create_jwt_required
from orderhub.application.ports.token_service import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenPayload,
    TokenServicePort,
)

TOKEN_VALIDO = "token-valido"
TOKEN_EXPIRADO = "token-expirado"

PAYLOAD = TokenPayload(user_id=7, username="juan", role="admin")


class FakeTokenService(TokenServicePort):
    def generate(self, user):  # pragma: no cover - no se usa en estos tests
        return TOKEN_VALIDO

    def verify(self, token: str) -> TokenPayload:
        if token == TOKEN_VALIDO:
            return PAYLOAD
        if token == TOKEN_EXPIRADO:
            raise ExpiredTokenError()
        raise InvalidTokenError()


@pytest.fixture
def client():
    app = Flask(__name__)
    jwt_required = create_jwt_required(FakeTokenService())

    @app.route("/protegido")
    @jwt_required
    def protegido():
        return jsonify({"username": g.current_user.username}), 200

    return app.test_client()


def test_sin_cabecera_authorization_responde_401(client):
    response = client.get("/protegido")

    assert response.status_code == 401
    assert "Authorization" in response.get_json()["message"]


def test_cabecera_sin_prefijo_bearer_responde_401(client):
    response = client.get("/protegido", headers={"Authorization": TOKEN_VALIDO})

    assert response.status_code == 401


def test_token_malformado_responde_401(client):
    response = client.get(
        "/protegido", headers={"Authorization": "Bearer no-es-un-token"}
    )

    assert response.status_code == 401
    assert response.get_json()["message"] == "Token inválido"


def test_token_expirado_responde_401(client):
    response = client.get(
        "/protegido", headers={"Authorization": f"Bearer {TOKEN_EXPIRADO}"}
    )

    assert response.status_code == 401
    assert response.get_json()["message"] == "Token expirado"


def test_token_valido_deja_pasar_y_expone_la_identidad(client):
    response = client.get(
        "/protegido", headers={"Authorization": f"Bearer {TOKEN_VALIDO}"}
    )

    assert response.status_code == 200
    assert response.get_json() == {"username": "juan"}


def test_bearer_sin_token_responde_401(client):
    response = client.get("/protegido", headers={"Authorization": "Bearer "})

    assert response.status_code == 401
    assert response.get_json()["message"] == "No se envió ningún token"

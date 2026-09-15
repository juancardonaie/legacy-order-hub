"""Tests del decorador require_role.

App Flask mínima en memoria: sin servidor ni base de datos. La identidad se
coloca directamente en g para probar require_role de forma aislada de
@jwt_required.
"""

import pytest
from flask import Flask, g, jsonify

from orderhub.adapters.inbound.http.require_role import require_role
from orderhub.application.ports.token_service import TokenPayload

ADMIN = TokenPayload(user_id=1, username="admin", role="admin")
CLIENT = TokenPayload(user_id=2, username="juan", role="client")


def _build_client(identity):
    """Monta una vista protegida simulando lo que haría @jwt_required."""
    app = Flask(__name__)
    # Deja que el RuntimeError salga a la vista en vez de convertirse en un 500.
    app.testing = True

    @app.before_request
    def inject_identity():
        if identity is not None:
            g.current_user = identity

    @app.route("/solo-admin")
    @require_role("admin")
    def solo_admin():
        return jsonify({"ok": True}), 200

    return app.test_client()


def test_un_admin_puede_entrar():
    response = _build_client(ADMIN).get("/solo-admin")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_un_client_recibe_403_y_no_401():
    response = _build_client(CLIENT).get("/solo-admin")

    assert response.status_code == 403
    assert "permisos" in response.get_json()["message"]


def test_sin_identidad_falla_de_forma_explicita():
    client = _build_client(None)

    with pytest.raises(RuntimeError, match="jwt_required"):
        client.get("/solo-admin")


def test_acepta_varios_roles():
    app = Flask(__name__)

    @app.before_request
    def inject_identity():
        g.current_user = CLIENT

    @app.route("/varios")
    @require_role("admin", "client")
    def varios():
        return jsonify({"ok": True}), 200

    assert app.test_client().get("/varios").status_code == 200


def test_require_role_sin_roles_es_un_error_de_programacion():
    with pytest.raises(ValueError):
        require_role()

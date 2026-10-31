from typing import Callable

from flask import Blueprint, jsonify, request

from orderhub.adapters.inbound.http.require_role import require_role
from orderhub.application.use_cases.create_user import CreateUser
from orderhub.domain.entities.user import ROLE_ADMIN, ROLE_CLIENT, User
from orderhub.domain.exceptions import (
    InvalidPasswordError,
    InvalidRoleError,
    InvalidUsernameError,
    UsernameAlreadyExistsError,
)


def _serialize(user: User) -> dict:
    """Representación JSON de un usuario. Nunca incluye contraseña ni hash."""
    return {"id": user.id, "username": user.username, "role": user.role}


def _error(message: str, status: int):
    return jsonify({"status": "error", "message": message}), status


def create_user_blueprint(
    create_user: CreateUser,
    jwt_required: Callable,
    rate_limit: Callable,
) -> Blueprint:
    """Adaptador primario HTTP para la creación de usuarios.

    POST /users es una operación administrativa: exige token válido
    (@jwt_required) y rol admin (require_role). El límite por usuario va entre
    los dos decoradores, así que se aplica antes de leer el body, de hashear o de
    consultar la base de datos.
    """
    blueprint = Blueprint("users", __name__)

    @blueprint.route("/users", methods=["POST"])
    @jwt_required
    @rate_limit
    @require_role(ROLE_ADMIN)
    def create_user_endpoint():
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return _error("El body debe ser un objeto JSON", 400)

        username = data.get("username")
        password = data.get("password")
        role = data.get("role", ROLE_CLIENT)
        if not all(isinstance(value, str) for value in (username, password, role)):
            return _error("username, password y role deben ser texto", 400)

        # Las reglas de negocio (formato, política de contraseña, rol válido)
        # viven en el dominio; aquí solo se traducen sus errores a HTTP.
        try:
            user = create_user.execute(username=username, password=password, role=role)
        except (
            InvalidUsernameError,
            InvalidPasswordError,
            InvalidRoleError,
        ) as error:
            return _error(str(error), 400)
        except UsernameAlreadyExistsError as error:
            return _error(str(error), 409)

        return jsonify({"status": "success", "user": _serialize(user)}), 201

    return blueprint

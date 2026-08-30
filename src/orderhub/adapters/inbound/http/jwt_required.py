"""Decorador de autorización para el adaptador HTTP.

Lee la cabecera `Authorization: Bearer <token>`, delega la verificación en el
TokenServicePort y deja la identidad en `flask.g.current_user`. No conoce JWT
ni PyJWT: solo el puerto.
"""

from functools import wraps
from typing import Callable

from flask import g, jsonify, request

from orderhub.application.ports.token_service import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenServicePort,
)

_AUTHORIZATION_HEADER = "Authorization"
_BEARER_PREFIX = "Bearer "


def _unauthorized(message: str):
    return jsonify({"status": "error", "message": message}), 401


def create_jwt_required(token_service: TokenServicePort) -> Callable:
    """Construye el decorador con el servicio de tokens ya inyectado.

    Se usa la forma factory (igual que create_*_blueprint) para no depender de
    un singleton global y poder inyectar un doble en los tests.
    """

    def jwt_required(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            header = request.headers.get(_AUTHORIZATION_HEADER)
            if not header:
                return _unauthorized("Falta la cabecera Authorization")

            if not header.startswith(_BEARER_PREFIX):
                return _unauthorized(
                    "Formato de cabecera inválido: se espera 'Bearer <token>'"
                )

            token = header[len(_BEARER_PREFIX) :].strip()
            if not token:
                return _unauthorized("No se envió ningún token")

            try:
                g.current_user = token_service.verify(token)
            except ExpiredTokenError as error:
                return _unauthorized(str(error))
            except InvalidTokenError as error:
                return _unauthorized(str(error))

            return view(*args, **kwargs)

        return wrapper

    return jwt_required

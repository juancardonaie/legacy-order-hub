from flask import Blueprint, jsonify, request

from orderhub.application.ports.token_service import TokenServicePort
from orderhub.application.use_cases.authenticate_user import AuthenticateUser
from orderhub.domain.exceptions import InvalidCredentialsError


def create_auth_blueprint(
    authenticate_user: AuthenticateUser,
    token_service: TokenServicePort,
) -> Blueprint:
    """Adaptador primario HTTP para /login.

    Traduce la petición al caso de uso y las excepciones de dominio al
    código HTTP correspondiente. Nunca serializa la contraseña ni su hash.

    La emisión del token de sesión se hace aquí y no dentro del caso de uso:
    autenticar es una regla de negocio, mientras que el formato en que se
    transporta la sesión es un detalle del protocolo HTTP.
    """
    blueprint = Blueprint("auth", __name__)

    @blueprint.route("/login", methods=["POST"])
    def login_endpoint():
        data = request.get_json(silent=True) or {}
        username = data.get("username")
        password = data.get("password")

        try:
            user = authenticate_user.execute(username=username, password=password)
        except InvalidCredentialsError as error:
            return jsonify({"status": "error", "message": str(error)}), 401

        return (
            jsonify(
                {
                    "status": "success",
                    "token": token_service.generate(user),
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                    },
                }
            ),
            200,
        )

    return blueprint

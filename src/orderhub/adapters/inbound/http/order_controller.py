from dataclasses import asdict
from typing import Callable

from flask import Blueprint, g, jsonify, request

from orderhub.application.use_cases.create_order import CreateOrder
from orderhub.application.use_cases.list_orders import ListOrders
from orderhub.domain.exceptions import (
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotFoundError,
)


def create_order_blueprint(
    create_order: CreateOrder,
    list_orders: ListOrders,
    jwt_required: Callable,
) -> Blueprint:
    """Adaptador primario HTTP.

    Traduce la petición al caso de uso y las excepciones de dominio al código
    HTTP correspondiente. No contiene reglas de negocio ni acceso a datos.
    Las rutas se mantienen iguales a las del sistema legado.

    Ambos endpoints exigen token válido. Crear una orden es comprar: basta con
    estar autenticado, NO se exige rol admin (eso aplica al catálogo, RF-01.4).
    """
    blueprint = Blueprint("orders", __name__)

    @blueprint.route("/create_order", methods=["POST"])
    @jwt_required
    def create_order_endpoint():
        data = request.get_json(silent=True) or {}
        try:
            order = create_order.execute(
                # El user_id se toma de la identidad del token, NO del body:
                # el body lo controla el cliente y permitiría crear órdenes a
                # nombre de otro usuario.
                user_id=g.current_user.user_id,
                product_id=data.get("product_id"),
                quantity=int(data.get("quantity", 1)),
            )
        except (ValueError, TypeError):
            return jsonify({"error": "Cantidad inválida"}), 400
        except ProductNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except InsufficientStockError as error:
            # RF-02.3: el rechazo por stock es un error de negocio esperado,
            # no una excepción cruda. Se devuelve 400 con el detalle que el
            # cliente necesita para corregir la petición.
            return (
                jsonify(
                    {
                        "error": str(error),
                        "product_id": error.product_id,
                        "requested": error.requested,
                        "available": error.available,
                    }
                ),
                400,
            )
        except InvalidQuantityError as error:
            return jsonify({"error": str(error)}), 400

        # TODO: reemplazar por NotifierPort cuando se implemente RF-04.1.
        # Se conserva temporalmente el comportamiento del sistema legado.
        print(
            "[LOG LEGADO]: Notificando al servicio de correos para la orden ID: "
            f"{order.id}..."
        )

        return (
            jsonify(
                {
                    "message": "Orden creada con éxito",
                    "order_id": order.id,
                    "total": order.total,
                }
            ),
            201,
        )

    @blueprint.route("/get_all_orders_legacy", methods=["GET"])
    @jwt_required
    def list_orders_endpoint():
        orders = list_orders.execute()
        return jsonify([asdict(order) for order in orders]), 200

    return blueprint

from dataclasses import asdict

from flask import Blueprint, jsonify, request

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
) -> Blueprint:
    """Adaptador primario HTTP.

    Traduce la petición al caso de uso y las excepciones de dominio al código
    HTTP correspondiente. No contiene reglas de negocio ni acceso a datos.
    Las rutas se mantienen iguales a las del sistema legado.
    """
    blueprint = Blueprint("orders", __name__)

    @blueprint.route("/create_order", methods=["POST"])
    def create_order_endpoint():
        data = request.get_json(silent=True) or {}
        try:
            order = create_order.execute(
                user_id=data.get("user_id"),
                product_id=data.get("product_id"),
                quantity=int(data.get("quantity", 1)),
            )
        except (ValueError, TypeError):
            return jsonify({"error": "Cantidad inválida"}), 400
        except ProductNotFoundError as error:
            return jsonify({"error": str(error)}), 404
        except (InsufficientStockError, InvalidQuantityError) as error:
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
    def list_orders_endpoint():
        orders = list_orders.execute()
        return jsonify([asdict(order) for order in orders]), 200

    return blueprint

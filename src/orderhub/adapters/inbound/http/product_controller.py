from typing import Callable

from flask import Blueprint, jsonify, request

from orderhub.adapters.inbound.http.require_role import require_role
from orderhub.application.use_cases.create_product import CreateProduct
from orderhub.application.use_cases.list_products import ListProducts
from orderhub.domain.entities.product import Product
from orderhub.domain.exceptions import (
    InvalidProductNameError,
    InvalidProductPriceError,
    InvalidStockError,
)

ADMIN_ROLE = "admin"


def _serialize(product: Product) -> dict:
    """Representación JSON de un producto. Única en el adaptador."""
    return {
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "stock": product.stock,
    }


def create_product_blueprint(
    create_product: CreateProduct,
    list_products: ListProducts,
    jwt_required: Callable,
) -> Blueprint:
    """Adaptador primario HTTP para el catálogo de productos.

    POST /products es una operación administrativa (RF-01.4): exige token
    válido (@jwt_required) y rol admin (require_role). El decorador de
    autenticación se inyecta porque depende del TokenServicePort.

    GET /products (RF-02.1) exige token pero NO rol admin: consultar el
    catálogo es lo que hace cualquier comprador antes de crear una orden,
    mismo criterio que POST /create_order.
    """
    blueprint = Blueprint("products", __name__)

    @blueprint.route("/products", methods=["GET"])
    @jwt_required
    def list_products_endpoint():
        products = list_products.execute()
        return jsonify([_serialize(product) for product in products]), 200

    @blueprint.route("/products", methods=["POST"])
    @jwt_required
    @require_role(ADMIN_ROLE)
    def create_product_endpoint():
        data = request.get_json(silent=True) or {}

        # Lo único que valida el controller es la forma del JSON; las reglas
        # de negocio (nombre no vacío, precio positivo) viven en Product.create.
        try:
            price = float(data.get("price"))
            stock = int(data.get("stock", 0))
        except (TypeError, ValueError):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "price debe ser numérico y stock entero",
                    }
                ),
                400,
            )

        try:
            product = create_product.execute(
                name=data.get("name"),
                price=price,
                stock=stock,
            )
        except (
            InvalidProductNameError,
            InvalidProductPriceError,
            InvalidStockError,
        ) as error:
            return jsonify({"status": "error", "message": str(error)}), 400

        return (
            jsonify({"status": "success", "product": _serialize(product)}),
            201,
        )

    return blueprint

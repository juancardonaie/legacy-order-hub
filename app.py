import os
import sys

from flask import Flask

from database import init_db

# La nueva arquitectura hexagonal vive en src/; se añade al path mientras el
# proyecto no esté empaquetado.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from orderhub import settings
from orderhub.adapters.inbound.http.auth_controller import create_auth_blueprint
from orderhub.adapters.inbound.http.jwt_required import create_jwt_required
from orderhub.adapters.inbound.http.order_controller import create_order_blueprint
from orderhub.adapters.inbound.http.product_controller import create_product_blueprint
from orderhub.container import Container

# Toda la configuración viene del entorno (.env); ya no hay literales aquí ni
# en un config.py con secretos. Ver RNF-02.1 y DT-01 en el registro de deuda.
app = Flask(__name__)
app.config["SECRET_KEY"] = settings.FLASK_SECRET_KEY

init_db(settings.DATABASE_PATH)

# Composition Root: se construyen las dependencias y se inyectan en el adaptador HTTP.
container = Container(database_path=settings.DATABASE_PATH)

# El decorador de autenticación se construye aquí porque depende del
# TokenServicePort; el Container no conoce Flask.
jwt_required = create_jwt_required(container.token_service)

app.register_blueprint(
    create_order_blueprint(
        create_order=container.create_order,
        list_orders=container.list_orders,
        jwt_required=jwt_required,
    )
)
app.register_blueprint(
    create_auth_blueprint(
        authenticate_user=container.authenticate_user,
        token_service=container.token_service,
    )
)
app.register_blueprint(
    create_product_blueprint(
        create_product=container.create_product,
        list_products=container.list_products,
        jwt_required=jwt_required,
    )
)


@app.route("/")
def index():
    # La UI (static/) es un cliente HTTP externo del backend: no forma parte
    # del hexágono. Flask ya sirve static/ en /static/*; aquí solo se entrega
    # su página de entrada.
    return app.send_static_file("index.html")


# Respuesta original de "/" antes de servir la UI, conservada como referencia
# histórica del sistema legado:
#   "<h1>Bienvenido a Legacy OrderHub API v1.0</h1>
#    <p>Estado del sistema: Producción con Deuda Técnica</p>"

# Los endpoints /login, /create_order, /get_all_orders_legacy, POST /products y
# GET /products fueron migrados a la arquitectura hexagonal y ahora los sirven
# los blueprints registrados arriba.


def _debug_enabled() -> bool:
    """APP_DEBUG activa el depurador de Werkzeug. Apagado por defecto (DT-18)."""
    return os.environ.get("APP_DEBUG", "").strip().lower() in ("1", "true", "yes")


if __name__ == "__main__":
    # Solo loopback: el depurador y la API no deben quedar expuestos en la red.
    app.run(host="127.0.0.1", port=5001, debug=_debug_enabled())

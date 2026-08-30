import os
import sys

from flask import Flask, render_template
import config
from database import init_db

# La nueva arquitectura hexagonal vive en src/; se añade al path mientras el
# proyecto no esté empaquetado.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from orderhub.adapters.inbound.http.auth_controller import create_auth_blueprint
from orderhub.adapters.inbound.http.jwt_required import create_jwt_required
from orderhub.adapters.inbound.http.order_controller import create_order_blueprint
from orderhub.adapters.inbound.http.product_controller import create_product_blueprint
from orderhub.container import Container

DB_PATH = "orderhub.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY

init_db()

# Composition Root: se construyen las dependencias y se inyectan en el adaptador HTTP.
container = Container(database_path=DB_PATH)

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
        jwt_required=jwt_required,
    )
)


@app.route("/")
def index():
    return render_template("index.html")


# Respuesta original de "/" antes de servir la plantilla, conservada como
# referencia histórica del sistema legado:
#   "<h1>Bienvenido a Legacy OrderHub API v1.0</h1>
#    <p>Estado del sistema: Producción con Deuda Técnica</p>"

# Los endpoints /login, /create_order y /get_all_orders_legacy fueron
# migrados a la arquitectura hexagonal y ahora los sirven los blueprints
# registrados arriba.

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)

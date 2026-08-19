import os
import sys

from flask import Flask, render_template
import config
from database import init_db

# La nueva arquitectura hexagonal vive en src/; se añade al path mientras el
# proyecto no esté empaquetado.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from orderhub.adapters.inbound.http.auth_controller import create_auth_blueprint
from orderhub.adapters.inbound.http.order_controller import create_order_blueprint
from orderhub.container import Container

DB_PATH = 'orderhub.db'

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

init_db()

# Composition Root: se construyen las dependencias y se inyectan en el adaptador HTTP.
container = Container(database_path=DB_PATH)
app.register_blueprint(
    create_order_blueprint(
        create_order=container.create_order,
        list_orders=container.list_orders,
    )
)
app.register_blueprint(
    create_auth_blueprint(authenticate_user=container.authenticate_user)
)

@app.route('/')
def index():
    return render_template('index.html')
# "<h1>Bienvenido a Legacy OrderHub API v1.0</h1><p>Estado del sistema: Producción con Deuda Técnica</p>"

# Los endpoints /login, /create_order y /get_all_orders_legacy fueron
# migrados a la arquitectura hexagonal y ahora los sirven los blueprints
# registrados arriba.

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
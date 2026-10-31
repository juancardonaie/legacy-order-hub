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
from orderhub.adapters.inbound.http.rate_limiting import (
    install_rate_limiting,
    rate_limit_by_ip,
    rate_limit_by_user,
)
from orderhub.adapters.inbound.http.user_controller import create_user_blueprint
from orderhub.container import Container

# Toda la configuración viene del entorno (.env); ya no hay literales aquí ni
# en un config.py con secretos. Ver RNF-02.1 y DT-01 en el registro de deuda.
app = Flask(__name__)
app.config["SECRET_KEY"] = settings.FLASK_SECRET_KEY

# Fuera de development no se siembran usuarios de demostración (DT-15). El primer
# administrador sale de ADMIN_USERNAME y ADMIN_PASSWORD, que solo se leen aquí y
# nunca se registran.
init_db(
    settings.DATABASE_PATH,
    app_env=settings.APP_ENV,
    admin_username=os.environ.get("ADMIN_USERNAME"),
    admin_password=os.environ.get("ADMIN_PASSWORD"),
)

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
        rate_limit=rate_limit_by_ip(container.rate_limiters.login),
    )
)
app.register_blueprint(
    create_product_blueprint(
        create_product=container.create_product,
        list_products=container.list_products,
        jwt_required=jwt_required,
    )
)
app.register_blueprint(
    create_user_blueprint(
        create_user=container.create_user,
        jwt_required=jwt_required,
        rate_limit=rate_limit_by_user(container.rate_limiters.users),
    )
)

# Límite global por IP (excluye "/" y "/static/*") y, si TRUSTED_PROXY_HOPS > 0,
# ProxyFix para leer la IP real detrás de un proxy.
install_rate_limiting(
    app,
    container.rate_limiters.global_,
    trusted_proxy_hops=settings.TRUSTED_PROXY_HOPS,
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


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5001
LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def _server_options() -> dict:
    """Host, puerto y debug del servidor de desarrollo (`python app.py`).

    Por defecto solo loopback y puerto 5001. APP_HOST y PORT permiten cambiarlos;
    en producción el servidor es gunicorn (ver gunicorn.conf.py) y esto no se usa.
    """
    host = os.environ.get("APP_HOST", "").strip() or DEFAULT_HOST
    raw_port = os.environ.get("PORT", "").strip() or str(DEFAULT_PORT)
    try:
        port = int(raw_port)
    except ValueError:
        raise RuntimeError(f"PORT debe ser un entero, no '{raw_port}'") from None
    debug = _debug_enabled()
    if debug and host not in LOOPBACK_HOSTS:
        raise RuntimeError(
            "APP_DEBUG solo se permite en loopback: el depurador de Werkzeug "
            f"ejecuta código y APP_HOST es '{host}' (DT-18)"
        )
    return {"host": host, "port": port, "debug": debug}


if __name__ == "__main__":
    app.run(**_server_options())

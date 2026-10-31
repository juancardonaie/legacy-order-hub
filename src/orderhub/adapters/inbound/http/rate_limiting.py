"""Adaptador HTTP del límite de peticiones.

Traduce un limitador (`rate_limiter.py`) a Flask: elige la clave (IP o usuario),
responde 429 con `Retry-After` y aplica el límite global. Vive en el adaptador
de entrada; ni el dominio ni la capa de aplicación saben que existe.
"""

from functools import wraps
from typing import Callable

from flask import Flask, g, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix

UNKNOWN_IP = "desconocida"


def _client_ip() -> str:
    # remote_addr es la IP del cliente solo si ProxyFix la reescribió (detrás de
    # un proxy de confianza); si no, X-Forwarded-For se ignora.
    return request.remote_addr or UNKNOWN_IP


def too_many_requests(retry_after: int):
    response = jsonify(
        {
            "status": "error",
            "message": f"Demasiadas peticiones. Intenta de nuevo en {retry_after} s",
        }
    )
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def _limit_by(limiter, key_for: Callable[[], str]) -> Callable:
    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            retry_after = limiter.hit(key_for())
            if retry_after:
                return too_many_requests(retry_after)
            return view(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_by_ip(limiter) -> Callable:
    """Decorador que limita la vista por IP del cliente."""
    return _limit_by(limiter, lambda: f"ip:{_client_ip()}")


def rate_limit_by_user(limiter) -> Callable:
    """Decorador que limita la vista por user_id del token.

    Debe ir debajo de @jwt_required. Si no hubiera identidad, cae a la IP.
    """

    def key_for() -> str:
        current_user = g.get("current_user")
        if current_user is None:
            return f"ip:{_client_ip()}"
        return f"user:{current_user.user_id}"

    return _limit_by(limiter, key_for)


def install_rate_limiting(
    app: Flask, global_limiter, trusted_proxy_hops: int = 0
) -> None:
    """Único punto de cableado del límite global y del proxy.

    - `trusted_proxy_hops` > 0 aplica ProxyFix(x_for=N): se confía en las N
      últimas entradas de X-Forwarded-For (las que añaden tus proxies). Con 0 no
      se confía en la cabecera, que cualquier cliente puede falsificar.
    - El límite global por IP no cuenta `/` ni `/static/*`.
    """
    if trusted_proxy_hops > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=trusted_proxy_hops)

    @app.before_request
    def global_rate_limit():
        if request.endpoint == "static" or request.path == "/":
            return None
        retry_after = global_limiter.hit(f"ip:{_client_ip()}")
        if retry_after:
            return too_many_requests(retry_after)
        return None

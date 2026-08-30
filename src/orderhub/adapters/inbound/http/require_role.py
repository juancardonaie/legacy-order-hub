"""Decorador de autorización por rol para el adaptador HTTP (RF-01.4).

Se apoya en la identidad que @jwt_required ya dejó en `flask.g.current_user`:
no vuelve a leer ni a decodificar el token. Autenticación y autorización son
dos pasos distintos y se componen apilando los dos decoradores.

A diferencia de jwt_required, este decorador no necesita ninguna dependencia
inyectada, así que la fábrica es el propio `require_role(*roles)`: no hay
estado global ni singletons.
"""

from functools import wraps
from typing import Callable

from flask import g, jsonify


def require_role(*roles: str) -> Callable:
    """Restringe la vista a los roles indicados.

    Devuelve 403 (no 401) cuando el usuario está autenticado pero su rol no
    basta: 401 significa "no sé quién eres", 403 significa "sé quién eres y
    aun así no puedes".
    """
    if not roles:
        raise ValueError("require_role necesita al menos un rol")

    allowed = frozenset(roles)

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            current_user = g.get("current_user")
            if current_user is None:
                # Error de programación, no del cliente: la vista se decoró
                # con require_role sin poner @jwt_required encima. Se falla
                # ruidosamente en vez de devolver un 401/403 que escondería
                # el cableado mal hecho.
                raise RuntimeError(
                    "require_role requiere @jwt_required por encima: "
                    "no hay identidad en g.current_user"
                )

            if current_user.role not in allowed:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": (
                                "No tienes permisos para esta operación. "
                                f"Se requiere rol: {', '.join(sorted(allowed))}"
                            ),
                        }
                    ),
                    403,
                )

            return view(*args, **kwargs)

        return wrapper

    return decorator

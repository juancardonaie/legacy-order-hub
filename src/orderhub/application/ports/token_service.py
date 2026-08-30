"""Puerto de salida hacia el servicio de tokens de sesión.

Esta capa no conoce JWT ni ninguna librería concreta: solo declara el contrato
"genera un token a partir de un usuario" y "verifica un token y devuelve quién
es". La implementación con PyJWT vive en adapters/outbound/security/.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from orderhub.domain.entities.user import User


class TokenError(Exception):
    """Error base al procesar un token de sesión.

    Se define aquí, y no en el adaptador, para que quien consume el puerto
    pueda capturar el fallo sin importar la librería concreta que lo produjo.
    """


class InvalidTokenError(TokenError):
    def __init__(self) -> None:
        super().__init__("Token inválido")


class ExpiredTokenError(TokenError):
    def __init__(self) -> None:
        super().__init__("Token expirado")


@dataclass(frozen=True)
class TokenPayload:
    """Identidad transportada por el token, ya traducida desde el formato
    concreto del proveedor."""

    user_id: int
    username: str
    role: str


class TokenServicePort(ABC):
    """Puerto de salida para emitir y verificar tokens de sesión."""

    @abstractmethod
    def generate(self, user: User) -> str:
        """Emite un token firmado y con expiración para el usuario dado."""

    @abstractmethod
    def verify(self, token: str) -> TokenPayload:
        """Devuelve la identidad del token.

        Lanza ExpiredTokenError si el token expiró e InvalidTokenError si la
        firma no cuadra o el contenido está malformado.
        """

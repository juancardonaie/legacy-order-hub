"""Implementación del puerto de tokens usando PyJWT.

Único punto del proyecto que importa la librería jwt. Traduce sus excepciones
a las del puerto para que las capas superiores no dependan de PyJWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt

from orderhub.application.ports.token_service import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenPayload,
    TokenServicePort,
)
from orderhub.domain.entities.user import User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class JWTTokenService(TokenServicePort):
    def __init__(
        self,
        secret_key: str,
        expiration_minutes: int,
        algorithm: str = "HS256",
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        """El reloj se inyecta para poder probar la expiración sin esperar."""
        self._secret_key = secret_key
        self._expiration = timedelta(minutes=expiration_minutes)
        self._algorithm = algorithm
        self._clock = clock

    def generate(self, user: User) -> str:
        issued_at = self._clock()
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "iat": issued_at,
            "exp": issued_at + self._expiration,
        }
        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify(self, token: str) -> TokenPayload:
        try:
            claims = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": ["exp", "user_id", "username", "role"]},
            )
        except jwt.ExpiredSignatureError:
            raise ExpiredTokenError()
        except jwt.PyJWTError:
            raise InvalidTokenError()

        return TokenPayload(
            user_id=claims["user_id"],
            username=claims["username"],
            role=claims["role"],
        )

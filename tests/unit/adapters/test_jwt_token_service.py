"""Tests unitarios de JWTTokenService.

No levantan Flask ni tocan la base de datos. La expiración se comprueba
inyectando un reloj falso en lugar de usar sleep().
"""

from datetime import datetime, timedelta, timezone

import pytest

from orderhub.adapters.outbound.security.jwt_token_service import JWTTokenService
from orderhub.application.ports.token_service import (
    ExpiredTokenError,
    InvalidTokenError,
)
from orderhub.domain.entities.user import User

# HS256 pide al menos 32 bytes de clave (RFC 7518); si no, PyJWT avisa.
SECRET = "secreto-de-pruebas-con-32-bytes-o-mas"
EXPIRATION_MINUTES = 15


@pytest.fixture
def user() -> User:
    return User(id=7, username="juan", password_hash="irrelevante", role="admin")


@pytest.fixture
def token_service() -> JWTTokenService:
    return JWTTokenService(secret_key=SECRET, expiration_minutes=EXPIRATION_MINUTES)


def test_un_token_recien_emitido_se_verifica_correctamente(token_service, user):
    payload = token_service.verify(token_service.generate(user))

    assert payload.user_id == user.id
    assert payload.username == user.username
    assert payload.role == user.role


def test_rechaza_un_token_con_la_firma_alterada(token_service, user):
    header, payload, signature = token_service.generate(user).split(".")

    # Se altera el PRIMER carácter de la firma, no el último: en base64url el
    # último carácter de una firma de 32 bytes solo aporta 4 de sus 6 bits, así
    # que hay sustituciones que decodifican al mismo byte y dejarían la firma
    # intacta (el test sería intermitente).
    alterada = ("A" if signature[0] != "A" else "B") + signature[1:]

    with pytest.raises(InvalidTokenError):
        token_service.verify(f"{header}.{payload}.{alterada}")


def test_rechaza_un_token_con_el_payload_manipulado(token_service, user):
    """Escalada de privilegios: cambiar el rol invalida la firma."""
    header, payload, signature = token_service.generate(user).split(".")
    otro_payload = token_service.generate(
        User(id=99, username="intruso", password_hash="x", role="admin")
    ).split(".")[1]

    with pytest.raises(InvalidTokenError):
        token_service.verify(f"{header}.{otro_payload}.{signature}")


def test_rechaza_un_token_firmado_con_otra_clave(user):
    intruso = JWTTokenService(
        secret_key="otra-clave-distinta-de-32-bytes-o-mas", expiration_minutes=15
    )
    legitimo = JWTTokenService(secret_key=SECRET, expiration_minutes=15)

    with pytest.raises(InvalidTokenError):
        legitimo.verify(intruso.generate(user))


def test_rechaza_un_token_expirado(user, token_service):
    # Reloj falso situado en el pasado: el token nace ya caducado respecto al
    # reloj real con el que se verifica. Sin sleep().
    pasado = datetime.now(timezone.utc) - timedelta(minutes=EXPIRATION_MINUTES + 1)
    emisor_en_el_pasado = JWTTokenService(
        secret_key=SECRET,
        expiration_minutes=EXPIRATION_MINUTES,
        clock=lambda: pasado,
    )

    with pytest.raises(ExpiredTokenError):
        token_service.verify(emisor_en_el_pasado.generate(user))


def test_rechaza_una_cadena_que_no_es_un_jwt(token_service):
    with pytest.raises(InvalidTokenError):
        token_service.verify("esto-no-es-un-token")

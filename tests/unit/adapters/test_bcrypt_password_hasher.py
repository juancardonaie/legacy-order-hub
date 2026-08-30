"""Tests de BcryptPasswordHasher (RF-01.2).

Usa bcrypt de verdad: es el adaptador cuyo trabajo es precisamente hablar con
esa librería. No hay base de datos ni Flask.
"""

import bcrypt
import pytest

from orderhub.adapters.outbound.security.bcrypt_password_hasher import (
    BcryptPasswordHasher,
)

PASSWORD = "contraseña-de-prueba"


def _hash(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


@pytest.fixture(scope="module")
def password_hash() -> str:
    """bcrypt es lento a propósito: se calcula una vez para todo el módulo."""
    return _hash(PASSWORD)


@pytest.fixture
def hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher()


def test_acepta_la_contrasena_correcta(hasher, password_hash):
    assert hasher.verify(PASSWORD, password_hash) is True


def test_rechaza_una_contrasena_incorrecta(hasher, password_hash):
    assert hasher.verify("otra-contrasena", password_hash) is False


def test_rechaza_una_contrasena_vacia(hasher, password_hash):
    assert hasher.verify("", password_hash) is False


def test_distingue_mayusculas_y_minusculas(hasher, password_hash):
    assert hasher.verify(PASSWORD.upper(), password_hash) is False


def test_el_hash_no_contiene_la_contrasena_en_claro(password_hash):
    assert PASSWORD not in password_hash


def test_dos_hashes_de_la_misma_contrasena_son_distintos(hasher):
    """El salt es aleatorio: dos hashes iguales delatarían su ausencia."""
    primero = _hash(PASSWORD)
    segundo = _hash(PASSWORD)

    assert primero != segundo
    # Y aun así ambos validan la misma contraseña.
    assert hasher.verify(PASSWORD, primero)
    assert hasher.verify(PASSWORD, segundo)


def test_verifica_contrasenas_con_caracteres_no_ascii(hasher):
    clave = "ñandú-Ω-🔐"

    assert hasher.verify(clave, _hash(clave)) is True
    assert hasher.verify("ñandu-Ω-🔐", _hash(clave)) is False

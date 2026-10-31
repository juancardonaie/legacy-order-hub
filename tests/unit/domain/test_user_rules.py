"""Reglas de negocio de User y de la política de credenciales.

Dominio puro: sin Flask, sin sqlite3, sin bcrypt.
"""

import pytest

from orderhub.domain.entities.user import (
    MAX_PASSWORD_BYTES,
    ROLE_ADMIN,
    ROLE_CLIENT,
    User,
    validate_password,
    validate_role,
    validate_username,
)
from orderhub.domain.exceptions import (
    InvalidPasswordError,
    InvalidRoleError,
    InvalidUsernameError,
)


def test_user_create_construye_un_usuario_sin_id():
    user = User.create(username="ana.lopez", password_hash="h", role=ROLE_CLIENT)

    assert user == User(id=None, username="ana.lopez", password_hash="h", role="client")


@pytest.mark.parametrize("role", [ROLE_ADMIN, ROLE_CLIENT])
def test_user_create_acepta_los_dos_roles(role):
    assert User.create("ana", "h", role).role == role


@pytest.mark.parametrize("username", ["abc", "a.b-c_d9", "x" * 32, "123", "a-b"])
def test_acepta_usernames_validos(username):
    validate_username(username)


@pytest.mark.parametrize(
    "username",
    [
        "ab",  # corto
        "x" * 33,  # largo
        "",
        "Ana",  # mayúsculas: se rechazan, no se normalizan
        "ana lopez",
        "ana@mail",
        "ñandú",
        "ana\n",  # el salto de línea final no debe colarse
        None,
        123,
        ["ana"],
    ],
)
def test_rechaza_usernames_invalidos(username):
    with pytest.raises(InvalidUsernameError) as error:
        validate_username(username)

    assert error.value.username == username


def test_user_create_valida_el_username():
    with pytest.raises(InvalidUsernameError):
        User.create("Ana", "h", ROLE_CLIENT)


@pytest.mark.parametrize(
    "role", ["ADMIN", "Admin", "false", "", "root", None, False, True, 1, ["admin"]]
)
def test_rechaza_roles_invalidos(role):
    with pytest.raises(InvalidRoleError) as error:
        validate_role(role)

    assert error.value.role == role


def test_user_create_valida_el_rol():
    with pytest.raises(InvalidRoleError):
        User.create("ana", "h", "superuser")


@pytest.mark.parametrize(
    "password",
    ["12345678", "a" * MAX_PASSWORD_BYTES, "ñ" * 36, "con espacios y ñ 🔐"],
)
def test_acepta_contrasenas_dentro_de_la_politica(password):
    validate_password(password)


@pytest.mark.parametrize("password", ["", "1234567", "corta"])
def test_rechaza_contrasenas_demasiado_cortas(password):
    with pytest.raises(InvalidPasswordError) as error:
        validate_password(password)

    assert "al menos 8" in str(error.value)


@pytest.mark.parametrize("password", ["a" * 73, "ñ" * 37])
def test_rechaza_contrasenas_de_mas_de_72_bytes(password):
    """'ñ' * 37 son 37 caracteres pero 74 bytes UTF-8."""
    with pytest.raises(InvalidPasswordError) as error:
        validate_password(password)

    assert "72 bytes" in str(error.value)


@pytest.mark.parametrize("password", [None, 12345678, ["12345678"], b"12345678"])
def test_rechaza_contrasenas_que_no_son_texto(password):
    with pytest.raises(InvalidPasswordError):
        validate_password(password)


def test_el_error_de_contrasena_no_revela_la_contrasena():
    secreta = "secreta"  # 7 caracteres: incumple el mínimo

    with pytest.raises(InvalidPasswordError) as error:
        validate_password(secreta)

    assert secreta not in str(error.value)

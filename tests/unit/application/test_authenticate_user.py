"""Tests unitarios de AuthenticateUser.

No se importa Flask, sqlite3 ni bcrypt: los puertos se sustituyen por dobles
en memoria, lo que demuestra que el caso de uso está desacoplado de la
infraestructura de persistencia y de hashing.
"""

from typing import Dict, List, Optional

import pytest

from orderhub.application.ports.password_hasher import PasswordHasher
from orderhub.application.ports.user_repository import UserRepository
from orderhub.application.use_cases.authenticate_user import AuthenticateUser
from orderhub.domain.entities.user import User
from orderhub.domain.exceptions import InvalidCredentialsError


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: Optional[List[User]] = None) -> None:
        self._users: Dict[str, User] = {u.username: u for u in (users or [])}

    def find_by_username(self, username: str) -> Optional[User]:
        return self._users.get(username)


class FakePasswordHasher(PasswordHasher):
    """No usa bcrypt: trata el hash como la contraseña en claro con un
    prefijo, suficiente para validar la orquestación del caso de uso."""

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"hashed::{plain_password}"


@pytest.fixture
def user() -> User:
    return User(id=1, username="juan", password_hash="hashed::123456", role="client")


@pytest.fixture
def user_repository(user: User) -> InMemoryUserRepository:
    return InMemoryUserRepository([user])


@pytest.fixture
def password_hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def authenticate_user(user_repository, password_hasher) -> AuthenticateUser:
    return AuthenticateUser(
        user_repository=user_repository,
        password_hasher=password_hasher,
    )


def test_login_exitoso_con_credenciales_correctas(authenticate_user, user):
    result = authenticate_user.execute(username="juan", password="123456")

    assert result == user


def test_rechaza_login_si_el_usuario_no_existe(authenticate_user):
    with pytest.raises(InvalidCredentialsError):
        authenticate_user.execute(username="desconocido", password="123456")


def test_rechaza_login_si_la_contrasena_es_incorrecta(authenticate_user):
    with pytest.raises(InvalidCredentialsError):
        authenticate_user.execute(username="juan", password="incorrecta")

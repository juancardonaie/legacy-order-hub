"""Tests unitarios de CreateUser.

Sin Flask, sqlite3 ni bcrypt: repositorio y hasher son dobles en memoria.
"""

from dataclasses import replace
from typing import Dict, List, Optional

import pytest

from orderhub.application.ports.password_hasher import PasswordHasher
from orderhub.application.ports.user_repository import UserRepository
from orderhub.application.use_cases.create_user import CreateUser
from orderhub.domain.entities.user import User
from orderhub.domain.exceptions import (
    InvalidPasswordError,
    InvalidRoleError,
    InvalidUsernameError,
    UsernameAlreadyExistsError,
)


class InMemoryUserRepository(UserRepository):
    def __init__(self, users: Optional[List[User]] = None) -> None:
        self.users: Dict[str, User] = {u.username: u for u in (users or [])}

    def find_by_username(self, username: str) -> Optional[User]:
        return self.users.get(username)

    def add(self, user: User) -> User:
        if user.username in self.users:
            raise UsernameAlreadyExistsError(user.username)
        saved = replace(user, id=len(self.users) + 1)
        self.users[saved.username] = saved
        return saved


class RacingUserRepository(InMemoryUserRepository):
    """Simula la carrera: find_by_username no ve al otro alta, pero add sí
    choca con ella (la restricción única del almacenamiento)."""

    def find_by_username(self, username: str) -> Optional[User]:
        return None


class SpyPasswordHasher(PasswordHasher):
    def __init__(self) -> None:
        self.hashed: List[str] = []

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == f"hashed::{plain_password}"

    def hash(self, plain_password: str) -> str:
        self.hashed.append(plain_password)
        return f"hashed::{plain_password}"


@pytest.fixture
def user_repository() -> InMemoryUserRepository:
    existing = User(id=1, username="juan", password_hash="x", role="client")
    return InMemoryUserRepository([existing])


@pytest.fixture
def password_hasher() -> SpyPasswordHasher:
    return SpyPasswordHasher()


@pytest.fixture
def create_user(user_repository, password_hasher) -> CreateUser:
    return CreateUser(user_repository=user_repository, password_hasher=password_hasher)


def test_crea_un_usuario_client_por_defecto(create_user, user_repository):
    user = create_user.execute(username="ana", password="clave-segura-1")

    assert user.id == 2
    assert user.username == "ana"
    assert user.role == "client"
    assert user_repository.find_by_username("ana") == user


def test_crea_un_administrador_si_se_pide(create_user):
    user = create_user.execute(username="adm", password="clave-segura-1", role="admin")

    assert user.role == "admin"


def test_guarda_el_hash_y_nunca_la_contrasena(create_user, password_hasher):
    user = create_user.execute(username="ana", password="clave-segura-1")

    assert user.password_hash == "hashed::clave-segura-1"
    assert "clave-segura-1" not in repr(replace(user, password_hash="h"))
    assert password_hasher.hashed == ["clave-segura-1"]


def test_rechaza_un_username_repetido_sin_gastar_el_hash(create_user, password_hasher):
    with pytest.raises(UsernameAlreadyExistsError) as error:
        create_user.execute(username="juan", password="clave-segura-1")

    assert error.value.username == "juan"
    assert password_hasher.hashed == []


def test_propaga_el_conflicto_si_otra_alta_gana_la_carrera(password_hasher):
    repository = RacingUserRepository(
        [User(id=1, username="ana", password_hash="x", role="client")]
    )
    use_case = CreateUser(user_repository=repository, password_hasher=password_hasher)

    with pytest.raises(UsernameAlreadyExistsError):
        use_case.execute(username="ana", password="clave-segura-1")


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"username": "Ana", "password": "clave-segura-1"}, InvalidUsernameError),
        ({"username": "ab", "password": "clave-segura-1"}, InvalidUsernameError),
        (
            {"username": "ana", "password": "clave-segura-1", "role": "ADMIN"},
            InvalidRoleError,
        ),
        (
            {"username": "ana", "password": "clave-segura-1", "role": None},
            InvalidRoleError,
        ),
        ({"username": "ana", "password": "corta"}, InvalidPasswordError),
        ({"username": "ana", "password": "a" * 73}, InvalidPasswordError),
        ({"username": "ana", "password": None}, InvalidPasswordError),
    ],
)
def test_entradas_invalidas_no_hashean_ni_guardan(
    create_user, user_repository, password_hasher, kwargs, error
):
    with pytest.raises(error):
        create_user.execute(**kwargs)

    assert password_hasher.hashed == []
    assert set(user_repository.users) == {"juan"}

"""Tests HTTP de POST /users: solo admin, con límite por usuario.

App Flask real con repositorio y hasher en memoria (sin base de datos ni
bcrypt). El token es el del JWTTokenService real.
"""

from dataclasses import replace
from typing import Dict, List, Optional

import pytest
from flask import Flask

from orderhub.adapters.inbound.http.jwt_required import create_jwt_required
from orderhub.adapters.inbound.http.rate_limiter import InMemoryRateLimiter
from orderhub.adapters.inbound.http.rate_limiting import rate_limit_by_user
from orderhub.adapters.inbound.http.user_controller import create_user_blueprint
from orderhub.adapters.outbound.security.jwt_token_service import JWTTokenService
from orderhub.application.ports.password_hasher import PasswordHasher
from orderhub.application.ports.user_repository import UserRepository
from orderhub.application.use_cases.create_user import CreateUser
from orderhub.domain.entities.user import User
from orderhub.domain.exceptions import UsernameAlreadyExistsError

VALIDO = {"username": "ana", "password": "clave-segura-1"}


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.users: Dict[str, User] = {
            "juan": User(id=2, username="juan", password_hash="x", role="client")
        }
        self.lookups = 0

    def find_by_username(self, username: str) -> Optional[User]:
        self.lookups += 1
        return self.users.get(username)

    def add(self, user: User) -> User:
        if user.username in self.users:
            raise UsernameAlreadyExistsError(user.username)
        saved = replace(user, id=len(self.users) + 10)
        self.users[saved.username] = saved
        return saved


class CountingHasher(PasswordHasher):
    def __init__(self) -> None:
        self.calls: List[str] = []

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return False

    def hash(self, plain_password: str) -> str:
        self.calls.append(plain_password)
        return f"hashed::{plain_password}"


@pytest.fixture
def repository() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def hasher() -> CountingHasher:
    return CountingHasher()


@pytest.fixture
def token_service(jwt_test_secret) -> JWTTokenService:
    return JWTTokenService(secret_key=jwt_test_secret, expiration_minutes=15)


class FakeClock:
    now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter(2, 60, clock=FakeClock())


@pytest.fixture
def http(repository, hasher, token_service, limiter):
    app = Flask(__name__)
    app.testing = True
    app.register_blueprint(
        create_user_blueprint(
            create_user=CreateUser(repository, hasher),
            jwt_required=create_jwt_required(token_service),
            rate_limit=rate_limit_by_user(limiter),
        )
    )
    return app.test_client()


@pytest.fixture
def admin_headers(token_service, admin_user, bearer):
    return bearer(token_service.generate(admin_user))


@pytest.fixture
def client_headers(token_service, client_user, bearer):
    return bearer(token_service.generate(client_user))


# --- Camino feliz -----------------------------------------------------------


def test_admin_crea_un_client_por_defecto(http, admin_headers, repository):
    response = http.post("/users", json=VALIDO, headers=admin_headers)

    assert response.status_code == 201
    assert response.get_json() == {
        "status": "success",
        "user": {"id": 11, "username": "ana", "role": "client"},
    }
    assert repository.users["ana"].password_hash == "hashed::clave-segura-1"


def test_admin_crea_otro_administrador(http, admin_headers):
    body = {**VALIDO, "role": "admin"}

    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "admin"


def test_la_respuesta_no_incluye_contrasena_ni_hash(http, admin_headers):
    response = http.post("/users", json=VALIDO, headers=admin_headers)

    texto = response.get_data(as_text=True)
    assert set(response.get_json()["user"]) == {"id", "username", "role"}
    assert "clave-segura-1" not in texto
    assert "hashed" not in texto


# --- Autenticación y autorización --------------------------------------------


def test_sin_token_recibe_401(http, repository):
    response = http.post("/users", json=VALIDO)

    assert response.status_code == 401
    assert "ana" not in repository.users


def test_un_client_recibe_403_y_no_crea_nada(http, client_headers, repository, hasher):
    response = http.post("/users", json=VALIDO, headers=client_headers)

    assert response.status_code == 403
    assert response.get_json()["status"] == "error"
    assert "ana" not in repository.users
    assert hasher.calls == []


def test_un_client_no_puede_crearse_un_admin_con_role(http, client_headers):
    body = {**VALIDO, "role": "admin"}

    response = http.post("/users", json=body, headers=client_headers)

    assert response.status_code == 403


# --- Validación de entrada ------------------------------------------------------


@pytest.mark.parametrize("body", [[1], ["a"], [], "abc", 5, True, None])
def test_un_body_que_no_es_un_objeto_da_400(http, admin_headers, body):
    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert response.get_json() == {
        "status": "error",
        "message": "El body debe ser un objeto JSON",
    }


def test_un_body_que_no_es_json_da_400(http, admin_headers):
    response = http.post(
        "/users", data="no es json", headers=admin_headers, content_type="text/plain"
    )

    assert response.status_code == 400


@pytest.mark.parametrize(
    "body",
    [
        {"username": ["ana"], "password": "clave-segura-1"},
        {"username": 123, "password": "clave-segura-1"},
        {"username": None, "password": "clave-segura-1"},
        {"password": "clave-segura-1"},
        {"username": "ana", "password": 12345678},
        {"username": "ana", "password": None},
        {"username": "ana"},
        {"username": "ana", "password": "clave-segura-1", "role": None},
        {"username": "ana", "password": "clave-segura-1", "role": False},
        {"username": "ana", "password": "clave-segura-1", "role": 1},
        {"username": "ana", "password": "clave-segura-1", "role": ["admin"]},
    ],
)
def test_los_campos_que_no_son_texto_dan_400_sin_hashear(
    http, admin_headers, repository, hasher, body
):
    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert response.get_json()["message"] == "username, password y role deben ser texto"
    assert hasher.calls == []
    assert "ana" not in repository.users


@pytest.mark.parametrize("role", ["ADMIN", "Admin", "false", "", "root"])
def test_un_rol_que_no_es_admin_ni_client_da_400(http, admin_headers, role, hasher):
    body = {**VALIDO, "role": role}

    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert response.get_json()["message"] == "El rol debe ser 'admin' o 'client'"
    assert hasher.calls == []


@pytest.mark.parametrize(
    "body, fragmento",
    [
        ({"username": "Ana", "password": "clave-segura-1"}, "nombre de usuario"),
        ({"username": "ab", "password": "clave-segura-1"}, "nombre de usuario"),
        ({"username": "ana", "password": "corta"}, "al menos 8"),
        ({"username": "ana", "password": "a" * 73}, "72 bytes"),
    ],
)
def test_las_reglas_del_dominio_dan_400(http, admin_headers, body, fragmento):
    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 400
    assert response.get_json()["status"] == "error"
    assert fragmento in response.get_json()["message"]


def test_el_mensaje_de_error_no_devuelve_la_contrasena(http, admin_headers):
    response = http.post(
        "/users", json={"username": "ana", "password": "corta"}, headers=admin_headers
    )

    assert "corta" not in response.get_json()["message"]


def test_un_username_repetido_da_409(http, admin_headers, hasher):
    body = {"username": "juan", "password": "clave-segura-1"}

    response = http.post("/users", json=body, headers=admin_headers)

    assert response.status_code == 409
    assert response.get_json() == {
        "status": "error",
        "message": "El nombre de usuario ya existe",
    }
    assert hasher.calls == []


# --- Orden de los decoradores: límite antes del body, del hash y de la BD -------


def test_el_limite_se_aplica_antes_de_leer_el_body_y_de_consultar(
    http, admin_headers, repository, hasher
):
    http.post("/users", json=[1], headers=admin_headers)  # 400, cuenta 1
    http.post("/users", json=[1], headers=admin_headers)  # 400, cuenta 2

    response = http.post("/users", json=VALIDO, headers=admin_headers)

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert repository.lookups == 0
    assert hasher.calls == []
    assert "ana" not in repository.users


def test_sin_token_la_peticion_no_gasta_el_limite_del_usuario(
    http, admin_headers, limiter
):
    for _ in range(5):
        assert http.post("/users", json=VALIDO).status_code == 401

    assert len(limiter) == 0
    assert http.post("/users", json=VALIDO, headers=admin_headers).status_code == 201

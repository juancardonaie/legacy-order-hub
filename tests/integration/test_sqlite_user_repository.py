"""Integración de SQLiteUserRepository contra una BD SQLite real.

Punto crítico: la tabla `users` conserva la columna legada `password` en texto
plano. El repositorio debe leer únicamente `password_hash`.
"""

import sqlite3

import pytest

from orderhub.adapters.outbound.persistence.sqlite.connection import (
    SQLiteConnectionFactory,
)
from orderhub.adapters.outbound.persistence.sqlite.sqlite_user_repository import (
    SQLiteUserRepository,
)


@pytest.fixture
def repository(database_path) -> SQLiteUserRepository:
    return SQLiteUserRepository(SQLiteConnectionFactory(database_path))


def test_recupera_un_usuario_por_su_username(repository):
    user = repository.find_by_username("admin")

    assert user.id == 1
    assert user.username == "admin"
    assert user.role == "admin"


def test_un_usuario_inexistente_devuelve_none(repository):
    assert repository.find_by_username("no-existe") is None


def test_lee_password_hash_y_no_la_columna_en_texto_plano(
    repository, connection, admin_password_hash
):
    """La fila tiene password='texto-plano-legado' y un hash bcrypt distinto."""
    fila = connection.execute(
        "SELECT password, password_hash FROM users WHERE username = ?", ("admin",)
    ).fetchone()
    assert fila["password"] == "texto-plano-legado"

    user = repository.find_by_username("admin")

    assert user.password_hash == admin_password_hash
    assert user.password_hash == fila["password_hash"]
    assert user.password_hash != fila["password"]
    assert "texto-plano-legado" not in str(user)


def test_la_entidad_user_no_expone_ningun_campo_password_en_claro(repository):
    user = repository.find_by_username("juan")

    assert not hasattr(user, "password")


def test_distingue_entre_usuarios(repository):
    assert repository.find_by_username("juan").role == "client"
    assert repository.find_by_username("admin").role == "admin"


def test_el_sql_parametrizado_neutraliza_un_intento_de_inyeccion(repository):
    """Con concatenación, esto devolvería el primer usuario de la tabla."""
    inyeccion = "' OR '1'='1"

    assert repository.find_by_username(inyeccion) is None


def test_un_username_con_comilla_simple_se_consulta_sin_romper(
    repository, connection, admin_password_hash
):
    connection.execute(
        "INSERT INTO users (username, password, password_hash, role) "
        "VALUES (?, ?, ?, ?)",
        ("O'Brien", "x", admin_password_hash, "client"),
    )
    connection.commit()

    user = repository.find_by_username("O'Brien")

    assert user is not None
    assert user.username == "O'Brien"


def test_no_se_pueden_guardar_dos_usuarios_con_el_mismo_username(
    connection, admin_password_hash
):
    """DT-09: la unicidad la garantiza el esquema, no el código de aplicación.

    Sin esta restricción, find_by_username() usa fetchone() y devolvería
    silenciosamente el primero que retornara SQLite, autenticando contra un
    hash que podría no ser el del usuario esperado.
    """
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO users (username, password, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            # 'admin' ya existe: lo siembra la fixture database_path.
            ("admin", "x", admin_password_hash, "client"),
        )
        connection.commit()


def test_la_unicidad_no_impide_crear_usuarios_con_username_distinto(
    repository, connection, admin_password_hash
):
    """Contrapartida del test anterior: la restricción no es demasiado amplia."""
    connection.execute(
        "INSERT INTO users (username, password, password_hash, role) "
        "VALUES (?, ?, ?, ?)",
        ("admin2", "x", admin_password_hash, "admin"),
    )
    connection.commit()

    assert repository.find_by_username("admin2") is not None
    assert repository.find_by_username("admin").id == 1

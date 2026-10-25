"""`database.init_db`: siembra solo en development y primer admin por entorno.

Cubre DT-15 (sin credenciales conocidas fuera de desarrollo) y el arranque del
primer administrador desde ADMIN_USERNAME / ADMIN_PASSWORD. Usa una base SQLite
temporal por test; nunca abre orderhub.db.
"""

import sqlite3

import bcrypt
import pytest

import database
from orderhub.container import Container

ADMIN_USERNAME = "operaciones"
ADMIN_PASSWORD = "una-clave-larga-de-prueba"


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    for nombre in ("APP_ENV", "ADMIN_USERNAME", "ADMIN_PASSWORD"):
        monkeypatch.delenv(nombre, raising=False)


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "init_test.db")


def _filas(db_path, sql, params=()):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        return connection.execute(sql, params).fetchall()
    finally:
        connection.close()


def _usuarios(db_path):
    return {
        fila["username"]: fila["role"]
        for fila in _filas(db_path, "SELECT username, role FROM users")
    }


def _productos(db_path):
    return _filas(db_path, "SELECT name FROM products")


# --- Siembra de demostración (DT-15) ------------------------------------------


def test_en_development_se_siembran_los_usuarios_y_productos_de_demostracion(db_path):
    database.init_db(db_path, app_env="development")

    assert _usuarios(db_path) == {"admin": "admin", "juan": "client"}
    assert len(_productos(db_path)) == 2


def test_sin_app_env_se_asume_development(db_path):
    database.init_db(db_path)

    assert _usuarios(db_path) == {"admin": "admin", "juan": "client"}


def test_el_seed_de_demostracion_guarda_hashes_bcrypt_verificables(db_path):
    database.init_db(db_path, app_env="development")

    fila = _filas(
        db_path, "SELECT password_hash FROM users WHERE username = ?", ("juan",)
    )[0]
    assert bcrypt.checkpw(b"123456", fila["password_hash"].encode("utf-8"))


@pytest.mark.parametrize("entorno", ["production", "staging", "cualquier-otro"])
def test_fuera_de_development_no_se_siembra_nada(db_path, entorno):
    database.init_db(db_path, app_env=entorno)

    assert _usuarios(db_path) == {}
    assert _productos(db_path) == []


def test_app_env_se_lee_del_entorno_si_no_se_pasa(db_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")

    database.init_db(db_path)

    assert _usuarios(db_path) == {}


def test_el_seed_no_se_repite_si_ya_hay_usuarios(db_path):
    database.init_db(db_path, app_env="development")
    connection = sqlite3.connect(db_path)
    connection.execute("DELETE FROM users WHERE username = 'juan'")
    connection.commit()
    connection.close()

    database.init_db(db_path, app_env="development")

    assert _usuarios(db_path) == {"admin": "admin"}


# --- Primer administrador desde el entorno ------------------------------------


def test_crea_el_primer_admin_en_produccion(db_path):
    database.init_db(
        db_path,
        app_env="production",
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
    )

    assert _usuarios(db_path) == {ADMIN_USERNAME: "admin"}
    assert _productos(db_path) == []


def test_la_contrasena_del_admin_solo_se_guarda_como_hash(db_path):
    database.init_db(
        db_path,
        app_env="production",
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
    )

    fila = _filas(db_path, "SELECT * FROM users")[0]
    assert fila["password"] is None
    assert ADMIN_PASSWORD not in [str(valor) for valor in tuple(fila)]
    assert bcrypt.checkpw(
        ADMIN_PASSWORD.encode("utf-8"), fila["password_hash"].encode("utf-8")
    )


def test_es_idempotente_y_no_toca_a_un_admin_existente(db_path):
    argumentos = dict(
        app_env="production",
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
    )
    database.init_db(db_path, **argumentos)
    antes = _filas(db_path, "SELECT * FROM users")[0]["password_hash"]

    database.init_db(db_path, **argumentos)
    database.init_db(db_path, **argumentos)

    filas = _filas(db_path, "SELECT * FROM users")
    assert len(filas) == 1
    assert filas[0]["password_hash"] == antes


def test_no_cambia_ni_el_rol_ni_la_contrasena_de_un_usuario_que_ya_existe(db_path):
    database.init_db(db_path, app_env="development")
    antes = _filas(db_path, "SELECT * FROM users WHERE username = 'juan'")[0]

    database.init_db(
        db_path,
        app_env="production",
        admin_username="juan",
        admin_password="otra-contrasena-distinta",
    )

    despues = _filas(db_path, "SELECT * FROM users WHERE username = 'juan'")[0]
    assert despues["role"] == "client"
    assert despues["password_hash"] == antes["password_hash"]


def test_las_variables_admin_se_leen_del_entorno_si_no_se_pasan(db_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_USERNAME", f"  {ADMIN_USERNAME}  ")
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    database.init_db(db_path)

    assert _usuarios(db_path) == {ADMIN_USERNAME: "admin"}


def test_tambien_crea_el_admin_en_development_si_se_define(db_path):
    database.init_db(
        db_path,
        app_env="development",
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
    )

    assert _usuarios(db_path) == {
        "admin": "admin",
        "juan": "client",
        ADMIN_USERNAME: "admin",
    }


@pytest.mark.parametrize("usuario, clave", [("", ""), ("   ", "   "), (None, None)])
def test_sin_variables_o_vacias_no_se_crea_ningun_admin(db_path, usuario, clave):
    database.init_db(
        db_path,
        app_env="production",
        admin_username=usuario,
        admin_password=clave,
    )

    assert _usuarios(db_path) == {}


@pytest.mark.parametrize(
    "usuario, clave",
    [(ADMIN_USERNAME, ""), ("", ADMIN_PASSWORD), (ADMIN_USERNAME, " ")],
)
def test_definir_solo_una_de_las_dos_variables_falla_claro(db_path, usuario, clave):
    with pytest.raises(ValueError) as error:
        database.init_db(
            db_path,
            app_env="production",
            admin_username=usuario,
            admin_password=clave,
        )

    mensaje = str(error.value)
    assert "ADMIN_USERNAME" in mensaje and "ADMIN_PASSWORD" in mensaje
    assert ADMIN_PASSWORD not in mensaje


def test_rechaza_una_contrasena_de_mas_de_72_bytes_sin_revelarla(db_path):
    larga = "x" * 73

    with pytest.raises(ValueError) as error:
        database.init_db(
            db_path,
            app_env="production",
            admin_username=ADMIN_USERNAME,
            admin_password=larga,
        )

    assert "72" in str(error.value)
    assert larga not in str(error.value)
    assert _usuarios(db_path) == {}


def test_crea_el_admin_sobre_una_base_legada_sin_password_hash(db_path):
    connection = sqlite3.connect(db_path)
    connection.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            role TEXT
        );
        INSERT INTO users (username, password, role) VALUES ('viejo', 'abc', 'client');
        """
    )
    connection.commit()
    connection.close()

    database.init_db(
        db_path,
        app_env="production",
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
    )

    assert _usuarios(db_path) == {"viejo": "client", ADMIN_USERNAME: "admin"}
    hashes = _filas(db_path, "SELECT password_hash FROM users")
    assert all(fila["password_hash"] for fila in hashes)


def test_el_admin_creado_puede_autenticarse_con_la_aplicacion_real(db_path):
    database.init_db(
        db_path,
        app_env="production",
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
    )

    user = Container(database_path=db_path).authenticate_user.execute(
        username=ADMIN_USERNAME, password=ADMIN_PASSWORD
    )

    assert user.role == "admin"

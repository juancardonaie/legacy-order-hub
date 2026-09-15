import os
import sqlite3

import bcrypt

DEFAULT_DATABASE_PATH = "orderhub.db"


def _resolve_database_path(database_path=None):
    """Ruta del fichero SQLite: argumento > entorno > valor por defecto.

    Se lee de `os.environ` en vez de importar `orderhub.settings` porque
    `app.py` importa este módulo antes de añadir `src/` al sys.path. El valor
    efectivo lo decide igualmente `settings.DATABASE_PATH`, que es quien lo
    pasa explícitamente desde el arranque.
    """
    if database_path is not None:
        return database_path
    return os.environ.get("DATABASE_PATH", DEFAULT_DATABASE_PATH)


def get_db_connection(database_path=None):
    conn = sqlite3.connect(_resolve_database_path(database_path))
    conn.row_factory = sqlite3.Row
    return conn


def _hash_password(plain_password):
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )


def _ensure_password_hash_column(conn):
    """Migración mínima: agrega password_hash si la BD viene del esquema legado.

    La columna `password` en texto plano se conserva porque
    _backfill_password_hashes la necesita como origen para calcular el hash de
    las bases anteriores, que solo tienen la contraseña en claro. Ningún
    código de autenticación la lee: SQLiteUserRepository consulta únicamente
    password_hash. Ver DT-03 en docs/TECHNICAL_DEBT_LOG.md.
    """
    cursor = conn.cursor()
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if "password_hash" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        conn.commit()


def _ensure_unique_username_index(conn):
    """Aplica la unicidad de username también a las bases ya creadas.

    `CREATE TABLE IF NOT EXISTS` no modifica una tabla existente, así que el
    UNIQUE declarado en el esquema solo alcanza a las bases nuevas. Un índice
    único impone exactamente la misma restricción sobre una tabla ya creada,
    sin tener que recrearla ni mover datos.

    Es idempotente y seguro de re-ejecutar. Si una base heredada tuviera
    usernames duplicados, la creación del índice fallará con IntegrityError:
    es el comportamiento deseado, porque esos datos deben resolverse a mano
    antes de poder garantizar la restricción. Ver DT-09 en
    docs/TECHNICAL_DEBT_LOG.md.
    """
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username)"
    )
    conn.commit()


def _backfill_password_hashes(conn):
    """Genera password_hash con bcrypt para las filas que todavía no lo tienen."""
    cursor = conn.cursor()
    rows = cursor.execute(
        "SELECT id, password FROM users WHERE password_hash IS NULL"
    ).fetchall()
    for row in rows:
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (_hash_password(row["password"]), row["id"]),
        )
    if rows:
        conn.commit()


def init_db(database_path=None):
    conn = get_db_connection(database_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            password_hash TEXT,
            role TEXT
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            stock INTEGER
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total REAL,
            status TEXT
        )
    """
    )

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            ("admin", "admin123", _hash_password("admin123"), "admin"),
        )
        cursor.execute(
            "INSERT INTO users (username, password, password_hash, role) "
            "VALUES (?, ?, ?, ?)",
            ("juan", "123456", _hash_password("123456"), "client"),
        )
        cursor.execute(
            "INSERT INTO products (name, price, stock) "
            "VALUES ('Laptop Legada', 1200.00, 5)"
        )
        cursor.execute(
            "INSERT INTO products (name, price, stock) VALUES ('Mouse USB', 15.50, 50)"
        )
        conn.commit()

    _ensure_password_hash_column(conn)
    _ensure_unique_username_index(conn)
    _backfill_password_hashes(conn)

    conn.close()

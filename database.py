import sqlite3

import bcrypt

def get_db_connection():
    conn = sqlite3.connect('orderhub.db')
    conn.row_factory = sqlite3.Row
    return conn

def _hash_password(plain_password):
    return bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def _ensure_password_hash_column(conn):
    """Migración mínima: agrega password_hash si la BD viene del esquema legado.

    Se conserva la columna `password` en texto plano para no romper el
    endpoint /login legado, que todavía la utiliza.
    """
    cursor = conn.cursor()
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()]
    if 'password_hash' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
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
            (_hash_password(row['password']), row['id']),
        )
    if rows:
        conn.commit()

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            password_hash TEXT,
            role TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price REAL,
            stock INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total REAL,
            status TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password, password_hash, role) VALUES (?, ?, ?, ?)",
            ('admin', 'admin123', _hash_password('admin123'), 'admin'),
        )
        cursor.execute(
            "INSERT INTO users (username, password, password_hash, role) VALUES (?, ?, ?, ?)",
            ('juan', '123456', _hash_password('123456'), 'client'),
        )
        cursor.execute("INSERT INTO products (name, price, stock) VALUES ('Laptop Legada', 1200.00, 5)")
        cursor.execute("INSERT INTO products (name, price, stock) VALUES ('Mouse USB', 15.50, 50)")
        conn.commit()

    _ensure_password_hash_column(conn)
    _backfill_password_hashes(conn)

    conn.close()
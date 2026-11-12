import os
import psycopg2
from psycopg2.extras import RealDictCursor

def connect():
    """Параметры можно задать переменными окружения либо изменить значения по умолчанию."""
    return psycopg2.connect(
        host=os.getenv("STUDUCHET_DB_HOST", "localhost"),
        port=os.getenv("STUDUCHET_DB_PORT", "5432"),
        dbname=os.getenv("STUDUCHET_DB_NAME", "studuchet"),
        user=os.getenv("STUDUCHET_DB_USER", "postgres"),
        password=os.getenv("STUDUCHET_DB_PASSWORD", "1234"),
        cursor_factory=RealDictCursor,
    )

def query(sql, params=None, fetch=False):
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                if fetch:
                    return cur.fetchall()
                return cur.rowcount
    finally:
        conn.close()

def one(sql, params=None):
    rows = query(sql, params, fetch=True)
    return rows[0] if rows else None

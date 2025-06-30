from psycopg2 import pool
from contextlib import contextmanager

import os

# Create connection pool
connection_pool = pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    host="localhost",
    database="mydb",
    user="user",
    password="pass"
)

@contextmanager
def get_db_connection():
    conn = connection_pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        connection_pool.putconn(conn)

# Usage
def get_user_data(user_id):
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()
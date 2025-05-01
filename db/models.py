# Работа с PostgreSQL: пользователи, админы, одобрение, удаление

import os
from datetime import datetime
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()

# Подключение к БД
conn = psycopg.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    row_factory=dict_row
)

# Инициализация таблицы пользователей
def init_db():
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                name TEXT,
                approved_at TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE
            )
        """)
        conn.commit()

# Загрузить список одобренных пользователей
def load_approved_users_db():
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE approved_at IS NOT NULL")
        rows = cur.fetchall()
        return {
            str(row['id']): {
                "name": row['name'],
                "approved_at": row['approved_at'].strftime("%Y-%m-%d %H:%M:%S") if row['approved_at'] else None,
                "is_admin": row['is_admin']
            } for row in rows
        }

# Добавить пользователя и пометить как одобренного
def approve_user_db(user_id: int, name: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (id, name, approved_at, is_admin)
            VALUES (%s, %s, now(), FALSE)
            ON CONFLICT (id) DO UPDATE SET 
                name = EXCLUDED.name,
                approved_at = now(),
                is_admin = users.is_admin
            """,
            (user_id, name)
        )
        conn.commit()

# Удалить пользователя
def reject_user_db(user_id: int):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()

# Получить всех пользователей
def get_all_users():
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users")
        return cur.fetchall()

# Получить пользователей без одобрения
def get_pending_users():
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE approved_at IS NULL")
        return cur.fetchall()

# Проверка: является ли пользователь админом
def is_admin(user_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT is_admin FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return row is not None and row['is_admin']

# Назначить админом
def make_admin(user_id: int):
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET is_admin = TRUE WHERE id = %s", (user_id,))
        conn.commit()

# Снять админку
def revoke_admin(user_id: int):
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET is_admin = FALSE WHERE id = %s", (user_id,))
        conn.commit()

# Инициализация при импорте
init_db()
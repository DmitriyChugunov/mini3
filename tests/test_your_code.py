import psycopg2
import bcrypt
import pyshorteners
from datetime import datetime
import pytest


# Фикстура для создания соединения с базой данных
@pytest.fixture
def connection():
    host = "127.0.0.1"
    user = "postgres"
    password = "1234"
    db_name = "postgres"

    conn = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name
    )
    conn.autocommit = True
    yield conn
    conn.close()


# Фикстура для создания курсора базы данных
@pytest.fixture
def cursor(connection):
    return connection.cursor()


# Создание таблицы для URL
def create_url_table(cursor):
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id SERIAL PRIMARY KEY,
            original_url TEXT NOT NULL,
            short_url TEXT NOT NULL,
            date_added TIMESTAMP NOT NULL
        )
    ''')


# Регистрация пользователя
def register_user(cursor, username, password):
    hashed_password = bcrypt.hashpw(password.encode('utf-8'),
                                    bcrypt.gensalt()).decode('utf-8')
    cursor.execute("INSERT INTO users (username, password)"
                   " VALUES (%s, %s)", (username, hashed_password))


# Функция для сокращения URL
def shorten_url(cursor, original_url, username):
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_id = cursor.fetchone()
    if user_id:
        user_id = user_id[0]
        shortener = pyshorteners.Shortener()
        short_url = shortener.tinyurl.short(original_url)
        date_added = datetime.now()
        cursor.execute("INSERT INTO url_project (original_url, short_url,"
                       " date_added, user_id) VALUES (%s, %s, %s, %s)",
                       (original_url, short_url, date_added, user_id))
        return short_url
    else:
        return None


# Получение всех сокращенных URL пользователя
def get_user_urls(cursor, username):
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user_id = cursor.fetchone()
    if user_id:
        user_id = user_id[0]
        cursor.execute("SELECT short_url FROM url_project WHERE"
                       " user_id = %s", (user_id,))
        urls = cursor.fetchall()
        return [url[0] for url in urls]
    else:
        return []


# Тесты
def test_create_url_table(cursor):
    create_url_table(cursor)
    cursor.execute("SELECT * FROM url_project")
    assert cursor.fetchone() is not None


def test_register_user(cursor):
    username = "test_user"
    password = "test_password"
    register_user(cursor, username, password)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    assert cursor.fetchone() is not None


def test_shorten_url(cursor):
    username = "test_user"
    original_url = "https://gpt-chatbot.ru/"
    shortened_url = shorten_url(cursor, original_url, username)
    assert shortened_url is not None


def test_get_user_urls(cursor):
    username = "test_user"
    user_urls = get_user_urls(cursor, username)
    assert isinstance(user_urls, list)


if __name__ != "__main__":
    pass
else:
    pytest.main([__file__])

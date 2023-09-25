import psycopg2
import bcrypt
import pyshorteners
from datetime import datetime, timedelta

connection = None

host = "127.0.0.1"
user = "postgres"
password = "1234"
db_name = "postgres"


# Функция для создания таблицы
def test_create_url_table(cursor):
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS url_project (
    id serial PRIMARY KEY,
    user_id INTEGER,
    original_url TEXT NOT NULL,
    short_url TEXT NOT NULL,
    expiration_date DATE,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )"""
    )

    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users (
        id serial PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL
    )"""
    )


# Функция для регистрации пользователя
def test_register_user(cursor, username, password):
    try:
        # Хеширование пароля
        hashed_password = test_hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed_password)
        )
        print("Пользователь успешно зарегистрирован.")
    except Exception as ex:
        print(f"Ошибка при регистрации пользователя: {ex}")


# аутентификации пользователя
def test_login_user(cursor, username, password):
    try:
        # Получаем хешированный пароль из базы данных для данного пользователя
        cursor.execute("SELECT id, password\
         FROM users WHERE username = %s", (username,))
        user_record = cursor.fetchone()

        if user_record:
            stored_password = user_record[1]

            # Проверяем хешированный пароль
            if test_check_password(password, stored_password):
                return user_record[0]

        return None  # Неверное имя пользователя или пароль
    except Exception as ex:
        print(f"Ошибка при входе в систему: {ex}")


# Функция для хеширования пароля
def test_hash_password(password):
    # Генерируем соль (salt)
    salt = bcrypt.gensalt()

    # Хешируем пароль с использованием соли
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

    return hashed_password.decode('utf-8')


# Функция для проверки пароля
def test_check_password(input_password, stored_password):
    # Сравниваем введенный пароль\
    # с хешем пароля из базы данных
    return bcrypt.checkpw(input_password.encode('utf-8'),
                          stored_password.encode('utf-8'))


# удаление истекших ссылок
def test_delete_expired_links(connection):
    try:
        current_date = datetime.now() \
            .date()
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM url_project\
             WHERE expiration_date < %s", (current_date,))
        print("[INFO] Если в базе имелись истекшие ссылки они удалены.")
    except Exception as ex:
        print(f"[INFO] {ex}")


# Функция для получения сжатых ссылок пользователя
def test_get_user_links(cursor, user_id):
    try:
        cursor.execute("SELECT original_url, short_url, expiration_date\
         FROM url_project WHERE user_id = %s",
                       (user_id,))
        user_links = cursor.fetchall()
        return user_links
    except Exception as ex:
        print(f"Ошибка при получении сжатых ссылок пользователя: {ex}")
        return []


# получение даты истечения срока действия сжатой ссылки
def test_get_expiration_date(cursor, short_url):
    try:
        cursor.execute("SELECT expiration_date FROM url_project\
         WHERE short_url = %s", (short_url,))
        expiration_date = cursor.fetchone()
        return expiration_date[0] if expiration_date else None
    except Exception as ex:
        print(f"Ошибка при получении даты истечения\
         срока действия сжатой ссылки: {ex}")
        return None


# соединение с базой данных
try:
    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=db_name
    )
    connection.autocommit = True
    with connection.cursor() as cursor:
        test_create_url_table(cursor)

        user_type = input("Вы зарегистрированный "
                          "пользователь? (да/нет): ").lower()

        if user_type == "да":
            username = input("Введите ваш логин: ")
            password_input = input("Введите ваш пароль: ")

            user_id = test_login_user(cursor, username, password_input)

            if user_id is not None:
                profiles = input("Хотите посмотреть свой профиль?(да/нет)")

                if profiles == "да":
                    user_links = test_get_user_links(cursor, user_id)
                    if user_links:
                        print("Ваши сжатые ссылки:")
                        for link in user_links:
                            original_url, short_url, expiration_date = link
                            print(f"Оригинальная URL ссылка: {original_url}")
                            print(f"Сжатая URL ссылка: {short_url}")
                            print(f"Дата истечения срока"
                                  f" действия: {expiration_date}")
                    else:
                        print("У вас нет сжатых ссылок.")
                else:
                    people_url = input("Введите"
                                       " ссылку для сжатия:")  # переменная для
                    # проверки введенной ссылки
                    expiration_days = int(
                        input("Введите количество дней"
                              " для срока действия ссылки:"))
                    # Запросить срок действия в днях
                    s = pyshorteners.Shortener()
                    # Оригинальная URL ссылка
                    if people_url.startswith("http://") or \
                            people_url.startswith(
                            "https://"):  # проверка введенного текста
                        short_url = s.tinyurl.short(people_url)
                        print("Оригинальная URL ссылка:", people_url)
                        print("Сжатая URL ссылка:", short_url)
                        # Получите идентификатор текущего
                        # пользователя из предыдущего входа в систему
                        user_id = test_login_user(cursor,
                                                  username, password_input)
                        if user_id is not None:
                            # сохранние в базе данных
                            expiration_date = datetime.now()\
                                              + timedelta(days=expiration_days)
                            cursor.execute(
                                "INSERT INTO url_project"
                                " (user_id, original_url,\
                                 short_url, expiration_date)"
                                " VALUES (%s, %s,"
                                " %s, %s)",
                                (user_id, people_url,
                                 short_url, expiration_date))
                            connection.commit()
                            print(f"Ссылка действительна до {expiration_date}")
                        else:
                            print("Невозможно добавить ссылку"
                                  " в профиль: неправильное имя"
                                  " пользователя или пароль.")
                    else:
                        print("Введен текст не похожий на ссылку.")
            else:
                print("Неправильное имя пользователя или пароль.")
        else:
            user_type2 = input(
                "Свои ссылки можно сжимать только после"
                " регистрации. Вы хотите зарегистрироваться?(да/нет)")
            if user_type2 == "да":
                new_username = input("Введите логин для регистрации: ")
                new_password = input("Введите пароль для регистрации: ")
                test_register_user(cursor, new_username, new_password)
                print("Вы можете войти или зарегистрироваться"
                      " для использования сервиса сжатия URL.")
            else:
                print("Незарегистрированным пользователям"
                      " можно только посмотреть"
                      " работу сжатия наших ссылок:")
                original_url2 = "https://auth.hr.alabuga.ru/auth/" \
                                "realms/Alabuga/protocol/openid-connect/" \
                                "auth?client_id=alb-player&redirect_uri=" \
                                "https%3A%2F%2Fhr.alabuga.ru%2F&state" \
                                "=850b5984-7872-4179-" \
                                "bcfd-abad20025de3&response"
                s = pyshorteners\
                    .Shortener()
                short_url2 = s.tinyurl.short(original_url2)
                # переменная = сжатие оригинальной ссылки

                print("Оригинальная URL ссылка:", original_url2)
                print("Сжатая URL ссылка:", short_url2)

except Exception as ex:
    print(f"[INFO] {ex}")
finally:
    if connection:
        test_delete_expired_links(connection)  # соединение в функцию
        connection.commit()
        connection.close()
        print("[INFO] PostgreSQL закончил свою работу.")

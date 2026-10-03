"""One-time migration of legacy plaintext user passwords to Werkzeug hashes."""

import os

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error
from werkzeug.security import generate_password_hash

load_dotenv()


def main():
    connection = None
    cursor = None
    try:
        password = os.environ.get("MYSQL_PASSWORD")
        if not password:
            raise RuntimeError("Set MYSQL_PASSWORD before running this migration.")

        connection = mysql.connector.connect(
            host=os.environ.get("MYSQL_HOST", "localhost"),
            user=os.environ.get("MYSQL_USER", "root"),
            password=password,
            database=os.environ.get("MYSQL_DATABASE", "nasa_food_inventory"),
        )
        cursor = connection.cursor()
        cursor.execute("SELECT user_id, password FROM users")
        users = cursor.fetchall()

        migrated = 0
        for user_id, stored_password in users:
            if stored_password.startswith(("scrypt:", "pbkdf2:")):
                continue
            cursor.execute(
                "UPDATE users SET password = %s WHERE user_id = %s",
                (generate_password_hash(stored_password), user_id),
            )
            migrated += 1

        connection.commit()
        print(f"Migrated {migrated} plaintext password(s).")
    except (Error, RuntimeError):
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    main()

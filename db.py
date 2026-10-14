import os
import mysql.connector
from mysql.connector import Error


DB_CONFIG = {
    'host': os.environ.get('DB_HOST')
            or os.environ.get('MYSQLHOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'database': os.environ.get('DB_NAME', 'spendwise_db'),
    'autocommit': True
}


def get_db_connection():
    """Create and return a MySQL database connection."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as e:
        print(f"[Database Error] Connection failed: {e}")
        return None


def init_db():
    """
    Create the database and required tables if they do not exist.
    Existing users and transactions are preserved.
    """

    server_config = DB_CONFIG.copy()
    server_config.pop('database', None)

    conn = None
    cursor = None

    try:
        conn = mysql.connector.connect(**server_config)
        cursor = conn.cursor()

        db_name = DB_CONFIG['database']

        # Create database if it does not exist.
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 "
            "COLLATE utf8mb4_unicode_ci"
        )

        cursor.execute(f"USE `{db_name}`")

        # Users table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
        """)

        # Transactions table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(100) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                type ENUM('income', 'expense') NOT NULL,
                category VARCHAR(50) NOT NULL,
                date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                INDEX idx_user_date (user_id, date)
            ) ENGINE=InnoDB
        """)

        # Monthly budget table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                category VARCHAR(50) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                month TINYINT NOT NULL,
                year SMALLINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                UNIQUE KEY unique_user_budget (
                    user_id,
                    category,
                    month,
                    year
                ),

                INDEX idx_budget_user_month (
                    user_id,
                    year,
                    month
                )
            ) ENGINE=InnoDB
        """)

        # Savings goals table.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(100) NOT NULL,
                target_amount DECIMAL(10, 2) NOT NULL,
                saved_amount DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                target_date DATE NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE,

                INDEX idx_goals_user (user_id)
            ) ENGINE=InnoDB
        """)

        print("Database initialization completed successfully.")
        return True

    except Error as e:
        print(f"[Database Error] Initialization failed: {e}")
        return False

    finally:
        if cursor:
            cursor.close()

        if conn and conn.is_connected():
            conn.close()


if __name__ == '__main__':
    init_db()

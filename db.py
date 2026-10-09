"""
db.py - Database Connection and Initialization Helper for SpendWise Student.

This module handles:
1. Connecting to the MySQL database using mysql-connector-python.
2. Initializing the spendwise_db database and required tables (users, transactions).
3. Ensuring safe parameterized query execution to prevent SQL Injection.
"""

import os
import mysql.connector
from mysql.connector import Error

# Database configuration dictionary (can be customized via environment variables)
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '127.0.0.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'database': os.environ.get('DB_NAME', 'spendwise_db'),
    'autocommit': True
}

def get_db_connection():
    """
    Establishes and returns a connection to the SpendWise MySQL database.
    Returns:
        mysql.connector.connection.MySQLConnection object, or None if connection fails.
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"[Database Error] Failed to connect to MySQL: {e}")
        return None

def init_db():
    """
    Initializes the database and tables if they do not already exist.
    Can be run automatically at application start or as a standalone script.
    """
    # Connect without specifying the database to ensure it can be created first
    server_config = DB_CONFIG.copy()
    server_config.pop('database', None)
    
    try:
        conn = mysql.connector.connect(**server_config)
        cursor = conn.cursor()
        
        # 1. Create database if it doesn't exist
        db_name = DB_CONFIG['database']
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute(f"USE `{db_name}`;")
        print(f"[Database] Selected database: {db_name}")
        
        # 2. Create users table
        # Stores student account details with hashed passwords
        create_users_table = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """
        cursor.execute(create_users_table)
        print("[Database] Verified 'users' table.")

        # 3. Create transactions table
        # Stores income & expense records linked to specific users
        create_transactions_table = """
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            title VARCHAR(100) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            type ENUM('income', 'expense') NOT NULL,
            category VARCHAR(50) NOT NULL,
            date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_date (user_id, date)
        ) ENGINE=InnoDB;
        """
        cursor.execute(create_transactions_table)
        print("[Database] Verified 'transactions' table.")

        cursor.close()
        conn.close()
        print("[Database] Initialization completed successfully.")
        return True
    except Error as e:
        print(f"[Database Error] Error initializing database: {e}")
        return False

if __name__ == '__main__':
    # When run directly, setup the database
    print("Initializing SpendWise Student database...")
    init_db()

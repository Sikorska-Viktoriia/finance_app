import sqlite3
import hashlib
from datetime import datetime
import re
import os

# -----------------------
# Database Initialization
# -----------------------
DB_NAME = "users.db"
SALT = "flamingo_secure_salt_2024"

def init_database():
    """Initializes and returns database connection and cursor."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Wallets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            balance REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Savings plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0.0,
            deadline DATE,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Savings transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (plan_id) REFERENCES savings_plans (id)
        )
    ''')

    conn.commit()
    return conn, cursor

# Security & Validation Functions
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    return len(password) >= 6

def hash_password(password):
    return hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        SALT.encode('utf-8'), 
        100000
    ).hex()

def check_password(password, hashed):
    try:
        return hash_password(password) == hashed
    except:
        return False

# Logging Functions
def log_transaction(cursor, conn, user_id, trans_type, amount, description=""):
    """Log a transaction to the database. Skip non-financial operations."""
    try:
        # Не логуємо не фінансові операції
        non_financial_types = ['login', 'logout', 'initial']
        if trans_type in non_financial_types:
            return
            
        # Перевіряємо, чи це дійсно фінансова операція
        if amount == 0 and trans_type not in ['deposit', 'withdrawal', 'savings_transfer', 'savings_return']:
            return
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO transactions(user_id, type, amount, description, created_at) VALUES(?, ?, ?, ?, ?)",
            (user_id, trans_type, amount, description, timestamp)
        )
        conn.commit()
        print(f"Logged transaction: {trans_type} - {amount} - {description}")
    except Exception as e:
        print(f"Error logging transaction: {e}")

def log_savings_transaction(cursor, conn, user_id, plan_id, amount, trans_type, description=""):
    """Log a savings transaction to the database."""
    try:
        cursor.execute(
            "INSERT INTO savings_transactions(user_id, plan_id, amount, type, description) VALUES(?, ?, ?, ?, ?)",
            (user_id, plan_id, amount, trans_type, description)
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging savings transaction: {e}")

# Initialize and export connection objects
conn, cursor = init_database()

os.environ['KIVY_NO_MTDEV'] = '1'

__all__ = [
    'conn', 'cursor', 
    'is_valid_email', 'is_valid_password', 'hash_password', 'check_password',
    'log_transaction', 'log_savings_transaction'
]
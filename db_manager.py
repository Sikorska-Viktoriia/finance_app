import sqlite3
import hashlib
from datetime import datetime
import re
import os
import json

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
            card_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (card_id) REFERENCES user_cards (id)
        )
    ''')

    # User cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_cards(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            number TEXT NOT NULL,
            bank TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            color TEXT DEFAULT '[0.2, 0.4, 0.8, 1]',
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

# Додайте цей код після init_database()
def fix_database_schema():
    """Fix database schema by adding missing columns"""
    try:
        # Додаємо колонку card_id до таблиці transactions, якщо її немає
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'card_id' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN card_id INTEGER")
            print("Додано колонку card_id до таблиці transactions")
        
        conn.commit()
    except Exception as e:
        print(f"Помилка оновлення схеми бази даних: {e}")

# Викликаємо функцію виправлення
fix_database_schema()

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

def safe_color_conversion(color):
    """Safely convert color string to list"""
    if isinstance(color, list):
        return color
    elif isinstance(color, str):
        try:
            return json.loads(color.replace("'", '"'))
        except:
            try:
                return eval(color)
            except:
                return [0.2, 0.4, 0.8, 1]
    return [0.2, 0.4, 0.8, 1]

# Card Management Functions
def create_user_card(cursor, conn, user_id, name, number, bank, balance=0.0, color=None):
    """Create a new card for user."""
    try:
        if color is None:
            color = '[0.2, 0.4, 0.8, 1]'
        elif isinstance(color, list):
            color = json.dumps(color)
            
        cursor.execute(
            "INSERT INTO user_cards (user_id, name, number, bank, balance, color) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, name, number, bank, balance, color)
        )
        conn.commit()
        
        # Логуємо створення картки
        card_id = cursor.lastrowid
        log_transaction(cursor, conn, user_id, 'card_creation', 0, f"Створено картку {name}", card_id)
        
        return card_id
    except Exception as e:
        print(f"Error creating user card: {e}")
        return None

def get_user_cards(cursor, user_id):
    """Get all cards for a user."""
    try:
        cursor.execute(
            "SELECT id, name, number, bank, balance, color FROM user_cards WHERE user_id=?",
            (user_id,)
        )
        cards = cursor.fetchall()
        
        result = []
        for card in cards:
            card_id, name, number, bank, balance, color = card
            result.append({
                'id': card_id,
                'name': name,
                'number': number,
                'bank': bank,
                'balance': balance,
                'color': safe_color_conversion(color)
            })
        
        return result
    except Exception as e:
        print(f"Error getting user cards: {e}")
        return []

def get_user_card_by_id(cursor, card_id):
    """Get specific card by ID."""
    try:
        cursor.execute(
            "SELECT id, name, number, bank, balance, color FROM user_cards WHERE id=?",
            (card_id,)
        )
        card = cursor.fetchone()
        
        if card:
            card_id, name, number, bank, balance, color = card
            return {
                'id': card_id,
                'name': name,
                'number': number,
                'bank': bank,
                'balance': balance,
                'color': safe_color_conversion(color)
            }
        return None
    except Exception as e:
        print(f"Error getting card by ID: {e}")
        return None

def get_total_balance(cursor, user_id):
    """Get total balance from all user cards."""
    try:
        cursor.execute(
            "SELECT SUM(balance) FROM user_cards WHERE user_id=?",
            (user_id,)
        )
        result = cursor.fetchone()
        total = result[0] if result and result[0] is not None else 0.0
        return total
    except Exception as e:
        print(f"Error getting total balance: {e}")
        return 0.0

def update_card_balance(cursor, conn, card_id, amount, description=""):
    """Update card balance by adding amount."""
    try:
        # Отримуємо інформацію про картку
        cursor.execute("SELECT user_id, name FROM user_cards WHERE id=?", (card_id,))
        card_info = cursor.fetchone()
        
        if not card_info:
            return False
            
        user_id, card_name = card_info
        
        # Оновлюємо баланс
        cursor.execute("UPDATE user_cards SET balance = balance + ? WHERE id=?", (amount, card_id))
        
        # Логуємо операцію
        trans_type = 'deposit' if amount > 0 else 'withdrawal'
        trans_description = f"Поповнення картки {card_name}" if amount > 0 else f"Зняття з картки {card_name}"
        if description:
            trans_description = description
            
        log_transaction(cursor, conn, user_id, trans_type, amount, trans_description, card_id)
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating card balance: {e}")
        return False

def delete_user_card(cursor, conn, card_id):
    """Delete user card from database."""
    try:
        # Отримуємо інформацію про картку перед видаленням
        cursor.execute("SELECT user_id, name FROM user_cards WHERE id=?", (card_id,))
        card_info = cursor.fetchone()
        
        cursor.execute("DELETE FROM user_cards WHERE id=?", (card_id,))
        conn.commit()
        
        # Логуємо видалення картки
        if card_info:
            user_id, card_name = card_info
            log_transaction(cursor, conn, user_id, 'card_deletion', 0, f"Видалено картку {card_name}", card_id)
        
        return True
    except Exception as e:
        print(f"Error deleting user card: {e}")
        return False

def update_user_card(cursor, conn, card_id, name=None, number=None, bank=None, balance=None, color=None):
    """Update user card information."""
    try:
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("name=?")
            params.append(name)
        if number is not None:
            update_fields.append("number=?")
            params.append(number)
        if bank is not None:
            update_fields.append("bank=?")
            params.append(bank)
        if balance is not None:
            update_fields.append("balance=?")
            params.append(balance)
        if color is not None:
            update_fields.append("color=?")
            if isinstance(color, list):
                color = json.dumps(color)
            params.append(color)
            
        if not update_fields:
            return False
            
        update_query = f"UPDATE user_cards SET {', '.join(update_fields)} WHERE id=?"
        params.append(card_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating user card: {e}")
        return False

def transfer_money_between_cards(cursor, conn, from_card_id, to_card_id, amount):
    """Transfer money between cards."""
    try:
        # Перевіряємо баланс відправника
        cursor.execute("SELECT balance, user_id, name FROM user_cards WHERE id=?", (from_card_id,))
        from_result = cursor.fetchone()
        if not from_result:
            return False, "Картку відправника не знайдено"
        
        from_balance, from_user_id, from_card_name = from_result
        
        # Перевіряємо чи існує картка отримувача
        cursor.execute("SELECT user_id, name FROM user_cards WHERE id=?", (to_card_id,))
        to_result = cursor.fetchone()
        if not to_result:
            return False, "Картку отримувача не знайдено"
        
        to_user_id, to_card_name = to_result
        
        if from_balance < amount:
            return False, "Недостатньо коштів на картці"
        
        # Знімаємо гроші з відправника
        cursor.execute("UPDATE user_cards SET balance = balance - ? WHERE id=?", (amount, from_card_id))
        # Додаємо гроші отримувачу
        cursor.execute("UPDATE user_cards SET balance = balance + ? WHERE id=?", (amount, to_card_id))
        
        # Логуємо переказ
        log_transaction(cursor, conn, from_user_id, 'transfer_out', -amount, f"Переказ на картку {to_card_name}", from_card_id)
        log_transaction(cursor, conn, to_user_id, 'transfer_in', amount, f"Переказ з картки {from_card_name}", to_card_id)
        
        conn.commit()
        return True, "Переказ успішний"
    except Exception as e:
        print(f"Error transferring money: {e}")
        return False, "Помилка переказу"

# Logging Functions
def log_transaction(cursor, conn, user_id, trans_type, amount, description="", card_id=None):
    """Log a transaction to the database."""
    try:
        # Не логуємо не фінансові операції
        non_financial_types = ['login', 'logout', 'initial']
        if trans_type in non_financial_types:
            return
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "INSERT INTO transactions(user_id, type, amount, description, card_id, created_at) VALUES(?, ?, ?, ?, ?, ?)",
            (user_id, trans_type, amount, description, card_id, timestamp)
        )
        conn.commit()
        print(f"Logged transaction: {trans_type} - {amount} - {description}")
    except Exception as e:
        print(f"Error logging transaction: {e}")

def get_user_transactions(cursor, user_id, limit=50):
    """Get transaction history for user."""
    try:
        cursor.execute('''
            SELECT t.type, t.amount, t.description, t.created_at, c.name as card_name
            FROM transactions t
            LEFT JOIN user_cards c ON t.card_id = c.id
            WHERE t.user_id=?
            ORDER BY t.created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        transactions = cursor.fetchall()
        result = []
        
        for trans in transactions:
            trans_type, amount, description, created_at, card_name = trans
            result.append({
                'type': trans_type,
                'amount': amount,
                'description': description,
                'date': created_at,
                'card_name': card_name
            })
        
        return result
    except Exception as e:
        print(f"Error getting transactions: {e}")
        return []

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
    'log_transaction', 'log_savings_transaction', 'get_user_transactions',
    'create_user_card', 'get_user_cards', 'get_user_card_by_id', 'get_total_balance', 
    'update_card_balance', 'delete_user_card', 'update_user_card', 'transfer_money_between_cards',
    'safe_color_conversion'
]
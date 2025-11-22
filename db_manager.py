import sqlite3
import hashlib
from datetime import datetime, timedelta
import re
import os
import json
import string
import secrets
import traceback

# -----------------------
# Database Initialization
# -----------------------
DB_NAME = "users.db"
SALT = "flamingo_secure_salt_2024"

def init_database():
    """Initializes and returns database connection and cursor."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()

    # Users table - звичайні ID
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

    # User cards table - звичайні ID
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
    
    # Envelopes (categories) table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS envelopes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            color TEXT DEFAULT '[0.2, 0.4, 0.8, 1]',
            budget_limit REAL DEFAULT 0.0,
            current_amount REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Envelope transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS envelope_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            envelope_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            card_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (envelope_id) REFERENCES envelopes (id),
            FOREIGN KEY (card_id) REFERENCES user_cards (id)
        )
    ''')

    conn.commit()
    return conn, cursor

def fix_database_schema(conn, cursor):
    """Fix database schema by adding missing columns"""
    try:
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'card_id' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN card_id INTEGER")
        
        conn.commit()
    except Exception as e:
        pass

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

# User Management Functions
def create_user(cursor, conn, username, email, password):
    """Створює нового користувача"""
    try:
        if not is_valid_email(email):
            return None, "Невірний формат email"
        
        if not is_valid_password(password):
            return None, "Пароль має містити принаймні 6 символів"
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE email=?", (email,))
        if cursor.fetchone()[0] > 0:
            return None, "Користувач з таким email вже існує"
        
        password_hashed = hash_password(password)
        
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password_hashed)
        )
        
        user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO wallets (user_id, balance) VALUES (?, ?)",
            (user_id, 0.0)
        )
        
        conn.commit()
        return user_id, "Користувача успішно створено"
        
    except Exception as e:
        return None, "Помилка створення користувача"

def get_user_by_email(cursor, email):
    """Отримує користувача за email"""
    try:
        cursor.execute(
            "SELECT id, username, email, password FROM users WHERE email=?",
            (email,)
        )
        user = cursor.fetchone()
        
        if user:
            user_id, username, email, password = user
            return {
                'id': user_id,
                'username': username,
                'email': email,
                'password': password
            }
        return None
    except Exception as e:
        return None

# Analytics Functions
def get_analytics_data(cursor, user_id, period='month', category=None, card_id=None):
    """Отримати дані для аналітики з фіксованою логікою"""
    try:
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            SELECT type, amount, description, created_at 
            FROM transactions 
            WHERE user_id=? AND created_at BETWEEN ? AND ?
            ORDER BY created_at DESC
        ''', (user_id, start_date_str, end_date_str))
        
        transactions = cursor.fetchall()

        total_income = 0
        total_expenses = 0
        transactions_count = len(transactions)

        for trans in transactions:
            trans_type, amount, description, created_at = trans
            
            if trans_type in ['deposit', 'card_deposit', 'transfer_in', 'income', 'savings_return', 'savings_completed']:
                total_income += amount
            elif trans_type in ['withdrawal', 'transfer', 'transfer_out', 'expense', 'savings_deposit', 'envelope_deposit']:
                total_expenses += amount

        net_balance = total_income - total_expenses
        
        days_in_period = (end_date - start_date).days or 1
        average_daily = total_expenses / days_in_period

        total_balance = get_total_balance(cursor, user_id)

        savings_rate = (net_balance / total_income * 100) if total_income > 0 else 0

        return {
            'total_income': round(total_income, 2),
            'total_expenses': round(total_expenses, 2),
            'net_balance': round(net_balance, 2),
            'average_daily': round(average_daily, 2),
            'transactions_count': transactions_count,
            'total_balance': round(total_balance, 2),
            'savings_rate': round(savings_rate, 1),
            'period_days': days_in_period
        }
        
    except Exception as e:
        return {
            'total_income': 0,
            'total_expenses': 0,
            'net_balance': 0,
            'average_daily': 0,
            'transactions_count': 0,
            'total_balance': 0,
            'savings_rate': 0,
            'period_days': 1
        }

def get_category_breakdown(cursor, user_id, period='month'):
    """Отримати розподіл по категоріях"""
    try:
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        cursor.execute('''
            SELECT amount, description, created_at 
            FROM transactions 
            WHERE user_id=? AND type IN ('withdrawal', 'transfer_out', 'expense') 
            AND created_at BETWEEN ? AND ?
        ''', (user_id, start_date_str, end_date_str))
        
        transactions = cursor.fetchall()

        categories = {
            'Food': {'amount': 0, 'color': [0.95, 0.3, 0.5, 1]},
            'Transport': {'amount': 0, 'color': [0.2, 0.7, 0.9, 1]},
            'Entertainment': {'amount': 0, 'color': [0.2, 0.8, 0.3, 1]},
            'Bills': {'amount': 0, 'color': [1, 0.6, 0.2, 1]},
            'Shopping': {'amount': 0, 'color': [0.7, 0.4, 0.9, 1]},
            'Other': {'amount': 0, 'color': [0.7, 0.7, 0.7, 1]}
        }

        keywords = {
            'Food': ['food', 'restaurant', 'grocery', 'cafe', 'meal', 'supermarket'],
            'Transport': ['transport', 'bus', 'taxi', 'fuel', 'gas', 'metro', 'train'],
            'Entertainment': ['movie', 'cinema', 'concert', 'game', 'entertainment', 'netflix'],
            'Bills': ['bill', 'rent', 'electricity', 'water', 'internet', 'phone'],
            'Shopping': ['shop', 'store', 'mall', 'clothes', 'electronics', 'purchase']
        }

        for amount, description, created_at in transactions:
            description_lower = (description or '').lower()
            categorized = False
            
            for category, words in keywords.items():
                if any(word in description_lower for word in words):
                    categories[category]['amount'] += amount
                    categorized = True
                    break
            
            if not categorized:
                categories['Other']['amount'] += amount

        total_expenses = sum(cat['amount'] for cat in categories.values())
        
        result = []
        for category, data in categories.items():
            if data['amount'] > 0:
                percentage = (data['amount'] / total_expenses * 100) if total_expenses > 0 else 0
                result.append({
                    'name': category,
                    'value': round(percentage, 1),
                    'amount': round(data['amount'], 2),
                    'color': data['color']
                })

        result.sort(key=lambda x: x['amount'], reverse=True)
        
        return result
        
    except Exception as e:
        return []

def get_top_categories(cursor, user_id, period='month', limit=5):
    """Отримати ТОП категорії витрат"""
    try:
        category_data = get_category_breakdown(cursor, user_id, period)
        return category_data[:limit]
    except Exception as e:
        return []

def get_cards_analytics(cursor, user_id, period='month'):
    """Отримати аналітику по картках"""
    try:
        end_date = datetime.now()
        if period == 'today':
            start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date = end_date - timedelta(days=7)
        elif period == 'month':
            start_date = end_date - timedelta(days=30)
        elif period == 'year':
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)

        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        user_cards = get_user_cards(cursor, user_id)
        cards_analytics = []

        for card in user_cards:
            card_id = card['id']
            
            cursor.execute('''
                SELECT SUM(amount) 
                FROM transactions 
                WHERE user_id=? AND card_id=? AND type IN ('deposit', 'transfer_in', 'income')
                AND created_at BETWEEN ? AND ?
            ''', (user_id, card_id, start_date_str, end_date_str))
            income_result = cursor.fetchone()
            income = income_result[0] or 0

            cursor.execute('''
                SELECT SUM(amount) 
                FROM transactions 
                WHERE user_id=? AND card_id=? AND type IN ('withdrawal', 'transfer_out', 'expense')
                AND created_at BETWEEN ? AND ?
            ''', (user_id, card_id, start_date_str, end_date_str))
            expenses_result = cursor.fetchone()
            expenses = expenses_result[0] or 0

            cards_analytics.append({
                'id': card_id,
                'name': card['name'],
                'income': round(income, 2),
                'expenses': round(expenses, 2),
                'balance': card['balance'],
                'color': card['color']
            })

        return cards_analytics
        
    except Exception as e:
        return []

def get_budget_progress(cursor, user_id):
    """Отримати прогрес по бюджетах (конвертах)"""
    try:
        envelopes = get_user_envelopes(cursor, user_id)
        budget_data = []
        
        for envelope in envelopes:
            spent = envelope['current_amount']
            limit = envelope['budget_limit']
            percentage = (spent / limit * 100) if limit > 0 else 0
            
            budget_data.append({
                'name': envelope['name'],
                'spent': round(spent, 2),
                'limit': round(limit, 2),
                'percentage': round(percentage, 1),
                'remaining': round(limit - spent, 2),
                'color': envelope['color'],
                'is_overbudget': percentage > 100
            })
        
        return budget_data
        
    except Exception as e:
        return []

def get_insights_and_forecasts(cursor, user_id):
    """Отримати інсайти та прогнози"""
    try:
        insights = []
        
        current_data = get_analytics_data(cursor, user_id, 'month')
        previous_data = get_analytics_data(cursor, user_id, 'month')
        
        budgets = get_budget_progress(cursor, user_id)
        for budget in budgets:
            if budget['percentage'] > 90:
                insights.append(f"⚠️ Можлива перевитрата в конверті '{budget['name']}' - використано {budget['percentage']}%")
            elif budget['percentage'] > 75:
                insights.append(f"🔔 Конверт '{budget['name']}' майже заповнений - {budget['percentage']}%")
        
        if current_data['total_expenses'] > previous_data['total_expenses'] * 1.2:
            increase_percent = ((current_data['total_expenses'] - previous_data['total_expenses']) / previous_data['total_expenses'] * 100)
            insights.append(f"📈 Зростання витрат на {increase_percent:.1f}% порівняно з минулим місяцем")
        
        today = datetime.now()
        days_passed = today.day
        days_in_month = 30
        daily_avg = current_data['average_daily']
        projected_expenses = daily_avg * days_in_month
        
        insights.append(f"🔮 Прогноз витрат до кінця місяця: ${projected_expenses:.2f}")
        
        savings_rate = current_data['savings_rate']
        if savings_rate > 20:
            insights.append(f"💰 Відмінно! Ваш рівень заощаджень: {savings_rate}%")
        elif savings_rate < 10:
            insights.append(f"💡 Можна покращити заощадження. Поточний рівень: {savings_rate}%")
        
        return insights
        
    except Exception as e:
        return ["💡 Аналіз даних тимчасово недоступний"]

def get_monthly_comparison(cursor, user_id, months=6):
    """Отримати порівняння по місяцях"""
    try:
        monthly_data = []
        
        for i in range(months):
            month_date = datetime.now() - timedelta(days=30*i)
            month_str = month_date.strftime('%Y-%m')
            
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN type IN ('deposit', 'transfer_in', 'income') THEN amount ELSE 0 END) as income,
                    SUM(CASE WHEN type IN ('withdrawal', 'transfer_out', 'expense') THEN amount ELSE 0 END) as expenses
                FROM transactions 
                WHERE user_id=? AND strftime('%Y-%m', created_at) = ?
            ''', (user_id, month_str))
            
            result = cursor.fetchone()
            income = result[0] or 0
            expenses = result[1] or 0
            
            monthly_data.append({
                'month': month_date.strftime('%b %Y'),
                'income': round(income, 2),
                'expenses': round(expenses, 2),
                'savings': round(income - expenses, 2)
            })
        
        monthly_data.reverse()
        return monthly_data
        
    except Exception as e:
        return []

# Card Management Functions
def create_user_card(cursor, conn, user_id, name, number, bank, balance=0.0, color=None):
    """Create a new card for user"""
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
        
        card_id = cursor.lastrowid
        
        log_transaction(cursor, conn, user_id, 'card_creation', 0, f"Створено картку {name}", card_id)
        
        return card_id
    except Exception as e:
        return None

def get_user_cards(cursor, user_id):
    """
    Оновлено: Повертає повний зашифрований номер картки ('number') 
    для подальшого розшифрування та маскування у HomeTab.
    """
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
                'number': number, # ТУТ ПОВЕРТАЄМО ЗАШИФРОВАНИЙ НОМЕР
                'bank': bank,
                'balance': balance,
                'color': safe_color_conversion(color)
            })
        
        return result
    except Exception as e:
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
            
            masked_number = f"**** **** **** {number[-4:]}" if number and len(number) >= 4 else "****"
            
            return {
                'id': card_id,
                'name': name,
                'number': masked_number,
                'full_number': number,
                'bank': bank,
                'balance': balance,
                'color': safe_color_conversion(color)
            }
        return None
    except Exception as e:
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
        return 0.0

def update_card_balance(cursor, conn, card_id, amount, description=""):
    """Update card balance by adding amount"""
    try:
        cursor.execute("SELECT user_id, name, balance FROM user_cards WHERE id=?", (card_id,))
        card_info = cursor.fetchone()
        
        if not card_info:
            return False
            
        user_id, card_name, current_balance = card_info
        new_balance = current_balance + amount
        
        cursor.execute(
            "UPDATE user_cards SET balance=? WHERE id=?",
            (new_balance, card_id)
        )
        conn.commit()
        
        if not description.startswith("(") or "конверт" not in description.lower():
            trans_type = 'deposit' if amount > 0 else 'withdrawal'
            trans_description = f"Поповнення картки {card_name}" if amount > 0 else f"Зняття з картки {card_name}"
            if description:
                trans_description = description
                
            log_transaction(cursor, conn, user_id, trans_type, amount, trans_description, card_id)
        
        return True
    except Exception as e:
        return False

def delete_user_card(cursor, conn, card_id):
    """Delete user card from database."""
    try:
        cursor.execute("SELECT user_id, name FROM user_cards WHERE id=?", (card_id,))
        card_info = cursor.fetchone()
        
        cursor.execute("DELETE FROM user_cards WHERE id=?", (card_id,))
        conn.commit()
        
        if card_info:
            user_id, card_name = card_info
            log_transaction(cursor, conn, user_id, 'card_deletion', 0, f"Видалено картку {card_name}", card_id)
        
        return True
    except Exception as e:
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
        return False

def transfer_money_between_cards(cursor, conn, from_card_id, to_card_id, amount):
    """Transfer money between cards."""
    try:
        cursor.execute("SELECT balance, user_id, name FROM user_cards WHERE id=?", (from_card_id,))
        from_result = cursor.fetchone()
        if not from_result:
            return False, "Картку відправника не знайдено"
        
        from_balance, from_user_id, from_card_name = from_result
        
        cursor.execute("SELECT user_id, name FROM user_cards WHERE id=?", (to_card_id,))
        to_result = cursor.fetchone()
        if not to_result:
            return False, "Картку отримувача не знайдено"
        
        to_user_id, to_card_name = to_result
        
        if from_balance < amount:
            return False, "Недостатньо коштів на картці"
        
        new_from_balance = from_balance - amount
        cursor.execute("UPDATE user_cards SET balance=? WHERE id=?", (new_from_balance, from_card_id))
        
        new_to_balance_result = cursor.execute("SELECT balance FROM user_cards WHERE id=?", (to_card_id,)).fetchone()
        new_to_balance = (new_to_balance_result[0] if new_to_balance_result else 0) + amount
        cursor.execute("UPDATE user_cards SET balance=? WHERE id=?", (new_to_balance, to_card_id))
        
        conn.commit()
        
        log_transaction(cursor, conn, from_user_id, 'transfer_out', -amount, f"Переказ на картку {to_card_name}", from_card_id)
        log_transaction(cursor, conn, to_user_id, 'transfer_in', amount, f"Переказ з картки {from_card_name}", to_card_id)
        
        return True, "Переказ успішний"
    except Exception as e:
        return False, "Помилка переказу"

def log_transaction(cursor, conn, user_id, transaction_type, amount, description="", card_id=None):
    """Логування транзакції з уникненням дублювання"""
    try:
        if transaction_type == 'card_creation':
            return True
            
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE user_id=? AND type=? AND amount=? AND description=? 
            AND created_at > datetime('now', '-1 minute')
        ''', (user_id, transaction_type, amount, description))
        
        recent_count = cursor.fetchone()[0]
        
        if recent_count > 0:
            return True
            
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description, card_id, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        ''', (user_id, transaction_type, amount, description, card_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        return False
    
def update_envelope(cursor, conn, envelope_id, name=None, budget_limit=None):
    """Update envelope information."""
    try:
        update_fields = []
        params = []
        
        if name is not None:
            update_fields.append("name=?")
            params.append(name)
        if budget_limit is not None:
            update_fields.append("budget_limit=?")
            params.append(budget_limit)
            
        if not update_fields:
            return False
            
        update_query = f"UPDATE envelopes SET {', '.join(update_fields)} WHERE id=?"
        params.append(envelope_id)
        
        cursor.execute(update_query, params)
        conn.commit()
        return True
    except Exception as e:
        return False
    
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
        pass

def create_envelope(cursor, conn, user_id, name, color=None, budget_limit=0.0):
    """Create a new envelope for user."""
    try:
        if color is None:
            color = '[0.2, 0.4, 0.8, 1]'
        elif isinstance(color, list):
            color = json.dumps(color)
            
        cursor.execute(
            "INSERT INTO envelopes (user_id, name, color, budget_limit) VALUES (?, ?, ?, ?)",
            (user_id, name, color, budget_limit)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        return None

def get_user_envelopes(cursor, user_id):
    """Get all envelopes for a user."""
    try:
        cursor.execute(
            "SELECT id, name, color, budget_limit, current_amount FROM envelopes WHERE user_id=?",
            (user_id,)
        )
        envelopes = cursor.fetchall()
        
        result = []
        for envelope in envelopes:
            env_id, name, color, budget_limit, current_amount = envelope
            result.append({
                'id': env_id,
                'name': name,
                'color': safe_color_conversion(color),
                'budget_limit': budget_limit,
                'current_amount': current_amount,
                'usage_percentage': (current_amount / budget_limit * 100) if budget_limit > 0 else 0
            })
        
        return result
    except Exception as e:
        return []

def add_to_envelope(cursor, conn, user_id, envelope_id, amount, description="", card_id=None):
    """Add money to envelope."""
    try:
        cursor.execute(
            "UPDATE envelopes SET current_amount = current_amount + ? WHERE id=?",
            (amount, envelope_id)
        )
        
        cursor.execute(
            "INSERT INTO envelope_transactions (user_id, envelope_id, amount, description, card_id) VALUES (?, ?, ?, ?, ?)",
            (user_id, envelope_id, amount, description, card_id)
        )
        
        envelope_name = get_envelope_name(cursor, envelope_id)
        log_transaction(cursor, conn, user_id, 'envelope_deposit', amount, 
                       f"{description} ({envelope_name})", card_id)
        
        conn.commit()
        return True
    except Exception as e:
        return False

def get_envelope_name(cursor, envelope_id):
    """Get envelope name by ID."""
    try:
        cursor.execute("SELECT name FROM envelopes WHERE id=?", (envelope_id,))
        result = cursor.fetchone()
        return result[0] if result else "Unknown"
    except:
        return "Unknown"

def get_envelope_transactions(cursor, user_id, envelope_id=None, limit=50):
    """Get transactions for envelopes."""
    try:
        query = '''
            SELECT et.amount, et.description, et.created_at, e.name as envelope_name, c.name as card_name
            FROM envelope_transactions et
            LEFT JOIN envelopes e ON et.envelope_id = e.id
            LEFT JOIN user_cards c ON et.card_id = c.id
            WHERE et.user_id=?
        '''
        params = [user_id]
        
        if envelope_id:
            query += " AND et.envelope_id=?"
            params.append(envelope_id)
            
        query += " ORDER BY et.created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        transactions = cursor.fetchall()
        
        result = []
        for trans in transactions:
            amount, description, created_at, envelope_name, card_name = trans
            result.append({
                'amount': amount,
                'description': description,
                'date': created_at,
                'envelope_name': envelope_name,
                'card_name': card_name
            })
        
        return result
    except Exception as e:
        return []

def get_envelope_stats(cursor, user_id):
    """Get statistics for all envelopes."""
    try:
        cursor.execute('''
            SELECT 
                e.name,
                e.budget_limit,
                e.current_amount,
                COUNT(et.id) as transaction_count,
                SUM(CASE WHEN et.amount > 0 THEN et.amount ELSE 0 END) as total_deposits
            FROM envelopes e
            LEFT JOIN envelope_transactions et ON e.id = et.envelope_id
            WHERE e.user_id=?
            GROUP BY e.id, e.name, e.budget_limit, e.current_amount
        ''', (user_id,))
        
        stats = cursor.fetchall()
        result = []
        
        for stat in stats:
            name, budget_limit, current_amount, transaction_count, total_deposits = stat
            result.append({
                'name': name,
                'budget_limit': budget_limit,
                'current_amount': current_amount,
                'transaction_count': transaction_count,
                'total_deposits': total_deposits or 0,
                'usage_percentage': (current_amount / budget_limit * 100) if budget_limit > 0 else 0
            })
        
        return result
    except Exception as e:
        return []

def debug_transactions(cursor, user_id):
    """Функція для відладки транзакцій"""
    try:
        cursor.execute(
            "SELECT type, amount, description, created_at FROM transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )
        transactions = cursor.fetchall()
        return transactions
    except Exception as e:
        return []

# Initialize and export connection objects
conn, cursor = init_database()

fix_database_schema(conn, cursor)

os.environ['KIVY_NO_MTDEV'] = '1'

__all__ = [
    'conn', 'cursor', 
    'is_valid_email', 'is_valid_password', 'hash_password', 'check_password',
    'log_transaction', 'log_savings_transaction', 'get_user_transactions',
    'create_user_card', 'get_user_cards', 'get_user_card_by_id', 'get_total_balance', 
    'update_card_balance', 'delete_user_card', 'update_user_card', 'transfer_money_between_cards',
    'safe_color_conversion',
    'create_envelope', 'get_user_envelopes', 'add_to_envelope', 'get_envelope_transactions', 'get_envelope_stats',
    'update_envelope',
    'create_user', 'get_user_by_email',
    # Analytics functions
    'get_analytics_data', 'get_category_breakdown', 'get_top_categories', 
    'get_cards_analytics', 'get_budget_progress', 'get_insights_and_forecasts', 'get_monthly_comparison',
    'debug_transactions'
]
import re
import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.properties import ListProperty, StringProperty, BooleanProperty, NumericProperty
from kivy.metrics import dp

# -----------------------
# Disable Kivy warnings
# -----------------------
os.environ['KIVY_NO_MTDEV'] = '1'

# -----------------------
# Database initialization with savings plans
# -----------------------
def init_database():
    conn = sqlite3.connect("users.db", check_same_thread=False)
    cursor = conn.cursor()

    # Users table with additional fields
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

    # Wallets table with additional fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets(
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Transactions table for history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Savings plans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_plans(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            target_amount REAL NOT NULL,
            current_amount REAL DEFAULT 0,
            deadline DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # Savings transactions table for history
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS savings_transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(plan_id) REFERENCES savings_plans(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_userid_wallet ON wallets(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_userid_transactions ON transactions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_savings_user ON savings_plans(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_savings_status ON savings_plans(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_savings_transactions ON savings_transactions(user_id, plan_id)')

    conn.commit()
    return conn, cursor

# Initialize database
conn, cursor = init_database()

# -----------------------
# Load KV file
# -----------------------
Builder.load_file("kv/screens.kv")

# -----------------------
# Functions with security improvements
# -----------------------
def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_password(password):
    return len(password) >= 6

def hash_password(password):
    salt = "flamingo_secure_salt_2024"
    return hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()

def check_password(password, hashed):
    try:
        return hash_password(password) == hashed
    except:
        return False

def log_transaction(user_id, trans_type, amount, description=""):
    """Log transaction to history"""
    try:
        cursor.execute(
            "INSERT INTO transactions(user_id, type, amount, description) VALUES(?, ?, ?, ?)",
            (user_id, trans_type, amount, description)
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging transaction: {e}")

def log_savings_transaction(user_id, plan_id, amount, trans_type, description=""):
    """Log savings transaction to history"""
    try:
        cursor.execute(
            "INSERT INTO savings_transactions(user_id, plan_id, amount, type, description) VALUES(?, ?, ?, ?, ?)",
            (user_id, plan_id, amount, trans_type, description)
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging savings transaction: {e}")

# -----------------------
# Custom Widget for Password Field with Toggle
# -----------------------
class PasswordTextInput(BoxLayout):
    text = StringProperty("")
    hint_text = StringProperty("")
    password = BooleanProperty(True)
    
    def toggle_password(self):
        self.password = not self.password

# -----------------------
# Savings Plan Item Widget
# -----------------------
class SavingsPlanItem(BoxLayout):
    plan_name = StringProperty("")
    current_amount = NumericProperty(0)
    target_amount = NumericProperty(0)
    progress = NumericProperty(0)
    days_left = NumericProperty(0)
    status = StringProperty("active")
    
    def add_to_plan(self):
        """Add money to this savings plan"""
        app = App.get_running_app()
        dashboard = app.root.get_screen('dashboard_screen')
        if hasattr(dashboard, 'add_to_savings_plan'):
            dashboard.add_to_savings_plan(self.plan_name)

# -----------------------
# Screens
# -----------------------
class StartScreen(Screen):
    pass

class RegistrationScreen(Screen):
    def register_user(self):
        username = self.ids.username.text.strip()
        email = self.ids.email.text.strip()
        password = self.ids.password_field.ids.password_input.text.strip()
        msg_label = self.ids.reg_message

        if not (username and email and password):
            msg_label.text = "Please fill in all fields"
            return
        
        if not is_valid_email(email):
            msg_label.text = "Invalid email format"
            return
        
        if not is_valid_password(password):
            msg_label.text = "Password must be at least 6 characters"
            return

        try:
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                msg_label.text = "Email already exists. Redirecting to login..."
                self.manager.transition.direction = 'left'
                self.manager.current = "login_screen"
                return

            hashed_pw = hash_password(password)
            cursor.execute(
                "INSERT INTO users(username, email, password) VALUES(?, ?, ?)",
                (username, email, hashed_pw)
            )
            conn.commit()

            cursor.execute("SELECT id FROM users WHERE email=?", (email,))
            user_id = cursor.fetchone()[0]

            cursor.execute("INSERT INTO wallets(user_id, balance) VALUES(?, ?)", (user_id, 0))
            log_transaction(user_id, "initial", 0, "Account created")
            conn.commit()

            self.manager.current_user = username
            self.manager.current_user_id = user_id
            self.manager.balance = 0.0
            self.manager.transition.direction = 'left'
            self.manager.current = "dashboard_screen"
            
        except sqlite3.Error as e:
            msg_label.text = f"Database error: {str(e)}"
        except Exception as e:
            msg_label.text = f"Error: {str(e)}"

class LoginScreen(Screen):
    def login_user(self):
        email = self.ids.email.text.strip()
        password = self.ids.password_field.ids.password_input.text.strip()
        msg_label = self.ids.login_message

        try:
            cursor.execute("SELECT id, username, password FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            if user and check_password(password, user[2]):
                msg_label.text = f"Successfully logged in: {user[1]}"
                self.manager.current_user = user[1]
                self.manager.current_user_id = user[0]

                cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (user[0],))
                result = cursor.fetchone()
                self.manager.balance = result[0] if result else 0.0

                log_transaction(user[0], "login", 0, "User logged in")
                self.manager.transition.direction = 'left'
                self.manager.current = "dashboard_screen"
            else:
                msg_label.text = "Invalid email or password"
                
        except Exception as e:
            msg_label.text = f"Login error: {str(e)}"

# -----------------------
# Bottom Menu Item Widget
# -----------------------
class BottomMenuItem(BoxLayout):
    tab_name = StringProperty("")
    icon_source = StringProperty("")
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            dashboard = app.root.get_screen('dashboard_screen')
            if hasattr(dashboard, 'switch_tab'):
                dashboard.switch_tab(self.tab_name)
            return True
        return super().on_touch_down(touch)

# -----------------------
# Dashboard with Savings Plans
# -----------------------
class DashboardScreen(Screen):
    def on_enter(self):
        self.update_dashboard()
    
    def update_dashboard(self):
        """Update all dashboard information"""
        self.ids.welcome_label.text = f"Welcome, {self.manager.current_user}!"
        self.ids.balance_label.text = f"Balance: {self.manager.balance:.2f} $"
        self.update_account_tab()
        self.update_savings_tab()
    
    def update_account_tab(self):
        if hasattr(self.manager, 'current_user'):
            self.ids.username_label.text = f"Username: {self.manager.current_user}"
            cursor.execute("SELECT email FROM users WHERE id=?", (self.manager.current_user_id,))
            email_result = cursor.fetchone()
            if email_result:
                self.ids.email_label.text = f"Email: {email_result[0]}"
    
    def update_savings_tab(self):
        
        savings_container = self.ids.savings_container
        savings_container.clear_widgets()
        
        try:
            print(f"Loading savings plans for user: {self.manager.current_user_id}")
            
            cursor.execute(
                "SELECT id, name, target_amount, current_amount, deadline, status FROM savings_plans WHERE user_id=? ORDER BY created_at DESC",
                (self.manager.current_user_id,)
            )
            plans = cursor.fetchall()
            
            print(f"Found {len(plans)} plans: {plans}")
            
            if not plans:
                # Show message if no plans
                no_plans_label = Label(
                    text="No savings plans yet.\nCreate your first plan!",
                    font_size=dp(18),
                    color=(0.5, 0.5, 0.5, 1),
                    halign="center",
                    text_size=(dp(300), None)
                )
                savings_container.add_widget(no_plans_label)
                return
            
            for plan in plans:
                plan_id, name, target, current, deadline, status = plan
                
                print(f"Processing plan: {name}, Target: {target}, Current: {current}")
                
                # Calculate progress
                progress = (current / target * 100) if target > 0 else 0
                
                # Calculate days left
                days_left = 0
                if deadline:
                    try:
                        deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                        today = datetime.now().date()
                        days_left = max(0, (deadline_date - today).days)
                    except ValueError:
                        days_left = 0
                
                # Create plan item
                plan_item = SavingsPlanItem()
                plan_item.plan_name = name
                plan_item.current_amount = current
                plan_item.target_amount = target
                plan_item.progress = progress
                plan_item.days_left = days_left
                plan_item.status = status
                
                savings_container.add_widget(plan_item)
                print(f"Added plan to UI: {name}")
                
        except Exception as e:
            print(f"Error loading savings plans: {e}")
    
    def create_savings_plan(self):
 
        plan_name = self.ids.plan_name_input.text.strip()
        target_text = self.ids.target_amount_input.text.strip()
        deadline = self.ids.deadline_input.text.strip()
        
        if not plan_name:
            self.ids.savings_message.text = "Please enter plan name"
            return
        
        try:
            target_amount = float(target_text)
            if target_amount <= 0:
                self.ids.savings_message.text = "Target amount must be positive"
                return
        except ValueError:
            self.ids.savings_message.text = "Enter valid target amount"
            return
        
        # Validate date format if provided
        if deadline:
            try:
                datetime.strptime(deadline, '%Y-%m-%d')
            except ValueError:
                self.ids.savings_message.text = "Invalid date format. Use YYYY-MM-DD"
                return
        
        try:
            cursor.execute(
                "INSERT INTO savings_plans (user_id, name, target_amount, deadline) VALUES (?, ?, ?, ?)",
                (self.manager.current_user_id, plan_name, target_amount, deadline if deadline else None)
            )
            plan_id = cursor.lastrowid
            
            # Log the creation of savings plan
            log_savings_transaction(
                self.manager.current_user_id,
                plan_id,
                0,
                "plan_created",
                f"Created savings plan: {plan_name}"
            )
            
            conn.commit()
            
            # Додамо відладку
            print(f"Savings plan created: {plan_name}, ID: {plan_id}, User ID: {self.manager.current_user_id}")
            
            # Перевіримо, чи план дійсно збережено
            cursor.execute("SELECT * FROM savings_plans WHERE user_id=?", (self.manager.current_user_id,))
            all_plans = cursor.fetchall()
            print(f"All plans for user: {all_plans}")
            
            # Clear inputs
            self.ids.plan_name_input.text = ""
            self.ids.target_amount_input.text = ""
            self.ids.deadline_input.text = ""
            self.ids.savings_message.text = "Savings plan created successfully!"
            
            # Update display
            self.update_savings_tab()
            
        except Exception as e:
            print(f"Error creating plan: {e}")
            self.ids.savings_message.text = f"Error creating plan: {str(e)}"
    
    def add_to_savings_plan(self, plan_name):
        """Add money to a specific savings plan"""
        try:
            # Get the amount from input
            amount_text = self.ids.savings_amount_input.text.strip()
            if not amount_text:
                self.ids.savings_message.text = "Please enter amount to add"
                return
            
            amount = float(amount_text)
            if amount <= 0:
                self.ids.savings_message.text = "Amount must be positive"
                return
            
            if amount > self.manager.balance:
                self.ids.savings_message.text = "Insufficient funds in wallet"
                return
            
            # Get plan details
            cursor.execute(
                "SELECT id, current_amount, target_amount FROM savings_plans WHERE name = ? AND user_id = ?",
                (plan_name, self.manager.current_user_id)
            )
            plan = cursor.fetchone()
            
            if not plan:
                self.ids.savings_message.text = "Plan not found"
                return
            
            plan_id, current_amount, target_amount = plan
            
            # Check if adding this amount would exceed target
            if current_amount + amount > target_amount:
                self.ids.savings_message.text = f"Amount exceeds plan target. Maximum you can add: ${target_amount - current_amount:.2f}"
                return
            
            # Update wallet balance
            self.manager.balance -= amount
            cursor.execute("UPDATE wallets SET balance=? WHERE user_id=?", 
                         (self.manager.balance, self.manager.current_user_id))
            
            # Update savings plan
            cursor.execute(
                "UPDATE savings_plans SET current_amount = current_amount + ? WHERE id = ?",
                (amount, plan_id)
            )
            
            # Log transactions
            log_transaction(
                self.manager.current_user_id, 
                "savings_transfer", 
                amount, 
                f"Transferred to savings plan: {plan_name}"
            )
            
            log_savings_transaction(
                self.manager.current_user_id,
                plan_id,
                amount,
                "deposit",
                f"Added to savings plan"
            )
            
            conn.commit()
            
            # Clear input and update display
            self.ids.savings_amount_input.text = ""
            self.ids.savings_message.text = f"Successfully added ${amount:.2f} to {plan_name}"
            self.update_dashboard()
            
        except ValueError:
            self.ids.savings_message.text = "Enter valid amount"
        except Exception as e:
            self.ids.savings_message.text = f"Error: {str(e)}"
    
    def add_money(self):
        try:
            amount_text = self.ids.amount_input.text.strip()
            if not amount_text:
                self.ids.balance_label.text = "Please enter an amount!"
                return
                
            amount = float(amount_text)
            if amount <= 0:
                self.ids.balance_label.text = "Amount must be positive!"
                return
                
            self.manager.balance += amount
            self.ids.balance_label.text = f"Balance: {self.manager.balance:.2f} $"
            self.ids.amount_input.text = ""
            
            cursor.execute("UPDATE wallets SET balance=? WHERE user_id=?", 
                           (self.manager.balance, self.manager.current_user_id))
            log_transaction(self.manager.current_user_id, "deposit", amount, "Added to wallet")
            conn.commit()
            
        except ValueError:
            self.ids.amount_input.text = ""
            self.ids.balance_label.text = "Enter a valid amount!"
        except Exception as e:
            self.ids.balance_label.text = f"Error: {str(e)}"

    def remove_money(self):
        try:
            amount_text = self.ids.amount_input.text.strip()
            if not amount_text:
                self.ids.balance_label.text = "Please enter an amount!"
                return
                
            amount = float(amount_text)
            if amount <= 0:
                self.ids.balance_label.text = "Amount must be positive!"
                return
                
            if amount > self.manager.balance:
                self.ids.balance_label.text = "Insufficient funds!"
                return
                
            self.manager.balance -= amount
            self.ids.balance_label.text = f"Balance: {self.manager.balance:.2f} $"
            self.ids.amount_input.text = ""
            
            cursor.execute("UPDATE wallets SET balance=? WHERE user_id=?", 
                           (self.manager.balance, self.manager.current_user_id))
            log_transaction(self.manager.current_user_id, "withdrawal", amount, "Withdrawn from wallet")
            conn.commit()
            
        except ValueError:
            self.ids.amount_input.text = ""
            self.ids.balance_label.text = "Enter a valid amount!"
        except Exception as e:
            self.ids.balance_label.text = f"Error: {str(e)}"

    def switch_tab(self, tab_name):
        if hasattr(self.ids, 'tab_manager'):
            self.ids.tab_manager.current = tab_name
            if tab_name == "account_tab":
                self.update_account_tab()
            elif tab_name == "savings_tab":
                self.update_savings_tab()

    def logout(self):
        self.manager.transition.direction = 'right'
        self.manager.current = "start_screen"

# -----------------------
# App
# -----------------------
class FinanceApp(App):
    def build(self):
        sm = ScreenManager(transition=SlideTransition(duration=0.4))
        sm.add_widget(StartScreen(name="start_screen"))
        sm.add_widget(RegistrationScreen(name="registration_screen"))
        sm.add_widget(LoginScreen(name="login_screen"))
        sm.add_widget(DashboardScreen(name="dashboard_screen"))
        return sm

    def on_stop(self):
        conn.close()

if __name__ == "__main__":
    FinanceApp().run()
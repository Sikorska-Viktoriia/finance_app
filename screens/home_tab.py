from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from db_manager import cursor, conn, log_transaction

class HomeTab(Screen):
    """Home tab with balance and transactions."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_scheduled = False
    
    def get_app(self):
        """Safe way to get app instance."""
        return App.get_running_app()
    
    def on_enter(self):
        """Called when the screen is entered."""
        # Використовуємо Clock.schedule_once для забезпечення повного завантаження віджета
        if not self._update_scheduled:
            Clock.schedule_once(lambda dt: self.update_content(), 0.1)
            self._update_scheduled = True
    
    def on_pre_enter(self):
        """Called before the screen is entered."""
        self._update_scheduled = False
    
    def update_content(self):
        """Update home tab content."""
        # Перевіряємо, чи ids доступні
        if not self.ids:
            Clock.schedule_once(lambda dt: self.update_content(), 0.1)
            return
            
        app = self.get_app()
        
        # Додамо відлагоджувальний вивід
        print(f"DEBUG: app.current_user = {getattr(app, 'current_user', 'NOT SET')}")
        print(f"DEBUG: app.current_user_id = {getattr(app, 'current_user_id', 'NOT SET')}")
        
        # Змінимо перевірку на отримання даних з додатка
        if hasattr(app, 'current_user') and app.current_user:
            if 'welcome_label' in self.ids:
                self.ids.welcome_label.text = f"Ласкаво просимо, {app.current_user}!"
            
            # Отримуємо баланс з бази даних
            try:
                cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
                result = cursor.fetchone()
                if result:
                    app.balance = result[0]
                    if 'balance_label' in self.ids:
                        self.ids.balance_label.text = f"Баланс: {app.balance:.2f} $"
                else:
                    # Якщо гаманця немає, створюємо його
                    cursor.execute("INSERT INTO wallets (user_id, balance) VALUES (?, ?)", 
                                (app.current_user_id, 0.0))
                    conn.commit()
                    app.balance = 0.0
                    if 'balance_label' in self.ids:
                        self.ids.balance_label.text = f"Баланс: 0.00 $"
                    
                # Оновлюємо історію транзакцій
                self.update_transactions_history()
                    
            except Exception as e:
                print(f"Error updating balance: {e}")
                if 'balance_label' in self.ids:
                    self.ids.balance_label.text = "Помилка завантаження балансу"
        else:
            if 'welcome_label' in self.ids:
                self.ids.welcome_label.text = "Ласкаво просимо!"
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Баланс: 0.00 $"   
    def update_transactions_history(self):
        """Update transactions history display."""
        if 'history_container' not in self.ids:
            return

        history_container = self.ids.history_container
        history_container.clear_widgets()

        try:
            app = self.get_app()
            
            # Перевіряємо, чи є current_user_id
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                no_history_label = Label(
                    text="Увійдіть в систему",
                    font_size=dp(16),
                    color=(0.5, 0.5, 0.5, 1),
                    size_hint_y=None,
                    height=dp(40)
                )
                history_container.add_widget(no_history_label)
                return
            
            # Фільтруємо транзакції - виключаємо тип 'login'
            cursor.execute(
                "SELECT type, amount, description, created_at FROM transactions WHERE user_id=? AND type != 'login' ORDER BY created_at DESC LIMIT 10",
                (app.current_user_id,)
            )
            transactions = cursor.fetchall()

            if not transactions:
                no_history_label = Label(
                    text="Ще немає транзакцій",
                    font_size=dp(16),
                    color=(0.5, 0.5, 0.5, 1),
                    size_hint_y=None,
                    height=dp(40)
                )
                history_container.add_widget(no_history_label)
                return

            for trans_type, amount, description, created_at in transactions:
                try:
                    # Обробка різних форматів дати
                    if isinstance(created_at, str):
                        if '.' in created_at:
                            date_time = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        else:
                            date_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    else:
                        date_time = created_at
                    
                    date_str = date_time.strftime('%d.%m %H:%M')

                    # Визначаємо колір та знак тільки для фінансових операцій
                    if trans_type in ('deposit', 'savings_return'):
                        amount_color = (0, 0.6, 0, 1)  # зелений
                        sign = "+"
                    elif trans_type in ('withdrawal', 'savings_transfer'):
                        amount_color = (0.8, 0, 0, 1)  # червоний
                        sign = "-"
                    else:
                        amount_color = (0.5, 0.5, 0.5, 1)  # сірий
                        sign = ""

                    trans_text = f"{date_str} - {description} - {sign}{amount:.2f} $"

                    trans_label = Label(
                        text=trans_text,
                        size_hint_y=None,
                        height=dp(30),
                        halign="left",
                        text_size=(self.width - dp(20), None)
                    )
                    trans_label.color = amount_color
                    history_container.add_widget(trans_label)

                except Exception as e:
                    print(f"Error processing transaction: {e}")
                    continue

        except Exception as e:
            print(f"Error loading transactions history: {e}")
            error_label = Label(
                text="Помилка завантаження історії",
                color=(0.8, 0, 0, 1),
                size_hint_y=None,
                height=dp(40)
            )
            history_container.add_widget(error_label)
    
    def add_money(self):
        """Add money to wallet."""
        try:
            if 'amount_input' not in self.ids or 'balance_label' not in self.ids:
                return
                
            amount_text = self.ids.amount_input.text.strip()
            if not amount_text:
                self.ids.balance_label.text = "Будь ласка, введіть суму!"
                return
                
            amount = float(amount_text)
            if amount <= 0:
                self.ids.balance_label.text = "Сума має бути додатною!"
                return
            
            app = self.get_app()
            
            # Перевіряємо, чи є current_user_id
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                self.ids.balance_label.text = "Будь ласка, увійдіть в систему!"
                return
            
            # Оновлюємо баланс в базі даних
            cursor.execute("UPDATE wallets SET balance = balance + ? WHERE user_id=?", 
                        (amount, app.current_user_id))
            conn.commit()
            
            # Отримуємо оновлений баланс
            cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
            result = cursor.fetchone()
            if result:
                app.balance = result[0]
            
            self.ids.balance_label.text = f"Баланс: {app.balance:.2f} $"
            self.ids.amount_input.text = ""
            
            log_transaction(cursor, conn, app.current_user_id, "deposit", amount, "Поповнення гаманця")
            
            self.update_transactions_history()
            
        except ValueError:
            if 'amount_input' in self.ids:
                self.ids.amount_input.text = ""
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Введіть коректну суму!"
        except Exception as e:
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = f"Помилка: {str(e)}"

    def remove_money(self):
        """Remove money from wallet."""
        try:
            if 'amount_input' not in self.ids or 'balance_label' not in self.ids:
                return
                
            amount_text = self.ids.amount_input.text.strip()
            if not amount_text:
                self.ids.balance_label.text = "Будь ласка, введіть суму!"
                return
                
            amount = float(amount_text)
            if amount <= 0:
                self.ids.balance_label.text = "Сума має бути додатною!"
                return
            
            app = self.get_app()
            
            # Перевіряємо, чи є current_user_id
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                self.ids.balance_label.text = "Будь ласка, увійдіть в систему!"
                return
            
            # Перевіряємо баланс в базі даних
            cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
            result = cursor.fetchone()
            current_balance = result[0] if result else 0.0
            
            if amount > current_balance:
                self.ids.balance_label.text = "Недостатньо коштів!"
                return
            
            # Оновлюємо баланс в базі даних
            cursor.execute("UPDATE wallets SET balance = balance - ? WHERE user_id=?", 
                        (amount, app.current_user_id))
            conn.commit()
            
            # Отримуємо оновлений баланс
            cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
            result = cursor.fetchone()
            if result:
                app.balance = result[0]
                
            self.ids.balance_label.text = f"Баланс: {app.balance:.2f} $"
            self.ids.amount_input.text = ""
            
            log_transaction(cursor, conn, app.current_user_id, "withdrawal", amount, "Виведення з гаманця")
            
            self.update_transactions_history()
            
        except ValueError:
            if 'amount_input' in self.ids:
                self.ids.amount_input.text = ""
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Введіть коректну суму!"
        except Exception as e:
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = f"Помилка: {str(e)}"
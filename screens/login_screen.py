from kivy.uix.screenmanager import Screen
from kivy.app import App
from db_manager import conn, cursor, check_password, log_transaction

class LoginScreen(Screen):
    """Екран входу користувача."""
    def login_user(self):
        email = self.ids.email.text.strip()
        password = self.ids.password_field.ids.password_input.text.strip()
        msg_label = self.ids.login_message

        try:
            cursor.execute("SELECT id, username, password FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            if user and check_password(password, user[2]):
                msg_label.text = f"Успішний вхід: {user[1]}"
                
                # Отримуємо додаток
                app = App.get_running_app()
                
                # Зберігаємо дані користувача в ДОДАТКУ
                app.current_user = user[1]
                app.current_user_id = user[0]

                # Отримуємо баланс з бази даних
                cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (user[0],))
                result = cursor.fetchone()
                if result:
                    app.balance = result[0]
                else:
                    # Якщо гаманця немає, створюємо його
                    cursor.execute("INSERT INTO wallets (user_id, balance) VALUES (?, ?)", 
                                 (user[0], 0.0))
                    conn.commit()
                    app.balance = 0.0

                # НЕ логуємо вхід як транзакцію - це не фінансова операція
                # log_transaction(cursor, conn, user[0], "login", 0, "Користувач увійшов")
                
                self.manager.transition.direction = 'left'
                self.manager.current = "dashboard_screen"
            else:
                msg_label.text = "Невірна електронна адреса або пароль"
        except Exception as e:
            msg_label.text = f"Помилка входу: {str(e)}"
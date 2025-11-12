# screens/login_screen.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from db_manager import conn, cursor, check_password

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
                
                app = App.get_running_app()
                
                # Зберігаємо дані в ОБОХ місцях для безпеки
                app.root.current_user = user[1]
                app.root.current_user_id = user[0]
                app.current_user = user[1]
                app.current_user_id = user[0]

                # Отримуємо баланс
                cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (user[0],))
                result = cursor.fetchone()
                if result:
                    balance = result[0]
                    app.root.balance = balance
                    app.balance = balance
                else:
                    cursor.execute("INSERT INTO wallets (user_id, balance) VALUES (?, ?)", 
                                 (user[0], 0.0))
                    conn.commit()
                    balance = 0.0
                    app.root.balance = balance
                    app.balance = balance

                print(f"Login successful: {user[1]}, balance: {balance}")
                
                self.manager.transition.direction = 'left'
                self.manager.current = "dashboard_screen"
                
                # Примусово оновлюємо dashboard після входу
                Clock.schedule_once(lambda dt: self.force_dashboard_update(), 0.5)
                
            else:
                msg_label.text = "Невірна електронна адреса або пароль"
        except Exception as e:
            msg_label.text = f"Помилка входу: {str(e)}"

    def force_dashboard_update(self):
        """Force dashboard to update after login."""
        dashboard = self.manager.get_screen('dashboard_screen')
        if hasattr(dashboard, 'update_all_tabs'):
            dashboard.update_all_tabs()
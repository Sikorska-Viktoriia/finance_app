from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from db_manager import conn, cursor, is_valid_email, is_valid_password, hash_password, log_transaction

class RegistrationScreen(Screen):
    """Реєстрація нового користувача."""
    def register_user(self):
        username = self.ids.username.text.strip()
        email = self.ids.email.text.strip()
        password = self.ids.password_field.ids.password_input.text.strip()
        password_confirm = self.ids.password_confirm_field.ids.password_input.text.strip()
        msg_label = self.ids.reg_message

        if not (username and email and password and password_confirm):
            msg_label.text = "Будь ласка, заповніть усі поля"
            return

        if not is_valid_email(email):
            msg_label.text = "Невірний формат електронної адреси"
            return

        if password != password_confirm:
            msg_label.text = "Паролі не співпадають!"
            return

        if not is_valid_password(password):
            msg_label.text = "Пароль має містити щонайменше 6 символів"
            return

        try:
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                msg_label.text = "Ця електронна адреса вже зареєстрована"
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

            # Створюємо гаманець для нового користувача
            cursor.execute("INSERT INTO wallets(user_id, balance) VALUES(?, ?)", (user_id, 0))
            conn.commit()
            
            log_transaction(cursor, conn, user_id, "initial", 0, "Створено обліковий запис")

            # АВТОМАТИЧНИЙ ВХІД після реєстрації
            self.auto_login_after_registration(user_id, username, email)
            
        except Exception as e:
            msg_label.text = f"Помилка: {str(e)}"

    def auto_login_after_registration(self, user_id, username, email):
        """Автоматичний вхід після успішної реєстрації."""
        try:
            app = App.get_running_app()
            
            # Зберігаємо дані в ОБОХ місцях для безпеки
            app.root.current_user = username
            app.root.current_user_id = user_id
            app.current_user = username
            app.current_user_id = user_id

            # Встановлюємо баланс
            app.root.balance = 0.0
            app.balance = 0.0

            print(f"Auto-login after registration: {username}, user_id: {user_id}")
            
            # Переходимо на головний екран
            self.manager.transition.direction = 'left'
            self.manager.current = "dashboard_screen"
            
            # Примусово оновлюємо dashboard після входу
            Clock.schedule_once(lambda dt: self.force_dashboard_update(), 0.5)
            
        except Exception as e:
            print(f"Error during auto-login: {e}")
            # Якщо автоматичний вхід не вдався, показуємо повідомлення про успішну реєстрацію
            self.ids.reg_message.text = "Реєстрація успішна! Будь ласка, увійдіть вручну."
            self.manager.transition.direction = 'left'
            self.manager.current = "login_screen"

    def force_dashboard_update(self):
        """Force dashboard to update after registration."""
        dashboard = self.manager.get_screen('dashboard_screen')
        if hasattr(dashboard, 'update_all_tabs'):
            dashboard.update_all_tabs()
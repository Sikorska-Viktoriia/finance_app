from kivy.uix.screenmanager import Screen
from kivy.app import App
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

            # Отримуємо додаток і зберігаємо дані
            app = App.get_running_app()
            app.root.current_user = username
            app.root.current_user_id = user_id
            app.root.balance = 0.0

            self.manager.transition.direction = 'left'
            self.manager.current = "dashboard_screen"
        except Exception as e:
            msg_label.text = f"Помилка: {str(e)}"
from kivy.uix.screenmanager import Screen
from kivy.app import App
from db_manager import cursor

class AccountTab(Screen):
    """Account settings tab."""
    
    def on_enter(self):
        self.update_account_tab()
    
    def update_account_tab(self):
        """Update account tab content."""
        try:
            app = App.get_running_app()
            
            # Тепер дані зберігаються в додатку
            if hasattr(app, 'current_user') and hasattr(app, 'current_user_id'):
                self.ids.username_label.text = f"Користувач: {app.current_user}"
                cursor.execute("SELECT email FROM users WHERE id=?", (app.current_user_id,))
                email_result = cursor.fetchone()
                if email_result:
                    self.ids.email_label.text = f"Електронна пошта: {email_result[0]}"
                else:
                    self.ids.email_label.text = "Електронна пошта: не знайдено"
            else:
                self.ids.username_label.text = "Користувач: не авторизовано"
                self.ids.email_label.text = "Електронна пошта: не доступно"
                
        except Exception as e:
            print(f"Помилка оновлення акаунту: {e}")
            self.ids.username_label.text = "Помилка завантаження"
            self.ids.email_label.text = "Помилка завантаження"
    
    def logout(self):
        """Log out the current user and return to login screen."""
        try:
            app = App.get_running_app()
            
            # Скидаємо дані користувача в додатку
            app.current_user = ""
            app.current_user_id = 0
            app.balance = 0.0
            
            # Переходимо на екран входу
            app.root.current = "login_screen"
            app.root.transition.direction = 'right'
            
            print("Успішний вихід з системи")
            
        except Exception as e:
            print(f"Помилка при виході: {e}")
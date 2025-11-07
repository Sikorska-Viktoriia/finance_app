from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from screens.start_screen import StartScreen
from screens.registration_screen import RegistrationScreen
from screens.login_screen import LoginScreen
from screens.dashboard import DashboardScreen
from db_manager import conn


Builder.load_file("kv/screens.kv")

class FinanceScreenManager(ScreenManager):
    pass


class FinanceApp(App):
    def build(self):
        sm = FinanceScreenManager(transition=SlideTransition(duration=0.4))
        sm.add_widget(StartScreen(name="start_screen"))
        sm.add_widget(RegistrationScreen(name="registration_screen"))
        sm.add_widget(LoginScreen(name="login_screen"))
        sm.add_widget(DashboardScreen(name="dashboard_screen"))
        return sm

    def on_stop(self):
        """Закриває з’єднання з БД при завершенні."""
        conn.close()

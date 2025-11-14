from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.core.window import Window
from kivy.properties import StringProperty, NumericProperty

# Import screens
from screens import (StartScreen, RegistrationScreen, LoginScreen, 
                    DashboardScreen, HomeTab, SavingsTab, AnalyticsTab, 
                    AITab, AccountTab)

# Load KV file
Builder.load_file("kv/screens.kv")

class FinanceScreenManager(ScreenManager):
    # Властивості для зберігання даних користувача
    current_user = StringProperty("")
    current_user_id = NumericProperty(0)
    balance = NumericProperty(0.0)

class FinanceApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Зберігаємо дані користувача в додатку
        self.current_user = ""
        self.current_user_id = 0
        self.balance = 0.0

    def build(self):
        Window.clearcolor = (0.9, 0.95, 1.0, 1)
        
        sm = FinanceScreenManager(transition=SlideTransition(duration=0.2))
        sm.add_widget(StartScreen(name="start_screen"))
        sm.add_widget(RegistrationScreen(name="registration_screen"))
        sm.add_widget(LoginScreen(name="login_screen"))
        
        # Create dashboard with tabs
        dashboard = DashboardScreen(name="dashboard_screen")
        
        # Додаємо вкладки до tab_manager Dashboard з унікальними назвами
        dashboard.ids.tab_manager.add_widget(HomeTab(name="home"))
        dashboard.ids.tab_manager.add_widget(AnalyticsTab(name="analytics"))
        dashboard.ids.tab_manager.add_widget(SavingsTab(name="savings"))
        dashboard.ids.tab_manager.add_widget(AITab(name="ai"))
        dashboard.ids.tab_manager.add_widget(AccountTab(name="account"))
        
        sm.add_widget(dashboard)
        
        return sm

    def on_stop(self):
        from db_manager import conn
        conn.close()

if __name__ == "__main__":
    FinanceApp().run()
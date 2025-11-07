# screens/dashboard.py
from kivy.uix.screenmanager import Screen

class DashboardScreen(Screen):
    """Main dashboard screen that manages tabs."""
    
    def switch_tab(self, tab_name):
        """Switches between tabs in the Dashboard."""
        if hasattr(self.ids, 'tab_manager'):
            available_tabs = ['home', 'analytics', 'savings', 'ai', 'account']  # Оновлені назви
            if tab_name in available_tabs:
                self.ids.tab_manager.current = tab_name
    
    def logout(self):
        """Logs the user out and returns to the start screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = "start_screen"
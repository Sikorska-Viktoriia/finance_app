# screens/dashboard.py
from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock

class DashboardScreen(Screen):
    """Main dashboard screen that manages tabs."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.initialize_content, 0.5)
    
    def initialize_content(self, dt):
        """Initialize tab content when dashboard loads."""
        print("Dashboard initializing...")
        self.update_all_tabs()
    
    def on_enter(self):
        """Called when screen is entered."""
        print("Dashboard screen entered")
        Clock.schedule_once(lambda dt: self.update_all_tabs(), 0.1)
    
    def update_all_tabs(self):
        """Update all tabs content."""
        if hasattr(self.ids, 'tab_manager'):
            print("Updating all tabs...")
            # Оновлюємо home tab
            home_tab = self.ids.tab_manager.get_screen('home')
            if home_tab and hasattr(home_tab, 'update_content'):
                print("Found home tab, updating content...")
                home_tab.update_content()
            else:
                print("Home tab not found or no update_content method")
    
    def switch_tab(self, tab_name):
        """Switches between tabs in the Dashboard."""
        if hasattr(self.ids, 'tab_manager'):
            available_tabs = ['home', 'analytics', 'savings', 'ai', 'account']
            if tab_name in available_tabs:
                self.ids.tab_manager.current = tab_name
                # Оновлюємо вміст при перемиканні табів
                current_tab = self.ids.tab_manager.current_screen
                if current_tab and hasattr(current_tab, 'update_content'):
                    current_tab.update_content()
    
    def logout(self):
        """Logs the user out and returns to the start screen."""
        self.manager.transition.direction = 'right'
        self.manager.current = "start_screen"
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import (
    StringProperty, 
    BooleanProperty, 
    NumericProperty, 
    ObjectProperty, 
    ListProperty
)
from kivy.app import App
from kivy.uix.behaviors import ButtonBehavior

class PasswordTextInput(BoxLayout):
    text = StringProperty("")
    hint_text = StringProperty("")
    password = BooleanProperty(True)
    
    def toggle_password(self):
        self.password = not self.password

class SavingsPlanItem(BoxLayout):
    plan_name = StringProperty("")
    current_amount = NumericProperty(0)
    target_amount = NumericProperty(0)
    progress = NumericProperty(0)
    days_left = NumericProperty(0)
    status = StringProperty("active")
    plan_id = NumericProperty(0)
    background_color = ListProperty([1, 1, 1, 1])
    is_selected = BooleanProperty(False)
    
    # Додано для оптимізації KV-коду та візуального виділення
    is_selected = BooleanProperty(False) 
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def on_touch_down(self, touch):
        """Обробка дотику для вибору плану."""
        if self.collide_point(*touch.pos):
            if self.on_plan_select:
                # Встановлення is_selected тепер відбувається у SavingsTab,
                # коли викликається on_plan_select.
                self.on_plan_select(self.plan_id, self.plan_name)
            return True
        return super().on_touch_down(touch)

    def get_app(self):
   
        return App.get_running_app()

class BottomMenuItem(BoxLayout):

    tab_name = StringProperty("")
    icon_source = StringProperty("")
    
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            # Припускаємо, що root є ScreenManager, і 'dashboard_screen' є одним з його екранів
            dashboard = app.root.get_screen('dashboard_screen') 
            if hasattr(dashboard, 'switch_tab'):
                dashboard.switch_tab(self.tab_name)
            return True 
        return super().on_touch_down(touch)

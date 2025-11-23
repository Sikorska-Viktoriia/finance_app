import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, StringProperty
from kivy.app import App
from kivy.clock import Clock
import threading


try:
    from ai_manager import AIManager
except ImportError as e:
    print(f"Import error: {e}")

    class AIManager:
        def __init__(self, user_id):
            self.user_id = user_id
            
        def ask(self, message):
            return f"Помилка: Не вдалося імпортувати AIManager. Тестова відповідь: {message}"
            
        def get_conversation_history(self):
            return []
            
        def clear_history(self):
            return True


class AITab(Screen):
    chat_output = ObjectProperty(None)
    chat_input = ObjectProperty(None)
    status_text = StringProperty("Готовий до роботи")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ai_manager = None
        
    def on_enter(self):
   
        app = App.get_running_app()
        if hasattr(app, 'current_user_id') and app.current_user_id:
            user_id = app.current_user_id
            self.ai_manager = AIManager(user_id)
            self.load_conversation_history()
            self.status_text = f"Помічник активований"
        else:
            self.status_text = "Увійдіть в систему"
            
    def load_conversation_history(self):
     
        if not self.ai_manager:
            return
            
        history = self.ai_manager.get_conversation_history()
        chat_text = ""
        
        for message, response, timestamp in history:
            chat_text += f"[color=2196f3] Ви:[/color] {message}\n"
            chat_text += f"[color=4caf50] Помічник:[/color] {response}\n\n"
            
        if self.chat_output:
            self.chat_output.text = chat_text
            self.scroll_to_bottom()

    def scroll_to_bottom(self):
        
        def scroll(dt):
            scroll_view = self.chat_output.parent
            while scroll_view and scroll_view.__class__.__name__ != 'ScrollView':
                scroll_view = scroll_view.parent
                
            if scroll_view and hasattr(scroll_view, 'scroll_y'):
                scroll_view.scroll_y = 0
                
        Clock.schedule_once(scroll, 0.1)
        
    def send_message(self):
      
        if not self.ai_manager:
            self.status_text = "Помічник не активований"
            return
            
        message = self.chat_input.text.strip()
        if not message:
            return
            

        current_text = self.chat_output.text
        self.chat_output.text = current_text + f"[color=2196f3] Ви:[/color] {message}\n[color=ffa500] Думає...[/color]\n\n"
        
        self.chat_input.text = ""
        self.status_text = "Обробляю запит..."
        self.scroll_to_bottom()
        

        thread = threading.Thread(target=self.process_ai_response, args=(message,))
        thread.daemon = True
        thread.start()

    def process_ai_response(self, message):

        try:
            response = self.ai_manager.ask(message)
      
            Clock.schedule_once(lambda dt: self.update_chat_response(response), 0)
        except Exception as e:
            error_msg = f"Помилка обробки: {str(e)}"
            Clock.schedule_once(lambda dt: self.update_chat_response(error_msg), 0)

    def update_chat_response(self, response):
     
        current_text = self.chat_output.text
        

        placeholder = "[color=ffa500] Думає...[/color]"
        idx = current_text.rfind(placeholder)
        
        if idx != -1:
          
            new_text = current_text[:idx] + current_text[idx:].replace(
                placeholder, 
                f"[color=4caf50] Помічник:[/color] {response}", 
                1 
            )
            self.chat_output.text = new_text
        else:
            
            self.chat_output.text = current_text + f"[color=4caf50] Помічник:[/color] {response}\n\n"
            
        self.status_text = "Готовий до роботи"
        self.scroll_to_bottom()

    def clear_chat(self):
       
        if self.ai_manager:
            self.ai_manager.clear_history() 
        self.chat_output.text = "[color=607d8b]Чат очищено. Задайте нове питання.[/color]"
        self.status_text = "Чат очищено"
        self.scroll_to_bottom()

    def show_financial_summary(self):
        
        if not self.ai_manager:
            self.status_text = "Помічник не активований"
            return
            
        message = "Надай короткий звіт про мою фінансову ситуацію за останній місяць."
        
        current_text = self.chat_output.text
        self.chat_output.text = current_text + f"[color=2196f3] Ви:[/color] {message}\n[color=ffa500] Думає...[/color]\n\n"
        self.status_text = "Обробляю запит..."
        self.scroll_to_bottom()
        
        thread = threading.Thread(target=self.process_ai_response, args=(message,))
        thread.daemon = True
        thread.start()
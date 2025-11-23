from kivy.uix.screenmanager import Screen
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.image import Image
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, Line
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
import os
import json
import shutil
from datetime import datetime
import csv

from db_manager import (
    cursor, conn, save_profile_photo, get_profile_photo, 
    log_user_session, get_login_history, get_user_settings, 
    update_user_settings, get_user_level, update_user_experience,
    log_security_action, get_user_by_email, check_password, 
    hash_password, get_total_balance, get_user_cards, get_user_envelopes,
    get_user_savings_plans, get_user_transactions, get_analytics_data,
    get_category_breakdown, get_top_categories, get_budget_progress
)


PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_BLUE = (0.92, 0.98, 1.0, 1)
ERROR_RED = (0.9, 0.2, 0.2, 1)
SUCCESS_GREEN = (0.2, 0.8, 0.3, 1)
WHITE = (1, 1, 1, 1)
DARK_TEXT = (0.1, 0.1, 0.1, 1)
LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
DARK_GRAY = (0.4, 0.4, 0.4, 1)

class WhitePopup(Popup):
   
    
    def __init__(self, **kwargs):
    
        kwargs.pop('background', '')
        kwargs.pop('background_color', None)
        kwargs.pop('background_normal', None)
        kwargs.pop('background_down', None)
        
        super().__init__(**kwargs)
        
    
        self.background = ''
        self.background_color = [1, 1, 1, 0]
        self.separator_height = 0
        self.auto_dismiss = False
        
   
        with self.canvas.before:
            Color(*WHITE)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
    
            Color(*DARK_GRAY)
            self.border_line = Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=1.2
            )
        
   
        self.bind(pos=self._update_graphics, size=self._update_graphics)
    
    def _update_graphics(self, *args):
        
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

class WhiteButton(Button):
   
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = PRIMARY_BLUE
        self.color = WHITE
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(45)
        self.bold = True
    
        with self.canvas.before:
            Color(*self.background_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.bind(pos=self._update_rect, size=self._update_rect)
        self.bind(background_color=self._update_color)
    
    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def _update_color(self, instance, value):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*value)
            self.rect = Rectangle(pos=self.pos, size=self.size)

class PasswordTextInput(TextInput):

    visibility_icon = StringProperty("eye-off")  
    
    def __init__(self, **kwargs):
      
        kwargs.pop('password', None)
        super().__init__(**kwargs)
        
        self.multiline = False
        self.padding = [dp(15), dp(12), dp(50), dp(12)]  
        self.background_normal = ''
        self.background_active = ''
        self.background_color = WHITE
        self.foreground_color = DARK_TEXT
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(48)
        self.cursor_color = PRIMARY_BLUE
        self.hint_text_color = LIGHT_GRAY
        self.write_tab = False
        
   
        self.password = True
        self.visibility_icon = "eye-off"
        
     
        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=1
            )
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

    def toggle_password(self):
        
        self.password = not self.password
        self.visibility_icon = "eye" if not self.password else "eye-off"
        self.focus = True  

class WhiteTextInput(TextInput):

    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.padding = [dp(15), dp(12)]
        self.background_normal = ''
        self.background_active = ''
        self.background_color = WHITE
        self.foreground_color = DARK_TEXT
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(48)
        self.cursor_color = PRIMARY_BLUE
        self.hint_text_color = LIGHT_GRAY
        self.write_tab = False
        

        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=1
            )
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)

class AccountTab(Screen):
    
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_session_id = None
        self.profile_photos_dir = "profile_photos"
        
    
        if not os.path.exists(self.profile_photos_dir):
            os.makedirs(self.profile_photos_dir)

    def on_enter(self):
   
        self.log_session_start()
        self.update_account_tab()

    def on_leave(self):
      
        self.log_session_end()

    def log_session_start(self):
    
        try:
            app = App.get_running_app()
            if hasattr(app, 'current_user_id') and app.current_user_id:
                device_info = f"{Window.width}x{Window.height}"
                self.current_session_id = log_user_session(cursor, conn, app.current_user_id, device_info, "127.0.0.1")
        except Exception as e:
            print(f"Помилка логування сесії: {e}")

    def log_session_end(self):
        
        try:
            if self.current_session_id:
                from db_manager import log_user_logout
                log_user_logout(cursor, conn, self.current_session_id)
        except Exception as e:
            print(f"Помилка логування кінця сесії: {e}")

    def update_account_tab(self):
    
        try:
            app = App.get_running_app()
            
            if hasattr(app, 'current_user') and hasattr(app, 'current_user_id') and app.current_user_id:
             
                cursor.execute("SELECT username, email, created_at FROM users WHERE id=?", (app.current_user_id,))
                user_data = cursor.fetchone()
                
                if user_data:
                    username, email, created_at = user_data
                    
           
                    self.ids.username_label.text = f"{username}"
                    self.ids.email_label.text = f"{email}"
                    
                    
                    total_balance = get_total_balance(cursor, app.current_user_id)
                    self.ids.balance_label.text = f"${total_balance:.2f}"
                    
                   
                    if created_at:
                        reg_date = created_at.split()[0] if ' ' in created_at else created_at
                        self.ids.registration_label.text = f"З нами з: {reg_date}"
                    else:
                        self.ids.registration_label.text = "З нами з: не вказано"
                    
                  
                    level_info = get_user_level(cursor, app.current_user_id)
                    self.ids.status_label.text = f"Рівень {level_info['level']} • {level_info['experience']} XP"
                    
                    
                    login_history = get_login_history(cursor, app.current_user_id, 1)
                    if login_history:
                        last_login = login_history[0]['login_time']
                        if ' ' in last_login:
                            last_login = last_login.split()[0]
                        self.ids.last_login_label.text = f"Останній вхід: {last_login}"
                    else:
                        self.ids.last_login_label.text = "Останній вхід: сьогодні"
                    
                  
                    self.load_profile_photo()
                
            else:
                self.show_unauthorized_state()
                
        except Exception as e:
            print(f"Помилка оновлення акаунту: {e}")
            self.show_error_state()

    def load_profile_photo(self):
      
        try:
            app = App.get_running_app()
            if hasattr(app, 'current_user_id') and app.current_user_id:
                photo_path = get_profile_photo(cursor, app.current_user_id)
                if photo_path and os.path.exists(photo_path):
                    self.ids.profile_image.source = photo_path
                else:
                    self.ids.profile_image.source = "assets/default_avatar.png"
        except Exception as e:
            print(f"Помилка завантаження фото: {e}")
            self.ids.profile_image.source = "assets/default_avatar.png"

  
    def change_profile_photo(self):
       
        try:
            content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
            
      
            with content.canvas.before:
                Color(*WHITE)
                self.content_rect = Rectangle(pos=content.pos, size=content.size)
            
            content.bind(pos=self._update_content_rect, size=self._update_content_rect)
            
            
            title_label = Label(
                text="Оберіть фото профілю",
                size_hint_y=None,
                height=dp(40),
                color=DARK_TEXT,
                font_size=dp(18),
                bold=True
            )
            content.add_widget(title_label)
            
        
            filechooser = FileChooserListView(
                filters=['*.png', '*.jpg', '*.jpeg'],
                path=os.getcwd()
            )
            
   
            content.add_widget(filechooser)
            
            btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            btn_select = WhiteButton(text='Вибрати')
            btn_select.background_color = PRIMARY_PINK
            btn_cancel = WhiteButton(text='Скасувати')
            btn_cancel.background_color = LIGHT_GRAY
            btn_cancel.color = DARK_TEXT
            
            def select_photo(instance):
                if filechooser.selection:
                    selected_file = filechooser.selection[0]
                    if self.process_profile_photo(selected_file):
                        popup.dismiss()
                    else:
                        self.show_message("Помилка при обробці фото")
                else:
                    self.show_message("Виберіть файл")
            
            btn_select.bind(on_press=select_photo)
            btn_cancel.bind(on_press=lambda x: popup.dismiss())
            
            btn_layout.add_widget(btn_select)
            btn_layout.add_widget(btn_cancel)
            content.add_widget(btn_layout)
            
            popup = WhitePopup(title='Виберіть фото профілю', content=content, size_hint=(0.9, 0.9))
            popup.open()
            
        except Exception as e:
            print(f"Помилка вибору фото: {e}")
            self.show_message("Помилка при виборі фото")

    def _update_content_rect(self, instance, value):
   
        if hasattr(self, 'content_rect'):
            self.content_rect.pos = instance.pos
            self.content_rect.size = instance.size

    def process_profile_photo(self, file_path):
       
        try:
            app = App.get_running_app()
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                return False
            
          
            filename = f"profile_{app.current_user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            dest_path = os.path.join(self.profile_photos_dir, filename)
          
            shutil.copy2(file_path, dest_path)
            
        
            if save_profile_photo(cursor, conn, app.current_user_id, dest_path):
             
                self.ids.profile_image.source = dest_path
                self.show_message("Фото профілю успішно оновлено!")
                
               
                log_security_action(cursor, conn, app.current_user_id, "profile_photo_changed", "Користувач змінив фото профілю")
                
                return True
            
            return False
            
        except Exception as e:
            print(f"Помилка обробки фото: {e}")
            return False


    def delete_account(self):
        """Показує підтвердження видалення акаунта"""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
  
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        content.add_widget(Label(
            text='Ця дія НЕЗВОРОТНА!\n\n' +
                 'Видаляться всі ваші дані:\n' +
                 '• Картки та транзакції\n' +
                 '• Конверти та плани\n' +
                 '• Вся історія та статистика\n\n' +
                 'Для підтвердження введіть пароль:',
            color=DARK_TEXT,
            text_size=(dp(400), None)
        ))
        
        password_input = PasswordTextInput(
            hint_text='Введіть ваш пароль'
        )
        content.add_widget(password_input)
        
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        btn_confirm = WhiteButton(text='Видалити акаунт')
        btn_confirm.background_color = ERROR_RED
        btn_cancel = WhiteButton(text='Скасувати')
        btn_cancel.background_color = LIGHT_GRAY
        btn_cancel.color = DARK_TEXT
        
        def confirm_delete(instance):
            password = password_input.text.strip()
            if password:
                if self.verify_password_for_deletion(password):
                    self.perform_account_deletion()
                    popup.dismiss()
                else:
                    self.show_message("Невірний пароль")
            else:
                self.show_message("Введіть пароль")
        
        btn_confirm.bind(on_press=confirm_delete)
        btn_cancel.bind(on_press=lambda x: popup.dismiss())
        
        btn_layout.add_widget(btn_confirm)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(btn_layout)
        
        popup = WhitePopup(title='Видалення акаунта', content=content, size_hint=(0.8, 0.6))
        popup.open()

    def verify_password_for_deletion(self, password):
      
        try:
            app = App.get_running_app()
            cursor.execute("SELECT password FROM users WHERE id=?", (app.current_user_id,))
            result = cursor.fetchone()
            
            if result:
                hashed_password = result[0]
                return check_password(password, hashed_password)
            return False
        except Exception as e:
            return False

    def perform_account_deletion(self):
     
        try:
            app = App.get_running_app()
            user_id = app.current_user_id
            username = app.current_user
            
         
            log_security_action(cursor, conn, user_id, "account_deletion", "Користувач видалив акаунт")
            
            
            tables = [
                'envelope_transactions', 'envelopes',
                'savings_transactions', 'savings_plans', 
                'transactions', 'user_cards',
                'security_logs', 'user_sessions', 
                'user_settings', 'user_levels',
                'user_profile_photos'
            ]
            
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
                except Exception as e:
                    print(f"Помилка видалення з {table}: {e}")
            
            
            cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
            
            conn.commit()
            
          
            self.cleanup_profile_photos(user_id)
            
           
            app.current_user = ""
            app.current_user_id = 0
            app.balance = 0.0
            
           
            app.root.current = "login_screen"
            app.root.transition.direction = 'right'
            
            self.show_message("Акаунт успішно видалено")
            
        except Exception as e:
            print(f"Помилка видалення акаунта: {e}")
            self.show_message("Помилка при видаленні акаунта")

    def cleanup_profile_photos(self, user_id):
        
        try:
            for filename in os.listdir(self.profile_photos_dir):
                if filename.startswith(f"profile_{user_id}_"):
                    file_path = os.path.join(self.profile_photos_dir, filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
        except Exception as e:
            print(f"Помилка очищення фото: {e}")

    def show_login_history(self):
        """Показує історію входів з прокруткою"""
        try:
            app = App.get_running_app()
            sessions = get_login_history(cursor, app.current_user_id, 20)  
            
            content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
            
         
            with content.canvas.before:
                Color(*WHITE)
                self.content_rect = Rectangle(pos=content.pos, size=content.size)
            
            content.bind(pos=self._update_content_rect, size=self._update_content_rect)
            
            content.add_widget(Label(
                text='Історія входів', 
                size_hint_y=None, 
                height=dp(40),
                bold=True,
                color=PRIMARY_PINK,
                font_size=dp(18)
            ))
            
            from kivy.uix.scrollview import ScrollView
            
      
            scroll_content = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None)
            scroll_content.bind(minimum_height=scroll_content.setter('height'))
            
            if not sessions:
                no_data_label = Label(
                    text='Історія входів відсутня',
                    size_hint_y=None,
                    height=dp(40),
                    color=DARK_TEXT
                )
                scroll_content.add_widget(no_data_label)
            else:
                for session in sessions:
                  
                    session_layout = BoxLayout(
                        orientation='vertical',
                        size_hint_y=None,
                        height=dp(80),
                        padding=dp(10)
                    )
                    
                    
                    with session_layout.canvas.before:
                        Color(0.95, 0.95, 0.95, 1)
                        session_layout.rect = Rectangle(pos=session_layout.pos, size=session_layout.size)
                    
                    session_layout.bind(pos=self._update_session_rect, size=self._update_session_rect)
                    
                   
                    device_label = Label(
                        text=f" {session['device']}",
                        size_hint_y=None,
                        height=dp(25),
                        text_size=(dp(450), None),
                        color=DARK_TEXT,
                        halign='left',
                        valign='middle'
                    )
                    device_label.bind(size=device_label.setter('text_size'))
                    
                    ip_label = Label(
                        text=f" IP: {session['ip']}",
                        size_hint_y=None,
                        height=dp(20),
                        text_size=(dp(450), None),
                        color=DARK_GRAY,
                        font_size=dp(12),
                        halign='left',
                        valign='middle'
                    )
                    ip_label.bind(size=ip_label.setter('text_size'))
                    
                
                    time_text = f" Вхід: {session['login_time']}"
                    if session['logout_time']:
                        time_text += f" | Тривалість: {session['duration']}"
                    else:
                        time_text += " |  Активна сесія"
                    
                    time_label = Label(
                        text=time_text,
                        size_hint_y=None,
                        height=dp(25),
                        font_size=dp(12),
                        text_size=(dp(450), None),
                        color=DARK_GRAY,
                        halign='left',
                        valign='middle'
                    )
                    time_label.bind(size=time_label.setter('text_size'))
                    
                    session_layout.add_widget(device_label)
                    session_layout.add_widget(ip_label)
                    session_layout.add_widget(time_label)
                    scroll_content.add_widget(session_layout)
            
         
            scroll_content.height = max(len(sessions) * dp(85), dp(200))
            
     
            scrollview = ScrollView(
                size_hint=(1, 1),
                do_scroll_x=False,
                do_scroll_y=True,
                scroll_type=['bars', 'content'],
                bar_width=dp(10),
                bar_color=[0.7, 0.7, 0.7, 0.8]
            )
            scrollview.add_widget(scroll_content)
            
         
            content.add_widget(scrollview)
            
         
            btn_close = WhiteButton(text='Закрити', size_hint_y=None, height=dp(50))
            btn_close.background_color = PRIMARY_BLUE
            btn_close.bind(on_press=lambda x: popup.dismiss())
            content.add_widget(btn_close)
            
            popup = WhitePopup(
                title='Історія входів', 
                content=content, 
                size_hint=(0.95, 0.8),
                auto_dismiss=True
            )
            popup.open()
            
        except Exception as e:
            print(f"Помилка показу історії: {e}")
            self.show_message("Помилка завантаження історії входів")

    def _update_session_rect(self, instance, value):
        
        if hasattr(instance, 'rect'):
            instance.rect.pos = instance.pos
            instance.rect.size = instance.size

    
    def edit_profile(self):
        
        try:
            app = App.get_running_app()
            cursor.execute("SELECT username, email FROM users WHERE id=?", (app.current_user_id,))
            user_data = cursor.fetchone()
            
            content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
            
         
            with content.canvas.before:
                Color(*WHITE)
                self.content_rect = Rectangle(pos=content.pos, size=content.size)
            
            content.bind(pos=self._update_content_rect, size=self._update_content_rect)
            
           
            content.add_widget(Label(text='Ім\'я:', color=DARK_TEXT))
            username_input = WhiteTextInput(
                text=user_data[0] if user_data else ''
            )
            content.add_widget(username_input)
            
            
            content.add_widget(Label(text='Email:', color=DARK_TEXT))
            email_input = WhiteTextInput(
                text=user_data[1] if user_data else ''
            )
            content.add_widget(email_input)
            
            
            content.add_widget(Label(text='Зміна пароля (за бажанням):', color=DARK_TEXT))
            
        
            current_password_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(70))
            current_password_layout.add_widget(Label(
                text='Поточний пароль:', 
                size_hint_y=None, 
                height=dp(25), 
                color=DARK_TEXT
            ))
            current_password_input = PasswordTextInput(
                hint_text='Введіть поточний пароль'
            )
            current_password_layout.add_widget(current_password_input)
            content.add_widget(current_password_layout)
            
            
            new_password_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(70))
            new_password_layout.add_widget(Label(
                text='Новий пароль:', 
                size_hint_y=None, 
                height=dp(25), 
                color=DARK_TEXT
            ))
            new_password_input = PasswordTextInput(
                hint_text='Введіть новий пароль'
            )
            new_password_layout.add_widget(new_password_input)
            content.add_widget(new_password_layout)
            
           
            confirm_password_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(70))
            confirm_password_layout.add_widget(Label(
                text='Підтвердіть новий пароль:', 
                size_hint_y=None, 
                height=dp(25), 
                color=DARK_TEXT
            ))
            confirm_password_input = PasswordTextInput(
                hint_text='Підтвердіть новий пароль'
            )
            confirm_password_layout.add_widget(confirm_password_input)
            content.add_widget(confirm_password_layout)
            
            btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            btn_save = WhiteButton(text='Зберегти')
            btn_save.background_color = PRIMARY_PINK
            btn_cancel = WhiteButton(text='Скасувати')
            btn_cancel.background_color = LIGHT_GRAY
            btn_cancel.color = DARK_TEXT
            
            def save_profile(instance):
                new_username = username_input.text.strip()
                new_email = email_input.text.strip()
                current_password = current_password_input.text
                new_password = new_password_input.text
                confirm_password = confirm_password_input.text
                
                if not new_username or not new_email:
                    self.show_message("Заповніть обов'язкові поля")
                    return
                
                
                password_change = bool(current_password or new_password or confirm_password)
                if password_change:
                    if not current_password:
                        self.show_message("Введіть поточний пароль")
                        return
                    if not new_password:
                        self.show_message("Введіть новий пароль")
                        return
                    if new_password != confirm_password:
                        self.show_message("Нові паролі не співпадають")
                        return
                    if len(new_password) < 6:
                        self.show_message("Новий пароль має містити принаймні 6 символів")
                        return
                
                self.update_user_profile(new_username, new_email, current_password, new_password)
                popup.dismiss()
            
            btn_save.bind(on_press=save_profile)
            btn_cancel.bind(on_press=lambda x: popup.dismiss())
            
            btn_layout.add_widget(btn_save)
            btn_layout.add_widget(btn_cancel)
            content.add_widget(btn_layout)
            
            popup = WhitePopup(title='Редагування профілю', content=content, size_hint=(0.9, 0.9))
            popup.open()
            
        except Exception as e:
            print(f"Помилка редагування профілю: {e}")
            self.show_message("Помилка відкриття редактора")

    def update_user_profile(self, username, email, current_password=None, new_password=None):
        
        try:
            app = App.get_running_app()
            
   
            if current_password and new_password:
                cursor.execute("SELECT password FROM users WHERE id=?", (app.current_user_id,))
                result = cursor.fetchone()
                if not result or not check_password(current_password, result[0]):
                    self.show_message("Невірний поточний пароль")
                    return
            
         
            update_fields = ["username=?", "email=?", "updated_at=CURRENT_TIMESTAMP"]
            params = [username, email]
            
            if new_password:
                update_fields.append("password=?")
                params.append(hash_password(new_password))
            
            params.append(app.current_user_id)
            
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id=?"
            cursor.execute(query, params)
            conn.commit()
            
         
            app.current_user = username
            
          
            action_desc = "Оновлено профіль"
            if new_password:
                action_desc += " зі зміною пароля"
            log_security_action(cursor, conn, app.current_user_id, "profile_updated", action_desc)
            
            self.update_account_tab()
            self.show_message("Профіль успішно оновлено!")
            
         
            update_user_experience(cursor, conn, app.current_user_id, 5)
            
        except Exception as e:
            print(f"Помилка оновлення профілю: {e}")
            self.show_message("Помилка при оновленні профілю")


    def download_user_data(self):
        """Експортує дані користувача"""
        try:
            app = App.get_running_app()
            
           
            exports_dir = "user_exports"
            if not os.path.exists(exports_dir):
                os.makedirs(exports_dir)
            
          
            filename = f"financial_data_{app.current_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(exports_dir, filename)
            
         
            self.create_text_report(filepath, app.current_user_id, app.current_user)
            
          
            log_security_action(cursor, conn, app.current_user_id, "data_export", "Користувач експортував дані")
            
            self.show_message(f"Дані експортовано:\n{filename}")
            
        except Exception as e:
            print(f"Помилка експорту: {e}")
            self.show_message("Помилка при експорті даних")

    def create_text_report(self, filepath, user_id, username):
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"ФІНАНСОВИЙ ЗВІТ - {username}\n")
                f.write("=" * 60 + "\n")
                f.write(f"Дата експорту: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
               
                f.write("👤 ОСНОВНА ІНФОРМАЦІЯ:\n")
                f.write("-" * 40 + "\n")
                cursor.execute("SELECT username, email, created_at FROM users WHERE id=?", (user_id,))
                user_data = cursor.fetchone()
                if user_data:
                    f.write(f"Ім'я: {user_data[0]}\n")
                    f.write(f"Email: {user_data[1]}\n")
                    f.write(f"Дата реєстрації: {user_data[2]}\n")
                
                total_balance = get_total_balance(cursor, user_id)
                f.write(f"Загальний баланс: ${total_balance:.2f}\n\n")
                
                
                cards = get_user_cards(cursor, user_id)
                f.write("💳 КАРТКИ:\n")
                f.write("-" * 40 + "\n")
                if cards:
                    for card in cards:
                        f.write(f"• {card['name']} ({card['bank']}): ${card['balance']:.2f}\n")
                else:
                    f.write("Картки відсутні\n")
                f.write("\n")
                
                
                envelopes = get_user_envelopes(cursor, user_id)
                f.write("📁 КОНВЕРТИ:\n")
                f.write("-" * 40 + "\n")
                if envelopes:
                    for env in envelopes:
                        f.write(f"• {env['name']}: ${env['current_amount']:.2f}/${env['budget_limit']:.2f} ({env['usage_percentage']:.1f}%)\n")
                else:
                    f.write("Конверти відсутні\n")
                f.write("\n")
                
               
                savings = get_user_savings_plans(cursor, user_id)
                f.write("🎯 ПЛАНИ ЗАОЩАДЖЕНЬ:\n")
                f.write("-" * 40 + "\n")
                if savings:
                    for plan in savings:
                        f.write(f"• {plan['name']}: ${plan['current_amount']:.2f}/${plan['target_amount']:.2f} ({plan['progress_percentage']:.1f}%)\n")
                else:
                    f.write("Плани заощаджень відсутні\n")
                f.write("\n")
                
             
                f.write("📊 АНАЛІТИКА ЗА МІСЯЦЬ:\n")
                f.write("-" * 40 + "\n")
                analytics = get_analytics_data(cursor, user_id, 'month')
                if analytics:
                    f.write(f"Доходи: ${analytics['total_income']:.2f}\n")
                    f.write(f"Витрати: ${analytics['total_expenses']:.2f}\n")
                    f.write(f"Чистий баланс: ${analytics['net_balance']:.2f}\n")
                    f.write(f"Середні витрати/день: ${analytics['average_daily']:.2f}\n")
                    f.write(f"Транзакції: {analytics['transactions_count']}\n")
                    f.write(f"Рівень заощаджень: {analytics['savings_rate']:.1f}%\n\n")
                
               
                top_categories = get_top_categories(cursor, user_id, 'month', 5)
                f.write("🏆 ТОП КАТЕГОРІЇ ВИТРАТ:\n")
                f.write("-" * 40 + "\n")
                if top_categories:
                    for cat in top_categories:
                        f.write(f"• {cat['name']}: ${cat['amount']:.2f} ({cat['value']:.1f}%)\n")
                else:
                    f.write("Дані про категорії відсутні\n")
                f.write("\n")
                
             
                transactions = get_user_transactions(cursor, user_id, 10)
                f.write("🔄 ОСТАННІ ТРАНЗАКЦІЇ:\n")
                f.write("-" * 40 + "\n")
                if transactions:
                    for trans in transactions:
                        amount_str = f"${trans['amount']:.2f}" if trans['amount'] >= 0 else f"-${abs(trans['amount']):.2f}"
                        f.write(f"• {trans['date'][:10]} | {trans['type']} | {amount_str} | {trans['description']}\n")
                else:
                    f.write("Транзакції відсутні\n")
                f.write("\n")
                
                f.write("=" * 60 + "\n")
                f.write("Звіт створено автоматично системою Financial Assistant\n")
                f.write("Усі дані захищено та конфіденційно\n")
                f.write("=" * 60 + "\n")
                
        except Exception as e:
            print(f"Помилка створення звіту: {e}")
            raise


    def show_level_info(self):
        
        try:
            app = App.get_running_app()
            level_info = get_user_level(cursor, app.current_user_id)
            
            content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
            
            
            with content.canvas.before:
                Color(*WHITE)
                self.content_rect = Rectangle(pos=content.pos, size=content.size)
            
            content.bind(pos=self._update_content_rect, size=self._update_content_rect)
            
         
            content.add_widget(Label(
                text=f'Рівень: {level_info["level"]}',
                font_size=dp(20),
                bold=True,
                size_hint_y=None,
                height=dp(40),
                color=PRIMARY_PINK
            ))
            
         
            progress_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(60), spacing=dp(5))
            progress_layout.add_widget(Label(
                text=f'Прогрес: {level_info["experience"]}/{level_info["next_level_xp"]} XP',
                size_hint_y=None,
                height=dp(20),
                color=DARK_TEXT
            ))
            
            progress_bar = ProgressBar(
                max=100,
                value=level_info['progress_percentage'],
                size_hint_y=None,
                height=dp(20)
            )
            progress_layout.add_widget(progress_bar)
            content.add_widget(progress_layout)
            
        
            achievements = level_info['achievements']
            if achievements:
                content.add_widget(Label(
                    text='Досягнення:',
                    size_hint_y=None,
                    height=dp(30),
                    bold=True,
                    color=DARK_TEXT
                ))
                
                for achievement in achievements:
                    content.add_widget(Label(
                        text=f"• {achievement}",
                        size_hint_y=None,
                        height=dp(25),
                        color=DARK_TEXT
                    ))
            else:
                content.add_widget(Label(
                    text='Ще немає досягнень',
                    size_hint_y=None,
                    height=dp(30),
                    color=DARK_GRAY
                ))
            
          
            content.add_widget(Label(
                text='\nЯк отримати XP:\n• Додавання транзакцій: +1 XP\n• Створення картки: +5 XP\n• Оновлення профілю: +5 XP',
                size_hint_y=None,
                height=dp(100),
                color=DARK_TEXT
            ))
            
            btn_close = WhiteButton(text='Закрити')
            btn_close.background_color = PRIMARY_BLUE
            btn_close.bind(on_press=lambda x: popup.dismiss())
            content.add_widget(btn_close)
            
            popup = WhitePopup(title='Рівень та досягнення', content=content, size_hint=(0.8, 0.7))
            popup.open()
            
        except Exception as e:
            print(f"Помилка показу інформації про рівень: {e}")

  
    def logout(self):
  
        try:
            app = App.get_running_app()
            
       
            log_security_action(cursor, conn, app.current_user_id, "logout", "Користувач вийшов з системи")
            
          
            self.log_session_end()
            
          
            app.current_user = ""
            app.current_user_id = 0
            app.balance = 0.0
            
           
            app.root.current = "login_screen"
            app.root.transition.direction = 'right'
            
        except Exception as e:
            print(f"Помилка при виході: {e}")

    def refresh_account(self):
    
        self.update_account_tab()
     
        app = App.get_running_app()
        update_user_experience(cursor, conn, app.current_user_id, 1)
        
        self.ids.refresh_button.opacity = 0.7
        Clock.schedule_once(self.reset_refresh_button, 0.5)
    
    def reset_refresh_button(self, dt):
     
        self.ids.refresh_button.opacity = 1

    def show_unauthorized_state(self):
     
        self.ids.username_label.text = "Не авторизовано"
        self.ids.email_label.text = "Не доступно"
        self.ids.balance_label.text = "$0.00"
        self.ids.registration_label.text = "Не доступно"
        self.ids.status_label.text = "Не авторизовано"
        self.ids.last_login_label.text = "Не доступно"
        self.ids.profile_image.source = "assets/default_avatar.png"

    def show_error_state(self):
 
        self.ids.username_label.text = "Помилка"
        self.ids.email_label.text = "Помилка"
        self.ids.balance_label.text = "Помилка"
        self.ids.registration_label.text = "Помилка"
        self.ids.status_label.text = "Помилка"
        self.ids.last_login_label.text = "Помилка"
        self.ids.profile_image.source = "assets/default_avatar.png"

    def show_message(self, message):
 
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(15))
        
      
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        content.add_widget(Label(text=message, color=DARK_TEXT, text_size=(dp(350), None)))
        
        btn_ok = WhiteButton(text='OK')
        btn_ok.background_color = PRIMARY_BLUE
        btn_ok.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(btn_ok)
        
        popup = WhitePopup(title='Повідомлення', content=content, size_hint=(0.7, 0.3))
        popup.open()
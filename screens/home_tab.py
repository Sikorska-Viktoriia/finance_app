from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.carousel import Carousel
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty
from kivy.graphics import Line, Rectangle, Color, RoundedRectangle
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import traceback

try:
    from db_manager import cursor, conn, log_transaction, get_user_cards, debug_transactions, get_total_balance, update_card_balance, create_user_card, update_user_card, delete_user_card, transfer_money_between_cards
except ImportError:
    class MockCursor:
        def execute(self, *args): pass
        def fetchall(self): return []
    cursor = MockCursor()
    class MockConn:
        def commit(self): pass
    conn = MockConn()
    def log_transaction(*args): pass
    def get_user_cards(*args): return []
    def debug_transactions(*args): return []
    def get_total_balance(*args): return 0.0
    def update_card_balance(*args): return True
    def create_user_card(*args): return 1
    def update_user_card(*args): return True
    def delete_user_card(*args): return True
    def transfer_money_between_cards(*args): return True, ""

# Кольорова палітра
PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_PINK = (1, 0.95, 0.95, 1)
LIGHT_BLUE = (0.92, 0.98, 1.0, 1)
ERROR_RED = (0.9, 0.2, 0.2, 1)
SUCCESS_GREEN = (0.2, 0.8, 0.3, 1)
WHITE = (1, 1, 1, 1)
DARK_TEXT = (0.1, 0.1, 0.1, 1)
LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
DARK_GRAY = (0.4, 0.4, 0.4, 1)

# Шифрування для номерів карток
class CardEncryption:
    def __init__(self):
        self.password = b"flamingo_card_encryption_key_2024"
        self.salt = b"flamingo_salt_2024"
        self._setup_encryption()
    
    def _setup_encryption(self):
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password))
        self.cipher_suite = Fernet(key)
    
    def encrypt_card_number(self, card_number):
        if not card_number:
            return None
        try:
            encrypted = self.cipher_suite.encrypt(card_number.encode('utf-8'))
            return encrypted.decode('utf-8')
        except Exception as e:
            return None
    
    def decrypt_card_number(self, encrypted_card):
        if not encrypted_card:
            return None
        try:
            decrypted = self.cipher_suite.decrypt(encrypted_card.encode('utf-8'))
            return decrypted.decode('utf-8')
        except Exception as e:
            # Якщо не вдається розшифрувати, повертаємо None
            return None

# Глобальний екземпляр шифрувальника
card_encryptor = CardEncryption()

def fix_existing_cards():
    try:
        # Припускаємо, що таблиця називається 'user_cards' (як у db_manager)
        cursor.execute("SELECT id, number FROM user_cards")
        cards = cursor.fetchall()
        
        for card_id, card_number in cards:
            if not card_number:
                continue

            is_encrypted = False
            decrypted_value = card_encryptor.decrypt_card_number(card_number)

            # Перевіряємо, чи розшифрований формат схожий на "XXXX XXXX XXXX XXXX"
            if decrypted_value and decrypted_value.count(' ') == 3 and len(decrypted_value) == 19:
                is_encrypted = True
            
            if not is_encrypted:
                clean_number = card_number.replace(" ", "").strip()
                if len(clean_number) == 16 and clean_number.isdigit():
                    formatted_number = f"{clean_number[:4]} {clean_number[4:8]} {clean_number[8:12]} {clean_number[12:16]}"
                    encrypted_number = card_encryptor.encrypt_card_number(formatted_number)
                    
                    if encrypted_number:
                        cursor.execute("UPDATE user_cards SET number = ? WHERE id = ?", 
                                     (encrypted_number, card_id))
        
        conn.commit()
    except Exception as e:
        pass

try:
    fix_existing_cards()
except Exception as e:
    pass

class ModernBankCard(BoxLayout):
    def __init__(self, card_data, **kwargs):
        super().__init__(**kwargs)
        self.card_data = card_data
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(250)
        self.padding = dp(35)
        self.spacing = dp(12)
        
        with self.canvas.before:
            Color(*self.get_darker_color(card_data['color']))
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(25)]
            )
            
            Color(1, 1, 1, 0.1)
            RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.6),
                size=(self.width, self.height * 0.4),
                radius=[dp(25)]
            )
            
            Color(1, 1, 1, 0.4)
            self.border = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(25)),
                width=dp(2)
            )
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
        header_layout = BoxLayout(
            size_hint_y=None,
            height=dp(30),
            spacing=dp(10)
        )
        
        bank_label = Label(
            text=card_data['bank'],
            size_hint_x=0.8,
            font_size=dp(16),
            bold=True,
            color=WHITE,
            halign='left'
        )
        bank_label.bind(size=bank_label.setter('text_size'))
        header_layout.add_widget(bank_label)
        self.add_widget(header_layout)
        
        number_layout = BoxLayout(
            size_hint_y=None,
            height=dp(40),
            orientation='vertical'
        )
        
        # ВИПРАВЛЕНО: Використовуємо коректно обчислений masked_number з load_user_cards
        masked_number = card_data.get('masked_number', '**** **** **** ****') 
        
        number_label = Label(
            text=masked_number,
            font_size=dp(18),
            color=WHITE
        )
        number_layout.add_widget(number_label)
        self.add_widget(number_layout)
        
        name_label = Label(
            text=card_data['name'].upper(),
            font_size=dp(14),
            color=(1, 1, 1, 0.8),
            halign='left'
        )
        name_label.bind(size=name_label.setter('text_size'))
        self.add_widget(name_label)
        
        balance_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50)
        )
        
        balance_label = Label(
            text=f"{card_data['balance']:.2f} $",
            font_size=dp(28),
            bold=True,
            color=WHITE,
            halign='left'
        )
        balance_label.bind(size=balance_label.setter('text_size'))
        
        balance_layout.add_widget(balance_label)
        balance_layout.add_widget(Label())
        self.add_widget(balance_layout)

    def get_darker_color(self, color):
        r, g, b, a = color
        return [max(0, r * 0.7), max(0, g * 0.7), max(0, b * 0.7), a]

    def update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(25))

class WhitePopup(Popup):
    
    def __init__(self, **kwargs):
        kwargs.pop('background', None)
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
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            
            Color(*DARK_GRAY)
            self.border_line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(10)),
                width=1.2
            )
        
        self.bind(pos=self._update_graphics, size=self._update_graphics)
    
    def _update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(10))

class WhiteButton(Button):
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = kwargs.get('background_color', PRIMARY_BLUE)
        self.color = WHITE
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(45)
        self.bold = True
        
        with self.canvas.before:
            Color(*self.background_color)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        
        self.bind(pos=self._update_rect, size=self._update_rect)
        self.bind(background_color=self._update_color)
    
    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def _update_color(self, instance, value):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*value)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])

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
        self.hint_text_color = DARK_GRAY
        self.write_tab = False
        
        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(
                rounded_rectangle=(self.x, self.y, self.width, self.height, dp(5)),
                width=1
            )
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(5))

class HomeTab(Screen):
    
    current_filter = StringProperty("Всі банки")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_scheduled = False
        self.cards_data = []
        self.available_banks = ["Всі банки"]
        self.current_popup = None
        Clock.schedule_once(self.delayed_init, 0.5)
    
    def delayed_init(self, dt):
        self.update_content()
    
    def get_app(self):
        return App.get_running_app()
    
    def on_enter(self):
        if not self._update_scheduled:
            Clock.schedule_once(lambda dt: self.update_content(), 0.1)
            self._update_scheduled = True
    
    def on_pre_enter(self):
        self._update_scheduled = False
    
    def update_content(self):
        app = self.get_app()
        
        if hasattr(app, 'current_user') and app.current_user:
            if 'welcome_label' in self.ids:
                self.ids.welcome_label.text = f"Вітаємо, {app.current_user}!"
            
            try:
                cards_balance = get_total_balance(cursor, app.current_user_id)
                
                if 'balance_label' in self.ids:
                    self.ids.balance_label.text = f"Загальний баланс: {cards_balance:.2f} $"
                    
                self.load_user_cards()
                self.update_transactions_history()
                    
            except Exception as e:
                if 'balance_label' in self.ids:
                    self.ids.balance_label.text = "Помилка завантаження"
        else:
            if 'welcome_label' in self.ids:
                self.ids.welcome_label.text = "Вітаємо!"
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Загальний баланс: 0.00 $"
    
    def load_user_cards(self):
        """
        Виправлено: Розшифровує зашифрований номер з db_manager та коректно маскує.
        """
        try:
            app = self.get_app()
            
            raw_cards_data = get_user_cards(cursor, app.current_user_id)
            
            self.cards_data = []
            for card in raw_cards_data:
                processed_card = card.copy()
                
                encrypted_number = card.get('number', '')
                
                # Крок 1: Розшифрування номера
                decrypted_number = card_encryptor.decrypt_card_number(encrypted_number)
                
                if decrypted_number:
                    # Крок 2: Очищення та маскування
                    clean_number = decrypted_number.replace(" ", "")
                    if len(clean_number) >= 4 and clean_number.isdigit():
                        last_four = clean_number[-4:]
                        processed_card['masked_number'] = f"**** **** **** {last_four}"
                    else:
                        processed_card['masked_number'] = "**** **** **** ****"
                    
                    processed_card['decrypted_number'] = decrypted_number # Форматований розшифрований (XXXX XXXX...)
                else:
                    processed_card['masked_number'] = "**** **** **** ****"
                    processed_card['decrypted_number'] = None
                
                # Зберігаємо зашифрований номер на випадок, якщо він потрібен в іншому місці
                processed_card['number'] = encrypted_number 
                
                self.cards_data.append(processed_card)
            
            self.update_bank_list()
            self.apply_bank_filter()
        
        except Exception as e:
            pass
    
    def check_card_exists(self, card_number, current_card_id=None):
        try:
            app = self.get_app()
            
            user_cards_data = get_user_cards(cursor, app.current_user_id)
            
            clean_new_number = card_number.replace(" ", "")
            
            for card in user_cards_data:
                encrypted_number = card.get('number', '')
                decrypted_existing = card_encryptor.decrypt_card_number(encrypted_number)
                
                if decrypted_existing:
                    clean_existing_number = decrypted_existing.replace(" ", "")
                    if clean_existing_number == clean_new_number:
                        if current_card_id is None or card.get('id') != current_card_id:
                            return True
            
            return False
        except Exception as e:
            return False
    
    def update_bank_list(self):
        banks = set(["Всі банки"])
        
        for card in self.cards_data:
            banks.add(card['bank'])
        
        self.available_banks = sorted(list(banks))
        
        if 'bank_spinner' in self.ids:
            self.ids.bank_spinner.values = self.available_banks
            if self.current_filter in self.available_banks:
                self.ids.bank_spinner.text = self.current_filter
            else:
                self.ids.bank_spinner.text = "Всі банки"
                self.current_filter = "Всі банки"
    
    def apply_bank_filter(self):
        filtered_cards = self.cards_data
        
        if self.current_filter != "Всі банки":
            filtered_cards = [card for card in self.cards_data if card['bank'] == self.current_filter]
        
        self.create_cards_carousel(filtered_cards)
    
    def change_bank_filter(self, bank_name):
        self.current_filter = bank_name
        self.apply_bank_filter()
    
    def create_cards_carousel(self, cards_data=None):
        if 'cards_container' not in self.ids:
            return
            
        if cards_data is None:
            cards_data = self.cards_data
            
        cards_container = self.ids.cards_container
        cards_container.clear_widgets()
        
        carousel = Carousel(
            direction='right',
            loop=False,
            size_hint=(1, 1)
        )
        
        for card_data in cards_data:
            card_widget = self.create_card_with_actions(card_data)
            carousel.add_widget(card_widget)
        
        if len(cards_data) < 10:
            add_card_button = self.create_add_card_button()
            carousel.add_widget(add_card_button)
        
        cards_container.add_widget(carousel)
    
    def create_card_with_actions(self, card_data):
        main_layout = BoxLayout(
            orientation='vertical',
            size_hint=(0.9, 0.9),
            spacing=dp(10),
            padding=dp(10)
        )
        
        card = ModernBankCard(card_data)
        main_layout.add_widget(card)
        
        actions_layout = BoxLayout(
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        topup_btn = WhiteButton(
            text='Поповнити',
            size_hint_x=0.5,
            background_color=SUCCESS_GREEN,
            color=WHITE,
            bold=True
        )
        topup_btn.bind(on_press=lambda x: self.show_deposit_modal(card_data))
        
        manage_btn = WhiteButton(
            text='Керувати',
            size_hint_x=0.5,
            background_color=PRIMARY_BLUE,
            color=WHITE,
            bold=True
        )
        manage_btn.bind(on_press=lambda x: self.show_card_management_modal(card_data))
        
        actions_layout.add_widget(topup_btn)
        actions_layout.add_widget(manage_btn)
        main_layout.add_widget(actions_layout)
        
        return main_layout
    
    def create_add_card_button(self):
        add_card_button = Button(
            text="+",
            font_size=dp(50),
            background_color=(0.3, 0.3, 0.3, 0.2),
            color=(1, 1, 1, 0.8),
            size_hint=(0.9, 0.9)
        )
        add_card_button.bind(on_press=self.show_create_card_modal)
        
        with add_card_button.canvas.before:
            Color(0.4, 0.4, 0.4, 0.3)
            RoundedRectangle(
                pos=add_card_button.pos,
                size=add_card_button.size,
                radius=[dp(20)]
            )
            Color(0.6, 0.6, 0.6, 0.6)
            Line(
                rounded_rectangle=[add_card_button.x, add_card_button.y, 
                                 add_card_button.width, add_card_button.height, dp(20)],
                dash_length=dp(5),
                dash_offset=dp(5),
                width=dp(2)
            )
        
        add_card_button.bind(pos=self._update_add_button_graphics, size=self._update_add_button_graphics)
        
        return add_card_button
    
    def _update_add_button_graphics(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.4, 0.4, 0.4, 0.3)
            RoundedRectangle(
                pos=instance.pos,
                size=instance.size,
                radius=[dp(20)]
            )
            Color(0.6, 0.6, 0.6, 0.6)
            Line(
                rounded_rectangle=[instance.x, instance.y, 
                                 instance.width, instance.height, dp(20)],
                dash_length=dp(5),
                dash_offset=dp(5),
                width=dp(2)
            )
    
    def show_create_card_modal(self, instance=None):
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text="Створити нову картку",
            font_size=dp(24),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(50),
            halign='left',
            valign='middle'
        )
        title.bind(size=title.setter('text_size'))
        content.add_widget(title)
        
        name_input = WhiteTextInput(
            hint_text="Назва картки",
            size_hint_y=None,
            height=dp(55)
        )
        content.add_widget(name_input)
        
        number_input = WhiteTextInput(
            hint_text="Номер картки (16 цифр)",
            input_filter='int',
            size_hint_y=None,
            height=dp(55)
        )
        content.add_widget(number_input)
        
        bank_spinner = Spinner(
            text="ПриватБанк",
            values=["ПриватБанк", "Монобанк", "Райффайзен", "Ощадбанк", "Укрексімбанк", "Інший"],
            size_hint_y=None,
            height=dp(55),
            color=DARK_TEXT,
            background_color=WHITE,
            halign='left',
            text_size=(dp(200), dp(55))
        )
        content.add_widget(bank_spinner)
        
        error_label = Label(
            text="",
            color=ERROR_RED,
            font_size=dp(16),
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(15))
        
        cancel_btn = WhiteButton(text="Скасувати")
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        
        create_btn = WhiteButton(text="Створити")
        create_btn.background_color = PRIMARY_PINK
        
        def create_card(instance):
            card_name = name_input.text.strip()
            card_number = number_input.text.strip()
            bank_name = bank_spinner.text
            
            if not card_name:
                error_label.text = "Введіть назву картки"
                return
                
            if len(card_number) != 16:
                error_label.text = "Введіть коректний номер картки (16 цифр)"
                return
            
            if self.check_card_exists(card_number):
                error_label.text = "Картка з таким номером вже існує"
                return
            
            success = self.create_card_from_modal(card_name, card_number, bank_name)
            if success:
                popup.dismiss()
            else:
                error_label.text = "Помилка при створенні картки"
        
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        create_btn.bind(on_press=create_card)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(create_btn)
        content.add_widget(buttons_layout)
        
        popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.85, 0.7)
        )
        popup.open()
    
    def _update_content_rect(self, instance, value):
        self.content_rect.pos = instance.pos
        self.content_rect.size = instance.size
    
    def create_card_from_modal(self, card_name, card_number, bank_name):
        try:
            formatted_number = f"{card_number[:4]} {card_number[4:8]} {card_number[8:12]} {card_number[12:16]}"
            app = self.get_app()
            
            bank_colors = {
                'ПриватБанк': [0.6, 0.1, 0.1, 1],
                'Монобанк': [0.1, 0.3, 0.6, 1],
                'Райффайзен': [0.8, 0.4, 0.0, 1],
                'Ощадбанк': [0.0, 0.4, 0.1, 1],
                'Укрексімбанк': [0.4, 0.1, 0.6, 1],
                'Інший': [0.2, 0.2, 0.2, 1]
            }
            
            color = bank_colors.get(bank_name, [0.2, 0.4, 0.8, 1])
            
            encrypted_number = card_encryptor.encrypt_card_number(formatted_number)
            
            if not encrypted_number:
                self.show_error_message("Помилка шифрування номера картки")
                return False
            
            card_id = create_user_card(
                cursor, conn, 
                app.current_user_id, 
                card_name, 
                encrypted_number,
                bank_name,
                0.0,
                color
            )
            
            if card_id:
                self.load_user_cards()
                self.show_success_message(f"Картка '{card_name}' успішно створена!")
                return True
            else:
                self.show_error_message("Помилка при створенні картки")
                return False
                
        except Exception as e:
            self.show_error_message("Сталася помилка")
            return False

    def show_card_management_modal(self, card_data):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text=f"Керування карткою: {card_data['name']}",
            font_size=dp(20),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title)
        
        balance_label = Label(
            text=f"Баланс: ${card_data['balance']:.2f}",
            font_size=dp(16),
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(30)
        )
        content.add_widget(balance_label)
        
        buttons_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=0.7)
        
        edit_btn = WhiteButton(text="Редагувати картку")
        edit_btn.background_color = PRIMARY_BLUE
        edit_btn.bind(on_press=lambda x: (self.current_popup.dismiss(), self.show_edit_card_modal(card_data)))
        buttons_layout.add_widget(edit_btn)
        
        transfer_btn = WhiteButton(text="Переказати гроші")
        transfer_btn.background_color = (0.8, 0.6, 0.2, 1)
        transfer_btn.bind(on_press=lambda x: (self.current_popup.dismiss(), self.show_transfer_modal(card_data)))
        buttons_layout.add_widget(transfer_btn)
        
        delete_btn = WhiteButton(text="Видалити картку")
        delete_btn.background_color = ERROR_RED
        delete_btn.bind(on_press=lambda x: (self.current_popup.dismiss(), self.show_delete_confirmation(card_data)))
        buttons_layout.add_widget(delete_btn)
        
        content.add_widget(buttons_layout)
        
        close_btn = WhiteButton(text="Закрити")
        close_btn.background_color = LIGHT_GRAY
        close_btn.color = DARK_TEXT
        close_btn.bind(on_press=lambda x: self.current_popup.dismiss())
        content.add_widget(close_btn)
        
        self.current_popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.7, 0.45)
        )
        self.current_popup.open()

    def show_deposit_modal(self, card_data):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text=f"Поповнення картки: {card_data['name']}",
            font_size=dp(20),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title)
        
        amount_input = WhiteTextInput(
            hint_text="Сума для поповнення",
            input_filter='float',
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(amount_input)
        
        error_label = Label(
            text="",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(30)
        )
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = WhiteButton(text="Скасувати")
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: self.current_popup.dismiss())
        
        deposit_btn = WhiteButton(text="Поповнити")
        deposit_btn.background_color = SUCCESS_GREEN
        
        def deposit_to_card(instance):
            try:
                amount_text = amount_input.text.strip()
                if not amount_text:
                    error_label.text = "Введіть суму"
                    return
                    
                amount = float(amount_text)
                if amount <= 0:
                    error_label.text = "Сума має бути додатною"
                    return
                
                success = update_card_balance(cursor, conn, card_data['id'], amount)
                
                if success:
                    self.current_popup.dismiss()
                    self.load_user_cards()
                    self.update_content()
                    
                    log_transaction(cursor, conn, self.get_app().current_user_id, 
                                "deposit", amount, f"Поповнення картки {card_data['name']}")
                    
                    self.show_success_message(f"Картку '{card_data['name']}' поповнено на {amount:.2f} $!")
                else:
                    error_label.text = "Помилка при поповненні картки"
                    
            except ValueError:
                error_label.text = "Введіть коректну суму"
            except Exception as e:
                error_label.text = f"Помилка: {str(e)}"
        
        deposit_btn.bind(on_press=deposit_to_card)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(deposit_btn)
        content.add_widget(buttons_layout)
        
        self.current_popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.7, 0.4)
        )
        self.current_popup.open()

    def show_edit_card_modal(self, card_data):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text="Редагувати картку",
            font_size=dp(20),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title)
        
        decrypted_number = card_data.get('decrypted_number', '')
        
        name_input = WhiteTextInput(
            text=card_data['name'],
            hint_text="Назва картки",
            size_hint_y=None,
            height=dp(45)
        )
        content.add_widget(name_input)
        
        number_input = WhiteTextInput(
            text=decrypted_number.replace(' ', '') if decrypted_number else "",
            hint_text="Номер картки",
            input_filter='int',
            size_hint_y=None,
            height=dp(45)
        )
        content.add_widget(number_input)
        
        bank_spinner = Spinner(
            text=card_data['bank'],
            values=["ПриватБанк", "Монобанк", "Райффайзен", "Ощадбанк", "Укрексімбанк", "Інший"],
            size_hint_y=None,
            height=dp(45),
            color=DARK_TEXT,
            background_color=WHITE,
            halign='left',
            text_size=(dp(200), dp(45))
        )
        content.add_widget(bank_spinner)
        
        error_label = Label(
            text="",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(30)
        )
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = WhiteButton(text="Скасувати")
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: self.current_popup.dismiss())
        
        save_btn = WhiteButton(text="Зберегти")
        save_btn.background_color = PRIMARY_PINK
        
        def save_changes(instance):
            new_name = name_input.text.strip()
            new_number = number_input.text.strip()
            new_bank = bank_spinner.text
            
            if not new_name:
                error_label.text = "Введіть назву картки"
                return
                
            if not new_number or len(new_number) != 16 or not new_number.isdigit():
                error_label.text = "Введіть коректний номер картки (16 цифр)"
                return
            
            clean_original = decrypted_number.replace(" ", "") if decrypted_number else ""
            if new_number != clean_original:
                if self.check_card_exists(new_number, current_card_id=card_data['id']):
                    error_label.text = "Картка з таким номером вже існує"
                    return
            
            formatted_number = f"{new_number[:4]} {new_number[4:8]} {new_number[8:12]} {new_number[12:16]}"
            
            encrypted_new_number = card_encryptor.encrypt_card_number(formatted_number)
            
            if not encrypted_new_number:
                error_label.text = "Помилка шифрування номера картки"
                return
            
            success = update_user_card(
                cursor, conn,
                card_data['id'],
                name=new_name,
                number=encrypted_new_number,
                bank=new_bank
            )
            
            if success:
                self.current_popup.dismiss()
                self.load_user_cards()
                self.show_success_message("Картку успішно оновлено!")
            else:
                error_label.text = "Помилка при оновленні картки"
        
        save_btn.bind(on_press=save_changes)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(save_btn)
        content.add_widget(buttons_layout)
        
        self.current_popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.8, 0.6)
        )
        self.current_popup.open()

    def show_delete_confirmation(self, card_data):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text=f"Видалити картку {card_data['name']}?",
            font_size=dp(18),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title)
        
        warning_label = Label(
            text="Цю дію не можна скасувати!",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(30)
        )
        content.add_widget(warning_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = WhiteButton(text="Скасувати")
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: self.current_popup.dismiss())
        
        delete_btn = WhiteButton(text="Видалити")
        delete_btn.background_color = ERROR_RED
        
        def delete_card(instance):
            success = delete_user_card(cursor, conn, card_data['id'])
            if success:
                self.current_popup.dismiss()
                self.load_user_cards()
                self.update_content()
                self.show_success_message("Картку успішно видалено!")
            else:
                self.show_error_message("Помилка при видаленні картки")
        
        delete_btn.bind(on_press=delete_card)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(delete_btn)
        content.add_widget(buttons_layout)
        
        self.current_popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.6, 0.3)
        )
        self.current_popup.open()

    def show_transfer_modal(self, from_card_data):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text=f"Переказ з картки: {from_card_data['name']}",
            font_size=dp(20),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(title)
        
        other_cards = [card for card in self.cards_data if card['id'] != from_card_data['id']]
        if not other_cards:
            error_label = Label(
                text="Немає інших карток для переказу",
                color=ERROR_RED,
                size_hint_y=None,
                height=dp(40)
            )
            content.add_widget(error_label)
            
            close_btn = WhiteButton(text="Закрити")
            close_btn.background_color = LIGHT_GRAY
            close_btn.color = DARK_TEXT
            close_btn.bind(on_press=lambda x: self.current_popup.dismiss())
            content.add_widget(close_btn)
            
            self.current_popup = WhitePopup(
                title='',
                content=content,
                size_hint=(0.7, 0.3)
            )
            self.current_popup.open()
            return
        
        to_card_spinner = Spinner(
            text=other_cards[0]['name'],
            values=[card['name'] for card in other_cards],
            size_hint_y=None,
            height=dp(45),
            color=DARK_TEXT,
            background_color=WHITE,
            halign='left',
            text_size=(dp(200), dp(45))
        )
        content.add_widget(to_card_spinner)
        
        amount_input = WhiteTextInput(
            hint_text="Сума для переказу",
            input_filter='float',
            size_hint_y=None,
            height=dp(45)
        )
        content.add_widget(amount_input)
        
        balance_label = Label(
            text=f"Доступно: ${from_card_data['balance']:.2f}",
            size_hint_y=None,
            height=dp(30),
            color=DARK_TEXT
        )
        content.add_widget(balance_label)
        
        error_label = Label(
            text="",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(30)
        )
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        cancel_btn = WhiteButton(text="Скасувати")
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: self.current_popup.dismiss())
        
        transfer_btn = WhiteButton(text="Переказати")
        transfer_btn.background_color = SUCCESS_GREEN

        def transfer_money(instance):
            try:
                amount_text = amount_input.text.strip()
                if not amount_text:
                    error_label.text = "Введіть суму"
                    return

                amount = float(amount_text)
                if amount <= 0:
                    error_label.text = "Сума має бути додатною"
                    return
                
                if amount > from_card_data['balance']:
                    error_label.text = "Недостатньо коштів"
                    return
                
                to_card_name = to_card_spinner.text
                to_card_id = None
                for card in other_cards:
                    if card['name'] == to_card_name:
                        to_card_id = card['id']
                        break
                
                if not to_card_id:
                    error_label.text = "Картку отримувача не знайдено"
                    return
                
                success, message = transfer_money_between_cards(
                    cursor, conn,
                    from_card_data['id'],
                    to_card_id,
                    amount
                )
                
                if success:
                    self.current_popup.dismiss()
                    self.load_user_cards()
                    self.update_content()
                    self.show_success_message(f"Переказ {amount:.2f} $ успішний!")
                    log_transaction(cursor, conn, self.get_app().current_user_id, 
                                  "transfer", amount, f"Переказ між картками")
                else:
                    error_label.text = message
                    
            except ValueError:
                error_label.text = "Введіть коректну суму"
            except Exception as e:
                error_label.text = f"Помилка: {str(e)}"
        
        transfer_btn.bind(on_press=transfer_money)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(transfer_btn)
        content.add_widget(buttons_layout)
        
        self.current_popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.8, 0.6)
        )
        self.current_popup.open()

    def update_transactions_history(self):
        if 'history_container' not in self.ids:
            return

        history_container = self.ids.history_container
        history_container.clear_widgets()
        history_container.orientation = 'vertical'
        history_container.size_hint_y = None
        history_container.bind(minimum_height=history_container.setter('height'))

        try:
            app = self.get_app()
            
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                no_history_label = Label(
                    text="Увійдіть в систему",
                    font_size=dp(16),
                    color=DARK_GRAY,
                    size_hint_y=None,
                    height=dp(40)
                )
                history_container.add_widget(no_history_label)
                return
            
            transactions = debug_transactions(cursor, app.current_user_id)

            if not transactions:
                no_history_label = Label(
                    text="Ще немає транзакцій",
                    font_size=dp(16),
                    color=DARK_GRAY,
                    size_hint_y=None,
                    height=dp(80)
                )
                history_container.add_widget(no_history_label)
                return

            header_layout = BoxLayout(
                size_hint_y=None,
                height=dp(40),
                padding=[dp(10), dp(5), dp(10), dp(5)]
            )
            
            header_date = Label(text="Дата", size_hint_x=0.25, color=DARK_GRAY, font_size=dp(14), bold=True)
            header_desc = Label(text="Опис", size_hint_x=0.5, color=DARK_GRAY, font_size=dp(14), bold=True)
            header_amount = Label(text="Сума", size_hint_x=0.25, color=DARK_GRAY, font_size=dp(14), bold=True)
            
            header_layout.add_widget(header_date)
            header_layout.add_widget(header_desc)
            header_layout.add_widget(header_amount)
            history_container.add_widget(header_layout)

            filtered_transactions = []
            seen_transactions = set()
            
            for trans in transactions:
                trans_type, amount, description, created_at = trans
                
                if trans_type == 'card_creation':
                    continue
                
                trans_key = (trans_type, amount, description, created_at)
                
                if trans_key not in seen_transactions:
                    seen_transactions.add(trans_key)
                    filtered_transactions.append(trans)

            for i, (trans_type, amount, description, created_at) in enumerate(filtered_transactions):
                try:
                    if isinstance(created_at, str):
                        try:
                            if 'T' in created_at:
                                date_time = datetime.strptime(created_at.replace('T', ' ').split('.')[0], '%Y-%m-%d %H:%M:%S')
                            elif '.' in created_at:
                                date_time = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                            else:
                                date_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        except ValueError as e:
                            date_time = datetime.now()
                    else:
                        date_time = created_at
                    
                    date_str = date_time.strftime('%d.%m %H:%M')

                    if trans_type in ('deposit', 'savings_return', 'card_deposit', 'savings_interest', 'savings_completed', 'transfer_in', 'income'):
                        amount_color = SUCCESS_GREEN
                        sign = "+"
                    elif trans_type in ('withdrawal', 'savings_deposit', 'transfer', 'transfer_out', 'savings_transfer', 'expense'):
                        amount_color = ERROR_RED
                        sign = "-"
                    else:
                        amount_color = DARK_GRAY
                        sign = ""

                    trans_layout = BoxLayout(
                        size_hint_y=None,
                        height=dp(55),
                        padding=[dp(10), dp(5), dp(10), dp(5)]
                    )
                    
                    with trans_layout.canvas.before:
                        bg_color = (0.98, 0.98, 0.98, 1) if i % 2 == 0 else (0.95, 0.95, 0.95, 1)
                        Color(*bg_color)
                        trans_layout.bg_rect = Rectangle(
                            pos=trans_layout.pos,
                            size=trans_layout.size
                        )
                    
                    def update_bg_rect(instance, value):
                        instance.bg_rect.pos = instance.pos
                        instance.bg_rect.size = instance.size
                    
                    trans_layout.bind(pos=update_bg_rect, size=update_bg_rect)
                    
                    date_label = Label(
                        text=date_str,
                        size_hint_x=0.25,
                        color=DARK_TEXT,
                        font_size=dp(12)
                    )
                    
                    desc_label = Label(
                        text=description,
                        size_hint_x=0.5,
                        color=DARK_TEXT,
                        font_size=dp(13),
                        halign='left',
                        valign='middle',
                        text_size=(trans_layout.width * 0.5 - dp(20), None)
                    )
                    desc_label.bind(size=desc_label.setter('text_size'))
                    
                    amount_label = Label(
                        text=f"{sign}{abs(amount):.2f} $",
                        size_hint_x=0.25,
                        color=amount_color,
                        font_size=dp(13),
                        bold=True
                    )
                    
                    trans_layout.add_widget(date_label)
                    trans_layout.add_widget(desc_label)
                    trans_layout.add_widget(amount_label)
                    history_container.add_widget(trans_layout)
                    
                except Exception as e:
                    continue

        except Exception as e:
            error_label = Label(
                text="Помилка завантаження історії",
                color=ERROR_RED,
                size_hint_y=None,
                height=dp(40)
            )
            history_container.add_widget(error_label)

    def show_success_message(self, message):
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        content.add_widget(Label(
            text=message, 
            color=SUCCESS_GREEN,
            font_size=dp(18)
        ))
        
        ok_btn = WhiteButton(text='OK')
        ok_btn.background_color = PRIMARY_PINK
        ok_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(ok_btn)
        
        popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.6, 0.3)
        )
        popup.open()

    def show_error_message(self, message):
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        content.add_widget(Label(
            text=message, 
            color=ERROR_RED,
            font_size=dp(18)
        ))
        
        ok_btn = WhiteButton(text='OK')
        ok_btn.background_color = PRIMARY_BLUE
        ok_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(ok_btn)
        
        popup = WhitePopup(
            title='',
            content=content,
            size_hint=(0.6, 0.3)
        )
        popup.open()
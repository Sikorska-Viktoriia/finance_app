from kivy.uix.boxlayout import BoxLayout
from kivy.uix.modalview import ModalView
from kivy.uix.spinner import Spinner
from kivy.uix.carousel import Carousel
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import (
    StringProperty, 
    BooleanProperty, 
    NumericProperty, 
    ObjectProperty, 
    ListProperty
)
from kivy.app import App
from kivy.uix.behaviors import ButtonBehavior
from kivy.metrics import dp

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
    
    on_plan_select = ObjectProperty(None, allownone=True)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def on_touch_down(self, touch):
        """Обробка дотику для вибору плану."""
        if self.collide_point(*touch.pos):
            if self.on_plan_select:
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
            dashboard = app.root.get_screen('dashboard_screen') 
            if hasattr(dashboard, 'switch_tab'):
                dashboard.switch_tab(self.tab_name)
            return True 
        return super().on_touch_down(touch)

class BankCard(BoxLayout):
    card_id = NumericProperty(0)
    card_name = StringProperty("")
    balance = NumericProperty(0.0)
    card_number = StringProperty("**** **** **** 0000")
    bank_name = StringProperty("")
    card_color = ListProperty([0.2, 0.4, 0.8, 1])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (0.9, 0.8)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        self.padding = dp(20)
        self.spacing = dp(10)
        
        with self.canvas.before:
            Color(*self.card_color)
            self.rect = RoundedRectangle(
                pos=self.pos, 
                size=self.size, 
                radius=[dp(20),]
            )
        
        self.bind(pos=self.update_rect, size=self.update_rect)
        
        # Логотип банку
        bank_icon = self.get_bank_icon()
        if bank_icon:
            icon_label = Label(
                text=f"{bank_icon} {self.bank_name}",
                font_size=dp(16),
                color=(1, 1, 1, 0.9),
                size_hint_y=None,
                height=dp(30)
            )
            self.add_widget(icon_label)
        
        # Назва картки
        title_label = Label(
            text=self.card_name,
            font_size=dp(18),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(30)
        )
        self.add_widget(title_label)
        
        # Номер картки
        number_label = Label(
            text=self.card_number,
            font_size=dp(16),
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(25)
        )
        self.add_widget(number_label)
        
        # Баланс
        balance_label = Label(
            text=f"Баланс: {self.balance:.2f} $",
            font_size=dp(20),
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(30)
        )
        self.add_widget(balance_label)
        
    def get_bank_icon(self):
        """Get icon for bank."""
        icons = {
            'ПриватБанк': '🏦',
            'Монобанк': '💳',
            'Райффайзен': '🦁',
            'Ощадбанк': '🐷',
            'Укрексімбанк': '🇺🇦',
            'Інший': '💼'
        }
        return icons.get(self.bank_name, '💳')
        
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class CreateCardModal(ModalView):
    """Modal window for creating new card."""
    
    def __init__(self, home_tab, **kwargs):
        super().__init__(**kwargs)
        self.home_tab = home_tab
        self.size_hint = (0.8, 0.6)
        self.auto_dismiss = False
        self.background_color = [1, 1, 1, 1]
        self.create_ui()
        
    def create_ui(self):
        """Create modal UI."""
        layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Title
        title_label = Label(
            text="Створити нову картку",
            font_size=dp(20),
            bold=True,
            size_hint_y=None,
            height=dp(40)
        )
        layout.add_widget(title_label)
        
        # Form container
        form_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=0.7)
        
        # Card name
        name_label = Label(
            text="Назва картки:",
            font_size=dp(16),
            size_hint_y=None,
            height=dp(25)
        )
        form_layout.add_widget(name_label)
        
        self.card_name_input = TextInput(
            hint_text="Наприклад: Основна картка",
            multiline=False,
            font_size=dp(16),
            size_hint_y=None,
            height=dp(45)
        )
        form_layout.add_widget(self.card_name_input)
        
        # Card number
        number_label = Label(
            text="Номер картки (16 цифр):",
            font_size=dp(16),
            size_hint_y=None,
            height=dp(25)
        )
        form_layout.add_widget(number_label)
        
        self.card_number_input = TextInput(
            hint_text="0000000000000000",
            multiline=False,
            font_size=dp(16),
            input_filter='int',
            size_hint_y=None,
            height=dp(45)
        )
        form_layout.add_widget(self.card_number_input)
        
        # Bank selection
        bank_label = Label(
            text="Банк:",
            font_size=dp(16),
            size_hint_y=None,
            height=dp(25)
        )
        form_layout.add_widget(bank_label)
        
        self.bank_spinner = Spinner(
            text="ПриватБанк",
            values=["ПриватБанк", "Монобанк", "Райффайзен", "Ощадбанк", "Укрексімбанк", "Інший"],
            size_hint_y=None,
            height=dp(45)
        )
        form_layout.add_widget(self.bank_spinner)
        
        layout.add_widget(form_layout)
        
        # Error label
        self.error_label = Label(
            text="",
            size_hint_y=None,
            height=dp(30)
        )
        layout.add_widget(self.error_label)
        
        # Buttons
        buttons_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10)
        )
        
        cancel_btn = Button(
            text="Скасувати",
            size_hint_x=0.5,
            on_press=lambda x: self.dismiss()
        )
        buttons_layout.add_widget(cancel_btn)
        
        create_btn = Button(
            text="Створити",
            size_hint_x=0.5,
            on_press=lambda x: self.create_card()
        )
        buttons_layout.add_widget(create_btn)
        
        layout.add_widget(buttons_layout)
        
        self.add_widget(layout)
    
    def create_card(self):
        """Create new card with specified parameters."""
        try:
            card_name = self.card_name_input.text.strip()
            card_number = self.card_number_input.text.strip()
            bank_name = self.bank_spinner.text
            
            if not card_name:
                self.error_label.text = "Введіть назву картки"
                return
                
            if not card_number or len(card_number) != 16 or not card_number.isdigit():
                self.error_label.text = "Введіть коректний номер картки (16 цифр)"
                return
            
            # Форматуємо номер картки
            formatted_number = f"{card_number[:4]} {card_number[4:8]} {card_number[8:12]} {card_number[12:16]}"
            
            app = self.home_tab.get_app()
            
            # Кольори для різних банків
            bank_colors = {
                'ПриватБанк': [0.8, 0.2, 0.2, 1],
                'Монобанк': [0.2, 0.4, 0.8, 1],
                'Райффайзен': [1.0, 0.5, 0.0, 1],
                'Ощадбанк': [0.0, 0.6, 0.2, 1],
                'Укрексімбанк': [0.6, 0.2, 0.8, 1],
                'Інший': [0.3, 0.3, 0.3, 1]
            }
            
            color = bank_colors.get(bank_name, [0.2, 0.4, 0.8, 1])
            
            # Створюємо картку в базі даних
            from db_manager import create_user_card, conn, cursor
            card_id = create_user_card(
                cursor, conn, 
                app.current_user_id, 
                card_name, 
                formatted_number,
                bank_name,
                0.0,
                color
            )
            
            if card_id:
                self.dismiss()
                self.home_tab.load_user_cards()
                self.home_tab.show_success_message(f"Картка '{card_name}' успішно створена!")
            else:
                self.error_label.text = "Помилка при створенні картки"
                
        except Exception as e:
            print(f"Error creating card: {e}")
            self.error_label.text = "Сталася помилка"

    def on_open(self):
        """Reset fields when modal opens."""
        self.card_name_input.text = ""
        self.card_number_input.text = ""
        self.bank_spinner.text = "ПриватБанк"
        self.error_label.text = ""
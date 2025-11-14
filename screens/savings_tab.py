from datetime import datetime, timedelta
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.spinner import Spinner
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, Line
from db_manager import cursor, conn, log_transaction, log_savings_transaction, get_user_cards, get_user_card_by_id
from widgets import SavingsPlanItem

# Кольори
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


class WhitePopup(Popup):
    """Базовий клас білого попапу з темним текстом"""
    
    def __init__(self, **kwargs):
        # Видаляємо всі параметри фону, щоб уникнути конфліктів
        kwargs.pop('background', '')
        kwargs.pop('background_color', None)
        kwargs.pop('background_normal', None)
        kwargs.pop('background_down', None)
        
        super().__init__(**kwargs)
        
        # Робимо фон повністю прозорим
        self.background = ''
        self.background_color = [1, 1, 1, 0]
        self.separator_height = 0
        self.auto_dismiss = False
        
        # Створюємо білий фон через canvas
        with self.canvas.before:
            Color(*WHITE)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            
            # Додаємо темну рамку
            Color(*DARK_GRAY)
            self.border_line = Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=1.2
            )
        
        # Прив'язуємо оновлення позиції та розміру
        self.bind(pos=self._update_graphics, size=self._update_graphics)
    
    def _update_graphics(self, *args):
        """Оновлюємо графічні елементи при зміні позиції чи розміру"""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)


class WhiteButton(Button):
    """Стилізована кнопка для білих попапів"""
    
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
        
        # Додаємо фон через canvas
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


class WhiteTextInput(TextInput):
    """Стилізоване текстове поле для білих попапів"""
    
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
        
        # Додаємо рамку
        with self.canvas.after:
            Color(*DARK_GRAY)
            self.border_line = Line(
                rectangle=(self.x, self.y, self.width, self.height),
                width=1
            )
        
        self.bind(pos=self._update_border, size=self._update_border)
    
    def _update_border(self, *args):
        self.border_line.rectangle = (self.x, self.y, self.width, self.height)


class DatePickerPopup(WhitePopup):
    """Календар з білим дизайном та темним текстом"""
    
    def __init__(self, callback, **kwargs):
        self.callback = callback
        self.selected_date = datetime.now().date()
        super().__init__(**kwargs)
        self.create_widgets()
    
    def create_widgets(self):
        # Основний контейнер
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        # Додаємо білий фон для контенту
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(
            pos=self._update_content_rect,
            size=self._update_content_rect
        )
        
        # Заголовок з поточною датою
        self.date_label = Label(
            text=self.selected_date.strftime('%d.%m.%Y'),
            font_size=dp(24),
            size_hint_y=None,
            height=dp(50),
            color=DARK_TEXT,
            bold=True
        )
        content.add_widget(self.date_label)
        
        # Навігація по датах
        nav_layout = BoxLayout(
            orientation='horizontal', 
            size_hint_y=None, 
            height=dp(50), 
            spacing=dp(10)
        )
        
        # Кнопка попереднього дня
        prev_btn = WhiteButton(text='<')
        prev_btn.background_color = LIGHT_GRAY
        prev_btn.color = DARK_TEXT
        prev_btn.bind(on_press=self.prev_day)
        nav_layout.add_widget(prev_btn)
        
        # Кнопка "сьогодні"
        today_btn = WhiteButton(text='СЬОГОДНІ')
        today_btn.background_color = PRIMARY_PINK
        today_btn.bind(on_press=self.set_today)
        nav_layout.add_widget(today_btn)
        
        # Кнопка наступного дня
        next_btn = WhiteButton(text='>')
        next_btn.background_color = LIGHT_GRAY
        next_btn.color = DARK_TEXT
        next_btn.bind(on_press=self.next_day)
        nav_layout.add_widget(next_btn)
        
        content.add_widget(nav_layout)
        
        # Швидкий вибір дат
        quick_layout = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(120))
        
        quick_buttons = [
            ('+7 днів', PRIMARY_BLUE, 7),
            ('+30 днів', PRIMARY_BLUE, 30),
            ('+90 днів', PRIMARY_BLUE, 90),
            ('+1 місяць', PRIMARY_PINK, 30),
            ('+3 місяці', PRIMARY_PINK, 90),
            ('+6 місяців', PRIMARY_PINK, 180),
        ]
        
        for text, color, days in quick_buttons:
            btn = WhiteButton(text=text)
            btn.background_color = color
            btn.bind(on_press=lambda instance, d=days: self.add_days(d))
            quick_layout.add_widget(btn)
        
        content.add_widget(quick_layout)
        
        # Кнопки дій
        btn_layout = BoxLayout(
            orientation='horizontal', 
            spacing=dp(15), 
            size_hint_y=None, 
            height=dp(50)
        )
        
        # Кнопка вибору дати
        select_btn = WhiteButton(text='ОБРАТИ ДАТУ')
        select_btn.background_color = PRIMARY_PINK
        select_btn.bind(on_press=self.select_date)
        btn_layout.add_widget(select_btn)
        
        # Кнопка скасування
        cancel_btn = WhiteButton(text='СКАСУВАТИ')
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: self.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        self.content = content
    
    def _update_content_rect(self, instance, value):
        """Оновлюємо фон контенту"""
        self.content_rect.pos = instance.pos
        self.content_rect.size = instance.size
    
    def prev_day(self, instance):
        self.selected_date -= timedelta(days=1)
        self.update_display()
    
    def next_day(self, instance):
        self.selected_date += timedelta(days=1)
        self.update_display()
    
    def set_today(self, instance):
        self.selected_date = datetime.now().date()
        self.update_display()
    
    def add_days(self, days):
        self.selected_date += timedelta(days=days)
        self.update_display()
    
    def update_display(self):
        self.date_label.text = self.selected_date.strftime('%d.%m.%Y')
    
    def select_date(self, instance):
        self.callback(self.selected_date.strftime('%Y-%m-%d'))
        self.dismiss()


class SavingsTab(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_plan_id = None
        self.selected_plan_name = ""
        self.user_cards = []  # Список карток користувача
    
    def get_app(self):
        return App.get_running_app()
    
    def on_enter(self):
        Clock.schedule_once(lambda dt: self.update_savings_tab(), 0.1)
        self.clear_inputs()
        self.load_user_cards()
    
    def load_user_cards(self):
        """Завантажити карти користувача"""
        try:
            app = self.get_app()
            if hasattr(app, 'current_user_id') and app.current_user_id:
                self.user_cards = get_user_cards(cursor, app.current_user_id)
        except Exception as e:
            print(f"Error loading user cards: {e}")
            self.user_cards = []
    
    def clear_inputs(self):
        if hasattr(self, 'ids'):
            if 'plan_name_input' in self.ids:
                self.ids.plan_name_input.text = ""
            if 'target_amount_input' in self.ids:
                self.ids.target_amount_input.text = ""
            if 'deadline_input' in self.ids:
                self.ids.deadline_input.text = ""
            if 'savings_message' in self.ids:
                self.ids.savings_message.text = ""
        
        self.selected_plan_id = None
        self.selected_plan_name = ""
    
    def show_calendar(self):
        def set_date(date_str):
            self.ids.deadline_input.text = date_str
        
        popup = DatePickerPopup(
            callback=set_date,
            title='Оберіть дату дедлайну',
            size_hint=(0.85, 0.65)
        )
        popup.open()
    
    def update_savings_tab(self):
        if 'savings_container' not in self.ids:
            Clock.schedule_once(lambda dt: self.update_savings_tab(), 0.1)
            return

        savings_container = self.ids.savings_container
        savings_container.clear_widgets()
        
        try:
            app = self.get_app()
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                no_plans_label = Label(
                    text="Будь ласка, увійдіть в систему",
                    font_size=dp(16),
                    color=DARK_TEXT,
                    halign="center"
                )
                savings_container.add_widget(no_plans_label)
                return
            
            cursor.execute(
                "SELECT id, name, target_amount, current_amount, deadline, status FROM savings_plans WHERE user_id=? ORDER BY created_at DESC",
                (app.current_user_id,)
            )
            plans = cursor.fetchall()
            
            if not plans:
                no_plans_label = Label(
                    text="Ще немає планів заощаджень\n\nСтворіть свій перший план заощаджень!",
                    font_size=dp(18),
                    color=DARK_TEXT,
                    halign="center",
                    text_size=(dp(300), None)
                )
                savings_container.add_widget(no_plans_label)
                return
            
            for plan in plans:
                plan_id, name, target, current, deadline, status = plan
                
                progress = (current / target * 100) if target > 0 else 0
                
                days_left = 0
                if deadline:
                    try:
                        deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                        today = datetime.now().date()
                        days_left = max(0, (deadline_date - today).days)
                    except ValueError:
                        days_left = 0
                
                is_completed = current >= target
                
                # Контейнер для плану з кнопками операцій
                plan_container = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(160))
                
                # Додаємо сам план
                plan_item = SavingsPlanItem()
                plan_item.plan_name = name
                plan_item.current_amount = current
                plan_item.target_amount = target
                plan_item.progress = progress
                plan_item.days_left = days_left
                plan_item.status = status
                plan_item.plan_id = plan_id
                
                if self.selected_plan_id == plan_id:
                    plan_item.is_selected = True
                else:
                    plan_item.is_selected = False
                
                plan_item.bind(
                    on_release=lambda instance, p_id=plan_id, p_name=name: self.on_plan_select(p_id, p_name)
                )
                
                plan_container.add_widget(plan_item)
                
                # Кнопки операцій
                operations_layout = BoxLayout(
                    orientation='horizontal', 
                    size_hint_y=None, 
                    height=dp(50),
                    spacing=dp(5),
                    padding=[dp(10), dp(5), dp(10), dp(5)]
                )
                
                # Поле для введення суми
                amount_input = WhiteTextInput(
                    hint_text='Сума',
                    input_filter='float',
                    size_hint_x=0.3,
                    font_size=dp(14)
                )
                operations_layout.add_widget(amount_input)
                
                # Кнопка додати
                add_btn = Button(
                    text='Додати',
                    size_hint_x=0.2,
                    background_color=PRIMARY_PINK,
                    color=WHITE,
                    font_size=dp(12),
                    background_normal=''
                )
                
                def make_add_callback(pid, pname, inp):
                    return lambda x: self.add_to_plan(pid, pname, inp.text)
                
                add_btn.bind(on_press=make_add_callback(plan_id, name, amount_input))
                operations_layout.add_widget(add_btn)
                
                # Кнопка вилучити
                withdraw_btn = Button(
                    text='Вилучити',
                    size_hint_x=0.2,
                    background_color=PRIMARY_BLUE,
                    color=WHITE,
                    font_size=dp(12),
                    background_normal=''
                )
                
                def make_withdraw_callback(pid, pname, inp):
                    return lambda x: self.remove_from_plan(pid, pname, inp.text)
                
                withdraw_btn.bind(on_press=make_withdraw_callback(plan_id, name, amount_input))
                operations_layout.add_widget(withdraw_btn)
                
                # Кнопка завершити або редагувати
                if is_completed:
                    complete_btn = Button(
                        text='Завершити',
                        size_hint_x=0.2,
                        background_color=SUCCESS_GREEN,
                        color=WHITE,
                        font_size=dp(12),
                        background_normal=''
                    )
                    
                    def make_complete_callback(pid, pname):
                        return lambda x: self.complete_savings_plan(pid, pname)
                    
                    complete_btn.bind(on_press=make_complete_callback(plan_id, name))
                    operations_layout.add_widget(complete_btn)
                else:
                    edit_btn = Button(
                        text='Редаг.',
                        size_hint_x=0.15,
                        background_color=SUCCESS_GREEN,
                        color=WHITE,
                        font_size=dp(12),
                        background_normal=''
                    )
                    
                    def make_edit_callback(pid, pname):
                        return lambda x: self.edit_specific_plan(pid, pname)
                    
                    edit_btn.bind(on_press=make_edit_callback(plan_id, name))
                    operations_layout.add_widget(edit_btn)
                
                # Кнопка видалити
                delete_btn = Button(
                    text='×',
                    size_hint_x=0.15,
                    background_color=ERROR_RED,
                    color=WHITE,
                    font_size=dp(14),
                    bold=True,
                    background_normal=''
                )
                
                def make_delete_callback(pid, pname):
                    return lambda x: self.delete_specific_plan(pid, pname)
                
                delete_btn.bind(on_press=make_delete_callback(plan_id, name))
                operations_layout.add_widget(delete_btn)
                
                plan_container.add_widget(operations_layout)
                savings_container.add_widget(plan_container)
                
        except Exception as e:
            print(f"Error loading savings plans: {e}")
            error_label = Label(
                text="Помилка завантаження планів",
                font_size=dp(16),
                color=ERROR_RED,
                halign="center"
            )
            savings_container.add_widget(error_label)
    
    def on_plan_select(self, plan_id, plan_name):
        """Обробка вибору плану"""
        self.selected_plan_id = plan_id
        self.selected_plan_name = plan_name
        self.update_savings_tab()
        
        if 'savings_message' in self.ids:
            self.ids.savings_message.text = f"Обрано план: {plan_name}"
            self.ids.savings_message.color = SUCCESS_GREEN
    
    def create_savings_plan(self):
        """Створення нового плану заощаджень"""
        if not hasattr(self, 'ids'):
            return
            
        plan_name = self.ids.plan_name_input.text.strip()
        target_text = self.ids.target_amount_input.text.strip()
        deadline = self.ids.deadline_input.text.strip()
        
        if not plan_name:
            self.ids.savings_message.text = "Будь ласка, введіть назву плану"
            self.ids.savings_message.color = ERROR_RED
            return
        
        try:
            target_amount = float(target_text)
            if target_amount <= 0:
                self.ids.savings_message.text = "Цільова сума має бути додатною"
                self.ids.savings_message.color = ERROR_RED
                return
        except ValueError:
            self.ids.savings_message.text = "Введіть коректну цільову суму"
            self.ids.savings_message.color = ERROR_RED
            return
        
        if deadline:
            try:
                datetime.strptime(deadline, '%Y-%m-%d')
            except ValueError:
                self.ids.savings_message.text = "Невірний формат дати. Використовуйте РРРР-ММ-ДД"
                self.ids.savings_message.color = ERROR_RED
                return
        
        try:
            app = self.get_app()
            cursor.execute(
                "INSERT INTO savings_plans (user_id, name, target_amount, deadline) VALUES (?, ?, ?, ?)",
                (app.current_user_id, plan_name, target_amount, deadline if deadline else None)
            )
            plan_id = cursor.lastrowid
            
            log_savings_transaction(
                cursor, conn,
                app.current_user_id,
                plan_id,
                0,
                "plan_created",
                f"Створено план заощаджень: {plan_name}"
            )
            
            conn.commit()
            
            self.clear_inputs()
            self.ids.savings_message.text = f"План '{plan_name}' успішно створено!"
            self.ids.savings_message.color = SUCCESS_GREEN
            self.update_savings_tab()
            
        except Exception as e:
            print(f"Error creating plan: {e}")
            self.ids.savings_message.text = f"Помилка створення плану: {str(e)}"
            self.ids.savings_message.color = ERROR_RED
    
    def add_to_plan(self, plan_id, plan_name, amount_text, card_id=None):
        """Додавання грошей до плану з вибраної картки"""
        if not amount_text:
            self.ids.savings_message.text = "Введіть суму"
            self.ids.savings_message.color = ERROR_RED
            return
            
        try:
            amount = float(amount_text)
            if amount <= 0:
                self.ids.savings_message.text = "Сума має бути додатною"
                self.ids.savings_message.color = ERROR_RED
                return
            
            app = self.get_app()
            
            # Якщо картка не вибрана, показуємо попап вибору
            if not card_id:
                self.show_card_selection_popup(plan_id, plan_name, amount, "add")
                return
            
            # Перевіряємо баланс на вибраній картці
            selected_card = get_user_card_by_id(cursor, card_id)
            
            if not selected_card:
                self.ids.savings_message.text = "Картку не знайдено"
                self.ids.savings_message.color = ERROR_RED
                return
            
            if amount > selected_card['balance']:
                self.ids.savings_message.text = f"Недостатньо коштів на картці. Доступно: ${selected_card['balance']:.2f}"
                self.ids.savings_message.color = ERROR_RED
                return
            
            cursor.execute(
                "SELECT current_amount, target_amount FROM savings_plans WHERE id = ? AND user_id = ?",
                (plan_id, app.current_user_id)
            )
            plan = cursor.fetchone()
            
            if not plan:
                self.ids.savings_message.text = "План не знайдено"
                self.ids.savings_message.color = ERROR_RED
                return
            
            current_amount, target_amount = plan
            
            if current_amount + amount > target_amount:
                max_amount = target_amount - current_amount
                self.ids.savings_message.text = f"Максимум: ${max_amount:.2f}"
                self.ids.savings_message.color = ERROR_RED
                return
            
            # Знімаємо гроші з картки
            cursor.execute(
                "UPDATE user_cards SET balance = balance - ? WHERE id = ?",
                (amount, card_id)
            )
            
            # Оновлюємо план заощаджень
            cursor.execute(
                "UPDATE savings_plans SET current_amount = current_amount + ? WHERE id = ?",
                (amount, plan_id)
            )
            
            log_transaction(
                cursor, conn,
                app.current_user_id, 
                "savings_deposit", 
                amount, 
                f"Переведено до плану '{plan_name}' з картки {selected_card['name']}"
            )
            
            log_savings_transaction(
                cursor, conn,
                app.current_user_id,
                plan_id,
                amount,
                "deposit",
                f"Додано до плану заощаджень з картки {selected_card['name']}"
            )
            
            conn.commit()
            
            self.ids.savings_message.text = f"Успішно додано ${amount:.2f} до {plan_name} з картки {selected_card['name']}"
            self.ids.savings_message.color = SUCCESS_GREEN
            self.update_savings_tab()
            
        except ValueError:
            self.ids.savings_message.text = "Введіть коректну суму"
            self.ids.savings_message.color = ERROR_RED
        
        from kivy.app import App
        app = App.get_running_app()
        if hasattr(app, 'root') and hasattr(app.root, 'home_tab'):
            app.root.home_tab.update_transactions_history()

    def remove_from_plan(self, plan_id, plan_name, amount_text, card_id=None):
        """Вилучення грошей з плану на вибрану картку"""
        if not amount_text:
            self.ids.savings_message.text = "Введіть суму"
            self.ids.savings_message.color = ERROR_RED
            return
            
        try:
            amount = float(amount_text)
            if amount <= 0:
                self.ids.savings_message.text = "Сума має бути додатною"
                self.ids.savings_message.color = ERROR_RED
                return
            
            app = self.get_app()
            
            # Якщо картка не вибрана, показуємо попап вибору
            if not card_id:
                self.show_card_selection_popup(plan_id, plan_name, amount, "remove")
                return
            
            cursor.execute(
                "SELECT current_amount FROM savings_plans WHERE id = ? AND user_id = ?",
                (plan_id, app.current_user_id)
            )
            plan = cursor.fetchone()
            
            if not plan:
                self.ids.savings_message.text = "План не знайдено"
                self.ids.savings_message.color = ERROR_RED
                return
            
            current_amount = plan[0]
            
            if amount > current_amount:
                self.ids.savings_message.text = f"Недостатньо коштів. Доступно: ${current_amount:.2f}"
                self.ids.savings_message.color = ERROR_RED
                return
            
            # Додаємо гроші на картку
            cursor.execute(
                "UPDATE user_cards SET balance = balance + ? WHERE id = ?",
                (amount, card_id)
            )
            
            # Оновлюємо план заощаджень
            cursor.execute(
                "UPDATE savings_plans SET current_amount = current_amount - ? WHERE id = ?",
                (amount, plan_id)
            )
            
            selected_card = get_user_card_by_id(cursor, card_id)
            card_name = selected_card['name'] if selected_card else "картки"
            
            log_transaction(
                cursor, conn,
                app.current_user_id, 
                "savings_return", 
                amount, 
                f"Повернено з плану '{plan_name}' на картку {card_name}"
            )
            
            log_savings_transaction(
                cursor, conn,
                app.current_user_id,
                plan_id,
                amount,
                "withdrawal",
                f"Вилучено з плану заощаджень на картку {card_name}"
            )
            
            conn.commit()
            
            self.ids.savings_message.text = f"Успішно вилучено ${amount:.2f} з {plan_name} на картку {card_name}"
            self.ids.savings_message.color = SUCCESS_GREEN
            self.update_savings_tab()
            
        except ValueError:
            self.ids.savings_message.text = "Введіть коректну суму"
            self.ids.savings_message.color = ERROR_RED
        
        from kivy.app import App
        app = App.get_running_app()
        if hasattr(app, 'root') and hasattr(app.root, 'home_tab'):
            app.root.home_tab.update_transactions_history()

    def show_card_selection_popup(self, plan_id, plan_name, amount, operation_type):
        """Попап для вибору картки"""
        if not self.user_cards:
            self.ids.savings_message.text = "У вас немає карток"
            self.ids.savings_message.color = ERROR_RED
            return
        
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        operation_text = "додавання до" if operation_type == "add" else "вилучення з"
        title_label = Label(
            text=f"Оберіть картку для {operation_text} плану",
            font_size=dp(18),
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40),
            bold=True
        )
        content.add_widget(title_label)
        
        info_label = Label(
            text=f"План: {plan_name}\nСума: ${amount:.2f}",
            font_size=dp(16),
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(info_label)
        
        # Список карток
        card_spinner = Spinner(
            text=self.user_cards[0]['name'],
            values=[card['name'] for card in self.user_cards],
            size_hint_y=None,
            height=dp(45),
            background_color=WHITE,
            color=DARK_TEXT
        )
        content.add_widget(card_spinner)
        
        # Кнопки
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None, height=dp(50))
        
        def confirm_selection(_):
            selected_card_name = card_spinner.text
            selected_card = next((card for card in self.user_cards if card['name'] == selected_card_name), None)
            
            if selected_card:
                if operation_type == "add":
                    self.add_to_plan(plan_id, plan_name, str(amount), selected_card['id'])
                else:
                    self.remove_from_plan(plan_id, plan_name, str(amount), selected_card['id'])
                popup.dismiss()
        
        confirm_btn = WhiteButton(text='ПІДТВЕРДИТИ')
        confirm_btn.background_color = PRIMARY_PINK
        confirm_btn.bind(on_press=confirm_selection)
        btn_layout.add_widget(confirm_btn)
        
        cancel_btn = WhiteButton(text='СКАСУВАТИ')
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        popup = WhitePopup(
            title='Вибір картки',
            content=content,
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def _update_content_rect(self, instance, value):
        """Оновлюємо фон контенту для попапів"""
        self.content_rect.pos = instance.pos
        self.content_rect.size = instance.size

    def complete_savings_plan(self, plan_id, plan_name):
        """Завершення плану заощаджень з переведенням грошей на вибрану картку"""
        try:
            app = self.get_app()
            cursor.execute(
                "SELECT current_amount FROM savings_plans WHERE id = ? AND user_id = ?",
                (plan_id, app.current_user_id)
            )
            plan = cursor.fetchone()
            
            if not plan:
                self.ids.savings_message.text = "План не знайдено"
                self.ids.savings_message.color = ERROR_RED
                return
            
            current_amount = plan[0]
            
            if current_amount <= 0:
                self.ids.savings_message.text = "У плані немає коштів для завершення"
                self.ids.savings_message.color = ERROR_RED
                return
            
            # Показуємо попап вибору картки для завершення плану
            self.show_card_selection_for_completion(plan_id, plan_name, current_amount)
            
        except Exception as e:
            print(f"Error in complete_savings_plan: {e}")
            self.ids.savings_message.text = f"Помилка: {str(e)}"
            self.ids.savings_message.color = ERROR_RED
    
    def show_card_selection_for_completion(self, plan_id, plan_name, amount):
        """Попап для вибору картки при завершенні плану"""
        if not self.user_cards:
            self.ids.savings_message.text = "У вас немає карток"
            self.ids.savings_message.color = ERROR_RED
            return
        
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title_label = Label(
            text=f"Оберіть картку для завершення плану",
            font_size=dp(18),
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40),
            bold=True
        )
        content.add_widget(title_label)
        
        info_label = Label(
            text=f"План: {plan_name}\nСума: ${amount:.2f}",
            font_size=dp(16),
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(info_label)
        
        # Список карток
        card_spinner = Spinner(
            text=self.user_cards[0]['name'],
            values=[card['name'] for card in self.user_cards],
            size_hint_y=None,
            height=dp(45),
            background_color=WHITE,
            color=DARK_TEXT
        )
        content.add_widget(card_spinner)
        
        # Кнопки
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None, height=dp(50))
        
        def confirm_completion(_):
            selected_card_name = card_spinner.text
            selected_card = next((card for card in self.user_cards if card['name'] == selected_card_name), None)
            
            if selected_card:
                try:
                    app = self.get_app()
                    
                    # Додаємо гроші на картку
                    cursor.execute(
                        "UPDATE user_cards SET balance = balance + ? WHERE id = ?",
                        (amount, selected_card['id'])
                    )
                    
                    # Позначаємо план як завершений
                    cursor.execute(
                        "UPDATE savings_plans SET status='completed', current_amount=0 WHERE id=?",
                        (plan_id,)
                    )
                    
                    log_transaction(
                        cursor, conn,
                        app.current_user_id, 
                        "savings_completed", 
                        amount, 
                        f"Завершено план заощаджень: {plan_name} на картку {selected_card['name']}"
                    )
                    
                    log_savings_transaction(
                        cursor, conn,
                        app.current_user_id,
                        plan_id,
                        amount,
                        "plan_completed",
                        f"Завершено план заощаджень на картку {selected_card['name']}"
                    )
                    
                    conn.commit()
                    
                    popup.dismiss()
                    self.update_savings_tab()
                    self.ids.savings_message.text = f"План '{plan_name}' успішно завершено! ${amount:.2f} додано на картку {selected_card['name']}."
                    self.ids.savings_message.color = SUCCESS_GREEN
                    
                except Exception as e:
                    print(f"Error completing plan: {e}")
                    self.ids.savings_message.text = f"Помилка завершення плану: {str(e)}"
                    self.ids.savings_message.color = ERROR_RED
        
        complete_btn = WhiteButton(text='ЗАВЕРШИТИ')
        complete_btn.background_color = SUCCESS_GREEN
        complete_btn.bind(on_press=confirm_completion)
        btn_layout.add_widget(complete_btn)
        
        cancel_btn = WhiteButton(text='СКАСУВАТИ')
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        popup = WhitePopup(
            title='Завершення плану заощаджень',
            content=content,
            size_hint=(0.8, 0.5)
        )
        popup.open()

    def edit_specific_plan(self, plan_id, plan_name):
        """Редагування конкретного плану"""
        self.selected_plan_id = plan_id
        self.selected_plan_name = plan_name
        self.edit_savings_plan()

    def delete_specific_plan(self, plan_id, plan_name):
        """Видалення конкретного плану"""
        self.selected_plan_id = plan_id
        self.selected_plan_name = plan_name
        self.delete_savings_plan()

    def edit_savings_plan(self):
        """Редагування обраного плану заощаджень з білим попапом"""
        if not self.selected_plan_id:
            self.ids.savings_message.text = "Будь ласка, оберіть план для редагування"
            self.ids.savings_message.color = ERROR_RED
            return
        
        # Створюємо попап редагування
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        # Додаємо білий фон для контенту
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(
            pos=self._update_content_rect,
            size=self._update_content_rect
        )
        
        # Отримуємо поточні дані плану
        cursor.execute(
            "SELECT name, target_amount, deadline FROM savings_plans WHERE id = ?",
            (self.selected_plan_id,)
        )
        plan_data = cursor.fetchone()
        
        if not plan_data:
            return
        
        current_name, current_target, current_deadline = plan_data
        
        # Поле введення назви
        name_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        name_layout.add_widget(Label(
            text='Назва:', 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        name_input = WhiteTextInput(
            text=current_name, 
            size_hint_x=0.6
        )
        name_layout.add_widget(name_input)
        content.add_widget(name_layout)
        
        # Поле введення цільової суми
        target_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        target_layout.add_widget(Label(
            text='Цільова сума:', 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        target_input = WhiteTextInput(
            text=str(current_target), 
            size_hint_x=0.6
        )
        target_layout.add_widget(target_input)
        content.add_widget(target_layout)
        
        # Поле введення дедлайну з календарем
        deadline_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        deadline_layout.add_widget(Label(
            text='Дедлайн:', 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        
        deadline_input = WhiteTextInput(
            text=current_deadline if current_deadline else "", 
            hint_text="РРРР-ММ-ДД",
            size_hint_x=0.4
        )
        deadline_layout.add_widget(deadline_input)
        
        calendar_btn = WhiteButton(text='📅')
        calendar_btn.background_color = PRIMARY_BLUE
        
        def show_calendar(_):
            def set_date(date_str):
                deadline_input.text = date_str
            popup = DatePickerPopup(
                callback=set_date,
                title='Оберіть дату дедлайну',
                size_hint=(0.85, 0.65)
            )
            popup.open()
            
        calendar_btn.bind(on_press=show_calendar)
        deadline_layout.add_widget(calendar_btn)
        
        content.add_widget(deadline_layout)
        
        # Кнопки
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None, height=dp(50))
        
        def save_plan(_):
            try:
                new_name = name_input.text.strip()
                new_target = float(target_input.text.strip())
                new_deadline = deadline_input.text.strip()
                
                if not new_name:
                    self.ids.savings_message.text = "Введіть назву плану"
                    self.ids.savings_message.color = ERROR_RED
                    return
                
                if new_target <= 0:
                    self.ids.savings_message.text = "Цільова сума має бути додатною"
                    self.ids.savings_message.color = ERROR_RED
                    return
                
                if new_deadline:
                    try:
                        datetime.strptime(new_deadline, '%Y-%m-%d')
                    except ValueError:
                        self.ids.savings_message.text = "Невірний формат дати"
                        self.ids.savings_message.color = ERROR_RED
                        return
                
                cursor.execute(
                    "UPDATE savings_plans SET name=?, target_amount=?, deadline=? WHERE id=?",
                    (new_name, new_target, new_deadline if new_deadline else None, self.selected_plan_id)
                )
                
                app = self.get_app()
                log_savings_transaction(
                    cursor, conn,
                    app.current_user_id,
                    self.selected_plan_id,
                    0,
                    "plan_updated",
                    f"Оновлено план заощаджень"
                )
                
                conn.commit()
                
                self.selected_plan_name = new_name
                popup.dismiss()
                self.update_savings_tab()
                self.ids.savings_message.text = "План успішно оновлено!"
                self.ids.savings_message.color = SUCCESS_GREEN
                
            except ValueError:
                self.ids.savings_message.text = "Введіть коректну цільову суму"
                self.ids.savings_message.color = ERROR_RED
            except Exception as e:
                print(f"Error updating plan: {e}")
                self.ids.savings_message.text = f"Помилка оновлення: {str(e)}"
                self.ids.savings_message.color = ERROR_RED
        
        save_btn = WhiteButton(text='ЗБЕРЕГТИ')
        save_btn.background_color = PRIMARY_PINK
        save_btn.bind(on_press=save_plan)
        btn_layout.add_widget(save_btn)
        
        cancel_btn = WhiteButton(text='СКАСУВАТИ')
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        popup = WhitePopup(
            title='Редагування плану заощаджень',
            content=content,
            size_hint=(0.85, 0.65)
        )
        popup.open()

    def delete_savings_plan(self):
        """Видалення обраного плану заощаджень з білим попапом підтвердження"""
        if not self.selected_plan_id:
            self.ids.savings_message.text = "Будь ласка, оберіть план для видалення"
            self.ids.savings_message.color = ERROR_RED
            return
        
        # Створюємо попап підтвердження
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        
        # Додаємо білий фон для контенту
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(
            pos=self._update_content_rect,
            size=self._update_content_rect
        )
        
        cursor.execute(
            "SELECT current_amount FROM savings_plans WHERE id = ?",
            (self.selected_plan_id,)
        )
        result = cursor.fetchone()
        current_amount = result[0] if result else 0
        
        warning_text = f"Ви дійсно хочете видалити план '{self.selected_plan_name}'?"
        if current_amount > 0:
            warning_text += f"\n\nУвага: у плані є ${current_amount:.2f}. Ці кошти будуть повернуті на вашу картку."
        
        warning_label = Label(
            text=warning_text, 
            text_size=(dp(320), None), 
            color=DARK_TEXT,
            font_size=dp(16),
            halign='center',
            valign='middle'
        )
        content.add_widget(warning_label)
        
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None, height=dp(50))
        
        def confirm_delete(_):
            try:
                app = self.get_app()
                
                # Повертаємо гроші на картку, якщо вони є
                if current_amount > 0:
                    # Показуємо попап вибору картки для повернення коштів
                    self.show_card_selection_for_deletion(self.selected_plan_id, self.selected_plan_name, current_amount)
                else:
                    # Просто видаляємо план без коштів
                    cursor.execute("DELETE FROM savings_plans WHERE id=?", (self.selected_plan_id,))
                    
                    log_savings_transaction(
                        cursor, conn,
                        app.current_user_id,
                        self.selected_plan_id,
                        0,
                        "plan_deleted",
                        f"Видалено план заощаджень"
                    )
                    
                    conn.commit()
                    
                    self.clear_inputs()
                    self.update_savings_tab()
                    self.ids.savings_message.text = "План успішно видалено!"
                    self.ids.savings_message.color = SUCCESS_GREEN
                
                popup.dismiss()
                
            except Exception as e:
                print(f"Error deleting plan: {e}")
                self.ids.savings_message.text = f"Помилка видалення: {str(e)}"
                self.ids.savings_message.color = ERROR_RED
        
        delete_btn = WhiteButton(text='ВИДАЛИТИ')
        delete_btn.background_color = ERROR_RED
        delete_btn.bind(on_press=confirm_delete)
        btn_layout.add_widget(delete_btn)
        
        cancel_btn = WhiteButton(text='СКАСУВАТИ')
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        popup = WhitePopup(
            title='Підтвердження видалення',
            content=content,
            size_hint=(0.8, 0.5)
        )
        popup.open()
    
    def show_card_selection_for_deletion(self, plan_id, plan_name, amount):
        """Попап для вибору картки при видаленні плану з коштами"""
        if not self.user_cards:
            self.ids.savings_message.text = "У вас немає карток"
            self.ids.savings_message.color = ERROR_RED
            return
        
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title_label = Label(
            text=f"Оберіть картку для повернення коштів",
            font_size=dp(18),
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(40),
            bold=True
        )
        content.add_widget(title_label)
        
        info_label = Label(
            text=f"План: {plan_name}\nСума: ${amount:.2f}",
            font_size=dp(16),
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(50)
        )
        content.add_widget(info_label)
        
        # Список карток
        card_spinner = Spinner(
            text=self.user_cards[0]['name'],
            values=[card['name'] for card in self.user_cards],
            size_hint_y=None,
            height=dp(45),
            background_color=WHITE,
            color=DARK_TEXT
        )
        content.add_widget(card_spinner)
        
        # Кнопки
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None, height=dp(50))
        
        def confirm_deletion(_):
            selected_card_name = card_spinner.text
            selected_card = next((card for card in self.user_cards if card['name'] == selected_card_name), None)
            
            if selected_card:
                try:
                    app = self.get_app()
                    
                    # Додаємо гроші на картку
                    cursor.execute(
                        "UPDATE user_cards SET balance = balance + ? WHERE id = ?",
                        (amount, selected_card['id'])
                    )
                    
                    # Видаляємо план
                    cursor.execute("DELETE FROM savings_plans WHERE id=?", (plan_id,))
                    
                    log_transaction(
                        cursor, conn,
                        app.current_user_id, 
                        "savings_return", 
                        amount, 
                        f"Повернено при видаленні плану: {plan_name} на картку {selected_card['name']}"
                    )
                    
                    log_savings_transaction(
                        cursor, conn,
                        app.current_user_id,
                        plan_id,
                        amount,
                        "plan_deleted",
                        f"Видалено план заощаджень з поверненням на картку {selected_card['name']}"
                    )
                    
                    conn.commit()
                    
                    popup.dismiss()
                    self.clear_inputs()
                    self.update_savings_tab()
                    self.ids.savings_message.text = f"План успішно видалено! ${amount:.2f} повернуто на картку {selected_card['name']}."
                    self.ids.savings_message.color = SUCCESS_GREEN
                    
                except Exception as e:
                    print(f"Error deleting plan with funds: {e}")
                    self.ids.savings_message.text = f"Помилка видалення: {str(e)}"
                    self.ids.savings_message.color = ERROR_RED
        
        delete_btn = WhiteButton(text='ВИДАЛИТИ')
        delete_btn.background_color = ERROR_RED
        delete_btn.bind(on_press=confirm_deletion)
        btn_layout.add_widget(delete_btn)
        
        cancel_btn = WhiteButton(text='СКАСУВАТИ')
        cancel_btn.background_color = LIGHT_GRAY
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        popup = WhitePopup(
            title='Повернення коштів при видаленні',
            content=content,
            size_hint=(0.8, 0.5)
        )
        popup.open()
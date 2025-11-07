from datetime import datetime, timedelta
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from db_manager import cursor, conn, log_transaction, log_savings_transaction
from widgets import SavingsPlanItem

# Константи кольорів для консистентності
PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_PINK = (1, 0.95, 0.95, 1)
LIGHT_BLUE = (0.92, 0.98, 1.0, 1)
ERROR_RED = (0.9, 0.2, 0.2, 1)
SUCCESS_GREEN = (0.2, 0.8, 0.3, 1)
WHITE = (1, 1, 1, 1)
DARK_TEXT = (0.1, 0.1, 0.1, 1)
LIGHT_GRAY = (0.9, 0.9, 0.9, 1)


class StyledButton(Button):
    """Стилізована кнопка для модальних вікон"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = PRIMARY_BLUE
        self.color = WHITE
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(45)


class StyledTextInput(TextInput):
    """Стилізоване текстове поле для модальних вікон"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.multiline = False
        self.padding = [dp(12), dp(12)]
        self.background_color = WHITE
        self.background_normal = ''
        self.background_active = ''
        self.foreground_color = DARK_TEXT
        self.font_size = dp(16)
        self.size_hint_y = None
        self.height = dp(45)
        self.cursor_color = DARK_TEXT


class DatePickerPopup(Popup):
    """Custom date picker popup with white design."""
    
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.background_color = WHITE
        self.title_color = DARK_TEXT
        self.separator_color = LIGHT_GRAY
        self.callback = callback
        self.selected_date = datetime.now().date()
        self.create_widgets()
    
    def create_widgets(self):
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        content.background_color = WHITE
        
        # Current date display
        self.date_label = Label(
            text=self.selected_date.strftime('%d.%m.%Y'),
            font_size=dp(22),
            size_hint_y=None,
            height=dp(45),
            color=DARK_TEXT,
            bold=True
        )
        content.add_widget(self.date_label)
        
        # Date navigation
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        
        prev_btn = StyledButton(text='◀', background_color=PRIMARY_BLUE)
        prev_btn.bind(on_press=self.prev_day)
        nav_layout.add_widget(prev_btn)
        
        today_btn = StyledButton(text='Сьогодні', background_color=PRIMARY_PINK)
        today_btn.bind(on_press=self.set_today)
        nav_layout.add_widget(today_btn)
        
        next_btn = StyledButton(text='▶', background_color=PRIMARY_BLUE)
        next_btn.bind(on_press=self.next_day)
        nav_layout.add_widget(next_btn)
        
        content.add_widget(nav_layout)
        
        # Quick selection buttons
        quick_layout = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(120))
        
        quick_buttons = [
            ('+7 днів', PRIMARY_BLUE, lambda x: self.add_days(7)),
            ('+30 днів', PRIMARY_BLUE, lambda x: self.add_days(30)),
            ('+90 днів', PRIMARY_BLUE, lambda x: self.add_days(90)),
            ('+1 місяць', PRIMARY_PINK, lambda x: self.add_months(1)),
            ('+3 місяці', PRIMARY_PINK, lambda x: self.add_months(3)),
            ('+6 місяців', PRIMARY_PINK, lambda x: self.add_months(6)),
        ]
        
        for text, color, callback in quick_buttons:
            btn = StyledButton(text=text, background_color=color)
            btn.bind(on_press=callback)
            quick_layout.add_widget(btn)
        
        content.add_widget(quick_layout)
        
        # Action buttons
        btn_layout = BoxLayout(orientation='horizontal', spacing=dp(15), size_hint_y=None, height=dp(50))
        
        select_btn = StyledButton(text='Обрати дату', background_color=PRIMARY_PINK)
        select_btn.bind(on_press=self.select_date)
        btn_layout.add_widget(select_btn)
        
        cancel_btn = StyledButton(text='Скасувати', background_color=LIGHT_GRAY)
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: self.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        self.content = content
    
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
    
    def add_months(self, months):
        year = self.selected_date.year
        month = self.selected_date.month + months
        day = self.selected_date.day
        
        while month > 12:
            month -= 12
            year += 1
        
        try:
            self.selected_date = self.selected_date.replace(year=year, month=month, day=min(day, 28))
        except ValueError:
            self.selected_date = self.selected_date.replace(year=year, month=month, day=28)
        
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
    
    def get_app(self):
        return App.get_running_app()
    
    def on_enter(self):
        Clock.schedule_once(lambda dt: self.update_savings_tab(), 0.1)
        self.clear_inputs()
    
    def clear_inputs(self):
        if hasattr(self, 'ids'):
            if 'plan_name_input' in self.ids:
                self.ids.plan_name_input.text = ""
            if 'target_amount_input' in self.ids:
                self.ids.target_amount_input.text = ""
            if 'deadline_input' in self.ids:
                self.ids.deadline_input.text = ""
            if 'savings_amount_input' in self.ids:
                self.ids.savings_amount_input.text = ""
            if 'savings_message' in self.ids:
                self.ids.savings_message.text = ""
        
        self.selected_plan_id = None
        self.selected_plan_name = ""
        self.update_operation_buttons()
    
    def update_operation_buttons(self):
        if not hasattr(self, 'ids'):
            return
            
        has_selection = self.selected_plan_id is not None
        
        if 'add_funds_btn' in self.ids:
            self.ids.add_funds_btn.disabled = not has_selection
        if 'withdraw_funds_btn' in self.ids:
            self.ids.withdraw_funds_btn.disabled = not has_selection
        if 'edit_plan_btn' in self.ids:
            self.ids.edit_plan_btn.disabled = not has_selection
        if 'delete_plan_btn' in self.ids:
            self.ids.delete_plan_btn.disabled = not has_selection
        
        if 'selected_plan_label' in self.ids:
            if has_selection:
                self.ids.selected_plan_label.text = f"Обрано: {self.selected_plan_name}"
                self.ids.selected_plan_label.color = PRIMARY_PINK
            else:
                self.ids.selected_plan_label.text = "Оберіть план для операцій"
                self.ids.selected_plan_label.color = (0.5, 0.5, 0.5, 1)
    
    def show_calendar(self):
        def set_date(date_str):
            self.ids.deadline_input.text = date_str
        
        popup = DatePickerPopup(
            callback=set_date,
            title='Оберіть дату дедлайну',
            size_hint=(0.85, 0.65),
            separator_height=dp(1)
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
                    color=(0.5, 0.5, 0.5, 1),
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
                    color=(0.5, 0.5, 0.5, 1),
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
                
                plan_item = SavingsPlanItem()
                plan_item.plan_name = name
                plan_item.current_amount = current
                plan_item.target_amount = target
                plan_item.progress = progress
                plan_item.days_left = days_left
                plan_item.status = status
                plan_item.plan_id = plan_id
                plan_item.on_plan_select = self.on_plan_select
                
                if self.selected_plan_id == plan_id:
                    plan_item.is_selected = True
                else:
                    plan_item.is_selected = False
                
                plan_item.bind(
                    on_release=lambda instance, p_id=plan_id, p_name=name: self.on_plan_select(p_id, p_name)
                )
                
                savings_container.add_widget(plan_item)
                
        except Exception as e:
            print(f"Error loading savings plans: {e}")
            error_label = Label(
                text="❌ Помилка завантаження планів",
                font_size=dp(16),
                color=ERROR_RED,
                halign="center"
            )
            savings_container.add_widget(error_label)
    
    def on_plan_select(self, plan_id, plan_name):
        """Handle plan selection."""
        self.selected_plan_id = plan_id
        self.selected_plan_name = plan_name
        self.update_savings_tab()
        self.update_operation_buttons()
        
        if 'savings_message' in self.ids:
            self.ids.savings_message.text = f"Обрано план: {plan_name}"
            self.ids.savings_message.color = SUCCESS_GREEN
    
    def create_savings_plan(self):
        """Create a new savings plan."""
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
    
    def add_to_savings_plan(self):
        """Add money to selected savings plan."""
        if not self.selected_plan_id:
            self.ids.savings_message.text = "Будь ласка, оберіть план"
            self.ids.savings_message.color = ERROR_RED
            return
            
        try:
            amount_text = self.ids.savings_amount_input.text.strip()
            if not amount_text:
                self.ids.savings_message.text = "Будь ласка, введіть суму для додавання"
                self.ids.savings_message.color = ERROR_RED
                return
            
            amount = float(amount_text)
            if amount <= 0:
                self.ids.savings_message.text = "Сума має бути додатною"
                self.ids.savings_message.color = ERROR_RED
                return
            
            app = self.get_app()
            if amount > app.balance:
                self.ids.savings_message.text = f"Недостатньо коштів у гаманці. Доступно: ${app.balance:.2f}"
                self.ids.savings_message.color = ERROR_RED
                return
            
            cursor.execute(
                "SELECT current_amount, target_amount FROM savings_plans WHERE id = ? AND user_id = ?",
                (self.selected_plan_id, app.current_user_id)
            )
            plan = cursor.fetchone()
            
            if not plan:
                self.ids.savings_message.text = "План не знайдено"
                self.ids.savings_message.color = ERROR_RED
                return
            
            current_amount, target_amount = plan
            
            if current_amount + amount > target_amount:
                max_amount = target_amount - current_amount
                self.ids.savings_message.text = f"Сума перевищує ціль плану. Максимум: ${max_amount:.2f}"
                self.ids.savings_message.color = ERROR_RED
                return
            
            # Update wallet balance
            app.balance -= amount
            cursor.execute("UPDATE wallets SET balance=? WHERE user_id=?", 
                         (app.balance, app.current_user_id))
            
            # Update savings plan
            cursor.execute(
                "UPDATE savings_plans SET current_amount = current_amount + ? WHERE id = ?",
                (amount, self.selected_plan_id)
            )
            
            log_transaction(
                cursor, conn,
                app.current_user_id, 
                "savings_transfer", 
                amount, 
                f"Переведено до плану: {self.selected_plan_name}"
            )
            
            log_savings_transaction(
                cursor, conn,
                app.current_user_id,
                self.selected_plan_id,
                amount,
                "deposit",
                f"Додано до плану заощаджень"
            )
            
            conn.commit()
            
            self.ids.savings_amount_input.text = ""
            self.ids.savings_message.text = f"Успішно додано ${amount:.2f} до {self.selected_plan_name}"
            self.ids.savings_message.color = SUCCESS_GREEN
            self.update_savings_tab()
            
        except ValueError:
            self.ids.savings_message.text = "Введіть коректну суму"
            self.ids.savings_message.color = ERROR_RED
        except Exception as e:
            self.ids.savings_message.text = f"Помилка: {str(e)}"
            self.ids.savings_message.color = ERROR_RED

    def remove_from_savings_plan(self):
        """Remove money from selected savings plan."""
        if not self.selected_plan_id:
            self.ids.savings_message.text = "Будь ласка, оберіть план"
            self.ids.savings_message.color = ERROR_RED
            return
            
        try:
            amount_text = self.ids.savings_amount_input.text.strip()
            if not amount_text:
                self.ids.savings_message.text = "Будь ласка, введіть суму для вилучення"
                self.ids.savings_message.color = ERROR_RED
                return
            
            amount = float(amount_text)
            if amount <= 0:
                self.ids.savings_message.text = "Сума має бути додатною"
                self.ids.savings_message.color = ERROR_RED
                return
            
            app = self.get_app()
            cursor.execute(
                "SELECT current_amount FROM savings_plans WHERE id = ? AND user_id = ?",
                (self.selected_plan_id, app.current_user_id)
            )
            plan = cursor.fetchone()
            
            if not plan:
                self.ids.savings_message.text = "План не знайдено"
                self.ids.savings_message.color = ERROR_RED
                return
            
            current_amount = plan[0]
            
            if amount > current_amount:
                self.ids.savings_message.text = f"Недостатньо коштів у плані. Доступно: ${current_amount:.2f}"
                self.ids.savings_message.color = ERROR_RED
                return
            
            # Update wallet balance
            app.balance += amount
            cursor.execute("UPDATE wallets SET balance=? WHERE user_id=?", 
                        (app.balance, app.current_user_id))
            
            # Update savings plan
            cursor.execute(
                "UPDATE savings_plans SET current_amount = current_amount - ? WHERE id = ?",
                (amount, self.selected_plan_id)
            )
            
            log_transaction(
                cursor, conn,
                app.current_user_id, 
                "savings_return", 
                amount, 
                f"Повернено з плану: {self.selected_plan_name}"
            )
            
            log_savings_transaction(
                cursor, conn,
                app.current_user_id,
                self.selected_plan_id,
                amount,
                "withdrawal",
                f"Вилучено з плану заощаджень"
            )
            
            conn.commit()
            
            self.ids.savings_amount_input.text = ""
            self.ids.savings_message.text = f"Успішно вилучено ${amount:.2f} з {self.selected_plan_name}"
            self.ids.savings_message.color = SUCCESS_GREEN
            self.update_savings_tab()
            
        except ValueError:
            self.ids.savings_message.text = "Введіть коректну суму"
            self.ids.savings_message.color = ERROR_RED
        except Exception as e:
            self.ids.savings_message.text = f"Помилка: {str(e)}"
            self.ids.savings_message.color = ERROR_RED

    def edit_savings_plan(self):
        """Edit selected savings plan with white popup."""
        if not self.selected_plan_id:
            self.ids.savings_message.text = "Будь ласка, оберіть план для редагування"
            self.ids.savings_message.color = ERROR_RED
            return
        
        # Create edit popup with white design
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        content.background_color = WHITE
        
        # Get current plan data
        cursor.execute(
            "SELECT name, target_amount, deadline FROM savings_plans WHERE id = ?",
            (self.selected_plan_id,)
        )
        plan_data = cursor.fetchone()
        
        if not plan_data:
            return
        
        current_name, current_target, current_deadline = plan_data
        
        # Name input
        name_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        name_layout.add_widget(Label(
            text='Назва:', 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        name_input = StyledTextInput(
            text=current_name, 
            size_hint_x=0.6
        )
        name_layout.add_widget(name_input)
        content.add_widget(name_layout)
        
        # Target amount input
        target_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        target_layout.add_widget(Label(
            text='Цільова сума:', 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        target_input = StyledTextInput(
            text=str(current_target), 
            size_hint_x=0.6
        )
        target_layout.add_widget(target_input)
        content.add_widget(target_layout)
        
        # Deadline input with calendar button
        deadline_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        deadline_layout.add_widget(Label(
            text='Дедлайн:', 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        
        deadline_input = StyledTextInput(
            text=current_deadline if current_deadline else "", 
            hint_text="РРРР-ММ-ДД",
            size_hint_x=0.4
        )
        deadline_layout.add_widget(deadline_input)
        
        calendar_btn = StyledButton(
            text='📅',
            size_hint_x=0.2,
            background_color=PRIMARY_BLUE
        )
        
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
        
        # Buttons
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
                self.update_operation_buttons()
                self.ids.savings_message.text = "План успішно оновлено!"
                self.ids.savings_message.color = SUCCESS_GREEN
                
            except ValueError:
                self.ids.savings_message.text = "Введіть коректну цільову суму"
                self.ids.savings_message.color = ERROR_RED
            except Exception as e:
                print(f"Error updating plan: {e}")
                self.ids.savings_message.text = f"Помилка оновлення: {str(e)}"
                self.ids.savings_message.color = ERROR_RED
        
        save_btn = StyledButton(text='💾 Зберегти', background_color=PRIMARY_PINK)
        save_btn.bind(on_press=save_plan)
        btn_layout.add_widget(save_btn)
        
        cancel_btn = StyledButton(text='Скасувати', background_color=LIGHT_GRAY)
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        popup = Popup(
            title='Редагування плану заощаджень',
            content=content,
            size_hint=(0.85, 0.65),
            background_color=WHITE,
            title_color=DARK_TEXT,
            separator_color=LIGHT_GRAY,
            separator_height=dp(1)
        )
        popup.open()

    def delete_savings_plan(self):
        """Delete selected savings plan with white confirmation popup."""
        if not self.selected_plan_id:
            self.ids.savings_message.text = "Будь ласка, оберіть план для видалення"
            self.ids.savings_message.color = ERROR_RED
            return
        
        # Create confirmation popup with white design
        content = BoxLayout(orientation='vertical', spacing=dp(20), padding=dp(25))
        content.background_color = WHITE
        
        cursor.execute(
            "SELECT current_amount FROM savings_plans WHERE id = ?",
            (self.selected_plan_id,)
        )
        result = cursor.fetchone()
        current_amount = result[0] if result else 0
        
        warning_text = f"Ви дійсно хочете видалити план '{self.selected_plan_name}'?"
        if current_amount > 0:
            warning_text += f"\n\nУвага: у плані є ${current_amount:.2f}. Ці кошти будуть повернуті на ваш основний рахунок."
        
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
                
                # Return money to wallet if any
                if current_amount > 0:
                    app.balance += current_amount
                    cursor.execute("UPDATE wallets SET balance=? WHERE user_id=?", 
                                (app.balance, app.current_user_id))
                    
                    log_transaction(
                        cursor, conn,
                        app.current_user_id, 
                        "savings_return", 
                        current_amount, 
                        f"Повернено при видаленні плану: {self.selected_plan_name}"
                    )
                
                # Delete the plan
                cursor.execute("DELETE FROM savings_plans WHERE id=?", (self.selected_plan_id,))
                
                log_savings_transaction(
                    cursor, conn,
                    app.current_user_id,
                    self.selected_plan_id,
                    current_amount,
                    "plan_deleted",
                    f"Видалено план заощаджень"
                )
                
                conn.commit()
                
                popup.dismiss()
                self.clear_inputs()
                self.update_savings_tab()
                self.ids.savings_message.text = "План успішно видалено!"
                self.ids.savings_message.color = SUCCESS_GREEN
                
            except Exception as e:
                print(f"Error deleting plan: {e}")
                self.ids.savings_message.text = f"Помилка видалення: {str(e)}"
                self.ids.savings_message.color = ERROR_RED
        
        delete_btn = StyledButton(text='Видалити', background_color=ERROR_RED)
        delete_btn.bind(on_press=confirm_delete)
        btn_layout.add_widget(delete_btn)
        
        cancel_btn = StyledButton(text='Скасувати', background_color=LIGHT_GRAY)
        cancel_btn.color = DARK_TEXT
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        btn_layout.add_widget(cancel_btn)
        
        content.add_widget(btn_layout)
        
        popup = Popup(
            title='Підтвердження видалення',
            content=content,
            size_hint=(0.8, 0.5),
            background_color=WHITE,
            title_color=DARK_TEXT,
            separator_color=LIGHT_GRAY,
            separator_height=dp(1)
        )
        popup.open()
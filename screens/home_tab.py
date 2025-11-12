from datetime import datetime
from kivy.uix.screenmanager import Screen
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.metrics import dp
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty
from kivy.graphics import Line  # Додаємо імпорт Line

from db_manager import cursor, conn, log_transaction

class HomeTab(Screen):
    """Home tab with balance and transactions."""
    current_filter = StringProperty("Всі")
    create_card_modal = ObjectProperty(None)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._update_scheduled = False
        self.current_card_index = 0
        self.cards_data = []
        # Додаємо затримку для ініціалізації
        Clock.schedule_once(self.delayed_init, 0.5)
    
    def delayed_init(self, dt):
        """Delayed initialization to ensure widgets are loaded."""
        self.update_content()
    
    def get_app(self):
        """Safe way to get app instance."""
        return App.get_running_app()
    
    def on_enter(self):
        """Called when the screen is entered."""
        if not self._update_scheduled:
            Clock.schedule_once(lambda dt: self.update_content(), 0.1)
            self._update_scheduled = True
    
    def on_pre_enter(self):
        """Called before the screen is entered."""
        self._update_scheduled = False
    
    def update_content(self):
        """Update home tab content."""
        print("Updating home tab content...")
        
        app = self.get_app()
        
        if hasattr(app, 'current_user') and app.current_user:
            print(f"User found: {app.current_user}")
            
            if 'welcome_label' in self.ids:
                self.ids.welcome_label.text = f"Ласкаво просимо, {app.current_user}!"
            
            # Отримуємо баланс з бази даних
            try:
                cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
                result = cursor.fetchone()
                if result:
                    app.balance = result[0]
                    if 'balance_label' in self.ids:
                        self.ids.balance_label.text = f"Баланс: {app.balance:.2f} $"
                        print(f"Balance loaded: {app.balance}")
                else:
                    cursor.execute("INSERT INTO wallets (user_id, balance) VALUES (?, ?)", 
                                (app.current_user_id, 0.0))
                    conn.commit()
                    app.balance = 0.0
                    if 'balance_label' in self.ids:
                        self.ids.balance_label.text = f"Баланс: 0.00 $"
                    
                # Завантажуємо картки користувача
                self.load_user_cards()
                # Оновлюємо історію транзакцій
                self.update_transactions_history()
                    
            except Exception as e:
                print(f"Error updating balance: {e}")
                if 'balance_label' in self.ids:
                    self.ids.balance_label.text = "Помилка завантаження балансу"
        else:
            print("No user found")
            if 'welcome_label' in self.ids:
                self.ids.welcome_label.text = "Ласкаво просимо!"
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Баланс: 0.00 $"
    
    def create_add_card_button(self):
        """Create add card button for carousel."""
        from kivy.uix.button import Button
        from kivy.graphics import Color, RoundedRectangle
        
        add_card_button = Button(
            text="+",
            font_size=dp(50),
            background_color=(0.3, 0.3, 0.3, 0.2),
            color=(1, 1, 1, 0.8),
            size_hint=(0.85, 0.75),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        add_card_button.bind(on_press=self.show_create_card_modal)
        
        with add_card_button.canvas.before:
            Color(0.4, 0.4, 0.4, 0.3)
            RoundedRectangle(
                pos=add_card_button.pos,
                size=add_card_button.size,
                radius=[dp(25),]
            )
            # Додаємо пунктирну рамку
            Color(0.6, 0.6, 0.6, 0.6)
            Line(
                rounded_rectangle=[add_card_button.x, add_card_button.y, 
                                 add_card_button.width, add_card_button.height, dp(25)],
                dash_length=dp(5),
                dash_offset=dp(5),
                width=dp(2)
            )
        
        return add_card_button
    
    def show_create_card_modal(self, instance=None):
        """Show modal for creating new card."""
        print("Showing create card modal")
        # Створюємо модальне вікно якщо його немає
        if not hasattr(self, 'create_card_modal') or self.create_card_modal is None:
            from kivy.uix.modalview import ModalView
            from kivy.uix.boxlayout import BoxLayout
            from kivy.uix.textinput import TextInput
            from kivy.uix.spinner import Spinner
            from kivy.uix.button import Button
            
            self.create_card_modal = ModalView(
                size_hint=(0.8, 0.6),
                background_color=(0, 0, 0, 0.5)
            )
            
            # Створюємо вміст модального вікна
            content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
            
            # Заголовок
            title = Label(
                text="Створити нову картку",
                font_size=dp(20),
                bold=True,
                size_hint_y=None,
                height=dp(40)
            )
            content.add_widget(title)
            
            # Поля вводу
            name_input = TextInput(
                hint_text="Назва картки",
                size_hint_y=None,
                height=dp(45)
            )
            content.add_widget(name_input)
            
            number_input = TextInput(
                hint_text="Номер картки (16 цифр)",
                input_filter='int',
                size_hint_y=None,
                height=dp(45)
            )
            content.add_widget(number_input)
            
            bank_spinner = Spinner(
                text="ПриватБанк",
                values=["ПриватБанк", "Монобанк", "Райффайзен", "Ощадбанк", "Укрексімбанк", "Інший"],
                size_hint_y=None,
                height=dp(45)
            )
            content.add_widget(bank_spinner)
            
            # Кнопки
            buttons_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            
            cancel_btn = Button(
                text="Скасувати",
                background_color=(0.8, 0.2, 0.2, 1)
            )
            cancel_btn.bind(on_press=lambda x: self.create_card_modal.dismiss())
            buttons_layout.add_widget(cancel_btn)
            
            create_btn = Button(
                text="Створити",
                background_color=(0.2, 0.8, 0.2, 1)
            )
            create_btn.bind(on_press=lambda x: self.create_card_from_modal(
                name_input.text, number_input.text, bank_spinner.text
            ))
            buttons_layout.add_widget(create_btn)
            
            content.add_widget(buttons_layout)
            self.create_card_modal.add_widget(content)
        
        self.create_card_modal.open()
    
    def show_success_message(self, message):
        """Show success message."""
        popup = Popup(
            title='Успіх',
            content=Label(text=message),
            size_hint=(0.6, 0.3)
        )
        popup.open()
    
    def create_card_from_modal(self, card_name, card_number, bank_name):
        """Create new card from modal input."""
        try:
            print(f"Creating card: {card_name}, {card_number}, {bank_name}")
            
            if not card_name:
                self.show_error_message("Введіть назву картки")
                return
                
            if not card_number or len(card_number) != 16 or not card_number.isdigit():
                self.show_error_message("Введіть коректний номер картки (16 цифр)")
                return
            
            # Форматуємо номер картки
            formatted_number = f"{card_number[:4]} {card_number[4:8]} {card_number[8:12]} {card_number[12:16]}"
            
            app = self.get_app()
            
            # Кольори для різних банків
            bank_colors = {
                'ПриватБанк': [0.8, 0.2, 0.2, 1],  # Червоний
                'Монобанк': [0.2, 0.4, 0.8, 1],    # Синій
                'Райффайзен': [1.0, 0.5, 0.0, 1],  # Оранжевий
                'Ощадбанк': [0.0, 0.6, 0.2, 1],    # Зелений
                'Укрексімбанк': [0.6, 0.2, 0.8, 1], # Фіолетовий
                'Інший': [0.3, 0.3, 0.3, 1]        # Сірий
            }
            
            color = bank_colors.get(bank_name, [0.2, 0.4, 0.8, 1])
            
            # Створюємо картку в базі даних
            from db_manager import create_user_card
            card_id = create_user_card(
                cursor, conn, 
                app.current_user_id, 
                card_name, 
                formatted_number,
                bank_name,
                app.balance if hasattr(app, 'balance') else 0.0,
                color
            )
            
            if card_id:
                print(f"Card created successfully with ID: {card_id}")
                # Закриваємо модальне вікно
                if hasattr(self, 'create_card_modal'):
                    self.create_card_modal.dismiss()
                # Оновлюємо картки
                self.load_user_cards()
                self.show_success_message(f"Картка '{card_name}' успішно створена!")
            else:
                self.show_error_message("Помилка при створенні картки")
                
        except Exception as e:
            print(f"Error creating card: {e}")
            self.show_error_message("Сталася помилка")
    
    def show_error_message(self, message):
        """Show error message."""
        popup = Popup(
            title='Помилка',
            content=Label(text=message),
            size_hint=(0.6, 0.3)
        )
        popup.open()
    
    def load_user_cards(self):
        """Load user cards from database."""
        try:
            app = self.get_app()
            from db_manager import get_user_cards
            
            print("Loading user cards...")
            self.cards_data = get_user_cards(cursor, app.current_user_id)
            print(f"Loaded {len(self.cards_data)} cards")
            
            # Якщо карток немає, створюємо дефолтну
            if not self.cards_data:
                print("No cards found, creating default card")
                self.create_default_card()
                self.cards_data = get_user_cards(cursor, app.current_user_id)
            
            self.apply_bank_filter()
            
        except Exception as e:
            print(f"Error loading user cards: {e}")
    
    def create_default_card(self):
        """Create default card for new user."""
        try:
            app = self.get_app()
            from db_manager import create_user_card
            
            print("Creating default card")
            create_user_card(
                cursor, conn,
                app.current_user_id,
                "Основний рахунок",
                "**** **** **** 0001",
                "ПриватБанк",
                app.balance if hasattr(app, 'balance') else 0.0,
                [0.2, 0.4, 0.8, 1]  # Синій колір
            )
        except Exception as e:
            print(f"Error creating default card: {e}")
    
    def apply_bank_filter(self):
        """Apply bank filter to cards."""
        print(f"Applying filter: {self.current_filter}")
        filtered_cards = self.cards_data
        
        if self.current_filter != "Всі":
            filtered_cards = [card for card in self.cards_data if card['bank'] == self.current_filter]
        
        print(f"Filtered to {len(filtered_cards)} cards")
        self.create_cards_carousel(filtered_cards)
    
    def create_cards_carousel(self, cards_data=None):
        """Create carousel with bank cards."""
        if 'cards_container' not in self.ids:
            print("cards_container not found in ids")
            return
            
        if cards_data is None:
            cards_data = self.cards_data
            
        cards_container = self.ids.cards_container
        cards_container.clear_widgets()
        
        from kivy.uix.carousel import Carousel
        
        # Створюємо карусель
        carousel = Carousel(
            direction='right',
            loop=False,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5}
        )
        
        # Додаємо картки в карусель
        for card_data in cards_data:
            card = self.create_bank_card(card_data)
            carousel.add_widget(card)
        
        # Додаємо кнопку "+" для створення нової картки
        if len(cards_data) < 10:
            add_card_button = self.create_add_card_button()
            carousel.add_widget(add_card_button)
        
        # Додаємо обробник зміни картки
        carousel.bind(current_slide=self.on_card_changed)
        
        cards_container.add_widget(carousel)
        
        print(f"Created carousel with {len(carousel.slides)} slides")
    
    def create_bank_card(self, card_data):
        """Create a bank card widget with modern design."""
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.graphics import Color, RoundedRectangle
        
        card = BoxLayout(
            orientation='vertical',
            size_hint=(0.85, 0.75),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            padding=dp(20),
            spacing=dp(10)
        )
        
        # Додаємо фон картки
        with card.canvas.before:
            Color(*card_data['color'])
            RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=[dp(25),]
            )
            # Додаємо тінь
            Color(0, 0, 0, 0.2)
            RoundedRectangle(
                pos=(card.x - dp(2), card.y - dp(2)),
                size=card.size,
                radius=[dp(25),]
            )
        
        # Назва банку
        bank_label = Label(
            text=card_data['bank'],
            font_size=dp(16),
            color=(1, 1, 1, 0.9),
            size_hint_y=None,
            height=dp(25),
            bold=True
        )
        card.add_widget(bank_label)
        
        # Назва картки
        name_label = Label(
            text=card_data['name'],
            font_size=dp(18),
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(30),
            bold=True
        )
        card.add_widget(name_label)
        
        # Номер картки
        number_label = Label(
            text=card_data['number'],
            font_size=dp(16),
            color=(1, 1, 1, 0.8),
            size_hint_y=None,
            height=dp(25)
        )
        card.add_widget(number_label)
        
        # Пустий простір
        card.add_widget(Label(size_hint_y=1))
        
        # Баланс
        balance_label = Label(
            text=f"${card_data['balance']:.2f}",
            font_size=dp(24),
            color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(35),
            bold=True
        )
        card.add_widget(balance_label)
        
        return card
    
    def on_card_changed(self, carousel, slide):
        """Called when card is changed in carousel."""
        if slide:
            print("Card changed")
    
    def change_bank_filter(self, bank_name):
        """Change bank filter."""
        print(f"Changing filter to: {bank_name}")
        self.current_filter = bank_name
        self.apply_bank_filter()

    # ІНШІ МЕТОДИ ЗАЛИШАЮТЬСЯ БЕЗ ЗМІН
    def update_transactions_history(self):
        """Update transactions history display."""
        if 'history_container' not in self.ids:
            return

        history_container = self.ids.history_container
        history_container.clear_widgets()

        try:
            app = self.get_app()
            
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                no_history_label = Label(
                    text="Увійдіть в систему",
                    font_size=dp(16),
                    color=(0.5, 0.5, 0.5, 1),
                    size_hint_y=None,
                    height=dp(40)
                )
                history_container.add_widget(no_history_label)
                return
            
            cursor.execute(
                "SELECT type, amount, description, created_at FROM transactions WHERE user_id=? AND type != 'login' ORDER BY created_at DESC LIMIT 10",
                (app.current_user_id,)
            )
            transactions = cursor.fetchall()

            if not transactions:
                no_history_label = Label(
                    text="Ще немає транзакцій",
                    font_size=dp(16),
                    color=(0.5, 0.5, 0.5, 1),
                    size_hint_y=None,
                    height=dp(40)
                )
                history_container.add_widget(no_history_label)
                return

            for trans_type, amount, description, created_at in transactions:
                try:
                    if isinstance(created_at, str):
                        if '.' in created_at:
                            date_time = datetime.strptime(created_at.split('.')[0], '%Y-%m-%d %H:%M:%S')
                        else:
                            date_time = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    else:
                        date_time = created_at
                    
                    date_str = date_time.strftime('%d.%m %H:%M')

                    if trans_type in ('deposit', 'savings_return'):
                        amount_color = (0, 0.6, 0, 1)
                        sign = "+"
                    elif trans_type in ('withdrawal', 'savings_transfer'):
                        amount_color = (0.8, 0, 0, 1)
                        sign = "-"
                    else:
                        amount_color = (0.5, 0.5, 0.5, 1)
                        sign = ""

                    trans_text = f"{date_str} - {description} - {sign}{amount:.2f} $"

                    trans_label = Label(
                        text=trans_text,
                        size_hint_y=None,
                        height=dp(30),
                        halign="left",
                        text_size=(self.width - dp(20), None)
                    )
                    trans_label.color = amount_color
                    history_container.add_widget(trans_label)

                except Exception as e:
                    print(f"Error processing transaction: {e}")
                    continue

        except Exception as e:
            print(f"Error loading transactions history: {e}")
            error_label = Label(
                text="Помилка завантаження історії",
                color=(0.8, 0, 0, 1),
                size_hint_y=None,
                height=dp(40)
            )
            history_container.add_widget(error_label)
    
    def add_money(self):
        """Add money to wallet."""
        try:
            if 'amount_input' not in self.ids or 'balance_label' not in self.ids:
                return
                
            amount_text = self.ids.amount_input.text.strip()
            if not amount_text:
                self.ids.balance_label.text = "Будь ласка, введіть суму!"
                return
                
            amount = float(amount_text)
            if amount <= 0:
                self.ids.balance_label.text = "Сума має бути додатною!"
                return
            
            app = self.get_app()
            
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                self.ids.balance_label.text = "Будь ласка, увійдіть в систему!"
                return
            
            cursor.execute("UPDATE wallets SET balance = balance + ? WHERE user_id=?", 
                        (amount, app.current_user_id))
            conn.commit()
            
            cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
            result = cursor.fetchone()
            if result:
                app.balance = result[0]
            
            self.ids.balance_label.text = f"Баланс: {app.balance:.2f} $"
            self.ids.amount_input.text = ""
            
            log_transaction(cursor, conn, app.current_user_id, "deposit", amount, "Поповнення гаманця")
            
            self.update_transactions_history()
            
        except ValueError:
            if 'amount_input' in self.ids:
                self.ids.amount_input.text = ""
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Введіть коректну суму!"
        except Exception as e:
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = f"Помилка: {str(e)}"

    def remove_money(self):
        """Remove money from wallet."""
        try:
            if 'amount_input' not in self.ids or 'balance_label' not in self.ids:
                return
                
            amount_text = self.ids.amount_input.text.strip()
            if not amount_text:
                self.ids.balance_label.text = "Будь ласка, введіть суму!"
                return
                
            amount = float(amount_text)
            if amount <= 0:
                self.ids.balance_label.text = "Сума має бути додатною!"
                return
            
            app = self.get_app()
            
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                self.ids.balance_label.text = "Будь ласка, увійдіть в систему!"
                return
            
            cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
            result = cursor.fetchone()
            current_balance = result[0] if result else 0.0
            
            if amount > current_balance:
                self.ids.balance_label.text = "Недостатньо коштів!"
                return
            
            cursor.execute("UPDATE wallets SET balance = balance - ? WHERE user_id=?", 
                        (amount, app.current_user_id))
            conn.commit()
            
            cursor.execute("SELECT balance FROM wallets WHERE user_id=?", (app.current_user_id,))
            result = cursor.fetchone()
            if result:
                app.balance = result[0]
                
            self.ids.balance_label.text = f"Баланс: {app.balance:.2f} $"
            self.ids.amount_input.text = ""
            
            log_transaction(cursor, conn, app.current_user_id, "withdrawal", amount, "Виведення з гаманця")
            
            self.update_transactions_history()
            
        except ValueError:
            if 'amount_input' in self.ids:
                self.ids.amount_input.text = ""
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = "Введіть коректну суму!"
        except Exception as e:
            if 'balance_label' in self.ids:
                self.ids.balance_label.text = f"Помилка: {str(e)}"
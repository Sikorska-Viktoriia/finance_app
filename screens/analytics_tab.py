from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Triangle, Line
from kivy.properties import ListProperty, NumericProperty, StringProperty
import math
from datetime import datetime, timedelta
import json

from db_manager import (
    conn, cursor, get_user_envelopes, create_envelope, add_to_envelope,
    get_user_cards, get_envelope_transactions, get_envelope_stats,
    get_analytics_data, get_category_breakdown, get_top_categories,
    get_cards_analytics, get_budget_progress, get_insights_and_forecasts,
    get_monthly_comparison
)

# Кольори
PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_PINK = (1, 0.95, 0.95, 1)
LIGHT_BLUE = (0.92, 0.98, 1.0, 1)
ERROR_RED = (0.9, 0.2, 0.2, 1)
SUCCESS_GREEN = (0.2, 0.8, 0.3, 1)
WARNING_ORANGE = (1, 0.6, 0.2, 1)
WHITE = (1, 1, 1, 1)
DARK_TEXT = (0.1, 0.1, 0.1, 1)
LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
MEDIUM_GRAY = (0.7, 0.7, 0.7, 1)
DARK_GRAY = (0.4, 0.4, 0.4, 1)

class CompactEnvelopeCard(BoxLayout):
    """Компактна картка конверту з покращеним дизайном"""
    def __init__(self, envelope_data, on_manage_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.envelope_data = envelope_data
        self.on_manage_callback = on_manage_callback
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = dp(130)
        self.padding = dp(12)
        self.spacing = dp(6)
        
        # Фон картки
        with self.canvas.before:
            Color(*envelope_data['color'])
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12)]
            )
            
            # Градієнтний ефект
            Color(1, 1, 1, 0.2)
            RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.4),
                size=(self.width, self.height * 0.6),
                radius=[dp(12)]
            )
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
        # Назва конверту
        name_label = Label(
            text=envelope_data['name'],
            font_size=dp(14),
            bold=True,
            color=WHITE,
            size_hint_y=None,
            height=dp(22)
        )
        self.add_widget(name_label)
        
        # Баланс
        balance_label = Label(
            text=f"{envelope_data['current_amount']:.2f} $",
            font_size=dp(18),
            bold=True,
            color=WHITE,
            size_hint_y=None,
            height=dp(26)
        )
        self.add_widget(balance_label)
        
        # Прогрес бар для бюджету
        if envelope_data['budget_limit'] > 0:
            self.progress_bg = Widget(size_hint_y=None, height=dp(6))
            with self.progress_bg.canvas:
                Color(1, 1, 1, 0.3)
                self.progress_bg_rect = Rectangle(
                    pos=self.progress_bg.pos,
                    size=self.progress_bg.size
                )
            self.add_widget(self.progress_bg)
            
            # Відсоток використання бюджету
            percentage = min((envelope_data['current_amount'] / envelope_data['budget_limit']) * 100, 100)
            percent_label = Label(
                text=f"{percentage:.0f}%",
                font_size=dp(10),
                color=WHITE,
                size_hint_y=None,
                height=dp(16)
            )
            self.add_widget(percent_label)
        
        # Кнопка поповнення
        add_btn = Button(
            text='+',
            size_hint_y=None,
            height=dp(28),
            background_color=(1, 1, 1, 0.3),
            color=WHITE,
            font_size=dp(14),
            bold=True
        )
        add_btn.bind(on_press=self.on_add_money)
        self.add_widget(add_btn)
        
        if hasattr(self, 'progress_bg'):
            self.progress_bg.bind(pos=self._update_progress_bg, size=self._update_progress_bg)

    def update_graphics(self, *args):
        """Оновити графічні елементи при зміні розміру"""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _update_progress_bg(self, instance, value):
        """Оновити позицію прогрес бару"""
        self.progress_bg_rect.pos = instance.pos
        self.progress_bg_rect.size = instance.size
        self.update_progress_bar()

    def update_progress_bar(self):
        """Оновити відображення прогрес бару"""
        if not hasattr(self, 'progress_bg') or self.envelope_data['budget_limit'] <= 0:
            return
            
        self.progress_bg.canvas.after.clear()
        percentage = min((self.envelope_data['current_amount'] / self.envelope_data['budget_limit']) * 100, 100)
        
        with self.progress_bg.canvas.after:
            # Колір залежно від відсотка заповнення
            if percentage < 70:
                Color(*SUCCESS_GREEN)
            elif percentage < 90:
                Color(*WARNING_ORANGE)
            else:
                Color(*ERROR_RED)
                
            progress_width = self.progress_bg.width * (percentage / 100)
            RoundedRectangle(
                pos=self.progress_bg.pos,
                size=(progress_width, self.progress_bg.height),
                radius=[dp(3)]
            )

    def on_add_money(self, instance):
        """Обробка натискання кнопки поповнення"""
        if self.on_manage_callback:
            self.on_manage_callback(self.envelope_data, 'add')

class StatCard(BoxLayout):
    """Картка статистики з покращеним дизайном"""
    def __init__(self, title, value, subtitle="", color=PRIMARY_BLUE, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = dp(100)
        self.padding = dp(10)
        self.spacing = dp(4)
        
        # Фон картки
        with self.canvas.before:
            Color(*color)
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(10)]
            )
        
        self.bind(pos=self._update, size=self._update)
        
        # Заголовок
        self.title_label = Label(
            text=title,
            font_size=dp(12),
            color=WHITE,
            bold=True,
            size_hint_y=None,
            height=dp(20)
        )
        self.add_widget(self.title_label)
        
        # Значення
        self.value_label = Label(
            text=str(value),
            font_size=dp(16),
            color=WHITE,
            bold=True,
            size_hint_y=None,
            height=dp(26)
        )
        self.add_widget(self.value_label)
        
        # Підзаголовок
        self.subtitle_label = Label(
            text=subtitle,
            font_size=dp(10),
            color=WHITE,
            size_hint_y=None,
            height=dp(16)
        )
        self.add_widget(self.subtitle_label)
    
    def update_data(self, value, subtitle=""):
        """Оновити дані картки"""
        self.value_label.text = str(value)
        self.subtitle_label.text = subtitle
    
    def _update(self, *args):
        """Оновити графіку при зміні розміру"""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

class PieChartWidget(Widget):
    """Кругова діаграма з правильним відображенням тексту"""
    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.size_hint = (1, None)
        self.height = dp(400)  # Збільшена висота для кращого відображення
        
        self.bind(pos=self.update_chart, size=self.update_chart)
    
    def update_data(self, data):
        """Оновити дані діаграми"""
        self.data = data
        self.update_chart()
    
    def update_chart(self, *args):
        """Оновити відображення діаграми"""
        self.canvas.clear()
        # Видаляємо всі текстові мітки
        for child in self.children[:]:
            self.remove_widget(child)
        
        if not self.data:
            self.show_no_data()
            return
        
        total = sum(item['amount'] for item in self.data)
        if total == 0:
            self.show_no_data()
            return
        
        # Центр діаграми
        center_x = self.center_x
        center_y = self.center_y + dp(30)
        radius = min(self.width * 0.3, self.height * 0.3)  # Адаптивний радіус
        
        start_angle = 0
        
        # Малюємо сектори діаграми
        for item in self.data:
            percentage = item['amount'] / total
            angle = percentage * 360
            
            # Малюємо сектор
            self.draw_sector(center_x, center_y, radius, start_angle, start_angle + angle, item['color'])
            
            # Додаємо текст всередині сектора (якщо сектор досить великий)
            if percentage > 0.05:  # Мінімум 5% для відображення тексту
                mid_angle = start_angle + angle / 2
                text_radius = radius * 0.5  # Текст всередині сектора
                text_x = center_x + text_radius * math.cos(math.radians(mid_angle))
                text_y = center_y + text_radius * math.sin(math.radians(mid_angle))
                
                # Відсоток усередині сектора
                percent_label = Label(
                    text=f"{percentage:.1%}",
                    pos=(text_x - dp(20), text_y - dp(8)),
                    size=(dp(40), dp(16)),
                    font_size=dp(11),
                    color=WHITE,  # Білий текст для контрасту
                    halign='center',
                    bold=True
                )
                self.add_widget(percent_label)
            
            start_angle += angle
        
        # Додаємо легенду
        self.draw_legend()

    def draw_sector(self, cx, cy, radius, start_angle, end_angle, color):
        """Малює сектор кругової діаграми"""
        points = [cx, cy]  # Починаємо з центру
        
        # Додаємо точки по колу
        steps = max(20, int((end_angle - start_angle) / 2))  # Більше кроків для гладкішого краю
        for i in range(steps + 1):
            angle = math.radians(start_angle + (end_angle - start_angle) * i / steps)
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.extend([x, y])
        
        # Замикаємо на центр
        points.extend([cx, cy])
        
        # Малюємо багатокутник
        with self.canvas:
            Color(*color)
            Triangle(points=points)
            
            # Контур сектора
            Color(0, 0, 0, 0.3)  # Темний контур
            Line(points=points[:2] + points[2:-2], width=1, close=False)

    def draw_legend(self):
        """Малює легенду діаграми"""
        legend_x = self.x + dp(20)
        legend_y = self.y + self.height - dp(50)
        
        # Заголовок легенди
        title_label = Label(
            text="Розподіл коштів:",
            pos=(legend_x, legend_y),
            size=(self.width - dp(40), dp(25)),
            font_size=dp(14),
            bold=True,
            color=DARK_TEXT,
            halign='left'
        )
        self.add_widget(title_label)
        
        legend_y -= dp(35)
        
        # Елементи легенди
        total = sum(item['amount'] for item in self.data)
        for item in self.data:
            if legend_y < self.y + dp(30):
                break
                
            # Квадратик кольору
            with self.canvas:
                Color(*item['color'])
                Rectangle(
                    pos=(legend_x, legend_y),
                    size=(dp(16), dp(16))
                )
            
            # Текст легенди з сумою та відсотком
            percentage = (item['amount'] / total) * 100
            text = f"{item['name']}: ${item['amount']:.2f} ({percentage:.1f}%)"
            
            text_label = Label(
                text=text,
                pos=(legend_x + dp(22), legend_y - dp(4)),
                size=(self.width - legend_x - dp(30), dp(20)),
                font_size=dp(12),
                color=DARK_TEXT,
                halign='left'
            )
            self.add_widget(text_label)
            
            legend_y -= dp(25)

    def show_no_data(self):
        """Показати повідомлення про відсутність даних"""
        with self.canvas:
            Color(*LIGHT_GRAY)
            Ellipse(
                pos=(self.center_x - dp(60), self.center_y - dp(30)), 
                size=(dp(120), dp(120))
            )
        
        no_data_label = Label(
            text="Немає даних для відображення",
            pos=(self.center_x - dp(90), self.center_y - dp(10)),
            size=(dp(180), dp(20)),
            font_size=dp(14),
            color=DARK_GRAY,
            halign='center'
        )
        self.add_widget(no_data_label)

class AnalyticsTab(Screen):
    """Вкладка аналітики з покращеним UI"""
    
    # Властивості для KV файлу
    primary_pink = ListProperty(PRIMARY_PINK)
    primary_blue = ListProperty(PRIMARY_BLUE)
    light_pink = ListProperty(LIGHT_PINK)
    light_blue = ListProperty(LIGHT_BLUE)
    error_red = ListProperty(ERROR_RED)
    success_green = ListProperty(SUCCESS_GREEN)
    white = ListProperty(WHITE)
    dark_text = ListProperty(DARK_TEXT)
    light_gray = ListProperty(LIGHT_GRAY)
    dark_gray = ListProperty(DARK_GRAY)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'analytics'
        self.user_cards = []
        self.envelopes_data = []
        self.current_popup = None
        self.analytics_data = {}
        self.use_budget = False
        
        Clock.schedule_once(self.create_ui, 0.1)
    
    def get_app(self):
        """Отримати поточний додаток"""
        return App.get_running_app()
    
    def create_ui(self, dt=None):
        """Створення інтерфейсу"""
        self.load_data()
    
    def on_enter(self):
        """Оновити дані при вході на вкладку"""
        Clock.schedule_once(lambda dt: self.load_data(), 0.1)
    
    def load_data(self):
        """Завантажити всі необхідні дані"""
        try:
            app = self.get_app()
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                return
            
            # Завантажити карти користувача
            self.user_cards = get_user_cards(cursor, app.current_user_id)
            
            # Завантажити конверти
            self.envelopes_data = get_user_envelopes(cursor, app.current_user_id)
            
            # Створити дефолтні конверти, якщо їх немає
            if not self.envelopes_data:
                self.create_default_envelopes()
            else:
                # Завантажити аналітичні дані
                self.load_analytics_data()
                
                # Оновити інтерфейс
                self.update_envelopes_display()
                self.update_stats_display()
                self.update_charts_display()
            
        except Exception as e:
            print(f"Помилка завантаження даних аналітики: {e}")
    
    def create_default_envelopes(self):
        """Створити стандартні конверти"""
        try:
            app = self.get_app()
            
            default_envelopes = [
                {"name": "Їжа", "color": [0.95, 0.3, 0.5, 1]},
                {"name": "Транспорт", "color": [0.2, 0.7, 0.9, 1]},
                {"name": "Розваги", "color": [0.2, 0.8, 0.3, 1]},
                {"name": "Одяг", "color": [1, 0.6, 0.2, 1]},
                {"name": "Здоров'я", "color": [0.6, 0.2, 0.8, 1]},
                {"name": "Подарунки", "color": [0.2, 0.8, 0.8, 1]}
            ]
            
            for envelope in default_envelopes:
                create_envelope(
                    cursor, conn, 
                    app.current_user_id, 
                    envelope["name"], 
                    envelope["color"], 
                    0.0  # Без бюджету
                )
            
            # Перезавантажити дані
            self.envelopes_data = get_user_envelopes(cursor, app.current_user_id)
            self.load_analytics_data()
            self.update_envelopes_display()
            self.update_stats_display()
            self.update_charts_display()
            
        except Exception as e:
            print(f"Помилка створення стандартних конвертів: {e}")
    
    def load_analytics_data(self):
        """Завантажити дані для аналітики"""
        try:
            app = self.get_app()
            
            # Основна аналітика
            self.analytics_data = get_analytics_data(cursor, app.current_user_id, 'month')
            print(f"Завантажена аналітика: {self.analytics_data}")
            
            # Дані про заощадження
            savings_data = self.get_savings_data(app.current_user_id)
            
            # Додати заощадження до аналітики
            if savings_data:
                self.analytics_data['total_savings'] = savings_data['total_savings']
                self.analytics_data['savings_progress'] = savings_data['savings_progress']
                self.analytics_data['active_savings_plans'] = savings_data['active_plans_count']
            
            # Підготувати дані для кругової діаграми
            self.envelopes_for_chart = []
            for envelope in self.envelopes_data:
                if envelope['current_amount'] > 0:
                    self.envelopes_for_chart.append({
                        'name': envelope['name'],
                        'amount': envelope['current_amount'],
                        'color': envelope['color']
                    })
            
            # Додати заощадження до діаграми
            if savings_data and savings_data['total_savings'] > 0:
                self.envelopes_for_chart.append({
                    'name': 'Заощадження',
                    'amount': savings_data['total_savings'],
                    'color': [0.4, 0.2, 0.9, 1]  # Фіолетовий для заощаджень
                })
            
        except Exception as e:
            print(f"Помилка завантаження аналітики: {e}")
            self.analytics_data = {}
            self.envelopes_for_chart = []

    def get_savings_data(self, user_id):
        """Отримати дані про заощадження"""
        try:
            cursor.execute('''
                SELECT 
                    SUM(current_amount) as total_savings,
                    SUM(target_amount) as total_target,
                    COUNT(*) as active_plans_count
                FROM savings_plans 
                WHERE user_id=? AND status='active'
            ''', (user_id,))
            
            result = cursor.fetchone()
            total_savings = result[0] or 0
            total_target = result[1] or 0
            active_plans = result[2] or 0
            
            savings_progress = (total_savings / total_target * 100) if total_target > 0 else 0
            
            return {
                'total_savings': total_savings,
                'total_target': total_target,
                'savings_progress': savings_progress,
                'active_plans_count': active_plans
            }
            
        except Exception as e:
            print(f"Помилка отримання даних заощаджень: {e}")
            return None
    
    def update_envelopes_display(self):
        """Оновити відображення конвертів"""
        if 'envelopes_container' not in self.ids:
            return
            
        container = self.ids.envelopes_container
        container.clear_widgets()
        container.cols = 3
        
        if not self.envelopes_data:
            return
        
        for envelope_data in self.envelopes_data:
            envelope_card = CompactEnvelopeCard(
                envelope_data,
                on_manage_callback=self.on_envelope_action
            )
            container.add_widget(envelope_card)
    
    def update_stats_display(self):
        """Оновити відображення статистики"""
        if 'stats_container' not in self.ids:
            return
            
        container = self.ids.stats_container
        container.clear_widgets()
        container.cols = 2
        
        if not self.analytics_data:
            no_data_label = Label(
                text="Немає даних для аналітики",
                font_size=dp(12),
                color=DARK_GRAY,
                size_hint_y=None,
                height=dp(50)
            )
            container.add_widget(no_data_label)
            return
        
        # Статистичні картки
        stats_cards = [
            {
                'title': 'Доходи',
                'value': f"${self.analytics_data.get('total_income', 0):.0f}",
                'subtitle': 'За місяць',
                'color': SUCCESS_GREEN
            },
            {
                'title': 'Витрати',
                'value': f"${self.analytics_data.get('total_expenses', 0):.0f}",
                'subtitle': 'За місяць',
                'color': ERROR_RED
            },
            {
                'title': 'Заощадження',
                'value': f"${self.analytics_data.get('total_savings', 0):.0f}",
                'subtitle': f"{self.analytics_data.get('savings_progress', 0):.0f}% від цілі",
                'color': [0.4, 0.2, 0.9, 1]
            },
            {
                'title': 'Транзакції',
                'value': self.analytics_data.get('transactions_count', 0),
                'subtitle': 'За місяць',
                'color': WARNING_ORANGE
            }
        ]
        
        for stat in stats_cards:
            stat_card = StatCard(
                stat['title'],
                stat['value'],
                stat['subtitle'],
                stat['color']
            )
            container.add_widget(stat_card)
    
    def update_charts_display(self):
        """Оновити відображення кругової діаграми"""
        if 'charts_container' not in self.ids:
            return
            
        container = self.ids.charts_container
        container.clear_widgets()
        
        # Основний контейнер для діаграми
        charts_main_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(450))
        
        if self.envelopes_for_chart:
            # Заголовок діаграми
            title_label = Label(
                text="Розподіл коштів по конвертах та заощадженнях",
                font_size=dp(16),
                bold=True,
                color=DARK_TEXT,
                size_hint_y=None,
                height=dp(30)
            )
            charts_main_layout.add_widget(title_label)
            
            # Кругова діаграма
            pie_chart = PieChartWidget(self.envelopes_for_chart)
            pie_chart.size_hint_y = 0.9
            charts_main_layout.add_widget(pie_chart)
        else:
            no_data_section = BoxLayout(orientation='vertical', size_hint_y=1)
            no_data_section.add_widget(Label(
                text="Немає даних для відображення діаграми",
                font_size=dp(14),
                color=DARK_GRAY,
                size_hint_y=None,
                height=dp(40)
            ))
            charts_main_layout.add_widget(no_data_section)
        
        container.add_widget(charts_main_layout)
    
    def on_envelope_action(self, envelope_data, action):
        """Обробка дій з конвертом"""
        if action == 'add':
            self.show_add_money_modal(envelope_data)
    
    def create_envelope(self):
        """Створити новий конверт"""
        try:
            name_input = self.ids.envelope_name_input
            budget_input = self.ids.envelope_budget_input
            message_label = self.ids.analytics_message
            
            name = name_input.text.strip()
            budget_text = budget_input.text.strip()
            
            if not name:
                message_label.text = "Введіть назву конверту"
                message_label.color = ERROR_RED
                return
            
            budget = float(budget_text) if budget_text else 0.0
            
            # Палітра кольорів
            color_palette = [
                [0.95, 0.3, 0.5, 1],
                [0.2, 0.7, 0.9, 1],
                [0.2, 0.8, 0.3, 1],
                [1, 0.6, 0.2, 1],
                [0.6, 0.2, 0.8, 1],
                [0.2, 0.8, 0.8, 1],
                [0.9, 0.2, 0.2, 1],
                [0.4, 0.2, 0.9, 1]
            ]
            
            # Вибираємо колір
            color_map = {
                'їжа': color_palette[0],
                'транспорт': color_palette[1],
                'розваги': color_palette[2],
                'одяг': color_palette[3],
                'здоровья': color_palette[4],
                'подарунки': color_palette[5]
            }
            
            color = color_map.get(name.lower(), color_palette[len(self.envelopes_data) % len(color_palette)])
            
            app = self.get_app()
            envelope_id = create_envelope(cursor, conn, app.current_user_id, name, color, budget)
            
            if envelope_id:
                message_label.text = f"Конверт '{name}' створено!"
                message_label.color = SUCCESS_GREEN
                name_input.text = ""
                budget_input.text = ""
                self.load_data()
            else:
                message_label.text = "Помилка створення конверту"
                message_label.color = ERROR_RED
                
        except ValueError:
            self.ids.analytics_message.text = "Введіть коректну суму бюджету"
            self.ids.analytics_message.color = ERROR_RED
        except Exception as e:
            print(f"Помилка створення конверту: {e}")
            self.ids.analytics_message.text = "Сталася помилка"
            self.ids.analytics_message.color = ERROR_RED
    
    def show_add_money_modal(self, envelope_data):
        """Показати модальне вікно поповнення конверту"""
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(15))
        
        title = Label(
            text=f"Поповнення: {envelope_data['name']}",
            font_size=dp(18),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(35)
        )
        content.add_widget(title)
        
        # Вибір картки
        card_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        card_layout.add_widget(Label(text="З картки:", size_hint_x=0.4, color=DARK_TEXT))
        
        card_spinner = Spinner(
            text=self.user_cards[0]['name'] if self.user_cards else "Немає карток",
            values=[card['name'] for card in self.user_cards],
            size_hint_x=0.6
        )
        card_layout.add_widget(card_spinner)
        content.add_widget(card_layout)
        
        # Сума поповнення
        amount_input = TextInput(
            hint_text="Сума поповнення",
            input_filter='float',
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(amount_input)
        
        # Опис
        desc_input = TextInput(
            hint_text="Опис (не обов'язково)",
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(desc_input)
        
        error_label = Label(
            text="",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(25)
        )
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        
        cancel_btn = Button(
            text="Скасувати",
            background_color=LIGHT_GRAY,
            color=DARK_TEXT
        )
        
        add_btn = Button(
            text="Поповнити",
            background_color=SUCCESS_GREEN,
            color=WHITE
        )
        
        def add_money(instance):
            amount_text = amount_input.text.strip()
            description = desc_input.text.strip()
            card_name = card_spinner.text
            
            if not amount_text:
                error_label.text = "Введіть суму"
                return
            
            try:
                amount = float(amount_text)
                if amount <= 0:
                    error_label.text = "Сума має бути додатною"
                    return
                
                # Знаходимо ID картки
                card_id = None
                for card in self.user_cards:
                    if card['name'] == card_name:
                        card_id = card['id']
                        break
                
                if not card_id:
                    error_label.text = "Картку не знайдено"
                    return
                
                # Перевіряємо баланс картки
                selected_card = next((card for card in self.user_cards if card['id'] == card_id), None)
                if selected_card and selected_card['balance'] < amount:
                    error_label.text = f"Недостатньо коштів. Доступно: {selected_card['balance']:.2f} $"
                    return
                
                success = self.add_money_to_envelope(envelope_data['id'], amount, description, card_id)
                if success:
                    popup.dismiss()
                    self.load_data()
                else:
                    error_label.text = "Помилка при поповненні"
                    
            except ValueError:
                error_label.text = "Введіть коректну суму"
        
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        add_btn.bind(on_press=add_money)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(add_btn)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title='Поповнення конверту',
            content=content,
            size_hint=(0.85, 0.5)
        )
        popup.open()
    
    def add_money_to_envelope(self, envelope_id, amount, description, card_id):
        """Додати гроші до конверту"""
        try:
            app = self.get_app()
            
            # Знімаємо гроші з картки
            cursor.execute(
                "UPDATE user_cards SET balance = balance - ? WHERE id = ?",
                (amount, card_id)
            )
            
            # Додаємо гроші до конверту
            success = add_to_envelope(cursor, conn, app.current_user_id, envelope_id, amount, description, card_id)
            
            conn.commit()
            
            return success
        except Exception as e:
            print(f"Помилка поповнення конверту: {e}")
            return False
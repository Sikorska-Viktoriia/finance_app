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
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line, Mesh
from kivy.properties import ListProperty, NumericProperty, StringProperty
import math
from datetime import datetime, timedelta
import json

from db_manager import (
    conn, cursor, get_user_envelopes, create_envelope, add_to_envelope,
    get_user_cards, get_envelope_transactions, get_envelope_stats,
    get_analytics_data, get_category_breakdown, get_top_categories,
    get_cards_analytics, get_budget_progress, get_insights_and_forecasts,
    get_monthly_comparison, update_envelope
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
        
        # Кнопки дій
        buttons_layout = BoxLayout(
            size_hint_y=None,
            height=dp(28),
            spacing=dp(5)
        )
        
        # Кнопка поповнення
        add_btn = Button(
            text='+',
            size_hint_x=0.5,
            background_color=(1, 1, 1, 0.3),
            color=WHITE,
            font_size=dp(14),
            bold=True
        )
        add_btn.bind(on_press=self.on_add_money)
        buttons_layout.add_widget(add_btn)
        
        # Кнопка редагування
        edit_btn = Button(
            text='✎',
            size_hint_x=0.5,
            background_color=(1, 1, 1, 0.2),
            color=WHITE,
            font_size=dp(12),
            bold=True
        )
        edit_btn.bind(on_press=self.on_edit)
        buttons_layout.add_widget(edit_btn)
        
        self.add_widget(buttons_layout)
        
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

    def on_edit(self, instance):
        """Обробка натискання кнопки редагування"""
        if self.on_manage_callback:
            self.on_manage_callback(self.envelope_data, 'edit')

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

class SimplePieChartWidget(Widget):
    """Кругова діаграма з заповненими секторами та інтелектуальними легендами"""
    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.size_hint = (1, None)
        self.height = dp(300)
        
        self.bind(pos=self.update_chart, size=self.update_chart)
    
    def update_data(self, data):
        """Оновити дані діаграми"""
        self.data = data
        self.update_chart()
    
    def update_chart(self, *args):
        """Оновити відображення діаграми"""
        self.canvas.clear()
        for child in self.children[:]:
            self.remove_widget(child)
        
        if not self.data:
            self.show_no_data()
            return
        
        total = sum(item['amount'] for item in self.data)
        if total == 0:
            self.show_no_data()
            return
        
        center_x = self.width / 2
        center_y = self.height / 2
        radius = min(self.width, self.height) * 0.35
        
        start_angle = 90  # Починаємо з 12-ї години (90 градусів)
        
        # Обходимо і малюємо сектори
        for i, item in enumerate(self.data):
            percentage = item['amount'] / total
            angle = percentage * 360
            
            # Kivy Ellipse малює проти годинникової стрілки,
            # тому кінцевий кут має бути меншим за початковий
            end_angle = start_angle - angle
            
            # Малюємо заповнений сектор
            self.draw_filled_sector(center_x, center_y, radius, end_angle, start_angle, item['color'])
            
            # Новий початковий кут для наступного сектора
            start_angle = end_angle
        
        # Потім додаємо легенди з уникненням перетинів
        # Передаємо обчислені дані для легенд
        self.draw_smart_legends(center_x, center_y, radius, total)

    def draw_filled_sector(self, cx, cy, radius, start_angle, end_angle, color):
        """Малює заповнений сектор кругової діаграми, використовуючи Ellipse."""
        with self.canvas:
            Color(*color)
            Ellipse(
                pos=(cx - radius, cy - radius),
                size=(radius * 2, radius * 2),
                angle_start=start_angle,
                angle_end=end_angle # end_angle < start_angle
            )

    def draw_smart_legends(self, cx, cy, radius, total):
        """
        ВИПРАВЛЕНО: Обчислення середнього кута для легенд,
        що відповідає обходу проти годинникової стрілки.
        """
        legend_positions = []
        
        # Починаємо з тієї ж точки, що і для малювання секторів
        current_angle = 90
        
        for i, item in enumerate(self.data):
            percentage = item['amount'] / total
            angle = percentage * 360
            
            # Пропускаємо дуже малі сектори (< 1 градус)
            if angle < 1:
                current_angle -= angle
                continue
                
            # mid_angle тепер знаходиться між поточним current_angle
            # та кутом, який буде current_angle - angle (кінцевий кут сектора)
            
            # ВИПРАВЛЕННЯ: Середній кут = Поточний_кут - Половина_ширини_сектора
            mid_angle = current_angle - angle / 2
            
            # Визначаємо оптимальну позицію для легенди
            text_pos, line_points = self.find_best_legend_position(
                cx, cy, radius, mid_angle, legend_positions, item
            )
            
            if text_pos:
                # ... (Малювання лінії та тексту залишається без змін) ...
                with self.canvas:
                    Color(*item['color'])
                    Line(points=line_points, width=dp(1.2))
                
                self.add_legend_text(text_pos, item, percentage)
                legend_positions.append(text_pos)
            
            # Переходимо до наступного сектора
            current_angle -= angle

    def draw_smart_legends(self, cx, cy, radius, total):
        """Малює інтелектуальні легенди з уникненням перетинів"""
        legend_positions = []  # Для відстеження позицій легенд
        
        start_angle = 90
        
        for i, item in enumerate(self.data):
            percentage = item['amount'] / total
            angle = percentage * 360
            
            # Пропускаємо дуже малі сектори (< 1 градус)
            if angle < 1:
                start_angle -= angle
                continue
                
            # Кут середини сектору
            mid_angle = start_angle - angle / 2
            
            # Визначаємо оптимальну позицію для легенди
            text_pos, line_points = self.find_best_legend_position(
                cx, cy, radius, mid_angle, legend_positions, item
            )
            
            if text_pos:
                # Малюємо лінію
                with self.canvas:
                    Color(*item['color'])
                    Line(points=line_points, width=dp(1.2))
                
                # Додаємо текст
                self.add_legend_text(text_pos, item, percentage)
                legend_positions.append(text_pos)
            
            start_angle -= angle # Переходимо до наступного сектора

    def find_best_legend_position(self, cx, cy, radius, angle, existing_positions, item):
        """
        ВИПРАВЛЕННЯ 3: Знаходить найкращу позицію для легенди з контрольованою довжиною.
        """
        angle_rad = math.radians(angle)
        
        # ЗМЕНШЕНО: Використовуємо менші множники для коротших ліній
        distances = [1.1, 1.25, 1.4, 1.55] 
        max_text_radius = radius * 1.6 # Обмежуємо максимальну довжину
        
        for distance_multiplier in distances:
            text_radius = radius * distance_multiplier
            
            # Обмежуємо радіус, щоб лінії не виходили занадто далеко
            text_radius = min(text_radius, max_text_radius)
            
            text_x = cx + text_radius * math.cos(angle_rad)
            text_y = cy + text_radius * math.sin(angle_rad)
            
            # Перевіряємо, чи не перетинається з існуючими легендами
            if not self.check_collision((text_x, text_y), existing_positions, dp(45)):
                # Точки для лінії: Edge -> Mid Point -> Text Position
                edge_x = cx + radius * math.cos(angle_rad)
                edge_y = cy + radius * math.sin(angle_rad)
                
                # Проміжна точка для згладжування лінії (виносимо трохи за радіус)
                mid_radius = radius * 1.05
                mid_x = cx + mid_radius * math.cos(angle_rad)
                mid_y = cy + mid_radius * math.sin(angle_rad)
                
                line_points = [edge_x, edge_y, mid_x, mid_y, text_x, text_y]
                return (text_x, text_y), line_points
        
        return None, None

    def check_collision(self, new_pos, existing_positions, min_distance):
        """Перевіряє колізії з існуючими легендами"""
        for pos in existing_positions:
            distance = math.sqrt((new_pos[0] - pos[0])**2 + (new_pos[1] - pos[1])**2)
            if distance < min_distance:
                return True
        return False

    def add_legend_text(self, position, item, percentage):
        """Додає текст легенди з правильним вирівнюванням"""
        text_x, text_y = position
        
        # Визначаємо вирівнювання на основі позиції
        # Використовуємо self.width / 2 для halign
        halign = 'left' if text_x >= self.width / 2 else 'right'
        valign = 'bottom' if text_y > self.height / 2 else 'top'
        
        # Компактний формат тексту
        text_content = f"{item['name']}\n({percentage:.1f}%)"
        if percentage * 100 > 5:  # Для більших секторів показуємо суму
            text_content = f"{item['name']}\n${item['amount']:.2f}\n({percentage:.1f}%)"
            text_height = dp(36)
        else:  # Для малих секторів - компактніше
            text_height = dp(28)
        
        text_width = dp(65)
        
        # Коригуємо позицію для вирівнювання
        pos_x = text_x if halign == 'left' else text_x - text_width
        pos_y = text_y if valign == 'bottom' else text_y - text_height
        
        # Перевіряємо, чи текст не виходить за межі віджета
        pos_x = max(dp(5), min(pos_x, self.width - text_width - dp(5)))
        pos_y = max(dp(5), min(pos_y, self.height - text_height - dp(5)))
        
        text_label = Label(
            text=text_content,
            pos=(pos_x, pos_y),
            size=(text_width, text_height),
            font_size=dp(8),
            color=DARK_TEXT,
            halign=halign,
            valign=valign,
            text_size=(text_width, None)
        )
        self.add_widget(text_label)

    def show_no_data(self):
        """Показати повідомлення про відсутність даних"""
        center_x = self.width / 2
        center_y = self.height / 2
        
        with self.canvas:
            Color(*LIGHT_GRAY)
            Ellipse(
                pos=(center_x - dp(40), center_y - dp(40)), 
                size=(dp(80), dp(80))
            )
        
        no_data_label = Label(
            text="Немає даних\nдля відображення",
            pos=(center_x - dp(60), center_y - dp(20)),
            size=(dp(120), dp(40)),
            font_size=dp(12),
            color=DARK_GRAY,
            halign='center',
            valign='middle'
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
        charts_main_layout = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None, height=dp(350))
        
        if self.envelopes_for_chart:
            # Заголовок діаграми
            # ВИПРАВЛЕННЯ: Додамо 'Візуалізація' як на зображенні
            vis_label = Label(
                text="Візуалізація",
                font_size=dp(18),
                bold=True,
                color=DARK_TEXT,
                size_hint_y=None,
                height=dp(25)
            )
            charts_main_layout.add_widget(vis_label)
            
            title_label = Label(
                text="Розподіл коштів по конвертах",
                font_size=dp(16),
                bold=True,
                color=DARK_TEXT,
                size_hint_y=None,
                height=dp(25)
            )
            charts_main_layout.add_widget(title_label)
            
            # Кругова діаграма
            # ВИПРАВЛЕННЯ: Використовуємо виправлений клас SimplePieChartWidget
            pie_chart = SimplePieChartWidget(self.envelopes_for_chart)
            pie_chart.size_hint_y = 1
            charts_main_layout.add_widget(pie_chart)
        else:
            no_data_label = Label(
                text="Немає даних для відображення діаграми",
                font_size=dp(14),
                color=DARK_GRAY,
                size_hint_y=None,
                height=dp(40)
            )
            charts_main_layout.add_widget(no_data_label)
        
        container.add_widget(charts_main_layout)
    


    def on_envelope_action(self, envelope_data, action):
        """Обробка дій з конвертом"""
        if action == 'add':
            self.show_add_money_modal(envelope_data)
        elif action == 'edit':
            self.show_edit_envelope_modal(envelope_data)
    
    def show_edit_envelope_modal(self, envelope_data):
        """Показати модальне вікно редагування конверту"""
        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(15))
        
        title = Label(
            text=f"Редагування: {envelope_data['name']}",
            font_size=dp(18),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(35)
        )
        content.add_widget(title)
        
        # Назва конверту
        name_input = TextInput(
            text=envelope_data['name'],
            hint_text="Назва конверту",
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(name_input)
        
        # Бюджет
        budget_input = TextInput(
            text=str(envelope_data['budget_limit']) if envelope_data['budget_limit'] > 0 else "",
            hint_text="Бюджет (не обов'язково)",
            input_filter='float',
            size_hint_y=None,
            height=dp(40)
        )
        content.add_widget(budget_input)
        
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
        
        save_btn = Button(
            text="Зберегти",
            background_color=SUCCESS_GREEN,
            color=WHITE
        )
        
        def save_changes(instance):
            new_name = name_input.text.strip()
            budget_text = budget_input.text.strip()
            
            if not new_name:
                error_label.text = "Введіть назву конверту"
                return
            
            try:
                new_budget = float(budget_text) if budget_text else 0.0
                
                # Оновлюємо конверт в базі даних
                success = update_envelope(
                    cursor, conn,
                    envelope_data['id'],
                    name=new_name,
                    budget_limit=new_budget
                )
                
                if success:
                    popup.dismiss()
                    self.load_data()
                    self.show_success_message(f"Конверт '{new_name}' успішно оновлено!")
                else:
                    error_label.text = "Помилка при оновленні конверту"
                    
            except ValueError:
                error_label.text = "Введіть коректну суму бюджету"
        
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        save_btn.bind(on_press=save_changes)
        
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(save_btn)
        content.add_widget(buttons_layout)
        
        popup = Popup(
            title='Редагування конверту',
            content=content,
            size_hint=(0.85, 0.5)
        )
        popup.open()
    
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
                # Миттєве оновлення
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
    
    def show_success_message(self, message):
        """Показати повідомлення про успіх"""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(20))
        
        content.add_widget(Label(
            text=message, 
            color=SUCCESS_GREEN,
            font_size=dp(16)
        ))
        
        ok_btn = Button(
            text='OK',
            size_hint_y=None,
            height=dp(40),
            background_color=PRIMARY_BLUE,
            color=WHITE
        )
        ok_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(ok_btn)
        
        popup = Popup(
            title='Успіх',
            content=content,
            size_hint=(0.6, 0.3)
        )
        popup.open()
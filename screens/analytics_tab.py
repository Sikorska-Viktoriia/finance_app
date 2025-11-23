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


PRIMARY_PINK = (0.95, 0.3, 0.5, 1)
PRIMARY_BLUE = (0.2, 0.7, 0.9, 1)
LIGHT_PINK = (1, 0.95, 0.95, 1)
LIGHT_BLUE = (0.92, 0.98, 1.0, 1)
ERROR_RED = (0.9, 0.2, 0.2, 1)
SUCCESS_GREEN = (0.2, 0.8, 0.3, 1)
WARNING_ORANGE = (1, 0.6, 0.2, 1)
SAVINGS_PINK = (0.95, 0.4, 0.6, 1) 
WHITE = (1, 1, 1, 1)
DARK_TEXT = (0.1, 0.1, 0.1, 1)
LIGHT_GRAY = (0.9, 0.9, 0.9, 1)
MEDIUM_GRAY = (0.7, 0.7, 0.7, 1)
DARK_GRAY = (0.4, 0.4, 0.4, 1)

ENVELOPE_COLORS = [
    [0.95, 0.3, 0.5, 1],    # Яскраво рожевий
    [0.2, 0.7, 0.9, 1],     # Блакитний
    [0.2, 0.8, 0.3, 1],     # Зелений
    [1.0, 0.6, 0.2, 1],     # Помаранчевий
    [0.6, 0.2, 0.8, 1],     # Фіолетовий
    [0.2, 0.8, 0.8, 1],     # Бірюзовий
    [0.9, 0.2, 0.2, 1],     # Червоний
    [0.4, 0.2, 0.9, 1],     # Синій
    [1.0, 0.8, 0.2, 1],     # Жовтий
    [0.8, 0.4, 0.9, 1],     # Лавандовий
    [0.3, 0.8, 0.6, 1],     # М'ятний
    [0.9, 0.5, 0.7, 1],     # Світло рожевий
    [0.5, 0.5, 0.9, 1],     # Синьо-фіолетовий
    [0.9, 0.7, 0.3, 1],     # Золотистий
    [0.7, 0.9, 0.4, 1],     # Салатовий
    [0.8, 0.6, 0.9, 1],     # Світло фіолетовий
]

def get_unique_color(envelope_count):

    return ENVELOPE_COLORS[envelope_count % len(ENVELOPE_COLORS)]


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


class CompactEnvelopeCard(BoxLayout):

    def __init__(self, envelope_data, on_manage_callback=None, **kwargs):
        super().__init__(**kwargs)
        self.envelope_data = envelope_data
        self.on_manage_callback = on_manage_callback
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = dp(130)
        self.padding = dp(12)
        self.spacing = dp(6)
        
      
        with self.canvas.before:
            Color(*envelope_data['color'])
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12)]
            )
     
            Color(1, 1, 1, 0.2)
            RoundedRectangle(
                pos=(self.x, self.y + self.height * 0.4),
                size=(self.width, self.height * 0.6),
                radius=[dp(12)]
            )
        
        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
  
        name_label = Label(
            text=envelope_data['name'],
            font_size=dp(14),
            bold=True,
            color=WHITE,
            size_hint_y=None,
            height=dp(22)
        )
        self.add_widget(name_label)
        

        balance_label = Label(
            text=f"{envelope_data['current_amount']:.2f} $",
            font_size=dp(18),
            bold=True,
            color=WHITE,
            size_hint_y=None,
            height=dp(26)
        )
        self.add_widget(balance_label)
        
     
        if envelope_data['budget_limit'] > 0:
            self.progress_bg = Widget(size_hint_y=None, height=dp(6))
            with self.progress_bg.canvas:
                Color(1, 1, 1, 0.3)
                self.progress_bg_rect = Rectangle(
                    pos=self.progress_bg.pos,
                    size=self.progress_bg.size
                )
            self.add_widget(self.progress_bg)
            
           
            percentage = min((envelope_data['current_amount'] / envelope_data['budget_limit']) * 100, 100)
            percent_label = Label(
                text=f"{percentage:.0f}%",
                font_size=dp(10),
                color=WHITE,
                size_hint_y=None,
                height=dp(16)
            )
            self.add_widget(percent_label)
        
     
        buttons_layout = BoxLayout(
            size_hint_y=None,
            height=dp(28),
            spacing=dp(5)
        )
        
     
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
       
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _update_progress_bg(self, instance, value):
     
        self.progress_bg_rect.pos = instance.pos
        self.progress_bg_rect.size = instance.size
        self.update_progress_bar()

    def update_progress_bar(self):
       
        if not hasattr(self, 'progress_bg') or self.envelope_data['budget_limit'] <= 0:
            return
            
        self.progress_bg.canvas.after.clear()
        percentage = min((self.envelope_data['current_amount'] / self.envelope_data['budget_limit']) * 100, 100)
        
        with self.progress_bg.canvas.after:
        
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
        
        if self.on_manage_callback:
            self.on_manage_callback(self.envelope_data, 'add')

    def on_edit(self, instance):
        
        if self.on_manage_callback:
            self.on_manage_callback(self.envelope_data, 'edit')


class StatCard(BoxLayout):
    
    def __init__(self, title, value, subtitle="", color=PRIMARY_BLUE, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint = (1, None)
        self.height = dp(100)
        self.padding = dp(10)
        self.spacing = dp(4)
        
       
        with self.canvas.before:
            Color(*color)
            self.bg_rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(10)]
            )
        
        self.bind(pos=self._update, size=self._update)
        
      
        self.title_label = Label(
            text=title,
            font_size=dp(12),
            color=WHITE,
            bold=True,
            size_hint_y=None,
            height=dp(20)
        )
        self.add_widget(self.title_label)
        
     
        self.value_label = Label(
            text=str(value),
            font_size=dp(16),
            color=WHITE,
            bold=True,
            size_hint_y=None,
            height=dp(26)
        )
        self.add_widget(self.value_label)
        
     
        self.subtitle_label = Label(
            text=subtitle,
            font_size=dp(10),
            color=WHITE,
            size_hint_y=None,
            height=dp(16)
        )
        self.add_widget(self.subtitle_label)
    
    def update_data(self, value, subtitle=""):
       
        self.value_label.text = str(value)
        self.subtitle_label.text = subtitle
    
    def _update(self, *args):
      
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class SimplePieChartWidget(Widget):
    
    def __init__(self, data=None, **kwargs):
        super().__init__(**kwargs)
        self.data = data or []
        self.size_hint = (1, None)
        self.height = dp(300)
        
        self.hovered_sector = None
        self.current_legend = None
        self.sectors = []
        self.center_x = 0
        self.center_y = 0
        self.radius = 0
        
        self.bind(pos=self.update_chart, size=self.update_chart)
    
    def update_data(self, data):
        
        self.data = data
        self.update_chart()
    
    def update_chart(self, *args):
       
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
        
        self.center_x = self.width / 2
        self.center_y = self.height / 2
        self.radius = min(self.width, self.height) * 0.35
        
        
        start_angle = 0
        self.sectors = []
        
       
        for i, item in enumerate(self.data):
            percentage = item['amount'] / total
            angle = percentage * 360
            
            end_angle = start_angle + angle
            
            self.draw_filled_sector(self.center_x, self.center_y, self.radius, start_angle, end_angle, item['color'])
            
            
            self.sectors.append({
                'item': item,
                'percentage': percentage,
                'start_angle': start_angle,
                'end_angle': end_angle,
                'color': item['color']
            })
            
            start_angle = end_angle
        
        self.add_hint()

    def draw_filled_sector(self, cx, cy, radius, start_angle, end_angle, color):
    
        with self.canvas:
            Color(*color)
            Ellipse(
                pos=(cx - radius, cy - radius),
                size=(radius * 2, radius * 2),
                angle_start=start_angle,
                angle_end=end_angle
            )

    def on_touch_move(self, touch):
    
        return self.handle_touch(touch)

    def on_touch_down(self, touch):
   
        return self.handle_touch(touch)

    def handle_touch(self, touch):
  
        if not self.collide_point(*touch.pos):
            self.hide_legend()
            self.hovered_sector = None
            return False
        
        sector = self.get_sector_at_pos(touch.x, touch.y)
        
        if sector != self.hovered_sector:
            self.hovered_sector = sector
            if sector:
                self.show_legend(sector, touch.x, touch.y)
            else:
                self.hide_legend()
        
        return True

    def get_sector_at_pos(self, x, y):

        dx = x - self.center_x
        dy = y - self.center_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > self.radius or distance == 0:
            return None
        

        angle_rad = math.atan2(dy, dx)
        

        angle_deg = math.degrees(angle_rad)
        

        angle_kivy = (90 - angle_deg) % 360
        if angle_kivy < 0:
            angle_kivy += 360
        

        
        for i, sector in enumerate(self.sectors):
            start = sector['start_angle']
            end = sector['end_angle']
            

            

            if start <= end:
                if start <= angle_kivy <= end:
        
                    return sector
            else:
    
                if angle_kivy >= start or angle_kivy <= end:
        
                    return sector
        

        return None

    def show_legend(self, sector, x, y):
 
        self.hide_legend()
        
        item = sector['item']
        percentage = sector['percentage']
        

        

        legend_content = f"{item['name']}\n${item['amount']:.2f}\n({percentage * 100:.1f}%)"
        

        text_width = dp(120)
        text_height = dp(65)

        pos_x = x + dp(15)
        pos_y = y + dp(15)
        

        if pos_x + text_width > self.width - dp(5):
            pos_x = x - text_width - dp(15)
        if pos_y + text_height > self.height - dp(5):
            pos_y = y - text_height - dp(15)
        
        pos_x = max(dp(5), min(pos_x, self.width - text_width - dp(5)))
        pos_y = max(dp(5), min(pos_y, self.height - text_height - dp(5)))


        self.current_legend = BoxLayout(
            orientation='vertical',
            size=(text_width, text_height),
            pos=(pos_x, pos_y),
            padding=dp(8),
            spacing=dp(3)
        )
        

        with self.current_legend.canvas.before:
            Color(1, 1, 1, 0.98)
            RoundedRectangle(
                pos=self.current_legend.pos,
                size=self.current_legend.size,
                radius=[dp(8)]
            )
            Color(0.3, 0.3, 0.3, 0.9)
            Line(
                rounded_rectangle=(
                    self.current_legend.x, self.current_legend.y,
                    self.current_legend.width, self.current_legend.height,
                    dp(8)
                ),
                width=dp(1.5)
            )
        

        color_indicator = Widget(size_hint_y=None, height=dp(4))
        with color_indicator.canvas:
            Color(*sector['color'])
            Rectangle(pos=color_indicator.pos, size=color_indicator.size)
        
  
        legend_label = Label(
            text=legend_content,
            font_size=dp(11),
            color=DARK_TEXT,
            halign='center',
            valign='middle',
            size_hint_y=1
        )
        
        self.current_legend.add_widget(color_indicator)
        self.current_legend.add_widget(legend_label)
        self.add_widget(self.current_legend)

    def hide_legend(self):

        if self.current_legend:
            self.remove_widget(self.current_legend)
            self.current_legend = None

    def add_hint(self):

        if not self.data:
            return
            
        hint_label = Label(
            text="Наведіть на сектор для деталей",
            pos=(dp(10), dp(5)),
            size=(self.width - dp(20), dp(20)),
            size_hint=(None, None),
            font_size=dp(10),
            color=DARK_GRAY,
            halign='center'
        )
        self.add_widget(hint_label)

    def show_no_data(self):
   
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

        return App.get_running_app()
    
    def create_ui(self, dt=None):

        self.load_data()
    
    def on_enter(self):

        Clock.schedule_once(lambda dt: self.load_data(), 0.1)
    
    def load_data(self):
 
        try:
            app = self.get_app()
            if not hasattr(app, 'current_user_id') or not app.current_user_id:
                return
            

            self.user_cards = get_user_cards(cursor, app.current_user_id)
            
      
            self.envelopes_data = get_user_envelopes(cursor, app.current_user_id)
            
     
            if not self.envelopes_data:
                self.create_default_envelopes()
            else:
           
                self.load_analytics_data()
                
      
                self.update_envelopes_display()
                self.update_stats_display()
                self.update_charts_display()
            
        except Exception as e:
            print(f"Помилка завантаження даних аналітики: {e}")
    
    def create_default_envelopes(self):
     
        try:
            app = self.get_app()
            
            default_envelopes = [
                {"name": "Їжа", "color": ENVELOPE_COLORS[0]},
                {"name": "Транспорт", "color": ENVELOPE_COLORS[1]},
                {"name": "Розваги", "color": ENVELOPE_COLORS[2]},
                {"name": "Одяг", "color": ENVELOPE_COLORS[3]},
                {"name": "Здоров'я", "color": ENVELOPE_COLORS[4]},
                {"name": "Подарунки", "color": ENVELOPE_COLORS[5]}
            ]
            
            for envelope in default_envelopes:
                create_envelope(
                    cursor, conn, 
                    app.current_user_id, 
                    envelope["name"], 
                    envelope["color"], 
                    0.0  
                )
            

            self.envelopes_data = get_user_envelopes(cursor, app.current_user_id)
            self.load_analytics_data()
            self.update_envelopes_display()
            self.update_stats_display()
            self.update_charts_display()
            
        except Exception as e:
            print(f"Помилка створення стандартних конвертів: {e}")
    
    def load_analytics_data(self):
    
        try:
            app = self.get_app()
            

            self.analytics_data = get_analytics_data(cursor, app.current_user_id, 'month')
            print(f"Завантажена аналітика: {self.analytics_data}")
            

            savings_data = self.get_savings_data(app.current_user_id)
            
        
            if savings_data:
                self.analytics_data['total_savings'] = savings_data['total_savings']
                self.analytics_data['savings_progress'] = savings_data['savings_progress']
                self.analytics_data['active_savings_plans'] = savings_data['active_plans_count']
            

            self.envelopes_for_chart = []
            for envelope in self.envelopes_data:
                if envelope['current_amount'] > 0:
                    self.envelopes_for_chart.append({
                        'name': envelope['name'],
                        'amount': envelope['current_amount'],
                        'color': envelope['color']
                    })
            
     
            if savings_data and savings_data['total_savings'] > 0:
                self.envelopes_for_chart.append({
                    'name': 'Заощадження',
                    'amount': savings_data['total_savings'],
                    'color': SAVINGS_PINK  
                })
            
        except Exception as e:
            print(f"Помилка завантаження аналітики: {e}")
            self.analytics_data = {}
            self.envelopes_for_chart = []

    def get_savings_data(self, user_id):

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
                'color': SAVINGS_PINK  # Рожевий для заощаджень
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
   
        if 'charts_container' not in self.ids:
            return
            
        container = self.ids.charts_container
        container.clear_widgets()
        
  
        charts_main_layout = BoxLayout(orientation='vertical', spacing=dp(5), size_hint_y=None, height=dp(350))
        
        if hasattr(self, 'envelopes_for_chart') and self.envelopes_for_chart:
  
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
    
        if action == 'add':
            self.show_add_money_modal(envelope_data)
        elif action == 'edit':
            self.show_edit_envelope_modal(envelope_data)
    
    def show_edit_envelope_modal(self, envelope_data):
      
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
        
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text=f"Редагування: {envelope_data['name']}",
            font_size=dp(18),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(35)
        )
        content.add_widget(title)
        
      
        name_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        name_layout.add_widget(Label(
            text='Назва:', 
            size_hint_x=0.3, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        name_input = WhiteTextInput(
            text=envelope_data['name'],
            size_hint_x=0.7
        )
        name_layout.add_widget(name_input)
        content.add_widget(name_layout)
        
       
        budget_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        budget_layout.add_widget(Label(
            text='Бюджет:', 
            size_hint_x=0.3, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        budget_input = WhiteTextInput(
            text=str(envelope_data['budget_limit']) if envelope_data['budget_limit'] > 0 else "",
            hint_text="Не обов'язково",
            input_filter='float',
            size_hint_x=0.7
        )
        budget_layout.add_widget(budget_input)
        content.add_widget(budget_layout)
        
        error_label = Label(
            text="",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(25)
        )
        content.add_widget(error_label)
        
        
        buttons_layout = BoxLayout(
            orientation='horizontal', 
            spacing=dp(10), 
            size_hint_y=None, 
            height=dp(50)
        )
        
        delete_btn = WhiteButton(
            text="Видалити",
            background_color=ERROR_RED
        )
        
        cancel_btn = WhiteButton(
            text="Скасувати",
            background_color=LIGHT_GRAY,
            color=DARK_TEXT
        )
        
        save_btn = WhiteButton(
            text="Зберегти",
            background_color=SUCCESS_GREEN
        )
        
        def save_changes(instance):
            new_name = name_input.text.strip()
            budget_text = budget_input.text.strip()
            
            if not new_name:
                error_label.text = "Введіть назву конверту"
                return
            
            try:
                new_budget = float(budget_text) if budget_text else 0.0
                
          
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
        
        def delete_envelope(instance):
        
            confirm_content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
            
            with confirm_content.canvas.before:
                Color(*WHITE)
                self.confirm_rect = Rectangle(pos=confirm_content.pos, size=confirm_content.size)
            
            confirm_content.bind(pos=self._update_confirm_rect, size=self._update_confirm_rect)
            
            confirm_content.add_widget(Label(
                text=f"Ви впевнені, що хочете видалити\nконверт '{envelope_data['name']}'?",
                halign='center',
                color=DARK_TEXT,
                font_size=dp(16)
            ))
            
            confirm_buttons = BoxLayout(
                orientation='horizontal', 
                spacing=dp(10), 
                size_hint_y=None, 
                height=dp(50)
            )
            
            no_btn = WhiteButton(
                text='Ні', 
                background_color=LIGHT_GRAY,
                color=DARK_TEXT
            )
            yes_btn = WhiteButton(
                text='Так', 
                background_color=ERROR_RED
            )
            
            def confirm_delete(instance):
                try:
                 
                    cursor.execute("DELETE FROM envelopes WHERE id=?", (envelope_data['id'],))
                    cursor.execute("DELETE FROM envelope_transactions WHERE envelope_id=?", (envelope_data['id'],))
                    conn.commit()
                    
                    confirm_popup.dismiss()
                    popup.dismiss()
                    self.load_data()
                    self.show_success_message(f"Конверт '{envelope_data['name']}' успішно видалено!")
                except Exception as e:
                    print(f"Помилка видалення конверту: {e}")
                    error_label.text = "Помилка при видаленні конверту"
            
            no_btn.bind(on_press=lambda x: confirm_popup.dismiss())
            yes_btn.bind(on_press=confirm_delete)
            
            confirm_buttons.add_widget(no_btn)
            confirm_buttons.add_widget(yes_btn)
            confirm_content.add_widget(confirm_buttons)
            
            confirm_popup = WhitePopup(
                title='Підтвердження видалення',
                content=confirm_content,
                size_hint=(0.7, 0.3)
            )
            confirm_popup.open()
        
        delete_btn.bind(on_press=delete_envelope)
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        save_btn.bind(on_press=save_changes)
        
        buttons_layout.add_widget(delete_btn)
        buttons_layout.add_widget(cancel_btn)
        buttons_layout.add_widget(save_btn)
        content.add_widget(buttons_layout)
        
        popup = WhitePopup(
            title='Редагування конверту',
            content=content,
            size_hint=(0.85, 0.5)
        )
        popup.open()
    
    def _update_content_rect(self, instance, value):
       
        self.content_rect.pos = instance.pos
        self.content_rect.size = instance.size
    
    def _update_confirm_rect(self, instance, value):
        
        self.confirm_rect.pos = instance.pos
        self.confirm_rect.size = instance.size
    
    def create_envelope(self):
     
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
            
          
            color = get_unique_color(len(self.envelopes_data))
            
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
       
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
    
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        title = Label(
            text=f"Поповнення: {envelope_data['name']}",
            font_size=dp(18),
            bold=True,
            color=DARK_TEXT,
            size_hint_y=None,
            height=dp(35)
        )
        content.add_widget(title)
        
       
        card_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        card_layout.add_widget(Label(
            text="З картки:", 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        
        card_spinner = Spinner(
            text=self.user_cards[0]['name'] if self.user_cards else "Немає карток",
            values=[card['name'] for card in self.user_cards],
            size_hint_x=0.6,
            background_color=WHITE,
            color=DARK_TEXT
        )
        card_layout.add_widget(card_spinner)
        content.add_widget(card_layout)
        
    
        amount_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        amount_layout.add_widget(Label(
            text="Сума:", 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        amount_input = WhiteTextInput(
            hint_text="Сума поповнення",
            input_filter='float',
            size_hint_x=0.6
        )
        amount_layout.add_widget(amount_input)
        content.add_widget(amount_layout)
       
        desc_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45))
        desc_layout.add_widget(Label(
            text="Опис:", 
            size_hint_x=0.4, 
            color=DARK_TEXT,
            font_size=dp(16)
        ))
        desc_input = WhiteTextInput(
            hint_text="Не обов'язково",
            size_hint_x=0.6
        )
        desc_layout.add_widget(desc_input)
        content.add_widget(desc_layout)
        
        error_label = Label(
            text="",
            color=ERROR_RED,
            size_hint_y=None,
            height=dp(25)
        )
        content.add_widget(error_label)
        
        buttons_layout = BoxLayout(
            orientation='horizontal', 
            spacing=dp(10), 
            size_hint_y=None, 
            height=dp(50)
        )
        
        cancel_btn = WhiteButton(
            text="Скасувати",
            background_color=LIGHT_GRAY,
            color=DARK_TEXT
        )
        
        add_btn = WhiteButton(
            text="Поповнити",
            background_color=SUCCESS_GREEN
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
                
      
                card_id = None
                for card in self.user_cards:
                    if card['name'] == card_name:
                        card_id = card['id']
                        break
                
                if not card_id:
                    error_label.text = "Картку не знайдено"
                    return
                
      
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
        
        popup = WhitePopup(
            title='Поповнення конверту',
            content=content,
            size_hint=(0.85, 0.5)
        )
        popup.open()
    
    def add_money_to_envelope(self, envelope_id, amount, description, card_id):
        """Додати гроші до конверту"""
        try:
            app = self.get_app()
            
          
            cursor.execute(
                "UPDATE user_cards SET balance = balance - ? WHERE id = ?",
                (amount, card_id)
            )
            
     
            success = add_to_envelope(cursor, conn, app.current_user_id, envelope_id, amount, description, card_id)
            
            conn.commit()
            
            return success
        except Exception as e:
            print(f"Помилка поповнення конверту: {e}")
            return False
    
    def show_success_message(self, message):
        """Показати повідомлення про успіх (білий дизайн)"""
        content = BoxLayout(orientation='vertical', spacing=dp(15), padding=dp(25))
        
     
        with content.canvas.before:
            Color(*WHITE)
            self.content_rect = Rectangle(pos=content.pos, size=content.size)
        
        content.bind(pos=self._update_content_rect, size=self._update_content_rect)
        
        content.add_widget(Label(
            text=message, 
            color=SUCCESS_GREEN,
            font_size=dp(16)
        ))
        
        ok_btn = WhiteButton(
            text='OK',
            background_color=PRIMARY_BLUE
        )
        ok_btn.bind(on_press=lambda x: popup.dismiss())
        content.add_widget(ok_btn)
        
        popup = WhitePopup(
            title='Успіх',
            content=content,
            size_hint=(0.6, 0.3)
        )
        popup.open()
import sqlite3
import json
from datetime import datetime
import sys
import os
import threading 
import traceback

# --- ІМПОРТИ ДЛЯ GEMINI ---
from google import genai
from google.genai import types
# --------------------------

# Додаємо шлях до кореня проекту для імпортів
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Ініціалізація з db_manager.py
try:
    from db_manager import conn, cursor, get_user_cards, get_user_envelopes, get_user_savings_plans, get_user_transactions, get_analytics_data
except ImportError:
    # Заглушка, якщо db_manager не імпортується
    DB_NAME = "users.db"
    
    def get_db_connection():
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        return conn, conn.cursor()
    
    conn, cursor = get_db_connection()
    print("⚠️ Використовується заглушка БД. Перевірте імпорт db_manager.py.")

# --- КОНФІГУРАЦІЯ GEMINI ---
GEMINI_MODEL_NAME = "gemini-2.0-flash"
try:
    client = genai.Client()
    print("Gemini Client ініціалізовано.")
except Exception as e:
    print(f"Помилка ініціалізації Gemini Client: {e}. Перевірте GEMINI_API_KEY.")
    client = None
# ---------------------------

class AIManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.conversation_history = []
        self.load_conversation_history()

    def get_user_data(self):
        """Повна інформація про користувача для AI"""
        try:
            cursor.execute("SELECT username, email, created_at FROM users WHERE id=?", (self.user_id,))
            user_result = cursor.fetchone()
            if not user_result:
                return {}
            
            username, email, created_at = user_result
            
            total_balance = self._get_total_balance_private()
            cards = get_user_cards(cursor, self.user_id)
            envelopes = self._get_envelopes_with_proper_limits()
            savings_plans = get_user_savings_plans(cursor, self.user_id)
            recent_transactions = get_user_transactions(cursor, self.user_id, limit=10)
            analytics = get_analytics_data(cursor, self.user_id, 'month')
            
            return {
                "username": username,
                "total_balance": total_balance,
                "cards": cards,
                "envelopes": envelopes,
                "savings_plans": savings_plans,
                "recent_transactions": recent_transactions,
                "analytics": analytics
            }
        except Exception as e:
            print(f"Error getting user data: {e}")
            return {}
    
    def _get_envelopes_with_proper_limits(self):
        """Отримує конверти з правильним визначенням бюджетних обмежень"""
        try:
            cursor.execute("""
                SELECT id, name, color, budget_limit, current_amount 
                FROM envelopes 
                WHERE user_id=?
            """, (self.user_id,))
            envelopes = cursor.fetchall()
            
            result = []
            for envelope in envelopes:
                env_id, name, color, budget_limit, current_amount = envelope
                
                # Визначаємо тип конверту
                if budget_limit > 0:
                    # Конверт з бюджетним обмеженням
                    envelope_type = "бюджетний"
                    remaining = budget_limit - current_amount
                    usage_info = f"{current_amount:.2f}/{budget_limit:.2f} грн (залишилось: {remaining:.2f} грн)"
                else:
                    # Конверт без бюджетного обмеження (звичайний конверт)
                    envelope_type = "звичайний"
                    usage_info = f"{current_amount:.2f} грн (без бюджетного обмеження)"
                
                result.append({
                    'id': env_id,
                    'name': name,
                    'color': self._safe_color_conversion(color),
                    'budget_limit': budget_limit,
                    'current_amount': current_amount,
                    'type': envelope_type,
                    'usage_info': usage_info
                })
            
            return result
        except Exception as e:
            print(f"Error getting envelopes: {e}")
            return []
    
    def _safe_color_conversion(self, color):
        """Безпечно конвертує колір"""
        if isinstance(color, list):
            return color
        elif isinstance(color, str):
            try:
                return json.loads(color.replace("'", '"'))
            except:
                try:
                    return eval(color)
                except:
                    return [0.2, 0.4, 0.8, 1]
        return [0.2, 0.4, 0.8, 1]
        
    def _get_total_balance_private(self):
        try:
            cursor.execute("SELECT SUM(balance) FROM user_cards WHERE user_id=?", (self.user_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else 0.0
        except:
            return 0.0

    def get_conversation_history(self, limit=10):
        try:
            cursor.execute("""
                SELECT message, response, timestamp 
                FROM ai_chat_history 
                WHERE user_id=? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (self.user_id, limit))
            history = cursor.fetchall()
            return list(reversed(history))
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []

    def load_conversation_history(self):
        self.conversation_history = self.get_conversation_history()

    def save_message(self, message, response):
        try:
            # Перевірка чи таблиця існує
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_chat_history'")
            if not cursor.fetchone():
                print("⚠️ Table ai_chat_history doesn't exist. Creating...")
                cursor.execute('''
                    CREATE TABLE ai_chat_history(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        message TEXT NOT NULL,
                        response TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()
            
            cursor.execute("""
                INSERT INTO ai_chat_history (user_id, message, response) 
                VALUES (?, ?, ?)
            """, (self.user_id, message, response))
            conn.commit()
            
            self.conversation_history.append((message, response, datetime.now().isoformat()))
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
                
        except Exception as e:
            print(f"Error saving message: {e}")
            
    def build_prompt(self, user_message):
        """Покращений промпт з правильним відображенням конвертів"""
        
        user_data = self.get_user_data()
        
        # Детальний контекст з усіма даними
        context = f"""Ти - персональний фінансовий помічник. Відповідай українською мовою.

ДАНІ КОРИСТУВАЧА:
- Ім'я: {user_data.get('username', 'Користувач')}
- Загальний баланс: {user_data.get('total_balance', 0):.2f} грн

КАРТКИ ТА РАХУНКИ:"""
        
        cards = user_data.get('cards', [])
        if cards:
            for card in cards:
                context += f"\n  - {card['name']} ({card['bank']}): {card['balance']:.2f} грн"
        else:
            context += "\n  - Картки не додані"

        context += "\n\nКОНВЕРТИ:"
        envelopes = user_data.get('envelopes', [])
        if envelopes:
            budget_envelopes = [env for env in envelopes if env['type'] == 'бюджетний']
            regular_envelopes = [env for env in envelopes if env['type'] == 'звичайний']
            
            if budget_envelopes:
                context += "\n  📊 БЮДЖЕТНІ КОНВЕРТИ (з обмеженням):"
                for envelope in budget_envelopes:
                    context += f"\n    - {envelope['name']}: {envelope['usage_info']}"
            
            if regular_envelopes:
                context += "\n  📁 ЗВИЧАЙНІ КОНВЕРТИ (без бюджетного обмеження):"
                for envelope in regular_envelopes:
                    context += f"\n    - {envelope['name']}: {envelope['current_amount']:.2f} грн"
        else:
            context += "\n  - Конверти не створені"

        context += "\n\nПЛАНИ ЗАОЩАДЖЕНЬ:"
        savings = user_data.get('savings_plans', [])
        if savings:
            for plan in savings:
                progress = (plan['current_amount'] / plan['target_amount'] * 100) if plan['target_amount'] > 0 else 0
                context += f"\n  - {plan['name']}: {plan['current_amount']:.2f}/{plan['target_amount']:.2f} грн ({progress:.1f}%)"
        else:
            context += "\n  - Плани заощаджень не створені"

        # Аналітика
        analytics = user_data.get('analytics', {})
        context += f"\n\nАНАЛІТИКА ЗА МІСЯЦЬ:"
        context += f"\n  - Доходи: {analytics.get('total_income', 0):.2f} грн"
        context += f"\n  - Витрати: {analytics.get('total_expenses', 0):.2f} грн"
        context += f"\n  - Чистий дохід: {analytics.get('net_balance', 0):.2f} грн"
        context += f"\n  - Рівень заощаджень: {analytics.get('savings_rate', 0):.1f}%"

        # Останні транзакції
        transactions = user_data.get('recent_transactions', [])
        if transactions:
            context += "\n\nОСТАННІ ТРАНЗАКЦІЇ:"
            for trans in transactions[:3]:
                sign = '+' if trans['type'] in ['deposit', 'income', 'transfer_in'] else '-'
                context += f"\n  - {sign}{trans['amount']:.2f} грн: {trans['description']}"

        # Історія чату
        if self.conversation_history:
            context += "\n\nПОПЕРЕДНЯ РОЗМОВА:"
            for msg, resp, timestamp in self.conversation_history[-2:]:
                context += f"\nКористувач: {msg}"
                context += f"\nПомічник: {resp}"

        context += f"\n\nПОТОЧНЕ ПИТАННЯ: {user_message}"
        context += "\n\nВАЖЛИВО: Уважно розрізняй бюджетні конверти (з обмеженням) та звичайні конверти (без бюджетного обмеження)."
        context += "\nВідповідай корисними, конкретними порадами на основі наданих даних. Аналізуй фінансову ситуацію, пропонуй способи оптимізації бюджету, поради щодо заощаджень та управління конвертами."

        return context
    
    def ask(self, message):
        """Основна функція для запитів до AI"""
        try:
            # Для простих питань використовуємо локальну логіку
            simple_response = self._handle_simple_queries(message)
            if simple_response:
                self.save_message(message, simple_response)
                return simple_response
                
            # Для складних питань - Gemini
            prompt = self.build_prompt(message)
            response = self.get_ai_response(prompt)
            self.save_message(message, response)
            return response
            
        except Exception as e:
            error_msg = f"Вибач, сталася помилка: {str(e)}"
            print(f"AI Error in ask(): {e}")
            return error_msg

    def _handle_simple_queries(self, message):
        """Обробляє прості запити без використання Gemini"""
        message_lower = message.lower()
        user_data = self.get_user_data()
        total_balance = user_data.get('total_balance', 0)
        
        if any(word in message_lower for word in ['баланс', 'гроші', 'скільки грошей']):
            return f"💰 Ваш загальний баланс: {total_balance:.2f} грн"
        
        elif any(word in message_lower for word in ['привіт', 'вітаю', 'добрий день', 'hello']):
            return f"👋 Привіт, {user_data.get('username', 'друже')}! Я ваш фінансовий помічник. Чим можу допомогти?"
        
        elif any(word in message_lower for word in ['допомога', 'можливості', 'що вмієш']):
            return """📊 Я можу:
• Аналізувати ваші фінанси
• Рахувати витрати та доходи  
• Допомагати з бюджетуванням
• Консультувати щодо заощаджень
• Аналізувати конверти та плани
• Давати персоналізовані поради

Запитайте що вас цікавить!"""
        
        return None

    def get_ai_response(self, prompt):
        """Безпечна обробка відповіді від Gemini API"""
        
        if not client:
            user_data = self.get_user_data()
            total_balance = user_data.get('total_balance', 0)
            return f"🤖 Наразі AI-помічник недоступний. Ваш баланс: {total_balance:.2f} грн. Спробуйте пізніше."
        
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=800,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            if response and response.text:
                return response.text.strip()
            else:
                return "🤔 Вибач, не можу зараз відповісти на це питання. Спробуй перефразувати або запитати про щось інше."
            
        except Exception as e:
            print(f"Gemini API Error: {e}")
            return self._fallback_ai_response(prompt)

    def _fallback_ai_response(self, prompt):
        """Резервна відповідь"""
        user_data = self.get_user_data()
        total_balance = user_data.get('total_balance', 0)
        
        return f"⚠️ Наразі AI-помічник тимчасово недоступний. Ваш баланс: {total_balance:.2f} грн. Спробуйте пізніше."

    def clear_history(self):
        try:
            cursor.execute("DELETE FROM ai_chat_history WHERE user_id=?", (self.user_id,))
            conn.commit()
            self.conversation_history = []
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False
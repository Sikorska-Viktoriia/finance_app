import sqlite3
import json
from datetime import datetime
import sys
import os
import threading 
import traceback


from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv('key.env')


sys.path.append(os.path.dirname(os.path.abspath(__file__)))


try:
    from db_manager import conn, cursor, get_user_cards, get_user_envelopes, get_user_savings_plans, get_user_transactions, get_analytics_data
except ImportError:

    DB_NAME = "users.db"
    
    def get_db_connection():
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        return conn, conn.cursor()
    
    conn, cursor = get_db_connection()
    print(" Використовується заглушка БД. Перевірте імпорт db_manager.py.")


GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL_NAME = "gemini-2.0-flash"

print(f" Перевірка API ключа: {'Знайдено' if GEMINI_API_KEY else 'Не знайдено'}")

try:
    if GEMINI_API_KEY:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print(" Gemini Client успішно ініціалізовано")
    else:
        print(" GEMINI_API_KEY не знайдено в key.env")
        client = None
except Exception as e:
    print(f" Помилка ініціалізації Gemini Client: {e}")
    client = None


class AIManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.conversation_history = []
        self.load_conversation_history()

    def get_user_data(self):
 
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
                
                
                if budget_limit > 0:
                    
                    envelope_type = "бюджетний"
                    remaining = budget_limit - current_amount
                    usage_info = f"{current_amount:.2f}/{budget_limit:.2f} грн (залишилось: {remaining:.2f} грн)"
                else:
                    
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
           
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ai_chat_history'")
            if not cursor.fetchone():
                print(" Table ai_chat_history doesn't exist. Creating...")
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
 
        
        user_data = self.get_user_data()
        
      
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
                context += "\n   БЮДЖЕТНІ КОНВЕРТИ (з обмеженням):"
                for envelope in budget_envelopes:
                    context += f"\n    - {envelope['name']}: {envelope['usage_info']}"
            
            if regular_envelopes:
                context += "\n   ЗВИЧАЙНІ КОНВЕРТИ (без бюджетного обмеження):"
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

        
        analytics = user_data.get('analytics', {})
        context += f"\n\nАНАЛІТИКА ЗА МІСЯЦЬ:"
        context += f"\n  - Доходи: {analytics.get('total_income', 0):.2f} грн"
        context += f"\n  - Витрати: {analytics.get('total_expenses', 0):.2f} грн"
        context += f"\n  - Чистий дохід: {analytics.get('net_balance', 0):.2f} грн"
        context += f"\n  - Рівень заощаджень: {analytics.get('savings_rate', 0):.1f}%"

        
        transactions = user_data.get('recent_transactions', [])
        if transactions:
            context += "\n\nОСТАННІ ТРАНЗАКЦІЇ:"
            for trans in transactions[:5]: 
                sign = '+' if trans['type'] in ['deposit', 'income', 'transfer_in'] else '-'
                context += f"\n  - {sign}{trans['amount']:.2f} грн: {trans['description']}"

     
        if self.conversation_history:
            context += "\n\nПОПЕРЕДНЯ РОЗМОВА:"
            for msg, resp, timestamp in self.conversation_history[-3:]:  
                context += f"\nКористувач: {msg}"
                context += f"\nПомічник: {resp}"

        context += f"\n\nПОТОЧНЕ ПИТАННЯ: {user_message}"
        context += "\n\nВАЖЛИВО: Уважно розрізняй бюджетні конверти (з обмеженням) та звичайні конверти (без бюджетного обмеження)."
        context += "\nВідповідай корисними, конкретними порадами на основі наданих даних. Аналізуй фінансову ситуацію, пропонуй способи оптимізації бюджету, поради щодо заощаджень та управління конвертами."
        context += "\n\nДАЙ ПОВНУ ТА ДЕТАЛЬНУ ВІДПОВІДЬ. НЕ ОБРІЗАЙ ВІДПОВІДЬ НАПІВСЛОВІ."

        return context
    
    def ask(self, message):
    
        try:
         
            simple_response = self._handle_simple_queries(message)
            if simple_response:
                self.save_message(message, simple_response)
                return simple_response
                
           
            prompt = self.build_prompt(message)
            print(f" Довжина промпта: {len(prompt)} символів")
            response = self.get_ai_response(prompt)
            self.save_message(message, response)
            return response
            
        except Exception as e:
            error_msg = f"Вибач, сталася помилка: {str(e)}"
            print(f"AI Error in ask(): {e}")
            return error_msg

    def _handle_simple_queries(self, message):
    
        message_lower = message.lower()
        user_data = self.get_user_data()
        total_balance = user_data.get('total_balance', 0)
        analytics = user_data.get('analytics', {})
        
        if any(word in message_lower for word in ['баланс', 'гроші', 'скільки грошей']):
            return f" Загальний баланс: {total_balance:.2f} грн\n Доходи: {analytics.get('total_income', 0):.2f} грн\n Витрати: {analytics.get('total_expenses', 0):.2f} грн"
        
        elif any(word in message_lower for word in ['привіт', 'вітаю', 'добрий день', 'hello']):
            return f" Привіт, {user_data.get('username', 'друже')}! Я ваш фінансовий помічник. Чим можу допомогти?"
        
        elif any(word in message_lower for word in ['допомога', 'можливості', 'що вмієш']):
            return """ Я можу:
• Аналізувати ваші фінанси
• Рахувати витрати та доходи  
• Допомагати з бюджетуванням
• Консультувати щодо заощаджень
• Аналізувати конверти та плани
• Давати персоналізовані поради

Запитайте що вас цікавить!"""
        
        elif any(word in message_lower for word in ['витрати', 'трати', 'куди пішли гроші']):
            return f" Ваші витрати за місяць: {analytics.get('total_expenses', 0):.2f} грн\n Доходи: {analytics.get('total_income', 0):.2f} грн\n💰 Чистий дохід: {analytics.get('net_balance', 0):.2f} грн"
        
        return None

    def get_ai_response(self, prompt):
        """Безпечна обробка відповіді від Gemini API з більшою кількістю токенів"""
        
        if not client:
            user_data = self.get_user_data()
            total_balance = user_data.get('total_balance', 0)
            return f" Наразі AI-помічник недоступний. Ваш баланс: {total_balance:.2f} грн. Спробуйте пізніше."
        
        try:
            print(" Надсилаю запит до Gemini...")
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=9000,  
                    top_p=0.8,
                    top_k=40
                )
            )
            
            if response and response.text:
                print(f" Отримано відповідь довжиною {len(response.text)} символів")
                return response.text.strip()
            else:
                return " Вибач, не можу зараз відповісти на це питання. Спробуй перефразувати або запитати про щось інше."
            
        except Exception as e:
            print(f" Gemini API Error: {e}")
            return self._fallback_ai_response(prompt)

    def _fallback_ai_response(self, prompt):
       
        user_data = self.get_user_data()
        total_balance = user_data.get('total_balance', 0)
        analytics = user_data.get('analytics', {})
        
        return f""" AI-помічник тимчасово недоступний.

 Ваша фінансова ситуація:
• Загальний баланс: {total_balance:.2f} грн
• Доходи: {analytics.get('total_income', 0):.2f} грн  
• Витрати: {analytics.get('total_expenses', 0):.2f} грн
• Чистий дохід: {analytics.get('net_balance', 0):.2f} грн

Спробуйте пізніше або задайте конкретне питання про ваші фінанси."""

    def clear_history(self):
        try:
            cursor.execute("DELETE FROM ai_chat_history WHERE user_id=?", (self.user_id,))
            conn.commit()
            self.conversation_history = []
            return True
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False
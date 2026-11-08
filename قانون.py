import telebot
from telebot import types
import time
import sqlite3

# --- الإعدادات الأساسية ---
API_TOKEN = '8650599068:AAFouWRAm8z8XWoOgZoDI44p0fS18oOEzew'
ADMIN_ID = 8210187722
ACTIVATION_CODE = "Tz#2"

bot = telebot.TeleBot(API_TOKEN)

# --- إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    # جدول المشتركين
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, active INTEGER)''')
    # جدول الوقت (الرشق كل 24 ساعة)
    cursor.execute('''CREATE TABLE IF NOT EXISTS requests (user_id INTEGER PRIMARY KEY, last_time REAL)''')
    conn.commit()
    conn.close()

def set_user_status(user_id, status):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (user_id, active) VALUES (?, ?)', (user_id, 1 if status else 0))
    conn.commit()
    conn.close()

def get_user_status(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT active FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] == 1 if row else False

def update_request_time(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO requests (user_id, last_time) VALUES (?, ?)', (user_id, time.time()))
    conn.commit()
    conn.close()

def get_last_request(user_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT last_time FROM requests WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

# --- لوحات المفاتيح الشفافة (Inline) ---

def main_menu_inline():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🚀 رشق متابعين", callback_data="service_followers"),
        types.InlineKeyboardButton("❤️ رشق إعجابات", callback_data="service_likes"),
        types.InlineKeyboardButton("👁️ رشق مشاهدات", callback_data="service_views"),
        types.InlineKeyboardButton("👤 حسابي", callback_data="my_profile")
    )
    return markup

def admin_panel_inline():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ تفعيل عضو", callback_data="admin_add"),
        types.InlineKeyboardButton("➖ إلغاء تفعيل", callback_data="admin_rem"),
        types.InlineKeyboardButton("📊 إحصائيات القاعدة", callback_data="admin_stats")
    )
    return markup

# --- معالجة الأوامر ---

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    init_db()

    if user_id == ADMIN_ID:
        bot.send_message(user_id, "💎 أهلاً بك يا سيدي الآدمن في لوحة التحكم الخاصة بك:", reply_markup=admin_panel_inline())
        return

    if not get_user_status(user_id):
        bot.send_message(user_id, "⚠️ هذا البوت مدفوع. يرجى إرسال كود التفعيل:")
        bot.register_next_step_handler(message, process_activation)
    else:
        bot.send_message(user_id, "🌟 خدمات الرشق جاهزة، اختر من القائمة الشفافة:", reply_markup=main_menu_inline())

def process_activation(message):
    if message.text == ACTIVATION_CODE:
        set_user_status(message.from_user.id, True)
        bot.send_message(message.chat.id, "✅ تم التفعيل بنجاح! تم حفظ حسابك في قاعدة البيانات.", reply_markup=main_menu_inline())
    else:
        bot.send_message(message.chat.id, "❌ كود خاطئ.")

# --- معالجة الضغط على الأزرار الشفافة ---

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    # خدمات العضو
    if call.data.startswith("service_"):
        if not get_user_status(user_id) and user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "🚫 غير مشترك", show_alert=True)
            return

        last_time = get_last_request(user_id)
        if time.time() - last_time < 86400:
            remaining = int((86400 - (time.time() - last_time)) / 3600)
            bot.answer_callback_query(call.id, f"⏳ متبقي {remaining} ساعة للرشق القادم", show_alert=True)
            return

        msg = bot.send_message(call.message.chat.id, "🔗 أرسل الآن اليوزر (User) أو الرابط المطلوب:")
        bot.register_next_step_handler(msg, complete_order)

    elif call.data == "my_profile":
        status = "مفعل ✅

import telebot
from telebot import types
import requests
import time
import os

TOKEN = os.environ.get("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

API_URL = "https://script.google.com/macros/s/AKfycbxaueWV_fKu2NtI1xqJ_L2HJgE7NkISl4bTFlBNiFfzuyA19vFKCt9nvxZheT8ZZXaleg/exec"

# =========================
# КНОПКИ
# =========================

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("🔔 Включить рассылку", "🔕 Выключить рассылку")
    markup.row("🔎 Закупки", "📦 Товародвижение")
    markup.row("📊 Аналитик", "🗂 Категорийный менеджер")
    markup.row("🔥 Лучшие сегодня", "🏠 Только удаленка")
    markup.row("💰 Зарплата 150k+", "⭐ Избранное")

    return markup

# =========================
# СТАРТ
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет 👋\n\nЯ карьерный ассистент Татьяны.",
        reply_markup=main_keyboard()
    )

# =========================
# ВКЛЮЧИТЬ РАССЫЛКУ
# =========================

@bot.message_handler(func=lambda message: message.text == "🔔 Включить рассылку")
def enable_subscription(message):

    try:
        response = requests.get(
            API_URL,
            params={
                "action": "add",
                "chat_id": message.chat.id
            },
            timeout=10
        )

        text = response.text.strip()

        if text == "already_exists":
            bot.send_message(
                message.chat.id,
                "⚠️ Рассылка уже включена."
            )
        else:
            bot.send_message(
                message.chat.id,
                "🔔 Рассылка включена.\n\nКаждый день в 10:00 буду присылать вакансии."
            )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Ошибка подключения:\n{e}"
        )

# =========================
# ВЫКЛЮЧИТЬ РАССЫЛКУ
# =========================

@bot.message_handler(func=lambda message: message.text == "🔕 Выключить рассылку")
def disable_subscription(message):

    try:
        requests.get(
            API_URL,
            params={
                "action": "remove",
                "chat_id": message.chat.id
            },
            timeout=10
        )

        bot.send_message(
            message.chat.id,
            "🔕 Рассылка выключена."
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"Ошибка подключения:\n{e}"
        )

# =========================
# ПРОЧИЕ КНОПКИ
# =========================

@bot.message_handler(func=lambda message: True)
def buttons(message):

    text = message.text

    if text == "🔎 Закупки":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

    elif text == "📦 Товародвижение":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

    elif text == "📊 Аналитик":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

    elif text == "🗂 Категорийный менеджер":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

    elif text == "🔥 Лучшие сегодня":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

    elif text == "🏠 Только удаленка":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

    elif text == "💰 Зарплата 150k+":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

    elif text == "⭐ Избранное":
        bot.send_message(message.chat.id, "Пока раздел в разработке.")

# =========================
# ЗАПУСК
# =========================

while True:
    try:
        print("BOT STARTED")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)

    except Exception as e:
        print(f"ERROR: {e}")
        time.sleep(5)

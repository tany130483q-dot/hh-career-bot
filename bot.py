import telebot
from telebot import types
import requests
import json
import time
import threading

TOKEN = "8878670055:AAFzmS9p8yfP1NZA7pxhTe-bpZjcGUQkp88"

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwf3UPzjUZIzLsn64wluSEMBp3uRA91sIEWwz6104WzSKRSy5OajIBuDLTb3hGB21Ui/exec"

bot = telebot.TeleBot(TOKEN)

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
# ПОДПИСКА
# =========================

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет 👋\nЯ карьерный ассистент Татьяны.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda m: m.text == "🔔 Включить рассылку")
def subscribe(message):
    chat_id = message.chat.id

    try:
        requests.get(
            SCRIPT_URL,
            params={
                "action": "add",
                "chat_id": chat_id
            },
            timeout=10
        )

        bot.send_message(
            chat_id,
            "🔔 Рассылка включена.\n\nКаждый день в 10:00 по Москве буду присылать вакансии."
        )

    except Exception as e:
        bot.send_message(chat_id, f"Ошибка подписки:\n{e}")


@bot.message_handler(func=lambda m: m.text == "🔕 Выключить рассылку")
def unsubscribe(message):
    chat_id = message.chat.id

    try:
        requests.get(
            SCRIPT_URL,
            params={
                "action": "remove",
                "chat_id": chat_id
            },
            timeout=10
        )

        bot.send_message(chat_id, "🔕 Рассылка выключена.")

    except Exception as e:
        bot.send_message(chat_id, f"Ошибка отписки:\n{e}")


# =========================
# КНОПКИ ФИЛЬТРОВ
# =========================

@bot.message_handler(func=lambda m: True)
def buttons(message):
    text = message.text

    responses = {
        "🔎 Закупки": "Показываю вакансии по закупкам.",
        "📦 Товародвижение": "Показываю вакансии по товародвижению.",
        "📊 Аналитик": "Показываю вакансии аналитика.",
        "🗂 Категорийный менеджер": "Показываю вакансии категорийного менеджера.",
        "🔥 Лучшие сегодня": "Показываю лучшие вакансии за сегодня.",
        "🏠 Только удаленка": "Показываю только удаленные вакансии.",
        "💰 Зарплата 150k+": "Показываю вакансии с зарплатой 150k+.",
        "⭐ Избранное": "Тут будут избранные вакансии."
    }

    if text in responses:
        bot.send_message(message.chat.id, responses[text])


# =========================
# РАССЫЛКА
# =========================

def mailing_loop():
    while True:
        try:
            now = time.localtime()

            # 10:00 по Москве
            if now.tm_hour == 10 and now.tm_min == 0:

                response = requests.get(
                    SCRIPT_URL,
                    params={"action": "list"},
                    timeout=10
                )

                subscribers = response.json()

                for chat_id in subscribers:
                    try:
                        bot.send_message(
                            chat_id,
                            "🔥 Новые вакансии уже ждут тебя!"
                        )

                    except:
                        pass

                time.sleep(60)

            time.sleep(20)

        except Exception as e:
            print("Ошибка рассылки:", e)
            time.sleep(30)


# =========================
# ЗАПУСК
# =========================

threading.Thread(target=mailing_loop).start()

print("Бот запущен")

bot.infinity_polling()

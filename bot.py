import os
import telebot
from telebot import types
from urllib.parse import quote


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь Environment Variables в Render.")

bot = telebot.TeleBot(TOKEN)


def make_hh_link(query):
    encoded_query = quote(query)

    return (
        "https://spb.hh.ru/search/vacancy"
        f"?text={encoded_query}"
        "&salary=100000"
        "&only_with_salary=true"
        "&from=suggest_post"
    )


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "🏠 Удаленка")
    keyboard.row("❓ Помощь")

    return keyboard


def send_hh_search(message, query):
    link = make_hh_link(query)

    text = (
        f"🔍 Поиск вакансий: {query}\n\n"
        f"📍 Регион: Санкт-Петербург / удаленно\n"
        f"💰 Зарплата: от 100 000 ₽\n\n"
        f"🔗 {link}"
    )

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Я карьерный ассистент для поиска вакансий на HH.\n\n"
        "Выбери направление кнопкой ниже 👇",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Команды:\n\n"
        "/start — открыть меню\n"
        "/search текст вакансии — ручной поиск\n\n"
        "Также можно пользоваться кнопками ниже.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["search"])
def search(message):
    query = message.text.replace("/search", "").strip()

    if not query:
        bot.send_message(
            message.chat.id,
            "Напиши запрос после команды.\n\n"
            "Пример:\n"
            "/search менеджер по закупкам",
            reply_markup=main_keyboard()
        )
        return

    send_hh_search(message, query)


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def button_purchases(message):
    send_hh_search(message, "менеджер по закупкам")


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def button_goods_movement(message):
    send_hh_search(message, "менеджер по товародвижению")


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def button_analyst(message):
    send_hh_search(message, "аналитик")


@bot.message_handler(func=lambda message: message.text == "🏠 Удаленка")
def button_remote(message):
    send_hh_search(message, "удаленная работа менеджер")


@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def button_help(message):
    help_command(message)


@bot.message_handler(func=lambda message: True)
def unknown_message(message):
    bot.send_message(
        message.chat.id,
        "Я пока понимаю команды и кнопки.\n\n"
        "Нажми кнопку ниже или напиши:\n"
        "/search менеджер по закупкам",
        reply_markup=main_keyboard()
    )


bot.infinity_polling(timeout=60, long_polling_timeout=60)

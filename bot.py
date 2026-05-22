import os
import telebot
from telebot import types
from urllib.parse import quote


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN в Render Environment Variables")

bot = telebot.TeleBot(TOKEN)


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "🏠 Удаленка")
    keyboard.row("🔥 Лучшие сегодня", "🚫 Без продаж")
    keyboard.row("❓ Помощь")

    return keyboard


def make_hh_link(query, salary=100000, remote=False):
    encoded_query = quote(query)

    link = (
        "https://spb.hh.ru/search/vacancy"
        f"?text={encoded_query}"
        f"&salary={salary}"
        "&only_with_salary=true"
        "&search_field=name"
        "&search_field=company_name"
        "&search_field=description"
    )

    if remote:
        link += "&schedule=remote"

    return link


def send_search_link(message, title, query, salary=100000, remote=False):
    link = make_hh_link(query, salary=salary, remote=remote)

    text = (
        f"{title}\n\n"
        f"🔍 Запрос: {query}\n"
        f"💰 Зарплата: от {salary} ₽\n"
    )

    if remote:
        text += "🏠 Формат: удаленно\n"

    text += f"\n🔗 {link}"

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard()
    )


def send_best_today(message):
    text = (
        "🔥 Лучшие направления на сегодня:\n\n"
        "1️⃣ Закупки\n"
        f"{make_hh_link('менеджер по закупкам')}\n\n"
        "2️⃣ Товародвижение\n"
        f"{make_hh_link('менеджер по товародвижению')}\n\n"
        "3️⃣ Аналитик\n"
        f"{make_hh_link('аналитик')}\n\n"
        "4️⃣ Координатор\n"
        f"{make_hh_link('координатор')}\n\n"
        "5️⃣ Удаленная работа\n"
        f"{make_hh_link('удаленная работа менеджер', remote=True)}"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard()
    )


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
        "Кнопки:\n"
        "🔎 Закупки — вакансии по закупкам\n"
        "📦 Товародвижение — товародвижение и товарные процессы\n"
        "📊 Аналитик — аналитические вакансии\n"
        "🏠 Удаленка — удаленные вакансии\n"
        "🔥 Лучшие сегодня — подборка направлений\n"
        "🚫 Без продаж — поиск без активных продаж",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["search"])
def manual_search(message):
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

    send_search_link(
        message,
        "🔎 Ручной поиск HH",
        query
    )


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_search_link(
        message,
        "🔎 Закупки",
        "менеджер по закупкам"
    )


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_search_link(
        message,
        "📦 Товародвижение",
        "менеджер по товародвижению"
    )


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_search_link(
        message,
        "📊 Аналитик",
        "аналитик"
    )


@bot.message_handler(func=lambda message: message.text == "🏠 Удаленка")
def remote(message):
    send_search_link(
        message,
        "🏠 Удаленная работа",
        "удаленная работа менеджер",
        remote=True
    )


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_best_today(message)


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_search_link(
        message,
        "🚫 Поиск без активных продаж",
        "менеджер координатор аналитик -продажи -холодные -звонки -клиенты"
    )


@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_button(message):
    help_command(message)


@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(
        message.chat.id,
        "Я понимаю команды и кнопки.\n\n"
        "Нажми кнопку ниже или напиши:\n"
        "/search менеджер по закупкам",
        reply_markup=main_keyboard()
    )


bot.infinity_polling(timeout=60, long_polling_timeout=60)

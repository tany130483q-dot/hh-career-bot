import os
import telebot
from telebot import types
from urllib.parse import quote


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "🔥 Лучшие сегодня")
    keyboard.row("🚫 Без продаж", "❓ Помощь")

    return keyboard


def make_hh_link(query, salary=100000, mode="remote"):
    encoded_query = quote(query)

    if mode == "remote":
        return (
            "https://hh.ru/search/vacancy"
            f"?text={encoded_query}"
            "&area=113"
            f"&salary={salary}"
            "&only_with_salary=true"
            "&work_schedule_by_days=FIVE_ON_TWO_OFF"
            "&work_format=REMOTE"
            "&search_field=name"
            "&search_field=company_name"
            "&search_field=description"
        )

    if mode == "hybrid_spb":
        return (
            "https://spb.hh.ru/search/vacancy"
            f"?text={encoded_query}"
            "&area=2"
            f"&salary={salary}"
            "&only_with_salary=true"
            "&work_schedule_by_days=FIVE_ON_TWO_OFF"
            "&work_format=HYBRID"
            "&search_field=name"
            "&search_field=company_name"
            "&search_field=description"
        )

    return ""


def search_buttons(query):
    keyboard = types.InlineKeyboardMarkup()

    remote_link = make_hh_link(query, mode="remote")
    hybrid_link = make_hh_link(query, mode="hybrid_spb")

    keyboard.add(
        types.InlineKeyboardButton(
            "🏠 Открыть удаленные вакансии",
            url=remote_link
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "🏢 Открыть гибрид СПб",
            url=hybrid_link
        )
    )

    return keyboard


def send_search_card(message, title, query, salary=100000):
    text = (
        f"{title}\n\n"
        f"🔍 Запрос: {query}\n"
        f"💰 Зарплата: от {salary} ₽\n"
        f"📅 График: только 5/2\n\n"
        f"Показываю только подходящие форматы:\n"
        f"🏠 удаленка — все города\n"
        f"🏢 гибрид — Санкт-Петербург\n\n"
        f"❌ Офисные вакансии «на месте работодателя» исключаем."
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=search_buttons(query)
    )


def send_best_today(message):
    directions = [
        ("🔎 Закупки", "менеджер по закупкам"),
        ("📦 Товародвижение", "менеджер по товародвижению"),
        ("📊 Аналитик", "аналитик"),
    ]

    bot.send_message(
        message.chat.id,
        "🔥 Лучшие направления на сегодня\n\n"
        "Каждая карточка содержит только:\n"
        "🏠 удаленку по всем городам\n"
        "🏢 гибрид по Санкт-Петербургу\n"
        "📅 график 5/2",
        reply_markup=main_keyboard()
    )

    for title, query in directions:
        send_search_card(message, title, query)


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Я карьерный ассистент для поиска вакансий на HH.\n\n"
        "Ищу только:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 график — только 5/2\n\n"
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
        "🔎 Закупки\n"
        "📦 Товародвижение\n"
        "📊 Аналитик\n"
        "🔥 Лучшие сегодня\n"
        "🚫 Без продаж\n\n"
        "Во всех вариантах бот показывает только удаленку или гибрид СПб.",
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

    send_search_card(
        message,
        "🔎 Ручной поиск HH",
        query
    )


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_search_card(
        message,
        "🔎 Закупки",
        "менеджер по закупкам"
    )


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_search_card(
        message,
        "📦 Товародвижение",
        "менеджер по товародвижению"
    )


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_search_card(
        message,
        "📊 Аналитик",
        "аналитик"
    )


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_best_today(message)


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_search_card(
        message,
        "🚫 Поиск без активных продаж",
        "менеджер аналитик -продажи -холодные -звонки -клиенты"
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

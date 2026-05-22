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


def send_two_search_links(message, title, query, salary=100000):
    remote_link = make_hh_link(query, salary=salary, mode="remote")
    hybrid_link = make_hh_link(query, salary=salary, mode="hybrid_spb")

    text = (
        f"{title}\n\n"
        f"🔍 Запрос: {query}\n"
        f"💰 Зарплата: от {salary} ₽\n"
        f"📅 График: только 5/2\n\n"
        f"Показываю только подходящие форматы:\n\n"
        f"🏠 Удаленка — все города\n"
        f"{remote_link}\n\n"
        f"🏢 Гибрид — только Санкт-Петербург\n"
        f"{hybrid_link}\n\n"
        f"❌ Вакансии «на месте работодателя» исключаем."
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard()
    )


def send_best_today(message):
    text = (
        "🔥 Лучшие направления на сегодня\n\n"
        "Везде используются только:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 график — только 5/2\n\n"

        "1️⃣ Закупки\n"
        f"🏠 {make_hh_link('менеджер по закупкам', mode='remote')}\n"
        f"🏢 {make_hh_link('менеджер по закупкам', mode='hybrid_spb')}\n\n"

        "2️⃣ Товародвижение\n"
        f"🏠 {make_hh_link('менеджер по товародвижению', mode='remote')}\n"
        f"🏢 {make_hh_link('менеджер по товародвижению', mode='hybrid_spb')}\n\n"

        "3️⃣ Аналитик\n"
        f"🏠 {make_hh_link('аналитик', mode='remote')}\n"
        f"🏢 {make_hh_link('аналитик', mode='hybrid_spb')}"
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
        "Ищу только два формата:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — только Санкт-Петербург\n"
        "📅 график — только 5/2\n\n"
        "Вакансии «на месте работодателя» исключаем.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Команды:\n\n"
        "/start — открыть меню\n"
        "/search текст вакансии — ручной поиск\n\n"
        "Важно:\n"
        "Любой поиск дает только 2 варианта:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 график — только 5/2\n\n"
        "Обычные офисные вакансии не используем.",
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

    send_two_search_links(
        message,
        "🔎 Ручной поиск HH",
        query
    )


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_two_search_links(
        message,
        "🔎 Закупки",
        "менеджер по закупкам"
    )


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_two_search_links(
        message,
        "📦 Товародвижение",
        "менеджер по товародвижению"
    )


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_two_search_links(
        message,
        "📊 Аналитик",
        "аналитик"
    )


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_best_today(message)


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_two_search_links(
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

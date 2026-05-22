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
    keyboard.row("📊 Аналитик", "🏠 Удаленка")
    keyboard.row("🏢 Гибрид СПб", "🔥 Лучшие сегодня")
    keyboard.row("🚫 Без продаж", "❓ Помощь")

    return keyboard


def make_hh_link(query, salary=100000, mode="spb"):
    encoded_query = quote(query)

    if mode == "remote":
        base_url = "https://hh.ru/search/vacancy"
        area = "113"          # вся Россия
        schedule = "remote"   # удаленка

    elif mode == "hybrid":
        base_url = "https://spb.hh.ru/search/vacancy"
        area = "2"            # Санкт-Петербург
        schedule = "flexible" # гибкий / гибридный формат

    else:
        base_url = "https://spb.hh.ru/search/vacancy"
        area = "2"
        schedule = ""

    link = (
        f"{base_url}"
        f"?text={encoded_query}"
        f"&area={area}"
        f"&salary={salary}"
        "&only_with_salary=true"
        "&search_field=name"
        "&search_field=company_name"
        "&search_field=description"
    )

    if schedule:
        link += f"&schedule={schedule}"

    return link


def send_search_link(message, title, query, salary=100000, mode="spb"):
    link = make_hh_link(query, salary=salary, mode=mode)

    if mode == "remote":
        region_text = "все города / удаленно"
    elif mode == "hybrid":
        region_text = "Санкт-Петербург / гибрид"
    else:
        region_text = "Санкт-Петербург"

    text = (
        f"{title}\n\n"
        f"🔍 Запрос: {query}\n"
        f"📍 Регион: {region_text}\n"
        f"💰 Зарплата: от {salary} ₽\n\n"
        f"🔗 {link}"
    )

    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())


def send_best_today(message):
    text = (
        "🔥 Лучшие направления на сегодня:\n\n"
        "1️⃣ Закупки — СПб\n"
        f"{make_hh_link('менеджер по закупкам', mode='spb')}\n\n"
        "2️⃣ Товародвижение — СПб\n"
        f"{make_hh_link('менеджер по товародвижению', mode='spb')}\n\n"
        "3️⃣ Аналитик — СПб\n"
        f"{make_hh_link('аналитик', mode='spb')}\n\n"
        "4️⃣ Удаленка — все города\n"
        f"{make_hh_link('менеджер координатор аналитик', mode='remote')}\n\n"
        "5️⃣ Гибрид — только Санкт-Петербург\n"
        f"{make_hh_link('менеджер координатор аналитик', mode='hybrid')}"
    )

    bot.send_message(message.chat.id, text, reply_markup=main_keyboard())


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Я карьерный ассистент для поиска вакансий на HH.\n\n"
        "Логика поиска:\n"
        "🏠 Удаленка — все города\n"
        "🏢 Гибрид — только Санкт-Петербург\n\n"
        "Выбери направление кнопкой ниже 👇",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Команды:\n\n"
        "/start — открыть меню\n"
        "/search текст вакансии — ручной поиск по СПб\n\n"
        "Кнопки:\n"
        "🔎 Закупки — СПб\n"
        "📦 Товародвижение — СПб\n"
        "📊 Аналитик — СПб\n"
        "🏠 Удаленка — все города\n"
        "🏢 Гибрид СПб — только Санкт-Петербург\n"
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
        query,
        mode="spb"
    )


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_search_link(
        message,
        "🔎 Закупки",
        "менеджер по закупкам",
        mode="spb"
    )


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_search_link(
        message,
        "📦 Товародвижение",
        "менеджер по товародвижению",
        mode="spb"
    )


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_search_link(
        message,
        "📊 Аналитик",
        "аналитик",
        mode="spb"
    )


@bot.message_handler(func=lambda message: message.text == "🏠 Удаленка")
def remote(message):
    send_search_link(
        message,
        "🏠 Удаленка — все города",
        "менеджер координатор аналитик",
        mode="remote"
    )


@bot.message_handler(func=lambda message: message.text == "🏢 Гибрид СПб")
def hybrid_spb(message):
    send_search_link(
        message,
        "🏢 Гибрид — Санкт-Петербург",
        "менеджер координатор аналитик",
        mode="hybrid"
    )


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_best_today(message)


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_search_link(
        message,
        "🚫 Поиск без активных продаж",
        "менеджер координатор аналитик -продажи -холодные -звонки -клиенты",
        mode="spb"
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

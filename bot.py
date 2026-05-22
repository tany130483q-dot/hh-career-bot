import os
import requests
import telebot
from telebot import types
from urllib.parse import quote


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN в Render Environment Variables")

bot = telebot.TeleBot(TOKEN)

HH_API_URL = "https://api.hh.ru/vacancies"


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "🏠 Удаленка")
    keyboard.row("❓ Помощь")
    return keyboard


def make_hh_link(query):
    return (
        "https://spb.hh.ru/search/vacancy"
        f"?text={quote(query)}"
        "&salary=100000"
        "&only_with_salary=true"
    )


def format_salary(salary):
    if not salary:
        return "зарплата не указана"

    salary_from = salary.get("from")
    salary_to = salary.get("to")
    currency = salary.get("currency", "RUR")

    if currency == "RUR":
        currency = "₽"

    if salary_from and salary_to:
        return f"{salary_from}–{salary_to} {currency}"
    if salary_from:
        return f"от {salary_from} {currency}"
    if salary_to:
        return f"до {salary_to} {currency}"

    return "зарплата не указана"


def get_real_vacancies(query):
    params = {
        "text": query,
        "per_page": 5,
        "page": 0,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CareerAssistantBot/1.0; +https://t.me)",
        "Accept": "application/json",
    }

    response = requests.get(
        HH_API_URL,
        params=params,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()
    return response.json().get("items", [])


def format_vacancy(vacancy):
    name = vacancy.get("name", "Без названия")
    company = vacancy.get("employer", {}).get("name", "Компания не указана")
    city = vacancy.get("area", {}).get("name", "Город не указан")
    url = vacancy.get("alternate_url", "")
    salary = format_salary(vacancy.get("salary"))

    return (
        f"📌 {name}\n"
        f"🏢 {company}\n"
        f"📍 {city}\n"
        f"💰 {salary}\n"
        f"🔗 {url}"
    )


def send_vacancies(message, query):
    bot.send_message(message.chat.id, f"Ищу реальные вакансии: {query}")

    try:
        vacancies = get_real_vacancies(query)

        if not vacancies:
            bot.send_message(
                message.chat.id,
                "Вакансии не найдены. Попробуй другой запрос.",
                reply_markup=main_keyboard()
            )
            return

        for vacancy in vacancies:
            bot.send_message(message.chat.id, format_vacancy(vacancy))

    except Exception:
        link = make_hh_link(query)

        bot.send_message(
            message.chat.id,
            "HH API сейчас не отдает вакансии напрямую.\n"
            "Даю рабочую ссылку на поиск HH:\n\n"
            f"🔗 {link}",
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
        "Или нажми кнопку ниже.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["search"])
def search(message):
    query = message.text.replace("/search", "").strip()

    if not query:
        bot.send_message(
            message.chat.id,
            "Напиши запрос после команды.\n\n"
            "Пример:\n/search менеджер по закупкам",
            reply_markup=main_keyboard()
        )
        return

    send_vacancies(message, query)


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_vacancies(message, "менеджер по закупкам")


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_vacancies(message, "менеджер по товародвижению")


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_vacancies(message, "аналитик")


@bot.message_handler(func=lambda message: message.text == "🏠 Удаленка")
def remote(message):
    send_vacancies(message, "удаленная работа менеджер")


@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_button(message):
    help_command(message)


@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(
        message.chat.id,
        "Нажми кнопку ниже или напиши:\n/search менеджер по закупкам",
        reply_markup=main_keyboard()
    )


bot.infinity_polling(timeout=60, long_polling_timeout=60)

import os
import requests
import telebot


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь Environment Variables в Render.")

bot = telebot.TeleBot(TOKEN)

HH_API_URL = "https://api.hh.ru/vacancies"


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


def search_hh_vacancies(query):
   params = {
    "text": query,
    "per_page": 5,
    "page": 0,
}

    headers = {
        "User-Agent": "HH-Career-Bot/1.0 (tany.130483q@gmail.com)",
        "Accept": "application/json",
    }

    response = requests.get(
        HH_API_URL,
        params=params,
        headers=headers,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()
    return data.get("items", [])


def format_vacancy(vacancy):
    name = vacancy.get("name", "Без названия")
    company = vacancy.get("employer", {}).get("name", "Компания не указана")
    city = vacancy.get("area", {}).get("name", "Город не указан")
    url = vacancy.get("alternate_url", "")
    salary = format_salary(vacancy.get("salary"))

    return (
        f"💼 {name}\n"
        f"🏢 {company}\n"
        f"📍 {city}\n"
        f"💰 {salary}\n"
        f"🔗 {url}"
    )


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Бот работает ✅\n\n"
        "Я умею искать вакансии на HH.\n\n"
        "Напиши команду так:\n"
        "/search менеджер по закупкам"
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.reply_to(
        message,
        "Команды:\n\n"
        "/start — запуск\n"
        "/help — помощь\n"
        "/search текст вакансии — поиск вакансий HH\n\n"
        "Пример:\n"
        "/search координатор"
    )


@bot.message_handler(commands=["search"])
def search(message):
    query = message.text.replace("/search", "").strip()

    if not query:
        bot.reply_to(
            message,
            "Напиши запрос после команды.\n\n"
            "Пример:\n"
            "/search менеджер по закупкам"
        )
        return

    bot.reply_to(message, f"Ищу вакансии: {query}")

    try:
        vacancies = search_hh_vacancies(query)

        if not vacancies:
            bot.send_message(
                message.chat.id,
                "Вакансии не найдены. Попробуй другой запрос."
            )
            return

        for vacancy in vacancies:
            bot.send_message(
                message.chat.id,
                format_vacancy(vacancy)
            )

    except requests.exceptions.HTTPError as error:
        bot.send_message(
            message.chat.id,
            f"Ошибка HH API: {error}\n\n"
            "Скорее всего HH временно заблокировал запрос. "
            "Попробуем исправить фильтры или User-Agent."
        )

    except Exception as error:
        bot.send_message(
            message.chat.id,
            f"Ошибка при поиске вакансий: {error}"
        )


@bot.message_handler(func=lambda message: True)
def unknown_message(message):
    bot.reply_to(
        message,
        "Я пока понимаю только команды:\n"
        "/start\n"
        "/help\n"
        "/search менеджер по закупкам"
    )


bot.infinity_polling(timeout=60, long_polling_timeout=60)

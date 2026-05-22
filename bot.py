import os
import requests
import telebot
from urllib.parse import quote


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN. Проверь Environment Variables в Render.")

bot = telebot.TeleBot(TOKEN)


def search_hh_vacancies(query):
    """
    Поиск через публичную страницу HH.
    Это временный рабочий вариант, если api.hh.ru возвращает 403.
    """

    search_url = (
        "https://spb.hh.ru/search/vacancy"
        f"?text={quote(query)}"
        "&salary=100000"
        "&only_with_salary=true"
        "&from=suggest_post"
    )

    return [
        {
            "name": f"Открыть поиск HH: {query}",
            "company": "HeadHunter",
            "city": "Санкт-Петербург / удаленно",
            "salary": "от 100 000 ₽",
            "url": search_url,
        }
    ]


def format_vacancy(vacancy):
    return (
        f"💼 {vacancy['name']}\n"
        f"🏢 {vacancy['company']}\n"
        f"📍 {vacancy['city']}\n"
        f"💰 {vacancy['salary']}\n"
        f"🔗 {vacancy['url']}"
    )


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "Бот работает ✅\n\n"
        "Я ищу вакансии на HH.\n\n"
        "Команда:\n"
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

    vacancies = search_hh_vacancies(query)

    for vacancy in vacancies:
        bot.send_message(message.chat.id, format_vacancy(vacancy))


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

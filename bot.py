import os
import requests
import telebot
from bs4 import BeautifulSoup
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
        )

    return ""


def get_vacancies_from_hh(query, mode="remote", limit=5):
    url = make_hh_link(query, mode=mode)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    cards = soup.select("[data-qa='vacancy-serp__vacancy']")

    vacancies = []

    for card in cards[:limit]:
        title_tag = card.select_one("[data-qa='serp-item__title']")
        company_tag = card.select_one("[data-qa='vacancy-serp__vacancy-employer']")
        salary_tag = card.select_one("[data-qa='vacancy-serp__vacancy-compensation']")
        address_tag = card.select_one("[data-qa='vacancy-serp__vacancy-address']")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        link = title_tag.get("href", "")

        company = company_tag.get_text(strip=True) if company_tag else "Компания не указана"
        salary = salary_tag.get_text(strip=True) if salary_tag else "Зарплата не указана"
        address = address_tag.get_text(strip=True) if address_tag else "Город не указан"

        vacancies.append(
            {
                "title": title,
                "company": company,
                "salary": salary,
                "address": address,
                "link": link,
            }
        )

    return vacancies


def send_vacancy_card(chat_id, vacancy):
    text = (
        f"📌 {vacancy['title']}\n\n"
        f"🏢 {vacancy['company']}\n"
        f"💰 {vacancy['salary']}\n"
        f"📍 {vacancy['address']}\n\n"
        f"🔗 {vacancy['link']}"
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "Открыть вакансию",
            url=vacancy["link"]
        )
    )

    bot.send_message(chat_id, text, reply_markup=keyboard)


def send_fallback_links(message, title, query):
    remote_link = make_hh_link(query, mode="remote")
    hybrid_link = make_hh_link(query, mode="hybrid_spb")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Открыть удалённые вакансии", url=remote_link))
    keyboard.add(types.InlineKeyboardButton("🏢 Открыть гибрид СПб", url=hybrid_link))

    text = (
        f"{title}\n\n"
        f"Не смогла получить карточки автоматически.\n"
        f"Открывай поиск вручную через кнопки ниже.\n\n"
        f"Фильтры сохранены:\n"
        f"🏠 удаленка — все города\n"
        f"🏢 гибрид — Санкт-Петербург\n"
        f"📅 график — только 5/2\n"
        f"💰 зарплата — от 100 000 ₽"
    )

    bot.send_message(message.chat.id, text, reply_markup=keyboard)


def send_real_vacancies(message, title, query):
    bot.send_message(
        message.chat.id,
        f"{title}\n\nИщу реальные вакансии...",
        reply_markup=main_keyboard()
    )

    found_any = False

    search_modes = [
        ("🏠 Удаленка — все города", "remote"),
        ("🏢 Гибрид — Санкт-Петербург", "hybrid_spb"),
    ]

    for mode_title, mode in search_modes:
        bot.send_message(message.chat.id, mode_title)

        try:
            vacancies = get_vacancies_from_hh(query, mode=mode, limit=3)

            if not vacancies:
                continue

            found_any = True

            for vacancy in vacancies:
                send_vacancy_card(message.chat.id, vacancy)

        except Exception:
            continue

    if not found_any:
        send_fallback_links(message, title, query)


def send_best_today(message):
    directions = [
        ("🔎 Закупки", "менеджер по закупкам"),
        ("📦 Товародвижение", "менеджер по товародвижению"),
        ("📊 Аналитик", "аналитик"),
    ]

    bot.send_message(
        message.chat.id,
        "🔥 Лучшие направления на сегодня\n\n"
        "Покажу карточки по каждому направлению.\n\n"
        "Фильтры:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 график — только 5/2\n"
        "💰 зарплата — от 100 000 ₽",
        reply_markup=main_keyboard()
    )

    for title, query in directions:
        send_real_vacancies(message, title, query)


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Я карьерный ассистент для поиска вакансий на HH.\n\n"
        "Ищу карточки вакансий по фильтрам:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 график — только 5/2\n"
        "💰 зарплата — от 100 000 ₽\n\n"
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
        "Если HH не отдаст карточки автоматически, бот даст рабочие ссылки.",
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

    send_real_vacancies(message, "🔎 Ручной поиск", query)


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_real_vacancies(
        message,
        "🔎 Закупки",
        "менеджер по закупкам"
    )


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_real_vacancies(
        message,
        "📦 Товародвижение",
        "менеджер по товародвижению"
    )


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_real_vacancies(
        message,
        "📊 Аналитик",
        "аналитик"
    )


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_best_today(message)


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_real_vacancies(
        message,
        "🚫 Без продаж",
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

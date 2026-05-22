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
        "User-Agent": "Mozilla/5.0",
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

        vacancies.append({
            "title": title,
            "company": company,
            "salary": salary,
            "address": address,
            "link": link,
        })

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
    keyboard.add(types.InlineKeyboardButton("Открыть вакансию", url=vacancy["link"]))

    bot.send_message(chat_id, text, reply_markup=keyboard)


def send_real_vacancies(message, title, query):
    bot.send_message(message.chat.id, f"{title}\n\nИщу реальные вакансии...")

    for mode_name, mode in [
        ("🏠 Удаленка — все города", "remote"),
        ("🏢 Гибрид — Санкт-Петербург", "hybrid_spb"),
    ]:
        bot.send_message(message.chat.id, mode_name)

        try:
            vacancies = get_vacancies_from_hh(query, mode=mode, limit=3)

            if not vacancies:
                link = make_hh_link(query, mode=mode)
                bot.send_message(
                    message.chat.id,
                    f"Не смог найти карточки автоматически.\nОткрой поиск вручную:\n{link}"
                )
                continue

            for vacancy in vacancies:
                send_vacancy_card(message.chat.id, vacancy)

        except Exception as error:
            link = make_hh_link(query, mode=mode)
            bot.send_message(
                message.chat.id,
                f"Не смог получить карточки HH.\nОткрой поиск вручную:\n{link}"
            )


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Ищу вакансии HH карточками.\n\n"
        "Фильтры:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 график — только 5/2",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["search"])
def manual_search(message):
    query = message.text.replace("/search", "").strip()

    if not query:
        bot.send_message(message.chat.id, "Пример:\n/search менеджер по закупкам")
        return

    send_real_vacancies(message, "🔎 Ручной поиск", query)


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_real_vacancies(message, "🔎 Закупки", "менеджер по закупкам")


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_real_vacancies(message, "📦 Товародвижение", "менеджер по товародвижению")


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_real_vacancies(message, "📊 Аналитик", "аналитик")


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_real_vacancies(message, "🔥 Закупки", "менеджер по закупкам")
    send_real_vacancies(message, "🔥 Товародвижение", "менеджер по товародвижению")
    send_real_vacancies(message, "🔥 Аналитик", "аналитик")


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_real_vacancies(
        message,
        "🚫 Без продаж",
        "менеджер аналитик -продажи -холодные -звонки -клиенты"
    )


@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_button(message):
    bot.send_message(
        message.chat.id,
        "Нажми кнопку ниже или напиши:\n/search менеджер по закупкам",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(
        message.chat.id,
        "Нажми кнопку ниже или напиши:\n/search менеджер по закупкам",
        reply_markup=main_keyboard()
    )


bot.infinity_polling(timeout=60, long_polling_timeout=60)

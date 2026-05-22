import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import random
import time

TOKEN = "ТВОЙ_ТОКЕН"

bot = telebot.TeleBot(TOKEN)

HEADERS = {
    "User-Agent": UserAgent().random,
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}

# =========================================
# ГЛАВНАЯ КЛАВИАТУРА
# =========================================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🔎 Закупки"),
            KeyboardButton(text="📦 Товародвижение")
        ],
        [
            KeyboardButton(text="📊 Аналитик"),
            KeyboardButton(text="🗂 Категорийный менеджер")
        ],
        [
            KeyboardButton(text="🔥 Лучшие сегодня"),
            KeyboardButton(text="🚫 Без продаж")
        ],
        [
            KeyboardButton(text="❓ Помощь")
        ]
    ],
    resize_keyboard=True
)

# =========================================
# ПЛОХИЕ СЛОВА
# =========================================

BAD_WORDS = [
    "маркетплейс",
    "wildberries",
    "wb",
    "ozon",
    "яндекс маркет",
    "avito",
    "продаж",
    "менеджер по продажам",
    "по работе с клиентами",
    "кредит",
    "страхование",
    "лизинг",
    "стажер",
    "стажёр",
    "недвижимость",
]

# =========================================
# СТАРТ
# =========================================

@bot.message_handler(commands=["start"])
def start(message):
    text = (
        "Я карьерный ассистент для поиска вакансий на HH.\n\n"
        "Ищу только:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 график — только 5/2\n\n"
        "Выбери направление кнопкой ниже 👇"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard
    )

# =========================================
# КНОПКИ
# =========================================

@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def procurement_jobs(message):
    send_search_results(
        message,
        query="менеджер по закупкам"
    )

@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def movement_jobs(message):
    send_search_results(
        message,
        query="товародвижение"
    )

@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst_jobs(message):
    send_search_results(
        message,
        query="аналитик"
    )

@bot.message_handler(func=lambda message: message.text == "🗂 Категорийный менеджер")
def category_manager_jobs(message):
    send_search_results(
        message,
        query="категорийный менеджер"
    )

@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    text = (
        "🔥 Лучшие направления на сегодня:\n\n"
        "1️⃣ Закупки\n"
        "2️⃣ Аналитик\n"
        "3️⃣ Категорийный менеджер\n"
        "4️⃣ Товародвижение\n\n"
        "💰 Зарплаты чаще 100–180k\n"
        "🏠 Много гибрида и удаленки"
    )

    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    text = (
        "🚫 Что бот исключает:\n\n"
        "• продажи\n"
        "• маркетплейсы\n"
        "• WB/Ozon\n"
        "• страхование\n"
        "• кредиты\n"
        "• недвижимость\n"
        "• стажировки"
    )

    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_message(message):
    text = (
        "❓ Как пользоваться ботом:\n\n"
        "1️⃣ Нажми кнопку направления\n"
        "2️⃣ Бот покажет вакансии\n"
        "3️⃣ Открой вакансию кнопкой\n\n"
        "Фильтры:\n"
        "🏠 удаленка\n"
        "🏢 гибрид СПБ\n"
        "📅 только график 5/2"
    )

    bot.send_message(message.chat.id, text)

# =========================================
# ПОИСК ВАКАНСИЙ
# =========================================

def send_search_results(message, query):

    bot.send_message(
        message.chat.id,
        f"🔎 Ищу вакансии: {query}"
    )

    remote_url = (
        "https://spb.hh.ru/search/vacancy?"
        f"text={query}"
        "&salary=100000"
        "&only_with_salary=true"
        "&schedule=fullDay"
        "&remote_work=1"
    )

    hybrid_url = (
        "https://spb.hh.ru/search/vacancy?"
        f"text={query}"
        "&area=2"
        "&salary=100000"
        "&only_with_salary=true"
        "&schedule=fullDay"
        "&work_format=HYBRID"
    )

    text = (
        f"🔎 Запрос: {query}\n"
        f"💰 Зарплата: от 100000 ₽\n"
        f"📅 График: только 5/2\n\n"
        f"Показываю только подходящие форматы:\n"
        f"🏠 удаленка — все города\n"
        f"🏢 гибрид — Санкт-Петербург\n\n"
        f"❌ Офисные вакансии «на месте работодателя» исключаем."
    )

    keyboard = InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton(
            "🏠 Открыть удаленные вакансии",
            url=remote_url
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "🏢 Открыть гибрид СПБ",
            url=hybrid_url
        )
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=keyboard
    )

    show_real_vacancies(
        message.chat.id,
        remote_url,
        "Удаленка"
    )

    show_real_vacancies(
        message.chat.id,
        hybrid_url,
        "Гибрид — Санкт-Петербург"
    )

# =========================================
# ПАРСИНГ HH
# =========================================

def show_real_vacancies(chat_id, url, title):

    try:
        time.sleep(random.randint(1, 3))

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=20
        )

        soup = BeautifulSoup(response.text, "html.parser")

        vacancies = soup.find_all("serp-item")

        if not vacancies:
            bot.send_message(
                chat_id,
                f"❌ По разделу '{title}' вакансий не найдено."
            )
            return

        bot.send_message(
            chat_id,
            f"📌 {title}"
        )

        shown = 0

        for vacancy in vacancies:

            if shown >= 3:
                break

            text = vacancy.get_text(" ").lower()

            if any(word in text for word in BAD_WORDS):
                continue

            title_tag = vacancy.find("a")

            if not title_tag:
                continue

            vacancy_name = title_tag.text.strip()
            vacancy_url = title_tag.get("href")

            company = "Не указано"
            company_tag = vacancy.find(attrs={"data-qa": "vacancy-serp__vacancy-employer"})

            if company_tag:
                company = company_tag.text.strip()

            salary = "Не указана"
            salary_tag = vacancy.find(attrs={"data-qa": "vacancy-serp__vacancy-compensation"})

            if salary_tag:
                salary = salary_tag.text.strip()

            area = "Не указан"
            area_tag = vacancy.find(attrs={"data-qa": "vacancy-serp__vacancy-address"})

            if area_tag:
                area = area_tag.text.strip()

            text_message = (
                f"📌 {vacancy_name}\n\n"
                f"🏢 {company}\n"
                f"💰 {salary}\n"
                f"📍 {area}"
            )

            keyboard = InlineKeyboardMarkup()

            keyboard.add(
                InlineKeyboardButton(
                    "Открыть вакансию",
                    url=vacancy_url
                )
            )

            bot.send_message(
                chat_id,
                text_message,
                reply_markup=keyboard
            )

            shown += 1

    except Exception as e:
        bot.send_message(
            chat_id,
            f"Ошибка загрузки вакансий:\n{e}"
        )

# =========================================
# ЗАПУСК
# =========================================

print("Бот запущен")

bot.infinity_polling(skip_pending=True)

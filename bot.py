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


STRICT_GOOD_WORDS = [
    "закуп",
    "закупк",
    "снабжен",
    "снабжение",
    "товародвиж",
    "категорий",
    "категорийный",
    "ассортимент",
    "аналитик",
    "аналитика",
    "планирован",
    "планирование",
    "поставщик",
    "поставщиками",
    "inventory",
    "replenishment",
    "demand planning",
    "supply chain",
    "procurement",
    "buyer",
    "category",
    "assortment",
]


BAD_WORDS = [
    "маркетплейс",
    "маркетплейсов",
    "wildberries",
    "wb",
    "ozon",
    "яндекс маркет",

    "стажер",
    "стажёр",
    "помощник",
    "ассистент",

    "продажи",
    "продаж",
    "менеджер по продажам",
    "продавец",
    "клиентами",
    "клиентов",
    "по работе с клиентами",
    "аккаунт",
    "account",
    "b2b",
    "b2c",

    "оператор",
    "операционный",
    "контакт-центр",
    "call-центр",
    "колл-центр",

    "недвижимость",
    "новостройки",
    "заявки",
    "входящие заявки",

    "кредит",
    "кредитный",
    "лизинг",
    "страхование",
    "страховой",

    "склад",
    "склада",
    "кладовщик",
    "комплектовщик",

    "размещение заказов",
    "размещению заказов",

    "магазин",
    "ритейл",
    "retail",

    "логист",
    "логистика",
    "курьер",
    "водитель",

    "support",
    "поддержка",
]


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


def is_good_vacancy(vacancy):
    title = vacancy.get("title", "").lower()

    for bad_word in BAD_WORDS:
        if bad_word in title:
            return False

    for good_word in STRICT_GOOD_WORDS:
        if good_word in title:
            return True

    return False


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

    for card in cards:
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

        vacancy = {
            "title": title,
            "company": company,
            "salary": salary,
            "address": address,
            "link": link,
        }

        if is_good_vacancy(vacancy):
            vacancies.append(vacancy)

        if len(vacancies) >= limit:
            break

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


def send_fallback_links(message, title, query):
    remote_link = make_hh_link(query, mode="remote")
    hybrid_link = make_hh_link(query, mode="hybrid_spb")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Удаленные вакансии", url=remote_link))
    keyboard.add(types.InlineKeyboardButton("🏢 Гибрид СПБ", url=hybrid_link))

    text = (
        f"{title}\n\n"
        f"Подходящих карточек после PRO-фильтра не нашлось.\n\n"
        f"Открывай готовый поиск HH:\n\n"
        f"🏠 удаленка — все города\n"
        f"🏢 гибрид — Санкт-Петербург\n"
        f"📅 только 5/2\n"
        f"💰 от 100 000 ₽"
    )

    bot.send_message(message.chat.id, text, reply_markup=keyboard)


def send_real_vacancies(message, title, query):
    bot.send_message(
        message.chat.id,
        f"{title}\n\nИщу вакансии и применяю PRO-фильтр...",
        reply_markup=main_keyboard()
    )

    found_any = False

    for mode_title, mode in [
        ("🏠 Удаленка — все города", "remote"),
        ("🏢 Гибрид — Санкт-Петербург", "hybrid_spb"),
    ]:
        bot.send_message(message.chat.id, mode_title)

        try:
            vacancies = get_vacancies_from_hh(query=query, mode=mode, limit=3)

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
        ("📊 Аналитик", "аналитик закупок"),
    ]

    bot.send_message(
        message.chat.id,
        "🔥 Лучшие направления на сегодня\n\n"
        "Фильтры:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 только 5/2\n"
        "💰 от 100 000 ₽\n\n"
        "Включен PRO-фильтр мусорных вакансий.",
        reply_markup=main_keyboard()
    )

    for title, query in directions:
        send_real_vacancies(message, title, query)


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Я AI-ассистент по поиску вакансий HH.\n\n"
        "Ищу только:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 только 5/2\n"
        "💰 от 100 000 ₽\n\n"
        "Включен PRO-фильтр мусорных вакансий.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Команды:\n\n"
        "/start — открыть меню\n"
        "/search текст вакансии\n\n"
        "Бот показывает только релевантные вакансии по закупкам, товародвижению и аналитике.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["search"])
def manual_search(message):
    query = message.text.replace("/search", "").strip()

    if not query:
        bot.send_message(
            message.chat.id,
            "Пример:\n/search менеджер по закупкам",
            reply_markup=main_keyboard()
        )
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
    send_real_vacancies(message, "📊 Аналитик", "аналитик закупок")


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_best_today(message)


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_real_vacancies(message, "🚫 Без продаж", "аналитик закупок")


@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_button(message):
    help_command(message)


@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(
        message.chat.id,
        "Используй кнопки ниже 👇",
        reply_markup=main_keyboard()
    )


bot.infinity_polling(timeout=60, long_polling_timeout=60)

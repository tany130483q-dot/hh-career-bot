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


USER_FAVORITES = {}
USER_LAST_VACANCIES = {}


BAD_WORDS_COMMON = [
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

    "оператор",
    "контакт-центр",
    "call-центр",
    "колл-центр",

    "недвижимость",
    "кредит",
    "кредитный",
    "лизинг",
    "страхование",

    "склад",
    "кладовщик",
    "комплектовщик",
    "курьер",
    "водитель",

    "бизнес-аналитик",
    "бизнес аналитик",
    "business analyst",
    "system analyst",
    "системный аналитик",
    "системного аналитика",
    "системная аналитика",

    "английский",
    "английского",
    "english",
    "upper-intermediate",
    "intermediate",
    "b1",
    "b2",
    "c1",
    "c2",
]


BAD_WORDS_TOVARODVIZHENIE = [
    "закупщик",
    "закупкам",
    "закупок",
    "закупки",
    "снабжение",
    "снабженец",
    "поставщик",
    "поставщиками",
]


GOOD_WORDS_BY_CATEGORY = {
    "Закупки": [
        "закуп",
        "снабжен",
        "поставщик",
        "procurement",
        "buyer",
    ],
    "Товародвижение": [
        "товародвиж",
        "товарное движение",
        "движение товара",
        "планирование поставок",
        "планирование товарных запасов",
        "inventory",
        "replenishment",
        "demand planning",
        "supply chain",
    ],
    "Аналитик": [
        "аналитик",
        "аналитика",
        "аналитик закуп",
        "аналитик ассортимента",
        "аналитик товар",
        "товарный аналитик",
        "inventory analyst",
        "demand analyst",
    ],
    "Категорийный менеджер": [
        "категорий",
        "category",
        "категорийный менеджер",
        "ассортимент",
        "category manager",
    ],
}


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "🗂 Категорийный менеджер")
    keyboard.row("🔥 Лучшие сегодня", "🚫 Без продаж")
    keyboard.row("⭐ Избранное", "❓ Помощь")

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


def get_vacancy_full_text(vacancy):
    return (
        vacancy.get("title", "") + " " +
        vacancy.get("company", "") + " " +
        vacancy.get("salary", "") + " " +
        vacancy.get("address", "")
    ).lower()


def is_good_vacancy(vacancy, category):
    full_text = get_vacancy_full_text(vacancy)
    title = vacancy.get("title", "").lower()

    for bad_word in BAD_WORDS_COMMON:
        if bad_word in full_text:
            return False

    if category == "Товародвижение":
        for bad_word in BAD_WORDS_TOVARODVIZHENIE:
            if bad_word in title:
                return False

    good_words = GOOD_WORDS_BY_CATEGORY.get(category, [])

    for good_word in good_words:
        if good_word in title:
            return True

    return False


def get_vacancies_from_hh(query, category, mode="remote", limit=5):
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

        if is_good_vacancy(vacancy, category):
            vacancies.append(vacancy)

        if len(vacancies) >= limit:
            break

    return vacancies


def save_last_vacancy(user_id, vacancy):
    if user_id not in USER_LAST_VACANCIES:
        USER_LAST_VACANCIES[user_id] = []

    USER_LAST_VACANCIES[user_id].append(vacancy)

    return len(USER_LAST_VACANCIES[user_id]) - 1


def send_vacancy_card(chat_id, user_id, vacancy):
    vacancy_index = save_last_vacancy(user_id, vacancy)

    text = (
        f"📌 {vacancy['title']}\n\n"
        f"🏢 {vacancy['company']}\n"
        f"💰 {vacancy['salary']}\n"
        f"📍 {vacancy['address']}\n\n"
        f"🔗 {vacancy['link']}"
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Открыть вакансию", url=vacancy["link"]))
    keyboard.add(types.InlineKeyboardButton("⭐ Сохранить", callback_data=f"save_{vacancy_index}"))

    bot.send_message(chat_id, text, reply_markup=keyboard)


def send_fallback_links(message, title, query):
    remote_link = make_hh_link(query, mode="remote")
    hybrid_link = make_hh_link(query, mode="hybrid_spb")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Удаленные вакансии", url=remote_link))
    keyboard.add(types.InlineKeyboardButton("🏢 Гибрид СПБ", url=hybrid_link))

    text = (
        f"{title}\n\n"
        f"Подходящих карточек после фильтра не нашлось.\n\n"
        f"Открывай готовый поиск HH:\n\n"
        f"🏠 удаленка — все города\n"
        f"🏢 гибрид — Санкт-Петербург\n"
        f"📅 только 5/2\n"
        f"💰 от 100 000 ₽"
    )

    bot.send_message(message.chat.id, text, reply_markup=keyboard)


def send_real_vacancies(message, title, query, category):
    user_id = message.from_user.id

    USER_LAST_VACANCIES[user_id] = []

    bot.send_message(
        message.chat.id,
        f"{title}\n\nИщу вакансии и применяю фильтр...",
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
            vacancies = get_vacancies_from_hh(
                query=query,
                category=category,
                mode=mode,
                limit=3,
            )

            if not vacancies:
                continue

            found_any = True

            for vacancy in vacancies:
                send_vacancy_card(message.chat.id, user_id, vacancy)

        except Exception:
            continue

    if not found_any:
        send_fallback_links(message, title, query)


def show_favorites(message):
    user_id = message.from_user.id
    favorites = USER_FAVORITES.get(user_id, [])

    if not favorites:
        bot.send_message(
            message.chat.id,
            "⭐ Избранное пока пустое.\n\nСохрани вакансию кнопкой ⭐ под карточкой.",
            reply_markup=main_keyboard()
        )
        return

    bot.send_message(
        message.chat.id,
        f"⭐ Избранные вакансии: {len(favorites)}",
        reply_markup=main_keyboard()
    )

    for vacancy in favorites:
        text = (
            f"📌 {vacancy['title']}\n\n"
            f"🏢 {vacancy['company']}\n"
            f"💰 {vacancy['salary']}\n"
            f"📍 {vacancy['address']}\n\n"
            f"🔗 {vacancy['link']}"
        )

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Открыть вакансию", url=vacancy["link"]))

        bot.send_message(message.chat.id, text, reply_markup=keyboard)


def send_best_today(message):
    bot.send_message(
        message.chat.id,
        "🔥 Лучшие направления на сегодня\n\n"
        "Фильтры:\n"
        "🏠 удаленка — все города\n"
        "🏢 гибрид — Санкт-Петербург\n"
        "📅 только 5/2\n"
        "💰 от 100 000 ₽\n\n"
        "Исключаю бизнес/системную аналитику и вакансии с английским.",
        reply_markup=main_keyboard()
    )

    send_real_vacancies(message, "🔎 Закупки", "менеджер по закупкам", "Закупки")
    send_real_vacancies(message, "📦 Товародвижение", "товародвижение", "Товародвижение")
    send_real_vacancies(message, "📊 Аналитик", "аналитик закупок", "Аналитик")
    send_real_vacancies(message, "🗂 Категорийный менеджер", "категорийный менеджер", "Категорийный менеджер")


@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def save_vacancy_callback(call):
    user_id = call.from_user.id
    vacancy_index = int(call.data.replace("save_", ""))

    last_vacancies = USER_LAST_VACANCIES.get(user_id, [])

    if vacancy_index >= len(last_vacancies):
        bot.answer_callback_query(call.id, "Не смогла сохранить. Обнови поиск.")
        return

    vacancy = last_vacancies[vacancy_index]

    if user_id not in USER_FAVORITES:
        USER_FAVORITES[user_id] = []

    already_saved = any(item["link"] == vacancy["link"] for item in USER_FAVORITES[user_id])

    if already_saved:
        bot.answer_callback_query(call.id, "Эта вакансия уже в избранном ⭐")
        return

    USER_FAVORITES[user_id].append(vacancy)

    bot.answer_callback_query(call.id, "Вакансия сохранена ⭐")


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
        "Можно сохранять вакансии в ⭐ Избранное.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Команды:\n\n"
        "/start — открыть меню\n"
        "/search текст вакансии\n\n"
        "Кнопки:\n"
        "🔎 Закупки\n"
        "📦 Товародвижение\n"
        "📊 Аналитик\n"
        "🗂 Категорийный менеджер\n"
        "🔥 Лучшие сегодня\n"
        "🚫 Без продаж\n"
        "⭐ Избранное",
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

    send_real_vacancies(message, "🔎 Ручной поиск", query, "Аналитик")


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_real_vacancies(message, "🔎 Закупки", "менеджер по закупкам", "Закупки")


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_real_vacancies(message, "📦 Товародвижение", "товародвижение", "Товародвижение")


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_real_vacancies(message, "📊 Аналитик", "аналитик закупок", "Аналитик")


@bot.message_handler(func=lambda message: message.text == "🗂 Категорийный менеджер")
def category_manager(message):
    send_real_vacancies(message, "🗂 Категорийный менеджер", "категорийный менеджер", "Категорийный менеджер")


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_best_today(message)


@bot.message_handler(func=lambda message: message.text == "🚫 Без продаж")
def no_sales(message):
    send_real_vacancies(message, "🚫 Без продаж", "аналитик закупок", "Аналитик")


@bot.message_handler(func=lambda message: message.text == "⭐ Избранное")
def favorites(message):
    show_favorites(message)


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

import os
import uuid
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
VACANCY_STORAGE = {}


BAD_WORDS_COMMON = [
    "маркетплейс", "маркетплейсов", "wildberries", "wb", "ozon", "яндекс маркет",
    "стажер", "стажёр", "помощник", "ассистент",
    "продажи", "продаж", "менеджер по продажам", "продавец",
    "клиентами", "клиентов", "по работе с клиентами",
    "оператор", "контакт-центр", "call-центр", "колл-центр",
    "недвижимость", "кредит", "кредитный", "лизинг", "страхование",
    "склад", "кладовщик", "комплектовщик", "курьер", "водитель",
    "бизнес-аналитик", "бизнес аналитик", "business analyst",
    "system analyst", "системный аналитик", "системного аналитика", "системная аналитика",
    "английский", "английского", "english", "upper-intermediate", "intermediate", "b1", "b2", "c1", "c2",
]


BAD_WORDS_TOVARODVIZHENIE = [
    "закупщик", "закупкам", "закупок", "закупки",
    "снабжение", "снабженец", "поставщик", "поставщиками",
]


GOOD_WORDS_BY_CATEGORY = {
    "Закупки": ["закуп", "снабжен", "поставщик", "procurement", "buyer"],
    "Товародвижение": [
        "товародвиж", "товарное движение", "движение товара",
        "планирование поставок", "планирование товарных запасов",
        "inventory", "replenishment", "demand planning", "supply chain",
    ],
    "Аналитик": [
        "аналитик", "аналитика", "аналитик закуп", "аналитик ассортимента",
        "аналитик товар", "товарный аналитик", "inventory analyst", "demand analyst",
    ],
    "Категорийный менеджер": [
        "категорий", "category", "категорийный менеджер", "ассортимент", "category manager",
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


def is_good_vacancy(vacancy, category):
    full_text = (
        vacancy.get("title", "") + " " +
        vacancy.get("company", "") + " " +
        vacancy.get("salary", "") + " " +
        vacancy.get("address", "")
    ).lower()

    title = vacancy.get("title", "").lower()

    for bad_word in BAD_WORDS_COMMON:
        if bad_word in full_text:
            return False

    if category == "Товародвижение":
        for bad_word in BAD_WORDS_TOVARODVIZHENIE:
            if bad_word in title:
                return False

    for good_word in GOOD_WORDS_BY_CATEGORY.get(category, []):
        if good_word in title:
            return True

    return False


def get_vacancies_from_hh(query, category, mode="remote", limit=5):
    url = make_hh_link(query, mode=mode)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36",
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

        vacancy = {
            "id": str(uuid.uuid4())[:8],
            "title": title_tag.get_text(strip=True),
            "link": title_tag.get("href", ""),
            "company": company_tag.get_text(strip=True) if company_tag else "Компания не указана",
            "salary": salary_tag.get_text(strip=True) if salary_tag else "Зарплата не указана",
            "address": address_tag.get_text(strip=True) if address_tag else "Город не указан",
        }

        if is_good_vacancy(vacancy, category):
            vacancies.append(vacancy)

        if len(vacancies) >= limit:
            break

    return vacancies


def send_vacancy_card(chat_id, vacancy):
    vacancy_id = vacancy["id"]
    VACANCY_STORAGE[vacancy_id] = vacancy

    text = (
        f"📌 {vacancy['title']}\n\n"
        f"🏢 {vacancy['company']}\n"
        f"💰 {vacancy['salary']}\n"
        f"📍 {vacancy['address']}\n\n"
        f"🔗 {vacancy['link']}"
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("Открыть вакансию", url=vacancy["link"]))
    keyboard.add(types.InlineKeyboardButton("⭐ Сохранить вакансию", callback_data=f"save:{vacancy_id}"))

    bot.send_message(chat_id, text, reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("save:"))
def save_vacancy_callback(call):
    user_id = call.from_user.id
    vacancy_id = call.data.split(":")[1]

    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия устарела. Запусти поиск заново.")
        return

    if user_id not in USER_FAVORITES:
        USER_FAVORITES[user_id] = []

    already_saved = any(item["link"] == vacancy["link"] for item in USER_FAVORITES[user_id])

    if already_saved:
        bot.answer_callback_query(call.id, "Уже есть в избранном ⭐")
        return

    USER_FAVORITES[user_id].append(vacancy)

    bot.answer_callback_query(call.id, "Сохранено в избранное ⭐")

    bot.send_message(
        call.message.chat.id,
        f"⭐ Сохранила вакансию:\n\n📌 {vacancy['title']}",
        reply_markup=main_keyboard()
    )


def show_favorites(message):
    user_id = message.from_user.id
    favorites = USER_FAVORITES.get(user_id, [])

    if not favorites:
        bot.send_message(
            message.chat.id,
            "⭐ Избранное пока пустое.\n\nСначала нажми кнопку ⭐ Сохранить вакансию под карточкой.",
            reply_markup=main_keyboard()
        )
        return

    bot.send_message(
        message.chat.id,
        f"⭐ Избранные вакансии: {len(favorites)}",
        reply_markup=main_keyboard()
    )

    for vacancy in favorites:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Открыть вакансию", url=vacancy["link"]))

        text = (
            f"📌 {vacancy['title']}\n\n"
            f"🏢 {vacancy['company']}\n"
            f"💰 {vacancy['salary']}\n"
            f"📍 {vacancy['address']}\n\n"
            f"🔗 {vacancy['link']}"
        )

        bot.send_message(message.chat.id, text, reply_markup=keyboard)


def send_fallback_links(message, title, query):
    remote_link = make_hh_link(query, mode="remote")
    hybrid_link = make_hh_link(query, mode="hybrid_spb")

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🏠 Удаленные вакансии", url=remote_link))
    keyboard.add(types.InlineKeyboardButton("🏢 Гибрид СПБ", url=hybrid_link))

    bot.send_message(
        message.chat.id,
        f"{title}\n\nПодходящих карточек после фильтра не нашлось.\n\nОткрой готовый поиск HH:",
        reply_markup=keyboard
    )


def send_real_vacancies(message, title, query, category):
    bot.send_message(
        message.chat.id,
        f"{title}\n\nИщу вакансии и применяю фильтр...",
        reply_markup=main_keyboard()
    )

    found_any = False

    for mode_title, mode in [
        ("🏠 Удаленка — все города", "remote"),
        ("🏢 Гибрид — Санкт-Петербург", "hybrid_spb"),
    ]:
        bot.send_message(message.chat.id, mode_title)

        try:
            vacancies = get_vacancies_from_hh(query, category, mode=mode, limit=3)

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
    send_real_vacancies(message, "🔎 Закупки", "менеджер по закупкам", "Закупки")
    send_real_vacancies(message, "📦 Товародвижение", "товародвижение", "Товародвижение")
    send_real_vacancies(message, "📊 Аналитик", "аналитик закупок", "Аналитик")
    send_real_vacancies(message, "🗂 Категорийный менеджер", "категорийный менеджер", "Категорийный менеджер")


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Можно искать вакансии и сохранять их в ⭐ Избранное.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["search"])
def manual_search(message):
    query = message.text.replace("/search", "").strip()

    if not query:
        bot.send_message(message.chat.id, "Пример:\n/search менеджер по закупкам", reply_markup=main_keyboard())
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
    bot.send_message(
        message.chat.id,
        "Нажми направление, затем под вакансией нажми ⭐ Сохранить вакансию.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(message.chat.id, "Используй кнопки ниже 👇", reply_markup=main_keyboard())


bot.infinity_polling(timeout=60, long_polling_timeout=60)

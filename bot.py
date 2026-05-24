import os
import uuid
import time
import threading
import schedule
import requests
import telebot

from bs4 import BeautifulSoup
from telebot import types
from urllib.parse import quote


TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwf3UPzjUZIzLsn64wluSEMBp3uRA91sIEWwz6104WzSKRSy5OajIBuDLTb3hGB21Ui/exec"

USER_FAVORITES = {}
VACANCY_STORAGE = {}

CURRENT_SALARY = 100000


BAD_WORDS_COMMON = [
    "маркетплейс", "маркетплейсов", "wildberries", "wb", "ozon", "яндекс маркет",
    "стажер", "стажёр", "помощник", "ассистент",
    "продажи", "продаж", "менеджер по продажам", "продавец",
    "клиентами", "клиентов", "по работе с клиентами",
    "оператор", "контакт-центр", "call-центр", "колл-центр",
    "недвижимость", "кредит", "кредитный", "лизинг", "страхование",
    "склад", "кладовщик", "комплектовщик", "курьер", "водитель",
    "бизнес-аналитик", "бизнес аналитик", "business analyst",
    "system analyst", "системный аналитик", "системного аналитика",
    "системная аналитика",
    "финансовый аналитик", "финансовая аналитика", "финансовый",
    "1с", "1c", "middle", "senior",
    "методология", "методолог", "методологии",
    "автомобиль", "автомобилей", "авто", "автоаукцион", "байер",
    "английский", "английского", "english",
    "китайский", "китайского", "chinese",
    "upper-intermediate", "intermediate", "b1", "b2", "c1", "c2",
]

BAD_WORDS_TOVARODVIZHENIE = [
    "закупщик", "закупкам", "закупок", "закупки",
    "снабжение", "снабженец", "поставщик", "поставщиками",
]

GOOD_WORDS_BY_CATEGORY = {
    "Закупки": [
        "закуп", "снабжен", "поставщик", "procurement", "buyer"
    ],
    "Товародвижение": [
        "товародвиж", "товарное движение", "движение товара",
        "планирование поставок", "планирование товарных запасов",
        "inventory", "replenishment", "demand planning", "supply chain"
    ],
    "Аналитик": [
        "аналитик закуп", "аналитик ассортимента",
        "аналитик товар", "товарный аналитик",
        "аналитик по товар", "inventory analyst", "demand analyst"
    ],
    "Категорийный менеджер": [
        "категорий", "category", "категорийный менеджер",
        "ассортимент", "category manager"
    ],
}


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "🗂 Категорийный менеджер")
    keyboard.row("🔥 Лучшие сегодня", "🏠 Только удаленка")
    keyboard.row("💰 Зарплата 150k+", "⭐ Избранное")
    keyboard.row("🔔 Включить рассылку", "🔕 Выключить рассылку")
    keyboard.row("❓ Помощь")

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


def get_vacancies_from_hh(query, category, salary, mode="remote", limit=3):
    url = make_hh_link(query, salary=salary, mode=mode)

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

        vacancy = {
            "id": str(uuid.uuid4())[:8],
            "title": title_tag.get_text(strip=True),
            "company": company_tag.get_text(strip=True) if company_tag else "Компания не указана",
            "salary": salary_tag.get_text(strip=True) if salary_tag else "Зарплата не указана",
            "address": address_tag.get_text(strip=True) if address_tag else "Город не указан",
            "link": title_tag.get("href", ""),
        }

        if is_good_vacancy(vacancy, category):
            vacancies.append(vacancy)

        if len(vacancies) >= limit:
            break

    return vacancies


def send_vacancy_card(chat_id, vacancy, show_save=True):
    vacancy_id = vacancy["id"]
    VACANCY_STORAGE[vacancy_id] = vacancy

    text = (
        f"📌 {vacancy['title']}\n\n"
        f"🏢 {vacancy['company']}\n"
        f"💰 {vacancy['salary']}\n"
        f"📍 {vacancy['address']}"
    )

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "🔗 Открыть вакансию",
            url=vacancy["link"]
        )
    )

    if show_save:
        keyboard.add(
            types.InlineKeyboardButton(
                "⭐ Сохранить вакансию",
                callback_data=f"save_{vacancy_id}"
            )
        )
    else:
        keyboard.add(
            types.InlineKeyboardButton(
                "🗑 Удалить из избранного",
                callback_data=f"delete_fav_{vacancy_id}"
            )
        )

    bot.send_message(
        chat_id,
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


def send_real_vacancies(
    chat_id,
    title,
    query,
    category,
    salary=CURRENT_SALARY,
    only_remote=False
):
    bot.send_message(
        chat_id,
        f"{title}\n\n💰 Зарплата от {salary:,} ₽",
        reply_markup=main_keyboard()
    )

    found_any = False

    search_modes = [("🏠 Удаленка — все города", "remote")]

    if not only_remote:
        search_modes.append(("🏢 Гибрид — Санкт-Петербург", "hybrid_spb"))

    for mode_title, mode in search_modes:
        bot.send_message(chat_id, mode_title)

        try:
            vacancies = get_vacancies_from_hh(
                query=query,
                category=category,
                salary=salary,
                mode=mode,
                limit=3
            )

            if not vacancies:
                continue

            found_any = True

            for vacancy in vacancies:
                send_vacancy_card(chat_id, vacancy, show_save=True)

        except Exception as error:
            print("HH ERROR:", error)
            continue

    if not found_any:
        bot.send_message(
            chat_id,
            "❌ Подходящих вакансий не найдено.",
            reply_markup=main_keyboard()
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def save_vacancy_callback(call):
    user_id = call.from_user.id
    vacancy_id = call.data.replace("save_", "")
    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия устарела.")
        return

    if user_id not in USER_FAVORITES:
        USER_FAVORITES[user_id] = []

    already_saved = any(
        item["link"] == vacancy["link"]
        for item in USER_FAVORITES[user_id]
    )

    if already_saved:
        bot.answer_callback_query(call.id, "Уже сохранена ⭐")
        return

    USER_FAVORITES[user_id].append(vacancy)
    bot.answer_callback_query(call.id, "Сохранено ⭐")

    bot.send_message(
        call.message.chat.id,
        f"⭐ Сохранила вакансию:\n\n📌 {vacancy['title']}",
        reply_markup=main_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_fav_"))
def delete_favorite_callback(call):
    user_id = call.from_user.id
    vacancy_id = call.data.replace("delete_fav_", "")

    favorites = USER_FAVORITES.get(user_id, [])

    USER_FAVORITES[user_id] = [
        vacancy for vacancy in favorites
        if vacancy.get("id") != vacancy_id
    ]

    bot.answer_callback_query(call.id, "Удалено 🗑")

    bot.send_message(
        call.message.chat.id,
        "🗑 Вакансия удалена из избранного.",
        reply_markup=main_keyboard()
    )


def show_favorites(message):
    user_id = message.from_user.id
    favorites = USER_FAVORITES.get(user_id, [])

    if not favorites:
        bot.send_message(
            message.chat.id,
            "⭐ Избранное пока пустое.",
            reply_markup=main_keyboard()
        )
        return

    bot.send_message(
        message.chat.id,
        f"⭐ Избранные вакансии: {len(favorites)}",
        reply_markup=main_keyboard()
    )

    for vacancy in favorites:
        VACANCY_STORAGE[vacancy["id"]] = vacancy
        send_vacancy_card(message.chat.id, vacancy, show_save=False)


def add_subscriber(chat_id):
    requests.get(
        SCRIPT_URL,
        params={
            "action": "add",
            "chat_id": chat_id
        },
        timeout=10
    )


def remove_subscriber(chat_id):
    requests.get(
        SCRIPT_URL,
        params={
            "action": "remove",
            "chat_id": chat_id
        },
        timeout=10
    )


def get_subscribers():
    response = requests.get(
        SCRIPT_URL,
        params={"action": "list"},
        timeout=10
    )
    return response.json()


def send_daily_jobs_to_chat(chat_id):
    bot.send_message(
        chat_id,
        "🔔 Ежедневная подборка вакансий",
        reply_markup=main_keyboard()
    )

    send_real_vacancies(chat_id, "🔎 Закупки", "менеджер по закупкам", "Закупки")
    send_real_vacancies(chat_id, "📦 Товародвижение", "товародвижение", "Товародвижение")
    send_real_vacancies(chat_id, "📊 Аналитик", "аналитик закупок", "Аналитик")
    send_real_vacancies(chat_id, "🗂 Категорийный менеджер", "категорийный менеджер", "Категорийный менеджер")


def daily_jobs():
    try:
        subscribers = get_subscribers()

        for chat_id in subscribers:
            try:
                send_daily_jobs_to_chat(chat_id)
            except Exception as error:
                print("SEND DAILY ERROR:", error)

    except Exception as error:
        print("DAILY JOB ERROR:", error)


def scheduler_loop():
    while True:
        schedule.run_pending()
        time.sleep(30)


schedule.every().day.at("07:00").do(daily_jobs)
threading.Thread(target=scheduler_loop, daemon=True).start()


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "Можно искать вакансии, сохранять избранное и включить ежедневную рассылку.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["subscribe"])
def subscribe_command(message):
    add_subscriber(message.chat.id)

    bot.send_message(
        message.chat.id,
        "🔔 Рассылка включена.\n\nКаждый день в 10:00 по Москве буду присылать вакансии.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(commands=["unsubscribe"])
def unsubscribe_command(message):
    remove_subscriber(message.chat.id)

    bot.send_message(
        message.chat.id,
        "🔕 Рассылка выключена.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "🔔 Включить рассылку")
def enable_notifications(message):
    add_subscriber(message.chat.id)

    bot.send_message(
        message.chat.id,
        "🔔 Рассылка включена.\n\nКаждый день в 10:00 по Москве буду присылать вакансии.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "🔕 Выключить рассылку")
def disable_notifications(message):
    remove_subscriber(message.chat.id)

    bot.send_message(
        message.chat.id,
        "🔕 Рассылка выключена.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_real_vacancies(
        message.chat.id,
        "🔎 Закупки",
        "менеджер по закупкам",
        "Закупки"
    )


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_real_vacancies(
        message.chat.id,
        "📦 Товародвижение",
        "товародвижение",
        "Товародвижение"
    )


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_real_vacancies(
        message.chat.id,
        "📊 Аналитик",
        "аналитик закупок",
        "Аналитик"
    )


@bot.message_handler(func=lambda message: message.text == "🗂 Категорийный менеджер")
def category_manager(message):
    send_real_vacancies(
        message.chat.id,
        "🗂 Категорийный менеджер",
        "категорийный менеджер",
        "Категорийный менеджер"
    )


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_daily_jobs_to_chat(message.chat.id)


@bot.message_handler(func=lambda message: message.text == "🏠 Только удаленка")
def only_remote(message):
    send_real_vacancies(
        message.chat.id,
        "🏠 Только удаленка",
        "менеджер по закупкам",
        "Закупки",
        only_remote=True
    )


@bot.message_handler(func=lambda message: message.text == "💰 Зарплата 150k+")
def salary_150(message):
    send_real_vacancies(message.chat.id, "🔎 Закупки 150k+", "менеджер по закупкам", "Закупки", salary=150000)
    send_real_vacancies(message.chat.id, "📦 Товародвижение 150k+", "товародвижение", "Товародвижение", salary=150000)
    send_real_vacancies(message.chat.id, "📊 Аналитик 150k+", "аналитик закупок", "Аналитик", salary=150000)
    send_real_vacancies(message.chat.id, "🗂 Категорийный менеджер 150k+", "категорийный менеджер", "Категорийный менеджер", salary=150000)


@bot.message_handler(func=lambda message: message.text == "⭐ Избранное")
def favorites(message):
    show_favorites(message)


@bot.message_handler(func=lambda message: message.text == "❓ Помощь")
def help_button(message):
    bot.send_message(
        message.chat.id,
        "Нажми направление поиска или включи 🔔 ежедневную рассылку.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(
        message.chat.id,
        "Используй кнопки ниже 👇",
        reply_markup=main_keyboard()
    )


bot.remove_webhook()
time.sleep(2)

print("Бот запущен")

bot.infinity_polling(
    timeout=60,
    long_polling_timeout=60,
    allowed_updates=["message", "callback_query"]
)

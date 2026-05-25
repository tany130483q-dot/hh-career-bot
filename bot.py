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
from datetime import datetime


TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwf3UPzjUZIzLsn64wluSEMBp3uRA91sIEWwz6104WzSKRSy5OajIBuDLTb3hGB21Ui/exec"

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
    "system analyst", "системный аналитик", "системного аналитика", "системная аналитика",
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
    "Закупки": ["закуп", "снабжен", "поставщик", "procurement", "buyer"],
    "Товародвижение": [
        "товародвиж", "товарное движение", "движение товара",
        "планирование поставок", "планирование товарных запасов",
        "inventory", "replenishment", "demand planning", "supply chain"
    ],
    "Аналитик": [
        "аналитик закуп", "аналитик ассортимента", "аналитик товар",
        "товарный аналитик", "аналитик по товар", "inventory analyst", "demand analyst"
    ],
    "Категорийный менеджер": [
        "категорий", "category", "категорийный менеджер", "ассортимент", "category manager"
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
            "&search_field=name"
            "&search_field=company_name"
            "&search_field=description"
        )

    return (
        "https://spb.hh.ru/search/vacancy"
        f"?text={encoded_query}"
        "&area=2"
        f"&salary={salary}"
        "&only_with_salary=true"
        "&work_schedule_by_days=FIVE_ON_TWO_OFF"
        "&work_format=HYBRID"
        "&search_field=name"
        "&search_field=company_name"
        "&search_field=description"
    )


def google_get(params):
    response = requests.get(SCRIPT_URL, params=params, timeout=30)
    return response


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


def vacancy_score(vacancy, category):
    title = vacancy.get("title", "").lower()
    text = (
        vacancy.get("title", "") + " " +
        vacancy.get("company", "") + " " +
        vacancy.get("salary", "") + " " +
        vacancy.get("address", "")
    ).lower()

    score = 50

    for good_word in GOOD_WORDS_BY_CATEGORY.get(category, []):
        if good_word in title:
            score += 10

    if "удален" in text or "remote" in text:
        score += 8

    if "гибрид" in text:
        score += 5

    if "150" in text or "160" in text or "170" in text or "180" in text or "200" in text:
        score += 10

    for bad_word in BAD_WORDS_COMMON:
        if bad_word in text:
            score -= 25

    if score < 0:
        score = 0

    if score > 100:
        score = 100

    return score


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

    response = requests.get(url, headers=headers, timeout=25)
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
            "category": category,
        }

        if is_good_vacancy(vacancy, category):
            vacancy["ai_score"] = vacancy_score(vacancy, category)
            vacancies.append(vacancy)

    vacancies.sort(key=lambda item: item.get("ai_score", 0), reverse=True)
    return vacancies[:limit]


def call_ai(prompt):
    if not OPENAI_API_KEY:
        return "AI-функция пока не подключена. Добавь OPENAI_API_KEY в Render Environment Variables."

    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты карьерный ассистент. Отвечай кратко, практично, по-русски, без шаблонных фраз."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
                "temperature": 0.4,
                "max_tokens": 700,
            },
            timeout=60,
        )

        data = response.json()

        if response.status_code != 200:
            error_message = data.get("error", {}).get("message", str(data))
            return f"Ошибка OpenAI API:\n{error_message}"

        if "choices" not in data:
            return f"Ошибка OpenAI API: нет поля choices.\nОтвет сервера:\n{str(data)[:1000]}"

        return data["choices"][0]["message"]["content"]

    except Exception as error:
        return f"Ошибка AI-запроса: {error}"


def vacancy_text(vacancy):
    return (
        f"Название: {vacancy.get('title')}\n"
        f"Компания: {vacancy.get('company')}\n"
        f"Зарплата: {vacancy.get('salary')}\n"
        f"Город/формат: {vacancy.get('address')}\n"
        f"Категория: {vacancy.get('category')}\n"
        f"Ссылка: {vacancy.get('link')}"
    )


def make_ai_analysis(vacancy):
    return call_ai(
        "Оцени вакансию для Татьяны.\n"
        "Опыт: закупки, товародвижение, аналитика, категорийный менеджмент.\n"
        "Не подходят: продажи, колл-центры, бизнес/системная аналитика, английский/китайский.\n"
        "Ответь кратко:\n"
        "1. Подходит или нет\n"
        "2. Почему\n"
        "3. Риски\n"
        "4. Стоит ли откликаться\n\n"
        + vacancy_text(vacancy)
    )


def make_ai_salary(vacancy):
    return call_ai(
        "Оцени зарплату по вакансии.\n"
        "Скажи кратко: низкая, нормальная или высокая для роли.\n"
        "Цель дохода 100–150k+ рублей.\n"
        "Дай рекомендацию, стоит ли откликаться.\n\n"
        + vacancy_text(vacancy)
    )


def make_cover_letter(vacancy):
    return call_ai(
        "Напиши короткое сопроводительное письмо для hh.ru.\n"
        "Важно: без фразы 'Уважаемые коллеги', без '[Ваше имя]', без воды, без шаблонности.\n"
        "Длина: 4–6 строк.\n"
        "Стиль: живой, уверенный, деловой.\n"
        "Опыт кандидата: закупки, товародвижение, аналитика, Excel, 1C/ERP, контроль остатков, перемещения, поставки.\n"
        "Письмо должно проходить ATS: используй ключевые слова из вакансии и релевантный опыт.\n\n"
        + vacancy_text(vacancy)
    )


def save_vacancy_full_to_sheet(vacancy, ai_analysis="", ai_salary="", cover_letter="", status="новая"):
    response = google_get({
        "action": "save_vacancy_full",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": vacancy.get("title", ""),
        "company": vacancy.get("company", ""),
        "salary": vacancy.get("salary", ""),
        "address": vacancy.get("address", ""),
        "link": vacancy.get("link", ""),
        "category": vacancy.get("category", ""),
        "ai_score": str(vacancy.get("ai_score", "")),
        "ai_analysis": ai_analysis,
        "ai_salary": ai_salary,
        "cover_letter": cover_letter,
        "status": status,
    })

    return response.text.strip()


def save_favorite_to_sheet(chat_id, vacancy):
    response = google_get({
        "action": "save_favorite",
        "chat_id": str(chat_id),
        "title": vacancy["title"],
        "company": vacancy["company"],
        "salary": vacancy["salary"],
        "address": vacancy["address"],
        "link": vacancy["link"],
        "status": "сохранено",
    })

    return response.text.strip()


def get_favorites_from_sheet(chat_id):
    response = google_get({
        "action": "get_favorites",
        "chat_id": str(chat_id)
    })

    try:
        return response.json()
    except Exception:
        return []


def delete_favorite_from_sheet(chat_id, link):
    response = google_get({
        "action": "delete_favorite",
        "chat_id": str(chat_id),
        "link": link,
    })

    return response.text.strip()


def update_status_in_sheet(chat_id, link, status):
    response = google_get({
        "action": "update_status",
        "chat_id": str(chat_id),
        "link": link,
        "status": status,
    })

    return response.text.strip()


def add_subscriber(chat_id):
    google_get({
        "action": "add",
        "chat_id": str(chat_id)
    })


def remove_subscriber(chat_id):
    google_get({
        "action": "remove",
        "chat_id": str(chat_id)
    })


def get_subscribers():
    response = google_get({
        "action": "list"
    })

    try:
        return response.json()
    except Exception:
        return []


def send_vacancy_card(chat_id, vacancy, from_favorites=False):
    vacancy_id = vacancy.get("id") or str(uuid.uuid4())[:8]
    vacancy["id"] = vacancy_id
    VACANCY_STORAGE[vacancy_id] = vacancy

    status = vacancy.get("status", "")
    ai_score = vacancy.get("ai_score", "")

    text = (
        f"📌 {vacancy['title']}\n\n"
        f"🏢 {vacancy['company']}\n"
        f"💰 {vacancy['salary']}\n"
        f"📍 {vacancy['address']}"
    )

    if ai_score != "":
        text += f"\n⭐ Рейтинг: {ai_score}/100"

    if status:
        text += f"\n📍 Статус: {status}"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔗 Открыть вакансию", url=vacancy["link"]))

    if from_favorites:
        keyboard.add(types.InlineKeyboardButton("🟢 Откликнулась", callback_data=f"status_applied_{vacancy_id}"))
        keyboard.add(types.InlineKeyboardButton("🔴 Отказ", callback_data=f"status_rejected_{vacancy_id}"))
        keyboard.add(types.InlineKeyboardButton("⚫ Не подходит", callback_data=f"status_bad_{vacancy_id}"))
        keyboard.add(types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{vacancy_id}"))
    else:
        keyboard.add(types.InlineKeyboardButton("⭐ Сохранить", callback_data=f"save_{vacancy_id}"))
        keyboard.add(types.InlineKeyboardButton("🤖 AI-анализ", callback_data=f"ai_{vacancy_id}"))
        keyboard.add(types.InlineKeyboardButton("💰 AI-зарплата", callback_data=f"salary_{vacancy_id}"))
        keyboard.add(types.InlineKeyboardButton("✉️ Сопроводительное", callback_data=f"cover_{vacancy_id}"))

    bot.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=True)


def send_real_vacancies(chat_id, title, query, category, salary=CURRENT_SALARY, only_remote=False):
    bot.send_message(chat_id, f"{title}\n\n💰 Зарплата от {salary:,} ₽", reply_markup=main_keyboard())

    found_any = False
    search_modes = [("🏠 Удаленка — все города", "remote")]

    if not only_remote:
        search_modes.append(("🏢 Гибрид — Санкт-Петербург", "hybrid_spb"))

    for mode_title, mode in search_modes:
        bot.send_message(chat_id, mode_title)

        try:
            vacancies = get_vacancies_from_hh(query, category, salary, mode, limit=3)

            if not vacancies:
                continue

            found_any = True

            for vacancy in vacancies:
                save_vacancy_full_to_sheet(vacancy, status="найдена")
                send_vacancy_card(chat_id, vacancy)

        except Exception as error:
            print("HH ERROR:", error)

    if not found_any:
        bot.send_message(chat_id, "❌ Подходящих вакансий не найдено.", reply_markup=main_keyboard())


@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def save_callback(call):
    vacancy_id = call.data.replace("save_", "")
    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия устарела. Запусти поиск заново.")
        return

    result = save_favorite_to_sheet(call.message.chat.id, vacancy)

    if result == "favorite_saved":
        save_vacancy_full_to_sheet(vacancy, status="сохранено")
        bot.answer_callback_query(call.id, "Сохранено ⭐")
        bot.send_message(call.message.chat.id, f"⭐ Сохранила:\n\n📌 {vacancy['title']}", reply_markup=main_keyboard())
    elif result == "already_saved":
        bot.answer_callback_query(call.id, "Уже есть в избранном ⭐")
    else:
        bot.answer_callback_query(call.id, "Ошибка сохранения")
        bot.send_message(call.message.chat.id, f"⚠️ Ответ таблицы: {result}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_callback(call):
    vacancy_id = call.data.replace("delete_", "")
    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия не найдена.")
        return

    result = delete_favorite_from_sheet(call.message.chat.id, vacancy["link"])
    update_status_in_sheet(call.message.chat.id, vacancy["link"], "удалена")

    bot.answer_callback_query(call.id, "Удалено 🗑")
    bot.send_message(call.message.chat.id, f"🗑 Удалила из избранного:\n\n{vacancy['title']}\n\nОтвет: {result}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
def status_callback(call):
    parts = call.data.split("_")

    if len(parts) < 3:
        bot.answer_callback_query(call.id, "Ошибка статуса.")
        return

    status_code = parts[1]
    vacancy_id = parts[2]
    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия не найдена.")
        return

    statuses = {
        "applied": "откликнулась",
        "rejected": "отказ",
        "bad": "не подходит",
    }

    status = statuses.get(status_code, "сохранено")
    result = update_status_in_sheet(call.message.chat.id, vacancy["link"], status)

    bot.answer_callback_query(call.id, "Статус обновлен")
    bot.send_message(call.message.chat.id, f"✅ Статус: {status}\n\nОтвет: {result}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("ai_"))
def ai_callback(call):
    vacancy_id = call.data.replace("ai_", "")
    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия не найдена.")
        return

    bot.answer_callback_query(call.id, "Делаю анализ...")
    answer = make_ai_analysis(vacancy)
    save_vacancy_full_to_sheet(vacancy, ai_analysis=answer, status="проанализирована")

    bot.send_message(call.message.chat.id, f"🤖 AI-анализ:\n\n{answer}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("salary_"))
def salary_callback(call):
    vacancy_id = call.data.replace("salary_", "")
    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия не найдена.")
        return

    bot.answer_callback_query(call.id, "Оцениваю зарплату...")
    answer = make_ai_salary(vacancy)
    save_vacancy_full_to_sheet(vacancy, ai_salary=answer, status="зарплата оценена")

    bot.send_message(call.message.chat.id, f"💰 AI-оценка зарплаты:\n\n{answer}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("cover_"))
def cover_callback(call):
    vacancy_id = call.data.replace("cover_", "")
    vacancy = VACANCY_STORAGE.get(vacancy_id)

    if not vacancy:
        bot.answer_callback_query(call.id, "Вакансия не найдена.")
        return

    bot.answer_callback_query(call.id, "Пишу сопроводительное...")
    answer = make_cover_letter(vacancy)
    save_vacancy_full_to_sheet(vacancy, cover_letter=answer, status="письмо готово")

    bot.send_message(call.message.chat.id, f"✉️ Сопроводительное:\n\n{answer}")


def show_favorites(message):
    favorites = get_favorites_from_sheet(message.chat.id)

    if not favorites:
        bot.send_message(message.chat.id, "⭐ Избранное пока пустое.", reply_markup=main_keyboard())
        return

    bot.send_message(message.chat.id, f"⭐ Избранные вакансии: {len(favorites)}", reply_markup=main_keyboard())

    for item in favorites:
        vacancy = {
            "id": str(uuid.uuid4())[:8],
            "title": item.get("title", ""),
            "company": item.get("company", ""),
            "salary": item.get("salary", ""),
            "address": item.get("address", ""),
            "link": item.get("link", ""),
            "status": item.get("status", "сохранено"),
            "category": "",
            "ai_score": "",
        }

        send_vacancy_card(message.chat.id, vacancy, from_favorites=True)


def send_daily_jobs_to_chat(chat_id):
    bot.send_message(chat_id, "🔔 Ежедневная подборка вакансий", reply_markup=main_keyboard())
    send_real_vacancies(chat_id, "🔎 Закупки", "менеджер по закупкам", "Закупки")
    send_real_vacancies(chat_id, "📦 Товародвижение", "товародвижение", "Товародвижение")
    send_real_vacancies(chat_id, "📊 Аналитик", "аналитик закупок", "Аналитик")
    send_real_vacancies(chat_id, "🗂 Категорийный менеджер", "категорийный менеджер", "Категорийный менеджер")


def daily_jobs():
    subscribers = get_subscribers()

    for chat_id in subscribers:
        try:
            send_daily_jobs_to_chat(chat_id)
        except Exception as error:
            print("DAILY SEND ERROR:", error)


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
        "v1.1: вакансии сохраняются в Google Sheets вместе с AI-анализом, зарплатой и сопроводительным.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "🔔 Включить рассылку")
def enable_notifications(message):
    add_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "🔔 Рассылка включена. Каждый день в 10:00 по Москве.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == "🔕 Выключить рассылку")
def disable_notifications(message):
    remove_subscriber(message.chat.id)
    bot.send_message(message.chat.id, "🔕 Рассылка выключена.", reply_markup=main_keyboard())


@bot.message_handler(func=lambda message: message.text == "🔎 Закупки")
def purchases(message):
    send_real_vacancies(message.chat.id, "🔎 Закупки", "менеджер по закупкам", "Закупки")


@bot.message_handler(func=lambda message: message.text == "📦 Товародвижение")
def goods_movement(message):
    send_real_vacancies(message.chat.id, "📦 Товародвижение", "товародвижение", "Товародвижение")


@bot.message_handler(func=lambda message: message.text == "📊 Аналитик")
def analyst(message):
    send_real_vacancies(message.chat.id, "📊 Аналитик", "аналитик закупок", "Аналитик")


@bot.message_handler(func=lambda message: message.text == "🗂 Категорийный менеджер")
def category_manager(message):
    send_real_vacancies(message.chat.id, "🗂 Категорийный менеджер", "категорийный менеджер", "Категорийный менеджер")


@bot.message_handler(func=lambda message: message.text == "🔥 Лучшие сегодня")
def best_today(message):
    send_daily_jobs_to_chat(message.chat.id)


@bot.message_handler(func=lambda message: message.text == "🏠 Только удаленка")
def only_remote(message):
    send_real_vacancies(message.chat.id, "🏠 Только удаленка", "менеджер по закупкам", "Закупки", only_remote=True)


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
        "Выбери направление. Вакансии и AI-данные автоматически сохраняются в Google Sheets.",
        reply_markup=main_keyboard()
    )


@bot.message_handler(func=lambda message: True)
def unknown(message):
    bot.send_message(message.chat.id, "Используй кнопки ниже 👇", reply_markup=main_keyboard())


def run_bot():
    while True:
        try:
            print("Бот запускается...")

            try:
                bot.remove_webhook()
                time.sleep(5)
            except Exception as error:
                print("REMOVE WEBHOOK ERROR:", error)

            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                allowed_updates=["message", "callback_query"],
                skip_pending=True
            )

        except Exception as error:
            print("BOT ERROR:", error)
            time.sleep(30)


run_bot()

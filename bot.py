import os
import uuid
import time
import threading
import schedule
import requests
import telebot

from telebot import types
from datetime import datetime, timezone


TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not TOKEN:
    raise ValueError("Не найден BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwf3UPzjUZIzLsn64wluSEMBp3uRA91sIEWwz6104WzSKRSy5OajIBuDLTb3hGB21Ui/exec"

VACANCY_STORAGE = {}
CURRENT_SALARY = 100000
HH_API_URL = "https://api.hh.ru/vacancies"


RESUME_PROFILES = {
    "Закупки": """
Резюме под закупки:
Менеджер по закупкам. Опыт: закупки, товарные запасы, работа с поставщиками, 1С:ERP, аналитика продаж, управление ассортиментом.
Релевантные факты: Рив Гош — менеджер по закупкам, контроль товарного запаса, анализ остатков, продаж и оборачиваемости, работа с отчетностью в 1С, оптимизация закупок.
Ле Муррр — ассортиментная матрица 5000+ SKU, ABC/XYZ, снижение низкооборачиваемых товаров с 8% до 4%, сокращение избыточных закупок на 17%.
SKL Group — анализ остатков и движения ТМЦ по 5 складам, автоматизация отчетности.
""",
    "Товародвижение": """
Резюме под товародвижение:
Менеджер по товародвижению. Опыт: движение ТМЦ, товарный учет, остатки, перемещения, логистика, склады, 1С/ERP, Excel.
Релевантные факты: SKL Group — анализ товарных остатков и движения ТМЦ по 5 складам, контроль корректности товарного учета и товародвижения, анализ потерь и избыточных запасов, взаимодействие с логистикой и складами.
Результат: автоматизация отчетности с 2 недель до 10 минут.
""",
    "Аналитик": """
Резюме под аналитику:
Аналитик товарных запасов / коммерческий аналитик. Опыт: ABC/XYZ-анализ, SKU-аналитика, анализ продаж, маржинальности, оборачиваемости, Excel, XLOOKUP/ВПР, сводные таблицы, 1С:ERP, DocsVision.
Релевантные факты: ассортимент 5000+ SKU, снижение неликвидов, оптимизация товарных запасов, автоматизация отчетности, коммерческая аналитика.
""",
    "Категорийный менеджер": """
Резюме под категорийного менеджера:
Категорийный менеджер / менеджер по планированию. Опыт: ассортиментная матрица 5000+ SKU, анализ продаж, маржинальности, оборачиваемости, контроль неликвидов, ABC/XYZ, оптимизация закупок и товарного планирования.
Результаты: снижение низкооборачиваемых товаров с 8% до 4%, сокращение избыточных закупок на 17%.
"""
}


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
    "1с-программист", "разработчик 1с", "middle", "senior",
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

SKIP_STATUSES = [
    "новая",
    "ai готов",
    "сохранено",
    "откликнулась",
    "отказ",
    "не подходит",
    "собеседование",
    "удалена",
]


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "🗂 Категорийный менеджер")
    keyboard.row("🔥 Лучшие сегодня", "🏠 Только удаленка")
    keyboard.row("💰 Зарплата 150k+", "⭐ Избранное")
    keyboard.row("🔔 Включить рассылку", "🔕 Выключить рассылку")
    keyboard.row("❓ Помощь")
    return keyboard


def google_get(params):
    response = requests.get(SCRIPT_URL, params=params, timeout=30)
    print("GOOGLE RESPONSE:", response.text[:500])
    return response


def test_google_connection():
    try:
        response = google_get({"action": "ping"})
        return response.text.strip()
    except Exception as error:
        return f"error: {error}"


def get_vacancy_status(link):
    try:
        response = google_get({
            "action": "get_vacancy_status",
            "link": link
        })
        return response.text.strip().lower()
    except Exception as error:
        print("GET VACANCY STATUS ERROR:", error)
        return "not_found"


def should_skip_vacancy(link):
    status = get_vacancy_status(link)

    if status in SKIP_STATUSES:
        print(f"SKIP VACANCY: {link} / status={status}")
        return True

    return False


def detect_work_format_from_api(vacancy):
    employment = vacancy.get("employment") or {}
    schedule = vacancy.get("schedule") or {}
    work_format = vacancy.get("work_format") or []
    working_days = vacancy.get("working_days") or []

    parts = []

    for item in work_format:
        name = item.get("name")
        if name:
            parts.append(name)

    if schedule.get("name"):
        parts.append(schedule.get("name"))

    for item in working_days:
        name = item.get("name")
        if name:
            parts.append(name)

    if employment.get("name"):
        parts.append(employment.get("name"))

    if not parts:
        return "не указан"

    text = ", ".join(parts).lower()

    if "удален" in text or "remote" in text:
        return "удалённо"

    if "гибрид" in text:
        return "гибрид"

    if "полный день" in text:
        return "офис / полный день"

    return ", ".join(parts)


def format_salary(salary):
    if not salary:
        return "Зарплата не указана"

    salary_from = salary.get("from")
    salary_to = salary.get("to")
    currency = salary.get("currency") or ""

    if salary_from and salary_to:
        return f"{salary_from}–{salary_to} {currency}"

    if salary_from:
        return f"от {salary_from} {currency}"

    if salary_to:
        return f"до {salary_to} {currency}"

    return "Зарплата не указана"


def is_good_vacancy(vacancy, category):
    full_text = (
        vacancy.get("title", "") + " " +
        vacancy.get("company", "") + " " +
        vacancy.get("salary", "") + " " +
        vacancy.get("address", "") + " " +
        vacancy.get("work_format", "")
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
        vacancy.get("address", "") + " " +
        vacancy.get("work_format", "")
    ).lower()

    score = 50

    for good_word in GOOD_WORDS_BY_CATEGORY.get(category, []):
        if good_word in title:
            score += 10

    if "удал" in text:
        score += 12

    if "гибрид" in text:
        score += 8

    if "150" in text or "160" in text or "170" in text or "180" in text or "200" in text:
        score += 10

    for bad_word in BAD_WORDS_COMMON:
        if bad_word in text:
            score -= 25

    return max(0, min(100, score))


def get_vacancies_from_hh(query, category, salary, only_remote=False, limit=3):
    params = {
        "text": query,
        "area": 113,
        "salary": salary,
        "only_with_salary": "true",
        "period": 1,
        "per_page": 30,
        "order_by": "publication_time",
        "search_field": ["name", "company_name", "description"],
    }

    response = requests.get(
    HH_API_URL,
    params=params,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "HH-User-Agent": "career-assistant-bot/1.6 (tany.130483q@gmail.com)"
    },
    timeout=30
)
    response.raise_for_status()

    data = response.json()
    items = data.get("items", [])

    vacancies = []

    for item in items:
        link = item.get("alternate_url", "")

        if not link:
            continue

        if should_skip_vacancy(link):
            continue

        title = item.get("name", "")
        company = (item.get("employer") or {}).get("name", "Компания не указана")
        area = (item.get("area") or {}).get("name", "Город не указан")
        salary_text = format_salary(item.get("salary"))
        work_format = detect_work_format_from_api(item)

        if only_remote and "удал" not in work_format.lower():
            continue

        vacancy = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "company": company,
            "salary": salary_text,
            "address": area,
            "work_format": work_format,
            "link": link,
            "category": category,
            "posted_time": item.get("published_at", ""),
        }

        if is_good_vacancy(vacancy, category):
            vacancy["ai_score"] = vacancy_score(vacancy, category)
            vacancies.append(vacancy)

        if len(vacancies) >= limit:
            break

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
                        "content": "Ты карьерный ассистент. Пиши по-русски, коротко, практично, без шаблонов и без AI-стиля."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    },
                ],
                "temperature": 0.35,
                "max_tokens": 700,
            },
            timeout=60,
        )

        data = response.json()

        if response.status_code != 200:
            error_message = data.get("error", {}).get("message", str(data))
            return f"Ошибка OpenAI API:\n{error_message}"

        return data["choices"][0]["message"]["content"]

    except Exception as error:
        return f"Ошибка AI-запроса: {error}"


def get_resume_profile(category):
    return RESUME_PROFILES.get(category, RESUME_PROFILES["Аналитик"])


def vacancy_text(vacancy):
    return (
        f"Название: {vacancy.get('title')}\n"
        f"Компания: {vacancy.get('company')}\n"
        f"Зарплата: {vacancy.get('salary')}\n"
        f"Город: {vacancy.get('address')}\n"
        f"Формат работы: {vacancy.get('work_format')}\n"
        f"Категория: {vacancy.get('category')}\n"
        f"Дата публикации: {vacancy.get('posted_time')}\n"
        f"Ссылка: {vacancy.get('link')}"
    )


def make_ai_analysis(vacancy):
    resume = get_resume_profile(vacancy.get("category", ""))

    return call_ai(
        "Проанализируй вакансию для кандидата.\n\n"
        f"{resume}\n\n"
        "Задача:\n"
        "1. Подходит ли вакансия кандидату.\n"
        "2. Какие ключевые совпадения с резюме.\n"
        "3. Какие риски: продажи, холодные звонки, английский, системная аналитика, офис.\n"
        "4. Стоит ли откликаться.\n"
        "Ответ коротко, без воды.\n\n"
        "Вакансия:\n"
        + vacancy_text(vacancy)
    )


def make_ai_salary(vacancy):
    resume = get_resume_profile(vacancy.get("category", ""))

    return call_ai(
        "Оцени зарплату по вакансии.\n\n"
        f"{resume}\n\n"
        "Цель кандидата: 100–150k+ рублей.\n"
        "Ответь кратко:\n"
        "1. Зарплата ниже рынка / нормальная / хорошая.\n"
        "2. Стоит ли откликаться.\n"
        "3. Если зарплата не указана — какой диапазон можно ожидать.\n\n"
        "Вакансия:\n"
        + vacancy_text(vacancy)
    )


def make_company_rating(vacancy):
    return call_ai(
        "Оцени компанию и вакансию с точки зрения риска для кандидата.\n\n"
        "Нужно определить company_rating:\n"
        "🟢 Хорошая — вакансия выглядит адекватно.\n"
        "🟡 Нормальная — есть вопросы, но можно рассмотреть.\n"
        "🔴 Подозрительная — есть признаки мусорной вакансии, скрытых продаж, массового найма, странных условий.\n\n"
        "Ответ должен быть коротким: сначала один из трех рейтингов, потом 1–2 причины.\n\n"
        "Вакансия:\n"
        + vacancy_text(vacancy)
    )


def make_cover_letter(vacancy):
    resume = get_resume_profile(vacancy.get("category", ""))

    return call_ai(
        "Напиши короткое сопроводительное письмо для hh.ru.\n\n"

        "Кандидат — женщина.\n"
        "Письмо ОБЯЗАТЕЛЬНО писать в женском роде.\n\n"

        "Пиши в стиле обычного живого человека, а не как ChatGPT.\n"
        "Текст должен выглядеть как нормальный отклик на hh.ru.\n"
        "Стиль: спокойно, уверенно, по-деловому.\n"
        "Без пафоса и без слишком идеальных формулировок.\n\n"

        "ПРИМЕР СТИЛЯ:\n"
        "Здравствуйте!\n"
        "Заинтересовала ваша вакансия, потому что у меня как раз есть опыт в ...\n"
        "Последние несколько лет работала с ...\n"
        "Хорошо владею Excel, 1С ...\n"
        "Думаю, мой опыт будет полезен вашей команде. Буду рада пообщаться подробнее.\n\n"

        "ЗАПРЕЩЕНО:\n"
        "- 'Уважаемые коллеги'\n"
        "- 'Меня зовут'\n"
        "- 'Вижу, что ваша команда ищет'\n"
        "- 'Уверен, что мой опыт'\n"
        "- 'Уверена, что мой опыт'\n"
        "- 'достижения целей вашей компании'\n"
        "- 'готова внести вклад'\n"
        "- слишком официальные формулировки\n"
        "- AI-style текст\n"
        "- длинные абзацы\n"
        "- чрезмерно продавать себя\n"
        "- перечислять цифры из резюме без необходимости\n\n"

        "ТРЕБОВАНИЯ:\n"
        "- 4–6 предложений\n"
        "- 2–3 коротких абзаца\n"
        "- использовать ключевые слова из вакансии естественно\n"
        "- письмо должно проходить ATS\n"
        "- адаптировать письмо под конкретную вакансию\n"
        "- использовать только релевантный опыт из резюме\n"
        "- не выдумывать опыт\n"
        "- использовать женский род\n"
        "- писать от лица Татьяны\n\n"

        f"Резюме кандидата:\n{resume}\n\n"

        f"Вакансия:\n{vacancy_text(vacancy)}\n\n"

        "Верни только текст письма."
    )


def make_full_ai_pack(vacancy):
    ai_analysis = make_ai_analysis(vacancy)
    time.sleep(1)

    ai_salary = make_ai_salary(vacancy)
    time.sleep(1)

    cover_letter = make_cover_letter(vacancy)
    time.sleep(1)

    company_rating = make_company_rating(vacancy)

    return ai_analysis, ai_salary, cover_letter, company_rating


def save_vacancy_full_to_sheet(
    vacancy,
    ai_analysis="",
    ai_salary="",
    cover_letter="",
    company_rating="",
    status="новая"
):
    response = google_get({
        "action": "save_vacancy_full",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "title": vacancy.get("title", ""),
        "company": vacancy.get("company", ""),
        "salary": vacancy.get("salary", ""),
        "address": vacancy.get("address", ""),
        "work_format": vacancy.get("work_format", ""),
        "link": vacancy.get("link", ""),
        "category": vacancy.get("category", ""),
        "ai_score": str(vacancy.get("ai_score", "")),
        "ai_analysis": ai_analysis,
        "ai_salary": ai_salary,
        "cover_letter": cover_letter,
        "status": status,
        "company_rating": company_rating,
        "posted_time": vacancy.get("posted_time", ""),
    })

    result = response.text.strip()
    print("SAVE VACANCY RESULT:", result)
    return result


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
        f"📍 {vacancy['address']}\n"
        f"🏠 Формат: {vacancy.get('work_format', 'не указан')}\n"
        f"🕒 Опубликована: {vacancy.get('posted_time', 'не указано')}"
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

    bot.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=True)


def send_real_vacancies(chat_id, title, query, category, salary=CURRENT_SALARY, only_remote=False):
    bot.send_message(
        chat_id,
        f"{title}\n\n💰 Зарплата от {salary:,} ₽\n🕒 Только вакансии за последние 24 часа",
        reply_markup=main_keyboard()
    )

    found_any = False

    try:
        vacancies = get_vacancies_from_hh(
            query=query,
            category=category,
            salary=salary,
            only_remote=only_remote,
            limit=3
        )

        if vacancies:
            found_any = True

        for vacancy in vacancies:
            bot.send_message(chat_id, f"🤖 Анализирую и сохраняю в таблицу:\n{vacancy['title']}")

            ai_analysis, ai_salary, cover_letter, company_rating = make_full_ai_pack(vacancy)

            save_vacancy_full_to_sheet(
                vacancy,
                ai_analysis=ai_analysis,
                ai_salary=ai_salary,
                cover_letter=cover_letter,
                company_rating=company_rating,
                status="новая"
            )

            send_vacancy_card(chat_id, vacancy)

    except Exception as error:
        print("HH ERROR:", error)
        bot.send_message(chat_id, f"⚠️ Ошибка поиска/записи:\n{error}")

    if not found_any:
        bot.send_message(
            chat_id,
            "❌ Новых подходящих вакансий за последние 24 часа не найдено.",
            reply_markup=main_keyboard()
        )


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
            "work_format": item.get("work_format", ""),
            "link": item.get("link", ""),
            "status": item.get("status", "сохранено"),
            "category": "",
            "ai_score": "",
            "posted_time": "",
        }

        send_vacancy_card(message.chat.id, vacancy, from_favorites=True)


def send_daily_jobs_to_chat(chat_id):
    bot.send_message(chat_id, "🔔 Ежедневная подборка новых вакансий за 24 часа", reply_markup=main_keyboard())
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
    google_status = test_google_connection()

    bot.send_message(
        message.chat.id,
        "Бот работает ✅\n\n"
        "v1.6: только вакансии за 24 часа + AI-рейтинг компании.\n"
        f"Google Sheets API: {google_status}",
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
        "Бот ищет только свежие вакансии за 24 часа, сохраняет AI-анализ и рейтинг компании в Google Sheets.",
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

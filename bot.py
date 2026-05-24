import telebot
from telebot import types
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

TOKEN = os.getenv("8878670055:AAFzmS9p8yfP1NZA7pxhTe-bpZjcGUQkp88")
bot = telebot.TeleBot(TOKEN)

# =========================
# GOOGLE SHEETS
# =========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json",
    scope
)

client = gspread.authorize(creds)

spreadsheet = client.open("hh-career-bot-data")

subscribers_sheet = spreadsheet.worksheet("subscribers")
favorites_sheet = spreadsheet.worksheet("favorites")

# =========================
# HH API
# =========================
BASE_URL = "https://api.hh.ru/vacancies"

HEADERS = {
    "User-Agent": "hh-career-bot"
}

# =========================
# КНОПКИ
# =========================
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

    kb.row("🔔 Включить рассылку", "📌 Отключить рассылку")
    kb.row("🔎 Закупки", "📦 Товародвижение")
    kb.row("📊 Аналитик", "📁 Категорийный менеджер")
    kb.row("🔥 Лучшие сегодня", "🏠 Только удаленка")
    kb.row("⭐ Избранное")

    return kb

# =========================
# HH ПОИСК
# =========================
def get_vacancies(text):

    params = {
        "text": text,
        "per_page": 5,
        "area": 2,  # СПБ
        "only_with_salary": False
    }

    response = requests.get(
        BASE_URL,
        headers=HEADERS,
        params=params,
        timeout=15
    )

    if response.status_code != 200:
        return []

    data = response.json()

    if "items" not in data:
        return []

    return data["items"]

# =========================
# КАРТОЧКА ВАКАНСИИ
# =========================
def send_vacancy(chat_id, vacancy):

    title = vacancy.get("name", "Без названия")

    employer = "Не указано"
    if vacancy.get("employer"):
        employer = vacancy["employer"].get("name", "Не указано")

    salary = "Зарплата не указана"

    if vacancy.get("salary"):
        s = vacancy["salary"]

        salary_from = s.get("from")
        salary_to = s.get("to")
        currency = s.get("currency", "")

        if salary_from and salary_to:
            salary = f"{salary_from}-{salary_to} {currency}"

        elif salary_from:
            salary = f"от {salary_from} {currency}"

        elif salary_to:
            salary = f"до {salary_to} {currency}"

    address = "Не указан"

    if vacancy.get("area"):
        address = vacancy["area"].get("name", "Не указан")

    link = vacancy.get("alternate_url", "")

    text = (
        f"📌 <b>{title}</b>\n\n"
        f"🏢 {employer}\n"
        f"💰 {salary}\n"
        f"📍 {address}"
    )

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            "🔗 Открыть вакансию",
            url=link
        )
    )

    kb.add(
        types.InlineKeyboardButton(
            "⭐ Сохранить вакансию",
            callback_data=f"save|{title}|{employer}|{salary}|{address}|{link}"
        )
    )

    bot.send_message(
        chat_id,
        text,
        parse_mode="HTML",
        reply_markup=kb
    )

# =========================
# СОХРАНЕНИЕ ВАКАНСИИ
# =========================
@bot.callback_query_handler(func=lambda call: call.data.startswith("save|"))
def save_vacancy(call):

    try:
        data = call.data.split("|")

        title = data[1]
        company = data[2]
        salary = data[3]
        address = data[4]
        link = data[5]

        favorites_sheet.append_row([
            str(call.message.chat.id),
            title,
            company,
            salary,
            address,
            link
        ])

        bot.answer_callback_query(
            call.id,
            "Вакансия сохранена ⭐"
        )

        bot.send_message(
            call.message.chat.id,
            f"⭐ Сохранила вакансию:\n\n{title}"
        )

    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            f"Ошибка сохранения:\n{e}"
        )

# =========================
# ИЗБРАННОЕ
# =========================
def show_favorites(chat_id):

    rows = favorites_sheet.get_all_values()

    found = False

    for row in rows[1:]:

        if str(row[0]) == str(chat_id):

            found = True

            text = (
                f"⭐ <b>{row[1]}</b>\n\n"
                f"🏢 {row[2]}\n"
                f"💰 {row[3]}\n"
                f"📍 {row[4]}\n\n"
                f"{row[5]}"
            )

            bot.send_message(
                chat_id,
                text,
                parse_mode="HTML"
            )

    if not found:
        bot.send_message(chat_id, "Избранного пока нет.")

# =========================
# START
# =========================
@bot.message_handler(commands=["start"])
def start(message):

    bot.send_message(
        message.chat.id,
        "Привет 👋\nЯ карьерный ассистент Татьяны.",
        reply_markup=main_keyboard()
    )

# =========================
# ТЕКСТ
# =========================
@bot.message_handler(func=lambda m: True)
def handle_text(message):

    text = message.text
    chat_id = message.chat.id

    # -------------------------
    # ВКЛ РАССЫЛКИ
    # -------------------------
    if text == "🔔 Включить рассылку":

        subscribers = subscribers_sheet.col_values(1)

        if str(chat_id) not in subscribers:
            subscribers_sheet.append_row([str(chat_id)])

        bot.send_message(
            chat_id,
            "🔔 Рассылка включена.\nКаждый день в 10:00 по Москве буду присылать вакансии."
        )

    # -------------------------
    # ВЫКЛ РАССЫЛКИ
    # -------------------------
    elif text == "📌 Отключить рассылку":

        rows = subscribers_sheet.get_all_values()

        for i, row in enumerate(rows):

            if row and row[0] == str(chat_id):
                subscribers_sheet.delete_rows(i + 1)
                break

        bot.send_message(
            chat_id,
            "📌 Рассылка выключена."
        )

    # -------------------------
    # ИЗБРАННОЕ
    # -------------------------
    elif text == "⭐ Избранное":

        show_favorites(chat_id)

    # -------------------------
    # ПОИСК ВАКАНСИЙ
    # -------------------------
    else:

        query = ""

        if text == "🔎 Закупки":
            query = "менеджер по закупкам"

        elif text == "📦 Товародвижение":
            query = "товародвижение"

        elif text == "📊 Аналитик":
            query = "аналитик"

        elif text == "📁 Категорийный менеджер":
            query = "категорийный менеджер"

        elif text == "🔥 Лучшие сегодня":
            query = "менеджер"

        elif text == "🏠 Только удаленка":
            query = "удаленная работа"

        if query:

            vacancies = get_vacancies(query)

            if not vacancies:
                bot.send_message(
                    chat_id,
                    "Вакансии не найдены."
                )
                return

            for vacancy in vacancies:
                send_vacancy(chat_id, vacancy)

# =========================
# RUN
# =========================
print("BOT STARTED")

bot.infinity_polling(skip_pending=True)

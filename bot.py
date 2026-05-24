import telebot
from telebot import types
import requests
import json
import os

TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwf3UPzjUZIzLsn64wluSEMBp3uRA91sIEWwz6104WzSKRSy5OajIBuDLTb3hGB21Ui/exec"

favorites_memory = {}

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# =========================================
# HH API
# =========================================

def get_vacancies(text=""):
    url = "https://api.hh.ru/vacancies"

    params = {
        "text": text,
        "per_page": 5,
        "order_by": "publication_time"
    }

    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code != 200:
        return []

    data = response.json()

    return data.get("items", [])


# =========================================
# GOOGLE SHEETS
# =========================================

def save_favorite(chat_id, vacancy):
    params = {
        "action": "save_favorite",
        "chat_id": chat_id,
        "title": vacancy["title"],
        "company": vacancy["company"],
        "salary": vacancy["salary"],
        "address": vacancy["address"],
        "link": vacancy["link"]
    }

    requests.get(GOOGLE_SCRIPT_URL, params=params)


def get_favorites(chat_id):
    params = {
        "action": "get_favorites",
        "chat_id": chat_id
    }

    response = requests.get(GOOGLE_SCRIPT_URL, params=params)

    try:
        return response.json()
    except:
        return []


# =========================================
# КНОПКИ
# =========================================

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("🔔 Включить рассылку", "📌 Выключить рассылку")
    keyboard.row("🔎 Закупки", "📦 Товародвижение")
    keyboard.row("📊 Аналитик", "📁 Категорийный менеджер")
    keyboard.row("🔥 Лучшие сегодня", "🏠 Только удаленка")
    keyboard.row("💰 Зарплата 150k+", "⭐ Избранное")

    return keyboard


# =========================================
# START
# =========================================

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет 👋\nЯ карьерный ассистент Татьяны.",
        reply_markup=main_keyboard()
    )


# =========================================
# РАССЫЛКА
# =========================================

@bot.message_handler(func=lambda m: m.text == "🔔 Включить рассылку")
def enable_sub(message):
    chat_id = message.chat.id

    requests.get(
        GOOGLE_SCRIPT_URL,
        params={
            "action": "add",
            "chat_id": chat_id
        }
    )

    bot.send_message(
        chat_id,
        "🔔 Рассылка включена.\nКаждый день в 10:00 по Москве буду присылать вакансии."
    )


@bot.message_handler(func=lambda m: m.text == "📌 Выключить рассылку")
def disable_sub(message):
    chat_id = message.chat.id

    requests.get(
        GOOGLE_SCRIPT_URL,
        params={
            "action": "remove",
            "chat_id": chat_id
        }
    )

    bot.send_message(chat_id, "📌 Рассылка выключена.")


# =========================================
# ИЗБРАННОЕ
# =========================================

@bot.message_handler(func=lambda m: m.text == "⭐ Избранное")
def show_favorites(message):
    chat_id = message.chat.id

    favorites = get_favorites(chat_id)

    if not favorites:
        bot.send_message(chat_id, "Избранного пока нет.")
        return

    for item in favorites:
        text = f"""
⭐ <b>{item['title']}</b>

🏢 {item['company']}
💰 {item['salary']}
📍 {item['address']}

🔗 {item['link']}
"""

        bot.send_message(
            chat_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True
        )


# =========================================
# ВАКАНСИИ
# =========================================

def send_vacancies(chat_id, query):
    vacancies = get_vacancies(query)

    if not vacancies:
        bot.send_message(chat_id, "Вакансии не найдены.")
        return

    for vac in vacancies:

        salary = "Не указана"

        if vac.get("salary"):
            s = vac["salary"]

            frm = s.get("from")
            to = s.get("to")
            cur = s.get("currency", "")

            if frm and to:
                salary = f"{frm} - {to} {cur}"
            elif frm:
                salary = f"от {frm} {cur}"
            elif to:
                salary = f"до {to} {cur}"

        vacancy_data = {
            "title": vac["name"],
            "company": vac["employer"]["name"],
            "salary": salary,
            "address": vac.get("area", {}).get("name", "Не указано"),
            "link": vac["alternate_url"]
        }

        text = f"""
<b>{vacancy_data['title']}</b>

🏢 {vacancy_data['company']}
💰 {vacancy_data['salary']}
📍 {vacancy_data['address']}

🔗 {vacancy_data['link']}
"""

        keyboard = types.InlineKeyboardMarkup()

        save_btn = types.InlineKeyboardButton(
            "⭐ Сохранить",
            callback_data=f"save_{vac['id']}"
        )

        keyboard.add(save_btn)

        favorites_memory[vac["id"]] = vacancy_data

        bot.send_message(
            chat_id,
            text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=keyboard
        )


# =========================================
# CALLBACK
# =========================================

@bot.callback_query_handler(func=lambda call: call.data.startswith("save_"))
def save_callback(call):
    vacancy_id = call.data.replace("save_", "")

    vacancy = favorites_memory.get(vacancy_id)

    if vacancy:
        save_favorite(call.message.chat.id, vacancy)

        bot.answer_callback_query(
            call.id,
            "Вакансия сохранена ⭐"
        )


# =========================================
# КНОПКИ ПОИСКА
# =========================================

@bot.message_handler(func=lambda m: m.text == "🔎 Закупки")
def zakupki(message):
    bot.send_message(message.chat.id, "Показываю вакансии по закупкам.")
    send_vacancies(message.chat.id, "специалист по закупкам")


@bot.message_handler(func=lambda m: m.text == "📦 Товародвижение")
def move(message):
    bot.send_message(message.chat.id, "Показываю вакансии по товародвижению.")
    send_vacancies(message.chat.id, "товародвижение")


@bot.message_handler(func=lambda m: m.text == "📊 Аналитик")
def analyst(message):
    bot.send_message(message.chat.id, "Показываю вакансии аналитика.")
    send_vacancies(message.chat.id, "аналитик")


@bot.message_handler(func=lambda m: m.text == "📁 Категорийный менеджер")
def category(message):
    bot.send_message(message.chat.id, "Показываю вакансии категорийного менеджера.")
    send_vacancies(message.chat.id, "категорийный менеджер")


@bot.message_handler(func=lambda m: m.text == "🔥 Лучшие сегодня")
def best(message):
    bot.send_message(message.chat.id, "Показываю лучшие вакансии.")
    send_vacancies(message.chat.id, "middle senior")


@bot.message_handler(func=lambda m: m.text == "🏠 Только удаленка")
def remote(message):
    bot.send_message(message.chat.id, "Показываю удаленные вакансии.")
    send_vacancies(message.chat.id, "удаленная работа")


@bot.message_handler(func=lambda m: m.text == "💰 Зарплата 150k+")
def salary(message):
    bot.send_message(message.chat.id, "Показываю вакансии с зарплатой 150k+.")
    send_vacancies(message.chat.id, "150000")


# =========================================
# RUN
# =========================================

print("BOT STARTED")

bot.infinity_polling(skip_pending=True)

import telebot
from telebot import types
import requests
import time
import threading

TOKEN = "ТВОЙ_ТОКЕН"

SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwf3UPzjUZIzLsn64wluSEMBp3uRA91sIEWwz6104WzSKRSy5OajIBuDLTb3hGB21Ui/exec"

bot = telebot.TeleBot(TOKEN)

# =========================
# HH API
# =========================

HH_URL = "https://api.hh.ru/vacancies"

SEARCHES = {
    "Закупки": "менеджер по закупкам",
    "Товародвижение": "товародвижение",
    "Аналитик": "аналитик",
    "Категорийный менеджер": "категорийный менеджер"
}


# =========================
# КНОПКИ
# =========================

def main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    markup.row("🔔 Включить рассылку", "🔕 Выключить рассылку")

    markup.row("🔎 Закупки", "📦 Товародвижение")
    markup.row("📊 Аналитик", "🗂 Категорийный менеджер")

    markup.row("🔥 Лучшие сегодня", "🏠 Только удаленка")
    markup.row("💰 Зарплата 150k+")

    return markup


# =========================
# HH ПОИСК
# =========================

def get_vacancies(search_text):

    params = {
        "text": search_text,
        "per_page": 5,
        "area": 113
    }

    response = requests.get(HH_URL, params=params).json()

    vacancies = []

    for item in response.get("items", []):

        title = item["name"]

        company = item["employer"]["name"]

        url = item["alternate_url"]

        salary = "Не указана"

        if item["salary"]:
            salary_from = item["salary"]["from"]
            salary_to = item["salary"]["to"]

            if salary_from and salary_to:
                salary = f"{salary_from} - {salary_to}"

            elif salary_from:
                salary = f"от {salary_from}"

            elif salary_to:
                salary = f"до {salary_to}"

        text = (
            f"💼 {title}\n"
            f"🏢 {company}\n"
            f"💰 {salary}\n\n"
            f"{url}"
        )

        vacancies.append(text)

    return vacancies


# =========================
# START
# =========================

@bot.message_handler(commands=['start'])
def start(message):

    bot.send_message(
        message.chat.id,
        "Привет 👋\nЯ карьерный бот Татьяны.",
        reply_markup=main_keyboard()
    )


# =========================
# ПОДПИСКА
# =========================

@bot.message_handler(func=lambda m: m.text == "🔔 Включить рассылку")
def subscribe(message):

    requests.get(
        SCRIPT_URL,
        params={
            "action": "add",
            "chat_id": message.chat.id
        }
    )

    bot.send_message(
        message.chat.id,
        "🔔 Рассылка включена."
    )


@bot.message_handler(func=lambda m: m.text == "🔕 Выключить рассылку")
def unsubscribe(message):

    requests.get(
        SCRIPT_URL,
        params={
            "action": "remove",
            "chat_id": message.chat.id
        }
    )

    bot.send_message(
        message.chat.id,
        "🔕 Рассылка выключена."
    )


# =========================
# КНОПКИ ВАКАНСИЙ
# =========================

@bot.message_handler(func=lambda m: True)
def buttons(message):

    text = message.text

    if text == "🔎 Закупки":

        vacancies = get_vacancies(
            SEARCHES["Закупки"]
        )

    elif text == "📦 Товародвижение":

        vacancies = get_vacancies(
            SEARCHES["Товародвижение"]
        )

    elif text == "📊 Аналитик":

        vacancies = get_vacancies(
            SEARCHES["Аналитик"]
        )

    elif text == "🗂 Категорийный менеджер":

        vacancies = get_vacancies(
            SEARCHES["Категорийный менеджер"]
        )

    elif text == "🔥 Лучшие сегодня":

        vacancies = get_vacancies(
            "менеджер"
        )

    elif text == "🏠 Только удаленка":

        vacancies = get_vacancies(
            "удаленная работа"
        )

    elif text == "💰 Зарплата 150k+":

        vacancies = get_vacancies(
            "150000"
        )

    else:
        return

    for vacancy in vacancies:
        bot.send_message(
            message.chat.id,
            vacancy
        )


# =========================
# АВТОРАССЫЛКА
# =========================

def mailing_loop():

    while True:

        now = time.localtime()

        if now.tm_hour == 10 and now.tm_min == 0:

            try:

                response = requests.get(
                    SCRIPT_URL,
                    params={"action": "list"}
                )

                subscribers = response.json()

                vacancies = get_vacancies(
                    "менеджер по закупкам"
                )

                for chat_id in subscribers:

                    for vacancy in vacancies:

                        try:
                            bot.send_message(
                                chat_id,
                                "🔥 Новые вакансии:\n\n" + vacancy
                            )

                        except:
                            pass

                time.sleep(60)

            except Exception as e:
                print(e)

        time.sleep(20)


# =========================
# ЗАПУСК
# =========================

threading.Thread(
    target=mailing_loop
).start()

print("Бот запущен")

bot.infinity_polling()

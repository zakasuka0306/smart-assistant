import sqlite3
import asyncio
import os

import requests
import edge_tts


from telegram import (
    Update,
    ReplyKeyboardMarkup,
    
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


TOKEN = "8930805749:AAFPIytZ9Mc1MKzcGpq1-zOQPiCbmf4k9U4"



conn = sqlite3.connect("history.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    request TEXT,
    result TEXT
)
""")

conn.commit()


def save_history(user_id, request, result):
    cursor.execute(
        "INSERT INTO history (user_id, request, result) VALUES (?, ?, ?)",
        (user_id, request, result)
    )
    conn.commit()


def get_history(user_id):
    cursor.execute(
        "SELECT request, result FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user_id,)
    )

    return cursor.fetchall()


def clear_history(user_id):
    cursor.execute(
        "DELETE FROM history WHERE user_id = ?",
        (user_id,)
    )
    conn.commit()



keyboard = [
    ["Погода", "Факт"],
    ["Перевод", "Озвучка"],
    ["История", "Очистить историю"],
]

reply_keyboard = ReplyKeyboardMarkup(
    keyboard,
    resize_keyboard=True
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Привет!\n\n"
        "Я многофункциональный бот.\n\n"
        "Что я умею:\n"
        "Узнавать погоду\n"
        "Показывать интересные факты\n"
        "Переводить текст\n"
        "Озвучивать текст\n"
        "Хранить историю запросов\n\n"
        "Выбери нужную функцию ниже",
        reply_markup=reply_keyboard
    )


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["mode"] = "weather"

    await update.message.reply_text(
        "Напиши название города.\n\n"
        "Например:\n"
        "Алматы\n"
        "Москва"
    )


async def get_weather(update: Update, city):

    url = f"https://wttr.in/{city}?format=j1"

    try:
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            raise Exception()

        data = response.json()

        current = data["current_condition"][0]

        temperature = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        wind = current["windspeedKmph"]
        description = current["weatherDesc"][0]["value"]

        result = (
            f"Погода в городе {city}\n\n"
            f"Температура: {temperature}°C\n"
            f"Ощущается как: {feels}°C\n"
            f"Состояние: {description}\n"
            f"Влажность: {humidity}%\n"
            f"Ветер: {wind} км/ч"
        )

        save_history(
            update.effective_user.id,
            f"Погода: {city}",
            result
        )

        await update.message.reply_text(result)

    except Exception:
        await update.message.reply_text(
            "Не удалось получить погоду.\n"
            "Проверь название города."
        )



async def fact(update: Update, context: ContextTypes.DEFAULT_TYPE):

    facts = [
        "У осьминога три сердца.",
        "Бананы являются ягодами с точки зрения ботаники.",
        "Мёд практически не портится и может храниться очень долго.",
        "У акул нет костей — их скелет состоит из хрящей.",
        "Сердце синего кита может весить больше 100 килограммов.",
        "У человека примерно 206 костей.",
        "В космосе звук не распространяется, потому что там почти нет воздуха.",
        "Скорость света составляет примерно 300 000 километров в секунду.",
        "Кошки проводят во сне примерно две трети своей жизни.",
        "Вода покрывает около 71 процента поверхности Земли."
    ]

    import random

    result = "Интересный факт:\n\n" + random.choice(facts)

    save_history(
        update.effective_user.id,
        "Интересный факт",
        result
    )

    await update.message.reply_text(result)



async def translate(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["mode"] = "translate"

    await update.message.reply_text(
        "Напиши текст, который нужно перевести.\n\n"
        "Например:\n"
        "Hello, how are you?"
    )


async def do_translate(update: Update, text):

    try:
        if any("а" <= char.lower() <= "я" for char in text):
            source = "ru"
            target = "en"
        else:
            source = "en"
            target = "ru"

        url = "https://api.mymemory.translated.net/get"

        params = {
            "q": text,
            "langpair": f"{source}|{target}"
        }

        response = requests.get(
            url,
            params=params,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        translated = data["responseData"]["translatedText"]

        if not translated:
            raise Exception("Пустой перевод")

        result = (
            "Перевод:\n\n"
            + translated
        )

        save_history(
            update.effective_user.id,
            f"Перевод: {text}",
            result
        )

        await update.message.reply_text(result)

    except Exception as e:

        print("Ошибка перевода:", e)

        await update.message.reply_text(
            "Не удалось перевести текст."
        )


async def voice(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data["mode"] = "voice"

    await update.message.reply_text(
        "Напиши текст, который нужно озвучить."
    )


async def make_voice(update: Update, text):

    filename = f"voice_{update.effective_user.id}.mp3"

    try:

        communicate = edge_tts.Communicate(
            text,
            "ru-RU-DmitryNeural"
        )

        await communicate.save(filename)

        with open(filename, "rb") as audio:

            await update.message.reply_voice(
                voice=audio
            )

        save_history(
            update.effective_user.id,
            f"Озвучка: {text}",
            "Голосовое сообщение"
        )

        os.remove(filename)

    except Exception as e:

        print("Ошибка озвучки:", e)

        await update.message.reply_text(
            "Не удалось создать голосовое сообщение."
        )



async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    records = get_history(user_id)

    if not records:

        await update.message.reply_text(
            "История пока пустая."
        )

        return

    text = "Последние запросы:\n\n"

    for i, (request, result) in enumerate(records, 1):

        text += f"{i}. {request}\n"

        short_result = result[:300]

        text += f"{short_result}\n\n"

    await update.message.reply_text(text)



async def clear_history_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    clear_history(update.effective_user.id)

    await update.message.reply_text(
        "🗑 История запросов очищена."
    )



async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    mode = context.user_data.get("mode")

    if text == "Погода":
        await weather(update, context)
        return

    if text == "Факт":
        await fact(update, context)
        return

    if text == "Перевод":
        await translate(update, context)
        return

    if text == "Озвучка":
        await voice(update, context)
        return

    if text == "История":
        await history(update, context)
        return

    if text == "Очистить историю":
        await clear_history_command(update, context)
        return

    if mode == "weather":

        context.user_data["mode"] = None

        await get_weather(update, text)
        return

    if mode == "translate":

        context.user_data["mode"] = None

        await do_translate(update, text)
        return

    if mode == "voice":

        context.user_data["mode"] = None

        await make_voice(update, text)
        return

    await update.message.reply_text(
        "Выбери действие с помощью кнопок ниже",
        reply_markup=reply_keyboard
    )



def main():

    print("Бот запущен...")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_handler
        )
    )

    app.run_polling()


if __name__ == "__main__":
    main()

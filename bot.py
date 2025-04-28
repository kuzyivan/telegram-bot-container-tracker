import logging
import os

BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pandas as pd
from datetime import timedelta
import re

GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/16PZrxpzsfBkF7hGN4OKDx6CRfIqySES4oLL9OoxOV8Q/export?format=csv"
COORD_FILE = "Stations_coord.xlsx"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)

telegram_app = ApplicationBuilder().token("7339977646:AAEg3_jWsEULwbt3eWM35_L1MYGXKuyS07Y").build()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "\U0001F44B Привет! Я бот для отслеживания контейнеров по железной дороге.\n\nПросто пришли мне номер контейнера (например: TCNU1234567), либо список через пробел, запятую, точку с запятой или с новой строки."
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Помощь:\n\nПросто отправь номер контейнера (например: TCNU1234567) или несколько номеров через пробел, запятую, точку с запятой или с новой строки — и я покажу тебе информацию о последних операциях."
    )

# /refresh (фиктивная команда)
async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Данные обновляются в реальном времени из Google Sheets. Ничего обновлять не нужно!")

# Обработка одного или нескольких контейнеров
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip().upper()
    container_list = re.split(r'[\s,;:\n\r\.]+', message_text)
    container_list = [c for c in container_list if c]

    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV)
        df.columns = [str(col).strip().replace('\ufeff', '') for col in df.columns]
        df["Дата и время операции"] = pd.to_datetime(df["Дата и время операции"], format="%d.%m.%Y %H:%M:%S", errors='coerce')

        result_df = (
            df[df["Номер контейнера"].isin(container_list)]
            .sort_values("Дата и время операции", ascending=False)
            .drop_duplicates(subset=["Номер контейнера"])
        )

        if result_df.empty:
            await update.message.reply_text("⚠️ Контейнеры не найдены в базе. Проверь номера.")
            return

        grouped = result_df.groupby(["Станция отправления", "Станция назначения"])
        reply = "\U0001F4E6 Отчёт по контейнерам:\n"

        for (start, end), group in grouped:
            reply += f"\n\U0001F682 *Маршрут:* {start} → {end}\n"
            for _, row in group.iterrows():
                station_name = str(row.get("Станция операции", "")).split("(")[0].strip().upper()
                date_op = row["Дата и время операции"]
                eta_str = "неизвестна"

                if pd.notnull(row.get("Расстояние оставшееся")):
                    try:
                        km = float(row["Расстояние оставшееся"])
                        eta_days = int(round(km / 600))
                        eta_str = f"через {eta_days} дн." if eta_days > 0 else "менее суток"
                    except:
                        pass

                date_op_str = date_op.strftime('%Y-%m-%d %H:%M') if pd.notnull(date_op) else "неизвестна"

                if "выгрузка из вагона на контейнерном пункте" in str(row['Операция']).lower():
                    reply += (
                        f"\n\U0001F4E6 № КТК: `{row['Номер контейнера']}`\n"
                        f"\U0001F682 Маршрут: {start} → {end}\n"
                        f"\U0001F552 Дата операции: {date_op_str}\n"
                        f"\U0001F4EC Контейнер прибыл на станцию назначения!\n"
                    )
                else:
                    reply += (
                        f"\n\U0001F4E6 № КТК: `{row['Номер контейнера']}`\n"
                        f"\U0001F682 Маршрут: {start} → {end}\n"
                        f"\U0001F4CD Дислокация: {station_name}\n"
                        f"⚙️ Операция: {row['Операция']}\n"
                        f"\U0001F552 Дата операции: {date_op_str}\n"
                        f"\U0001F4C5 Прогноз прибытия: {eta_str}\n"
                    )

        await update.message.reply_text(reply, parse_mode="Markdown")

    except Exception as e:
        logging.exception("Ошибка при обработке запроса")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке запроса. Проверь данные.")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("refresh", refresh))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track))

if __name__ == '__main__':
    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )
    while True:
        time.sleep(10)

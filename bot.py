import logging
import os
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pandas as pd

GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/16PZrxpzsfBkF7hGN4OKDx6CRfIqySES4oLL9OoxOV8Q/export?format=csv"
COORD_FILE = "Stations_coord.xlsx"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)

telegram_app = ApplicationBuilder().token("7339977646:AAHez8tXVk7fOyve8qRYlHYX93Ud9eQNMhc").build()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для отслеживания контейнеров по железной дороге.\n\nПросто пришли мне номер контейнера (например: TCNU1234567), либо список через пробел."
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Помощь:\n\nПросто отправь номер контейнера (например: TCNU1234567) или несколько номеров через пробел — и я покажу тебе информацию о последних операциях."
    )

# /refresh (фиктивная команда)
async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Данные обновляются в реальном времени из Google Sheets. Ничего обновлять не нужно!")

# Обработка одного или нескольких контейнеров
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip().upper()
    container_list = message_text.split()

    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV)
        df.columns = [str(col).strip().replace('\ufeff', '') for col in df.columns]
        df["Дата и время операции"] = pd.to_datetime(df["Дата и время операции"], errors='coerce')

        result_df = (
            df[df["Контейнер"].isin(container_list)]
            .sort_values("Дата и время операции", ascending=False)
            .drop_duplicates(subset=["Контейнер"])
        )

        if result_df.empty:
            await update.message.reply_text("⚠️ Контейнеры не найдены в базе. Проверь номера.")
            return

        grouped = result_df.groupby(["Станция отправления", "Станция назначения"])
        reply = "📦 Отчёт по контейнерам:\n"

        for (start, end), group in grouped:
            reply += f"\n🚆 *Маршрут:* {start} → {end}\n"
            for _, row in group.iterrows():
                station_name = str(row["Станция операция"]).split("(")[0].strip().upper()
                reply += (
                    f"— `{row['Контейнер']}` | 📍 {station_name} | ⚙️ {row['Операция']} | 📅 {row['Дата и время операции']}\n"
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

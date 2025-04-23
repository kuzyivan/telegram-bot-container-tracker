import logging
import os
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import pandas as pd
from upload_map import upload_map_to_github
import folium

GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/16PZrxpzsfBkF7hGN4OKDx6CRfIqySES4oLL9OoxOV8Q/export?format=csv"
COORD_FILE = "Stations_coord.xlsx"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)

telegram_app = ApplicationBuilder().token("7339977646:AAHez8tXVk7fOyve8qRYlHYX93Ud9eQNMhc").build()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для отслеживания контейнеров по железной дороге.\n\nПросто пришли мне номер контейнера, например: TCNU1234567"
    )

# /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❓ Помощь:\n\nПросто отправь номер контейнера (например: TCNU1234567) — и я покажу тебе карту и информацию о последней операции."
    )

# /refresh (фиктивная команда)
async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Данные обновляются в реальном времени из Google Sheets. Ничего обновлять не нужно!")

# Обработка номера контейнера
async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    container_number = update.message.text.strip().upper()

    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV)
        df.columns = [str(col).strip().replace('\ufeff', '') for col in df.columns]

        info = df[df["Контейнер"] == container_number].iloc[0]
        station_name = str(info["Станция операция"]).split("(")[0].strip().upper()

        coords_df = pd.read_excel(COORD_FILE)
        coords_df["Станции"] = coords_df["Станции"].astype(str).str.upper().str.strip()

        coord_row = coords_df[coords_df["Станции"] == station_name]

        if coord_row.empty:
            await update.message.reply_text(f"Станция '{station_name}' не найдена в справочнике координат.")
            return

        lat, lon = coord_row.iloc[0]["Широта"], coord_row.iloc[0]["Долгота"]

        message = f"""Контейнер №{container_number}
Маршрут: {info['Станция отправления']} → {info['Станция назначения']}
Станция: {station_name}
Операция: {info['Операция']}
Дата операции: {info['Дата и время операции']}
Номер накладной: {info['Номер накладной']}
Данные актуальны на: текущий момент"""

        filename = "map.html"
        m = folium.Map(location=[lat, lon], zoom_start=10)
        folium.Marker(location=[lat, lon], popup=message, tooltip=container_number).add_to(m)
        m.save(filename)

        url = upload_map_to_github(filename)
        os.remove(filename)

        await update.message.reply_text(message + f"\n\n🗺️ Карта: {url}")

    except Exception as e:
        logging.exception("Ошибка при обработке контейнера")
        await update.message.reply_text("Произошла ошибка при обработке контейнера. Проверь данные.")

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

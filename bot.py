import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pandas as pd
from upload_map import upload_map_to_github
import folium
from flask import Flask, request

GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/16PZrxpzsfBkF7hGN4OKDx6CRfIqySES4oLL9OoxOV8Q/export?format=csv"
COORD_FILE = "Stations_coord.xlsx"
PORT = int(os.environ.get("PORT", 10000))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

telegram_app = ApplicationBuilder().token("7339977646:AAHez8tXVk7fOyve8qRYlHYX93Ud9eQNMhc").build()

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи номер контейнера: /track TCNU1234567")
        return

    container_number = context.args[0].upper()

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

        filename = f"map_{container_number}.html"
        m = folium.Map(location=[lat, lon], zoom_start=10)
        folium.Marker(location=[lat, lon], popup=message, tooltip=container_number).add_to(m)
        m.save(filename)

        url = upload_map_to_github(filename)
        os.remove(filename)

        await update.message.reply_text(message + f"\n\n🗺️ Карта: {url}")

    except Exception as e:
        logging.exception("Ошибка при обработке контейнера")
        await update.message.reply_text("Произошла ошибка при обработке контейнера. Проверь данные.")

telegram_app.add_handler(CommandHandler("track", track))

@app.route(f"/webhook/{telegram_app.bot.token}", methods=["POST"])
def webhook():
    telegram_app.update_queue.put(Update.de_json(request.get_json(force=True), telegram_app.bot))
    return "ok"

if __name__ == '__main__':
    from flask import Flask
    import sys
    import subprocess
    try:
        import flask
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
        import flask

    telegram_app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=telegram_app.bot.token,
        webhook_url=f"{WEBHOOK_URL}/webhook/{telegram_app.bot.token}"
    )

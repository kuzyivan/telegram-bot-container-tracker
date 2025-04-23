import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pandas as pd
from upload_map import upload_map_to_github
import folium
import os

GOOGLE_SHEET_CSV = "https://docs.google.com/spreadsheets/d/16PZrxpzsfBkF7hGN4OKDx6CRfIqySES4oLL9OoxOV8Q/export?format=csv"
COORD_FILE = "Stations_coord.xlsx"

logging.basicConfig(level=logging.INFO)

async def track(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажи номер контейнера: /track TCNU1234567")
        return

    container_number = context.args[0].upper()

    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV)
        df.columns = [str(col).strip().replace('\ufeff', '') for col in df.columns]  # чистка скрытых символов

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


if __name__ == '__main__':
    from telegram.ext import Application
    TOKEN = "7339977646:AAHez8tXVk7fOyve8qRYlHYX93Ud9eQNMhc"
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("track", track))
    app.run_polling()

import os
import telebot
from flask import Flask, request
import mercadopago
from bot import bot  # ✅ Importa el bot correctamente

TOKEN = os.getenv("BOT_TOKEN")  # ✅ Definir el token antes de usarlo
if not TOKEN:
    raise ValueError("ERROR: BOT_TOKEN no está definido en las variables de entorno.")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # La URL pública en Render

app = Flask(__name__)

# ✅ Configurar el webhook de Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])  # ✅ No es necesario llamar a `bot.bot`
    return "OK", 200

# ✅ Página de inicio para verificar que el bot está en ejecución
@app.route("/")
def index():
    return "Bot en ejecución correctamente 🚀", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")  # ✅ URL correcta

    port = int(os.environ.get("PORT", 5000))
    print(f"DEBUG: Iniciando Flask en puerto {port}")
    app.run(host="0.0.0.0", port=port)

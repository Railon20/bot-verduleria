import os
import telebot
from flask import Flask, request
import mercadopago
from bot.bot import bot  # Importa explícitamente el objeto 'bot' del módulo bot.py
  # ✅ Importa el bot correctamente

TOKEN = os.getenv("BOT_TOKEN")  # ✅ Definir el token antes de usarlo
if not TOKEN:
    raise ValueError("ERROR: BOT_TOKEN no está definido en las variables de entorno.")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # La URL pública en Render
print(f"DEBUG: WEBHOOK_URL = {WEBHOOK_URL}")

app = Flask(__name__)

# ✅ Configurar el webhook de Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    print(f"DEBUG: Recibido JSON de Telegram: {json_str}")  # 📌 Verifica que los datos lleguen bien

    try:
        update = telebot.types.Update.de_json(json_str)
        if update:
            print("DEBUG: Update correctamente deserializado")  # 📌 Asegura que no hay problema con la conversión
        
        print(f"DEBUG: Comandos del bot registrados: {bot.get_my_commands()}")
        bot.process_new_updates([update])  # 📌 Prueba llamar a bot directamente
        print("DEBUG: bot.process_new_updates ejecutado con éxito")  # 📌 Confirma que el bot lo procesó
    except Exception as e:
        print(f"ERROR en webhook: {str(e)}")  # 📌 Registra cualquier error en Render
        return "Error interno", 500

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

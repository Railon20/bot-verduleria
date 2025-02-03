import os
import telebot
from flask import Flask, request
import mercadopago
from bot import bot  # Asegura que 'bot' es accesible como un módulo
  # ✅ Importa el bot correctamente (ejecuta los handlers)

app = Flask(__name__)

def enviar_email(destinatario, asunto, mensaje):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    remitente = "tuemail@gmail.com"
    clave = "tucontraseña"

    msg = MIMEText(mensaje, "html")
    msg["Subject"] = asunto
    msg["From"] = remitente
    msg["To"] = destinatario

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(remitente, clave)
    server.sendmail(remitente, destinatario, msg.as_string())
    server.quit()

def actualizar_estado_pago(payment_id):
    conn = conectar_db()
    cursor = conn.cursor()

    pago = sdk.payment().get(payment_id)
    status = pago["response"]["status"]
    user_email = pago["response"]["payer"]["email"]

    if status == "approved":
        cursor.execute("UPDATE pedidos SET estado = 'completado' WHERE usuario_email = %s", (user_email,))
        conn.commit()

        # Notificación al usuario
        asunto = "✅ Pago Confirmado"
        mensaje = f"<h1>¡Gracias por tu compra!</h1><p>Tu pedido ha sido confirmado y está en preparación.</p>"
        enviar_email(user_email, asunto, mensaje)

        # Notificación al proveedor
        email_proveedor = "proveedor@email.com"
        asunto_proveedor = "📦 Nuevo Pedido Pagado"
        mensaje_proveedor = f"<h1>Nuevo pedido confirmado</h1><p>El usuario {user_email} ha realizado un pago. Revisa los detalles en el sistema.</p>"
        enviar_email(email_proveedor, asunto_proveedor, mensaje_proveedor)

    conn.close()


# ✅ Configurar el webhook de Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.bot.process_new_updates([update])  # ✅ Procesa actualizaciones usando bot.bot
    return "OK", 200

# ✅ Página de inicio para verificar que el bot está en ejecución
@app.route("/")
def index():
    return "Bot en ejecución correctamente 🚀", 200

if __name__ == "__main__":
    bot.bot.remove_webhook()
    bot.bot.set_webhook(url=f"https://bot-verduleria.onrender.com/{TOKEN}")

    port = int(os.environ.get("PORT", 5000))
    print(f"DEBUG: Iniciando Flask en puerto {port}")
    app.run(host="0.0.0.0", port=port)
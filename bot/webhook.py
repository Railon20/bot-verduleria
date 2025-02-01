from flask import Flask, request, jsonify
import mercadopago
from config import MERCADO_PAGO_ACCESS_TOKEN
import smtplib
from email.mime.text import MIMEText


app = Flask(__name__)
sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)


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


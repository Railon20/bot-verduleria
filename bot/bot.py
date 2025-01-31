# bot/bot.py
import sys
import telebot
from config.config import TOKEN

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "¡Bienvenido a la tienda de verdulería! 🥦🍎\nUsa /menu para ver opciones.")

@bot.message_handler(commands=['menu'])
def show_menu(message):
    menu = "📌 Opciones disponibles:\n"
    menu += "/registrar - Registrar usuario\n"
    menu += "/productos - Ver productos\n"
    menu += "/carrito - Ver carrito\n"
    menu += "/comprar - Finalizar compra\n"
    bot.send_message(message.chat.id, menu)

    from database.db import conectar

usuarios_pendientes = {}

@bot.message_handler(commands=['registrar'])
def registrar_usuario(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Por favor, ingresa tu nombre:")
    usuarios_pendientes[chat_id] = {}
    bot.register_next_step_handler(message, guardar_nombre)

def guardar_nombre(message):
    chat_id = message.chat.id
    usuarios_pendientes[chat_id]['nombre'] = message.text
    bot.send_message(chat_id, "Ahora ingresa tu correo electrónico:")
    bot.register_next_step_handler(message, guardar_email)

def guardar_email(message):
    chat_id = message.chat.id
    usuarios_pendientes[chat_id]['email'] = message.text
    bot.send_message(chat_id, "Por último, ingresa tu dirección:")
    bot.register_next_step_handler(message, guardar_direccion)

def guardar_direccion(message):
    chat_id = message.chat.id
    usuarios_pendientes[chat_id]['direccion'] = message.text

    datos = usuarios_pendientes[chat_id]
    conn = conectar()
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO usuarios (telegram_id, nombre, email, direccion) VALUES (%s, %s, %s, %s)", 
                       (chat_id, datos['nombre'], datos['email'], datos['direccion']))
        conn.commit()
        bot.send_message(chat_id, "✅ ¡Registro completado con éxito!")
    except Exception as e:
        bot.send_message(chat_id, "❌ Error al registrar. Puede que el correo ya esté en uso.")
    finally:
        cursor.close()
        conn.close()
        del usuarios_pendientes[chat_id]


if __name__ == "__main__":
    print("Bot iniciado...")
    bot.polling()

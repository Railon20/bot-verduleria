import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import mysql.connector
import requests
import json
from flask import Flask, request


app = Flask(__name__)


# Configuración del bot
TOKEN = "TU_TOKEN_AQUI"
bot = telebot.TeleBot(TOKEN)

# Conexión a MySQL
db = mysql.connector.connect(
    host="localhost",
    user="tu_usuario_mysql",
    password="tu_contraseña_mysql",
    database="verduleria_db"
)
cursor = db.cursor()

# Función para obtener productos de la base de datos
def obtener_productos():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre, unidad, precio FROM productos")
    productos = cursor.fetchall()
    cursor.close()
    return productos

# Función para mostrar los productos en el menú "Ordenar"
@bot.message_handler(func=lambda message: message.text == "Ordenar")
def menu_ordenar(message):
    productos = obtener_productos()
    if not productos:
        bot.send_message(message.chat.id, "No hay productos disponibles en este momento.")
        return
    
    markup = InlineKeyboardMarkup()
    
    for producto in productos:
        texto_boton = f"{producto['nombre']} - {producto['precio']} por {'100g' if producto['unidad'] == 'gramos' else 'unidad'}"
        markup.add(InlineKeyboardButton(texto_boton, callback_data=f"producto_{producto['id']}"))

    markup.add(InlineKeyboardButton("⬅️ Volver", callback_data="volver_menu"))
    
    bot.send_message(message.chat.id, "Selecciona un producto:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("producto_"))
def seleccionar_producto(call):
    producto_id = call.data.split("_")[1]
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
    producto = cursor.fetchone()
    cursor.close()

    if not producto:
        bot.answer_callback_query(call.id, "Producto no encontrado.")
        return
    
    mensaje_precio = f"📌 {producto['nombre']}\n💰 Precio: {producto['precio']} por {'100g' if producto['unidad'] == 'gramos' else 'unidad'}\n\n¿Cuántos {'gramos' if producto['unidad'] == 'gramos' else 'unidades'} quieres?"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("⬅️ Volver", callback_data="volver_ordenar"))
    
    bot.send_message(call.message.chat.id, mensaje_precio, reply_markup=markup)
    
    bot.register_next_step_handler(call.message, lambda msg: procesar_cantidad(msg, producto))

def procesar_cantidad(message, producto):
    try:
        cantidad = float(message.text)
        if cantidad <= 0:
            bot.send_message(message.chat.id, "Por favor ingresa una cantidad válida.")
            return
        
        # Guardamos la selección del producto y la cantidad en un diccionario temporal (puedes mejorar esto con una base de datos)
        user_data[message.chat.id] = {"producto": producto, "cantidad": cantidad}
        
        # Ahora mostramos los carritos disponibles
        mostrar_carritos(message)
    
    except ValueError:
        bot.send_message(message.chat.id, "Por favor ingresa un número válido.")

def mostrar_carritos(message):
    usuario_id = message.chat.id  # Usamos el ID del usuario de Telegram
    
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, nombre FROM carritos WHERE usuario_id = %s", (usuario_id,))
    carritos = cursor.fetchall()
    cursor.close()

    markup = InlineKeyboardMarkup()

    if not carritos:
        bot.send_message(message.chat.id, "No tienes carritos disponibles.")
        markup.add(InlineKeyboardButton("➕ Crear carrito", callback_data="crear_carrito"))
    else:
        for carrito in carritos:
            markup.add(InlineKeyboardButton(carrito["nombre"], callback_data=f"carrito_{carrito['id']}"))

    markup.add(InlineKeyboardButton("⬅️ Volver", callback_data="volver_ordenar"))
    
    bot.send_message(message.chat.id, "Selecciona un carrito:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("carrito_"))
def agregar_a_carrito(call):
    carrito_id = call.data.split("_")[1]
    usuario_id = call.message.chat.id

    if usuario_id not in user_data:
        bot.answer_callback_query(call.id, "Error: No hay producto seleccionado.")
        return
    
    producto = user_data[usuario_id]["producto"]
    cantidad = user_data[usuario_id]["cantidad"]
    total_producto = cantidad * (producto["precio"] / 100 if producto["unidad"] == "gramos" else producto["precio"])

    # Insertamos el producto en el carrito
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO carrito_productos (carrito_id, producto_id, cantidad, total) VALUES (%s, %s, %s, %s)",
        (carrito_id, producto["id"], cantidad, total_producto)
    )
    db.commit()
    cursor.close()
    
    mensaje_confirmacion = f"✅ {producto['nombre']} agregado al carrito.\n💰 Total del carrito con este producto: {total_producto:.2f}\n\n¿Deseas agregar más productos?"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ Sí, agregar más productos", callback_data="volver_ordenar"))
    markup.add(InlineKeyboardButton("🛒 Proceder al pago", callback_data="pagar_carrito"))
    markup.add(InlineKeyboardButton("⬅️ Volver al menú", callback_data="volver_menu"))

    bot.send_message(call.message.chat.id, mensaje_confirmacion, reply_markup=markup)

    MERCADOPAGO_ACCESS_TOKEN = "TU_ACCESS_TOKEN"


def generar_pago(carrito_id, usuario_id):
    cursor = db.cursor(dictionary=True)
    
    # Obtener los productos del carrito
    cursor.execute("""
        SELECT p.nombre, cp.cantidad, p.precio, p.unidad
        FROM carrito_productos cp
        JOIN productos p ON cp.producto_id = p.id
        WHERE cp.carrito_id = %s
    """, (carrito_id,))
    productos = cursor.fetchall()
    
    if not productos:
        return None

    # Crear la lista de ítems para Mercado Pago
    items = []
    total = 0

    for producto in productos:
        precio_unitario = producto["precio"] / 100 if producto["unidad"] == "gramos" else producto["precio"]
        subtotal = producto["cantidad"] * precio_unitario
        total += subtotal

        items.append({
            "title": producto["nombre"],
            "quantity": int(producto["cantidad"]),
            "unit_price": round(precio_unitario, 2),
            "currency_id": "ARS"
        })

    cursor.close()

    # Crear la preferencia de pago
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "items": items,
        "payer": {
            "email": f"usuario_{usuario_id}@correo.com"
        },
        "back_urls": {
            "success": "https://tuweb.com/exito",
            "failure": "https://tuweb.com/error",
            "pending": "https://tuweb.com/pendiente"
        },
        "auto_return": "approved"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 201:
        return response.json()["init_point"]
    else:
        return None


@bot.callback_query_handler(func=lambda call: call.data == "pagar_carrito")
def pagar_carrito(call):
    usuario_id = call.message.chat.id

    # Obtener el carrito del usuario
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM carritos WHERE usuario_id = %s ORDER BY id DESC LIMIT 1", (usuario_id,))
    carrito = cursor.fetchone()
    cursor.close()

    if not carrito:
        bot.send_message(call.message.chat.id, "No tienes un carrito activo.")
        return

    # Generar el enlace de pago
    link_pago = generar_pago(carrito["id"], usuario_id)

    if link_pago:
        mensaje_pago = f"🛒 Tu pedido está listo.\n💳 Paga haciendo clic en el siguiente enlace:\n\n👉 [Pagar ahora]({link_pago})"
        bot.send_message(call.message.chat.id, mensaje_pago, parse_mode="Markdown")
    else:
        bot.send_message(call.message.chat.id, "Hubo un problema al generar el pago. Intenta nuevamente.")


# Función para crear el menú principal
def menu_principal(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn_ordenar = KeyboardButton("🛒 Ordenar")
    btn_carritos = KeyboardButton("🛍️ Carritos")
    btn_historial = KeyboardButton("📜 Historial")
    btn_pendientes = KeyboardButton("⏳ Pendientes")
    
    markup.add(btn_ordenar, btn_carritos)
    markup.add(btn_historial, btn_pendientes)

    bot.send_message(message.chat.id, "🏠 *Menú Principal*", reply_markup=markup, parse_mode="Markdown")

# Comando de inicio
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "¡Bienvenido a la tienda de verdulería!", reply_markup=menu_principal())

# Función para manejar los botones del menú principal
@bot.message_handler(func=lambda message: message.text in ["🛒 Ordenar", "📜 Historial", "⏳ Pendientes", "🛍️ Carritos"])
def menu_handler(message):
    if message.text == "🛒 Ordenar":
        mostrar_productos(message)
    elif message.text == "📜 Historial":
        mostrar_historial(message)
    elif message.text == "⏳ Pendientes":
        mostrar_pendientes(message)
    elif message.text == "🛍️ Carritos":
        mostrar_carritos(message)

# Funciones para cada opción del menú (se implementarán en los siguientes pasos)
def mostrar_productos(message):
    bot.send_message(message.chat.id, "Aquí se mostrarán los productos disponibles.")

@bot.message_handler(func=lambda message: message.text == "📜 Historial")
def mostrar_historial(message):
    usuario_id = message.chat.id
    cursor = db.cursor(dictionary=True)

    # Obtener los últimos 20 pedidos completados
    cursor.execute("""
        SELECT id, total, fecha FROM pedidos 
        WHERE usuario_id = %s AND estado = 'Completado' 
        ORDER BY fecha DESC LIMIT 20
    """, (usuario_id,))
    pedidos = cursor.fetchall()
    cursor.close()

    if not pedidos:
        bot.send_message(usuario_id, "📭 No tienes pedidos completados.")
        return

    mensaje = "📜 *Historial de Pedidos*\n\n"
    for pedido in pedidos:
        mensaje += f"🆔 Pedido: {pedido['id']}\n💰 Total: ${pedido['total']}\n📅 Fecha: {pedido['fecha']}\n\n"

    bot.send_message(usuario_id, mensaje, parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text == "⏳ Pendientes")
def mostrar_pendientes(message):
    usuario_id = message.chat.id
    cursor = db.cursor(dictionary=True)

    # Obtener pedidos pendientes
    cursor.execute("""
        SELECT id, total, fecha FROM pedidos 
        WHERE usuario_id = %s AND estado = 'Pendiente' 
        ORDER BY fecha DESC
    """, (usuario_id,))
    pedidos = cursor.fetchall()
    cursor.close()

    if not pedidos:
        bot.send_message(usuario_id, "📭 No tienes pedidos pendientes.")
        return

    mensaje = "⏳ *Pedidos Pendientes*\n\n"
    for pedido in pedidos:
        mensaje += f"🆔 Pedido: {pedido['id']}\n💰 Total: ${pedido['total']}\n📅 Fecha: {pedido['fecha']}\n\n"

    bot.send_message(usuario_id, mensaje, parse_mode="Markdown")

def mostrar_carritos(message):
    bot.send_message(message.chat.id, "Aquí se mostrarán los carritos disponibles.")

# Iniciar el bot
bot.polling()


@app.route("/webhook", methods=["POST"])
def recibir_webhook():
    data = request.json

    if "type" in data and data["type"] == "payment":
        payment_id = data["data"]["id"]

        # Consultar el estado del pago en Mercado Pago
        headers = {"Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}"}
        response = requests.get(f"https://api.mercadopago.com/v1/payments/{payment_id}", headers=headers)

        if response.status_code == 200:
            pago = response.json()
            status = pago["status"]
            carrito_id = pago["external_reference"]

            if status == "approved":
                cursor = db.cursor(dictionary=True)

                # Marcar el carrito como pagado
                cursor.execute("UPDATE carritos SET estado = 'Pagado' WHERE id = %s", (carrito_id,))
                db.commit()

                # Obtener el usuario del carrito
                cursor.execute("SELECT usuario_id FROM carritos WHERE id = %s", (carrito_id,))
                carrito = cursor.fetchone()
                usuario_id = carrito["usuario_id"]

                # Enviar mensaje de confirmación al usuario
                mensaje_usuario = "✅ ¡Tu pago fue aprobado! Tu pedido está en proceso. 🚀"
                bot.send_message(usuario_id, mensaje_usuario)

                 # Obtener productos del carrito
                cursor.execute("""
                    SELECT p.nombre, cp.cantidad, p.unidad
                    FROM carrito_productos cp
                    JOIN productos p ON cp.producto_id = p.id
                    WHERE cp.carrito_id = %s
                """, (carrito_id,))
                productos = cursor.fetchall()

                # Construir el mensaje para el proveedor
                mensaje_proveedor = "📦 *Nuevo Pedido Confirmado*\n\n"
                for producto in productos:
                    mensaje_proveedor += f"🍏 {producto['nombre']}: {producto['cantidad']} {producto['unidad']}\n"
                mensaje_proveedor += "\n✅ ¡Prepara el pedido!"

                # Enviar mensaje al proveedor
                PROVEEDOR_ID = 123456789  # Reemplaza con el ID de Telegram del proveedor
                bot.send_message(PROVEEDOR_ID, mensaje_proveedor, parse_mode="Markdown")

                cursor.close()

    return "OK", 200

if __name__ == "__main__":
    app.run(port=5000)


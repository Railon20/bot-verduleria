import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import mysql.connector

TOKEN = os.getenv("BOT_TOKEN")
MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")



bot = telebot.TeleBot(TOKEN)



# ✅ Función para conectar a la base de datos
def conectar_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# ✅ MENÚ PRINCIPAL
@bot.message_handler(commands=['start'])
def start(message):
    print(f"DEBUG: /start recibido de {message.chat.id}")  # 📌 Verificación
    print(f"DEBUG: /start recibido de {message.chat.id}")
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🛒 Ordenar"), KeyboardButton("📦 Carritos"))
    markup.add(KeyboardButton("📜 Historial"), KeyboardButton("🚀 Pendientes"))
    bot.send_message(message.chat.id, "¡Bienvenido a la tienda de verdulería! ¿Qué deseas hacer?", reply_markup=markup)

# ✅ MOSTRAR PRODUCTOS DISPONIBLES
@bot.message_handler(func=lambda message: message.text == "🛒 Ordenar")
def mostrar_productos(message):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM productos")
    productos = cursor.fetchall()
    conn.close()

    if not productos:
        bot.send_message(message.chat.id, "No hay productos disponibles.")
        return

    markup = InlineKeyboardMarkup()
    for prod_id, nombre in productos:
        markup.add(InlineKeyboardButton(nombre, callback_data=f"producto_{prod_id}"))

    bot.send_message(message.chat.id, "Selecciona un producto para ver detalles:", reply_markup=markup)

print("DEBUG: Handlers del bot cargados correctamente.")  # 📌 Asegura que los handlers están registrados


# MOSTRAR DETALLE DEL PRODUCTO SELECCIONADO
@bot.callback_query_handler(func=lambda call: call.data.startswith("producto_"))
def detalle_producto(call):
    prod_id = int(call.data.split("_")[1])

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT nombre, precio, unidad FROM productos WHERE id = %s", (prod_id,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        bot.send_message(call.message.chat.id, "Producto no encontrado.")
        return

    nombre, precio, unidad = producto
    precio_mostrar = precio / 10 if unidad == 'gramos' else precio

    bot.send_message(call.message.chat.id, f"💰 {nombre}\n💵 Precio: ${precio_mostrar} por {'100g' if unidad == 'gramos' else 'unidad'}\n\n¿Cuánto deseas comprar? Escribe la cantidad.")
    
    bot.register_next_step_handler(call.message, lambda m: agregar_a_carrito(m, prod_id, unidad, precio))

# AÑADIR AL CARRITO
def agregar_a_carrito(message, prod_id, unidad, precio):
    try:
        cantidad = float(message.text)
        if cantidad <= 0:
            bot.send_message(message.chat.id, "La cantidad debe ser mayor a 0. Intenta nuevamente.")
            return
    except ValueError:
        bot.send_message(message.chat.id, "Por favor, ingresa un número válido.")
        return

    if unidad == 'gramos':
        cantidad = cantidad * 10  # Convertimos 100g a gramos reales

    # Verificar si el usuario tiene carritos
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM carritos WHERE usuario_id = %s", (message.chat.id,))
    carritos = cursor.fetchall()

    if not carritos:
        bot.send_message(message.chat.id, "No tienes carritos. Escribe un nombre para crear uno.")
        bot.register_next_step_handler(message, lambda m: crear_carrito(m, prod_id, cantidad, precio))
    else:
        markup = InlineKeyboardMarkup()
        for carrito_id, nombre in carritos:
            markup.add(InlineKeyboardButton(nombre, callback_data=f"add_carrito_{carrito_id}_{prod_id}_{cantidad}_{precio}"))
        markup.add(InlineKeyboardButton("➕ Crear nuevo carrito", callback_data=f"crear_carrito_{prod_id}_{cantidad}_{precio}"))

        bot.send_message(message.chat.id, "Selecciona un carrito o crea uno nuevo:", reply_markup=markup)

# CREAR CARRITO NUEVO
def crear_carrito(message, prod_id, cantidad, precio):
    nombre_carrito = message.text.strip()

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO carritos (usuario_id, nombre) VALUES (%s, %s)", (message.chat.id, nombre_carrito))
    conn.commit()
    carrito_id = cursor.lastrowid

    cursor.execute("INSERT INTO carrito_productos (carrito_id, producto_id, cantidad) VALUES (%s, %s, %s)", (carrito_id, prod_id, cantidad))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, f"✅ Carrito '{nombre_carrito}' creado y producto añadido.")

# AÑADIR PRODUCTO A UN CARRITO EXISTENTE
@bot.callback_query_handler(func=lambda call: call.data.startswith("add_carrito_"))
def agregar_a_carrito_existente(call):
    _, carrito_id, prod_id, cantidad, precio = call.data.split("_")
    carrito_id, prod_id, cantidad, precio = int(carrito_id), int(prod_id), float(cantidad), float(precio)

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO carrito_productos (carrito_id, producto_id, cantidad) VALUES (%s, %s, %s)", (carrito_id, prod_id, cantidad))
    conn.commit()
    conn.close()

    bot.send_message(call.message.chat.id, "✅ Producto añadido al carrito.")

@bot.message_handler(func=lambda message: message.text == "📦 Carritos")
def mostrar_carritos(message):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM carritos WHERE usuario_id = %s", (message.chat.id,))
    carritos = cursor.fetchall()
    conn.close()

    if not carritos:
        bot.send_message(message.chat.id, "No tienes carritos. Usa 'Ordenar' para crear uno.")
        return

    markup = InlineKeyboardMarkup()
    for carrito_id, nombre in carritos:
        markup.add(InlineKeyboardButton(nombre, callback_data=f"ver_carrito_{carrito_id}"))

    markup.add(InlineKeyboardButton("➕ Crear nuevo carrito", callback_data="crear_carrito"))

    bot.send_message(message.chat.id, "Estos son tus carritos:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("ver_carrito_"))
def ver_carrito(call):
    carrito_id = int(call.data.split("_")[2])

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nombre, cp.cantidad, p.precio, p.unidad 
        FROM carrito_productos cp
        JOIN productos p ON cp.producto_id = p.id
        WHERE cp.carrito_id = %s
    """, (carrito_id,))
    productos = cursor.fetchall()
    conn.close()

    if not productos:
        bot.send_message(call.message.chat.id, "El carrito está vacío.")
        return

    mensaje = "🛍️ Carrito:\n\n"
    total = 0
    for nombre, cantidad, precio, unidad in productos:
        subtotal = (precio / 10 * cantidad) if unidad == 'gramos' else (precio * cantidad)
        mensaje += f"🛒 {nombre} - {cantidad} {unidad} - ${subtotal:.2f}\n"
        total += subtotal

    mensaje += f"\n💰 Total: ${total:.2f}"

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ Agregar Producto", callback_data=f"agregar_a_carrito_{carrito_id}"))
    markup.add(InlineKeyboardButton("❌ Eliminar Producto", callback_data=f"eliminar_producto_{carrito_id}"))
    markup.add(InlineKeyboardButton("🗑 Eliminar Carrito", callback_data=f"eliminar_carrito_{carrito_id}"))
    markup.add(InlineKeyboardButton("🔙 Volver", callback_data="volver_carritos"))

    bot.send_message(call.message.chat.id, mensaje, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("agregar_a_carrito_"))
def agregar_a_carrito(call):
    carrito_id = int(call.data.split("_")[3])

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre FROM productos")
    productos = cursor.fetchall()
    conn.close()

    markup = InlineKeyboardMarkup()
    for prod_id, nombre in productos:
        markup.add(InlineKeyboardButton(nombre, callback_data=f"agregar_producto_{prod_id}_{carrito_id}"))

    bot.send_message(call.message.chat.id, "Selecciona un producto para agregar:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("eliminar_producto_"))
def eliminar_producto_carrito(call):
    carrito_id = int(call.data.split("_")[2])

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.nombre 
        FROM carrito_productos cp
        JOIN productos p ON cp.producto_id = p.id
        WHERE cp.carrito_id = %s
    """, (carrito_id,))
    productos = cursor.fetchall()
    conn.close()

    if not productos:
        bot.send_message(call.message.chat.id, "El carrito está vacío.")
        return

    markup = InlineKeyboardMarkup()
    for prod_id, nombre in productos:
        markup.add(InlineKeyboardButton(nombre, callback_data=f"confirmar_eliminar_{prod_id}_{carrito_id}"))

    bot.send_message(call.message.chat.id, "Selecciona el producto a eliminar:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirmar_eliminar_"))
def confirmar_eliminar_producto(call):
    _, prod_id, carrito_id = call.data.split("_")
    prod_id, carrito_id = int(prod_id), int(carrito_id)

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM carrito_productos WHERE carrito_id = %s AND producto_id = %s", (carrito_id, prod_id))
    conn.commit()
    conn.close()

    bot.send_message(call.message.chat.id, "✅ Producto eliminado del carrito.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("eliminar_carrito_"))
def eliminar_carrito(call):
    carrito_id = int(call.data.split("_")[2])

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM carritos WHERE id = %s", (carrito_id,))
    conn.commit()
    conn.close()

    bot.send_message(call.message.chat.id, "🗑 Carrito eliminado.")


def generar_link_pago(carrito_id, user_id):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.nombre, cp.cantidad, p.precio, p.unidad 
        FROM carrito_productos cp
        JOIN productos p ON cp.producto_id = p.id
        WHERE cp.carrito_id = %s
    """, (carrito_id,))
    productos = cursor.fetchall()
    conn.close()

    if not productos:
        return None

    total = 0
    items = []
    for nombre, cantidad, precio, unidad in productos:
        subtotal = (precio / 10 * cantidad) if unidad == 'gramos' else (precio * cantidad)
        total += subtotal
        items.append({
            "title": nombre,
            "quantity": int(cantidad),
            "currency_id": "ARS",
            "unit_price": round(subtotal, 2)
        })

    

    preference_data = {
        "items": items,
        "payer": {
            "email": "cliente@email.com"
        },
        "back_urls": {
            "success": "https://tubot.com/pago_exitoso",
            "failure": "https://tubot.com/pago_fallido",
            "pending": "https://tubot.com/pago_pendiente"
        },
        "auto_return": "approved",
        "notification_url": MERCADO_PAGO_WEBHOOK_URL
    }

    preference_response = sdk.preference().create(preference_data)
    return preference_response["response"]["init_point"]

@bot.callback_query_handler(func=lambda call: call.data.startswith("pagar_carrito_"))
def pagar_carrito(call):
    carrito_id = int(call.data.split("_")[2])
    user_id = call.message.chat.id

    link_pago = generar_link_pago(carrito_id, user_id)
    if not link_pago:
        bot.send_message(user_id, "❌ No se pudo generar el link de pago.")
        return

    bot.send_message(user_id, f"💳 Paga tu pedido aquí:\n{link_pago}")


bot.set_my_commands([
    telebot.types.BotCommand("start", "Iniciar el bot"),
    telebot.types.BotCommand("registrar", "Registrar usuario")
])

print("Comandos registrados correctamente.")

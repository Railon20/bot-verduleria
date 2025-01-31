# database/db.py
import mysql.connector

def conectar():
    return mysql.connector.connect(
        host="localhost",
        user="vanina",
        password="lalala22R",
        database="tienda_verduleria"
    )

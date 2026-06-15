#!/usr/bin/env python3
"""
🤖 PUNTO DE ENTRADA PRINCIPAL DEL BOT DE TELEGRAM
Inicializa el bot con pyTelegramBotAPI (telebot), conecta el controlador central,
y arranca el bucle de polling infinito para escuchar comandos en caliente.
"""

import sys
import os
import telebot

# Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Agregar directorio raíz al PYTHONPATH para importaciones limpias
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.config.settings import Settings
from src.controllers.telegram_controller import TelegramController

def mostrar_guia_error():
    print("=" * 60)
    print("❌ ERROR CRÍTICO: CONFIGURACIÓN FALTANTE")
    print("=" * 60)
    print("No se encontró un TOKEN de Telegram válido.")
    print("Asegúrate de configurar tu archivo `.env` en la raíz del proyecto.")
    print("Ejemplo de contenido para el archivo `.env`:")
    print("TELEGRAM_BOT_TOKEN=tu_token_aqui")
    print("TELEGRAM_CHAT_ID=tu_chat_id_aqui")
    print("=" * 60)

def main():
    # Validar token
    token = Settings.TELEGRAM_BOT_TOKEN
    if not token or "TU_TOKEN_DE_TELEGRAM_AQUI" in token:
        mostrar_guia_error()
        sys.exit(1)
        
    print("🤖 Inicializando bot de Telegram...")
    bot = telebot.TeleBot(token)
    
    # Inyectar el controlador de enrutamiento central (delega la escucha a comandos SOLID)
    router = TelegramController(bot)
    
    print("🚀 ¡Bot activo y escuchando comandos en vivo! (Presiona Ctrl+C para salir)")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Error crítico en ejecución del bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    from src.database.session import init_db
    from src.services.gestor_banca_service import run_async
    print("🗄️ Inicializando base de datos en bot...")
    run_async(init_db())
    main()


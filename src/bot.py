#!/usr/bin/env python3
"""
🤖 PUNTO DE ENTRADA PRINCIPAL DEL BOT DE TELEGRAM
Inicializa el bot con pyTelegramBotAPI (telebot), conecta el controlador central,
arranca el scheduler de picks diario, y lanza el bucle de polling infinito.
"""

import sys
import os
import telebot
import src.config.encoding  # noqa: F401 — Centraliza reconfigure de stdout/stderr UTF-8

# Agregar directorio raíz al PYTHONPATH para importaciones limpias
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.config.settings import Settings
from src.controllers.telegram_controller import TelegramController
from src.services.scheduler_service import SchedulerService

# Instancia global del scheduler para acceso desde el controlador
scheduler_instance = None

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
    global scheduler_instance
    
    # Validar token
    token = Settings.TELEGRAM_BOT_TOKEN
    if not token or "TU_TOKEN_DE_TELEGRAM_AQUI" in token:
        mostrar_guia_error()
        sys.exit(1)
        
    print("🤖 Inicializando bot de Telegram...")
    bot = telebot.TeleBot(token)
    
    # Iniciar el scheduler de picks diarios
    scheduler_instance = SchedulerService()
    scheduler_instance.iniciar()
    
    # Inyectar el controlador de enrutamiento central (delega la escucha a comandos SOLID)
    router = TelegramController(bot, scheduler=scheduler_instance)
    
    print("🚀 ¡Bot activo y escuchando comandos en vivo! (Presiona Ctrl+C para salir)")
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n🧹 Deteniendo bot y scheduler...")
        scheduler_instance.detener()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error crítico en ejecución del bot: {e}")
        scheduler_instance.detener()
        sys.exit(1)

if __name__ == "__main__":
    main()



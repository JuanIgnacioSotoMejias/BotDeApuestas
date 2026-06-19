#!/usr/bin/env python3
"""
🚀 SUPERVISOR DE PROCESOS
Lanza el dashboard web y el bot de Telegram con auto-reinicio
si algún proceso cae inesperadamente (máximo 5 reintentos).
"""
import subprocess
import sys
import time
import os

# Agregar raíz al PYTHONPATH
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.database.session import init_db
from src.services.gestor_banca_service import run_async

# Configuración de reintentos
MAX_REINTENTOS = 5
DELAY_REINTENTO = 5  # segundos entre reintentos

print("🗄️ [Supervisor] Inicializando base de datos relacional...")
try:
    run_async(init_db())
    print("✅ [Supervisor] Base de datos inicializada con éxito.")
except Exception as e:
    print(f"⚠️ [Supervisor] Error al inicializar base de datos: {e}")

print("📡 [Supervisor] Iniciando Servidor Web del Dashboard (Puerto 8000)...")
web_process = subprocess.Popen([sys.executable, "src/services/web_server.py"])

print("🤖 [Supervisor] Iniciando Bot de Telegram con Scheduler...")
bot_process = subprocess.Popen([sys.executable, "src/bot.py"])

bot_reintentos = 0
web_reintentos = 0

try:
    while True:
        web_code = web_process.poll()
        bot_code = bot_process.poll()
        
        if web_code is not None:
            web_reintentos += 1
            if web_reintentos > MAX_REINTENTOS:
                print(f"❌ [Supervisor] El Servidor Web ha superado {MAX_REINTENTOS} reintentos. Terminando.")
                bot_process.terminate()
                sys.exit(web_code)
            print(f"⚠️ [Supervisor] Servidor Web caído (código {web_code}). Reiniciando... ({web_reintentos}/{MAX_REINTENTOS})")
            time.sleep(DELAY_REINTENTO)
            web_process = subprocess.Popen([sys.executable, "src/services/web_server.py"])
            
        if bot_code is not None:
            bot_reintentos += 1
            if bot_reintentos > MAX_REINTENTOS:
                print(f"❌ [Supervisor] El Bot de Telegram ha superado {MAX_REINTENTOS} reintentos. Terminando.")
                web_process.terminate()
                sys.exit(bot_code)
            print(f"⚠️ [Supervisor] Bot de Telegram caído (código {bot_code}). Reiniciando... ({bot_reintentos}/{MAX_REINTENTOS})")
            time.sleep(DELAY_REINTENTO)
            bot_process = subprocess.Popen([sys.executable, "src/bot.py"])
            
        time.sleep(2)
except KeyboardInterrupt:
    print("\n🧹 [Supervisor] Deteniendo procesos de forma limpia...")
    web_process.terminate()
    bot_process.terminate()
    sys.exit(0)

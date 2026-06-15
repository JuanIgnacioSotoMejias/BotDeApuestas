#!/usr/bin/env python3
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

print("🗄️ [Supervisor] Inicializando base de datos relacional...")
try:
    run_async(init_db())
    print("✅ [Supervisor] Base de datos inicializada con éxito.")
except Exception as e:
    print(f"⚠️ [Supervisor] Error al inicializar base de datos: {e}")

print("📡 [Supervisor] Iniciando Servidor Web del Dashboard (Puerto 8000)...")
web_process = subprocess.Popen([sys.executable, "src/services/web_server.py"])

print("🤖 [Supervisor] Iniciando Bot de Telegram en modo Polling...")
bot_process = subprocess.Popen([sys.executable, "src/bot.py"])


try:
    while True:
        # Monitorear si algún proceso ha terminado
        web_code = web_process.poll()
        bot_code = bot_process.poll()
        
        if web_code is not None:
            print(f"❌ [Supervisor] El Servidor Web ha terminado abruptamente con código {web_code}.")
            bot_process.terminate()
            sys.exit(web_code)
            
        if bot_code is not None:
            print(f"❌ [Supervisor] El Bot de Telegram ha terminado abruptamente con código {bot_code}.")
            web_process.terminate()
            sys.exit(bot_code)
            
        time.sleep(2)
except KeyboardInterrupt:
    print("\n🧹 [Supervisor] Deteniendo procesos de forma limpia...")
    web_process.terminate()
    bot_process.terminate()
    sys.exit(0)

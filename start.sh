#!/bin/sh
# start.sh: Iniciar el servidor web del dashboard y el bot de Telegram en paralelo

echo "📡 Iniciando Servidor Web del Dashboard en puerto 8000..."
python src/services/web_server.py &

echo "🤖 Iniciando Bot de Telegram en modo Polling..."
python src/bot.py

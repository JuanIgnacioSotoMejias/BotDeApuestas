#!/usr/bin/env python3
"""
🚀 COMANDO /START
Muestra un mensaje de bienvenida y guía al usuario en el uso del bot.
"""

from src.commands.base_command import BaseCommand
from src.config.settings import Settings

class StartCommand(BaseCommand):
    def ejecutar(self, bot, message, args):
        chat_id = message.chat.id
        es_admin = chat_id in Settings.TELEGRAM_ADMIN_IDS
        
        msg = (
            "🏆 *Bienvenido al Bot de Apuestas del Mundial 2026* 🏆\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Soy tu Analista Deportivo y Científico de Datos Personal. Estoy aquí para "
            "proporcionar análisis cuantitativos, valor esperado (EV) y reportes predictivos de partidos.\n\n"
            "📋 *Comandos Disponibles:*\n"
            "• `/start` - Muestra este menú de bienvenida.\n"
            "• `/analisis <equipo>` - Inicia un análisis predictivo para el partido de un equipo.\n"
            "• `/banca` - Consulta las estadísticas actuales y rendimiento de la banca.\n"
            "• `/picks` - Muestra las combinadas oficiales de hoy.\n"
        )
        
        if es_admin:
            msg += (
                "\n⚙️ *Comandos de Administrador:*\n"
                "• `/admin` o `/liquidar` - Panel inline para asentar tickets activos.\n"
                "• `/crear_picks` - Asistente guiado paso a paso para crear combinadas.\n"
                "• `/generar_picks` - Generar picks automáticamente con la IA de agentes.\n"
            )
            
        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 _Gestiona tu banca de forma inteligente y minimiza el riesgo de ruina._"
        )
        bot.reply_to(message, msg, parse_mode="Markdown")


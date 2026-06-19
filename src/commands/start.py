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
            "🏆 <b>Bienvenido al Bot de Apuestas del Mundial 2026</b> 🏆\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Soy tu Analista Deportivo y Científico de Datos Personal. Estoy aquí para "
            "proporcionar análisis cuantitativos, valor esperado (EV) y reportes predictivos de partidos.\n\n"
            "📋 <b>Comandos Disponibles:</b>\n"
            "• <code>/start</code> - Muestra este menú de bienvenida.\n"
            "• <code>/analisis &lt;equipo&gt;</code> - Inicia un análisis predictivo para el partido de un equipo.\n"
            "• <code>/banca</code> - Consulta las estadísticas actuales y rendimiento de la banca.\n"
            "• <code>/picks</code> - Muestra las combinadas oficiales de hoy.\n"
        )
        
        if es_admin:
            msg += (
                "\n⚙️ <b>Comandos de Administrador:</b>\n"
                "• <code>/admin</code> o <code>/liquidar</code> - Panel inline para asentar tickets activos.\n"
                "• <code>/crear_picks</code> - Asistente guiado paso a paso para crear combinadas.\n"
                "• <code>/generar_picks</code> - Generar picks automáticamente con la IA de agentes.\n"
                "• <code>/status</code> - Ver estado del bot, scheduler y uptime.\n"
            )
            
        msg += (
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <i>Gestiona tu banca de forma inteligente y minimiza el riesgo de ruina.</i>"
        )
        bot.reply_to(message, msg, parse_mode="HTML")


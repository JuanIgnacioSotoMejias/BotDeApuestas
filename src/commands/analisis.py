#!/usr/bin/env python3
"""
📊 COMANDO /ANALISIS
Este comando delega la orquestación a la arquitectura Multi-Agente (OrchestratorAgent)
y responde al usuario final en Telegram.
"""

from src.commands.base_command import BaseCommand
from src.agents.orchestrator_agent import OrchestratorAgent

class AnalisisCommand(BaseCommand):
    def __init__(self):
        self.orchestrator = OrchestratorAgent()

    def ejecutar(self, bot, message, args):
        if not args:
            bot.reply_to(
                message, 
                "⚠️ *Uso incorrecto del comando.*\n"
                "Por favor, indica el nombre de un equipo o el ID del partido.\n"
                "Ejemplo: `/analisis España` o `/analisis Cabo Verde`",
                parse_mode="Markdown"
            )
            return

        consulta = " ".join(args)
        chat_id = message.chat.id
        
        # Enviar mensaje de carga (smooth UX)
        loading_msg = bot.reply_to(
            message, 
            "🔍 *Activando equipo de agentes (Scout, Científico de Datos, Periodista)...*\n"
            "_(Esto puede tardar entre 5 y 15 segundos)_", 
            parse_mode="Markdown"
        )

        try:
            # Ejecutar el análisis a través del orquestador multi-agente
            segmentos = self.orchestrator.ejecutar_analisis_completo(chat_id, consulta)
            
            # Enviar cada segmento con fallback robusto a texto plano si falla el parseo de Markdown
            for segmento in segmentos:
                try:
                    bot.send_message(chat_id, segmento, parse_mode="Markdown")
                except Exception as e_parse:
                    print(f"⚠️ AnalisisCommand: Error de Markdown en segmento ({e_parse}). Reenviando en texto plano...")
                    bot.send_message(chat_id, segmento)
                
            # Limpiar el mensaje de carga de forma segura
            try:
                bot.delete_message(chat_id, loading_msg.message_id)
            except Exception:
                pass

        except Exception as e:
            print(f"❌ Error en AnalisisCommand (Multi-Agent): {e}")
            bot.reply_to(
                message,
                "❌ *Error al procesar el análisis con el equipo de agentes.*\n"
                "Ocurrió un inconveniente al coordinar los servicios del Scout o Científico.",
                parse_mode="Markdown"
            )
            bot.delete_message(chat_id, loading_msg.message_id)

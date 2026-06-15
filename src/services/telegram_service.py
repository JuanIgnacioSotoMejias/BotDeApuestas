#!/usr/bin/env python3
"""
📢 SERVICIO DE NOTIFICACIONES DE TELEGRAM (SOLID)
Este servicio se encarga exclusivamente de formatear y enviar reportes a Telegram.
Se alimenta de la clase de configuración Settings.
"""

import os
import json
import urllib.request
import sys
from src.config.settings import Settings

# Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

class TelegramService:
    def __init__(self):
        self.token = Settings.TELEGRAM_BOT_TOKEN
        self.chat_id = Settings.TELEGRAM_CHAT_ID

    def validar_configuracion(self):
        """Verifica que existan credenciales válidas y que no sean los valores por defecto."""
        if not self.token or not self.chat_id or \
           "TU_TOKEN_DE_TELEGRAM_AQUI" in self.token or \
           "TU_CHAT_ID_DE_TELEGRAM_AQUI" in self.chat_id:
            return False
        return True

    def enviar_mensaje(self, texto):
        """Envía un mensaje en formato Markdown a la API de Telegram."""
        if not self.validar_configuracion():
            print("⚠️ Telegram Service: Credenciales no configuradas o inválidas en Settings.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": texto,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                res = json.loads(response.read().decode("utf-8"))
                if res.get("ok"):
                    return True
                else:
                    print(f"❌ Error en respuesta de la API de Telegram: {res}")
                    return False
        except Exception as e:
            print(f"❌ Error de red en TelegramService: {e}")
            return False

    def enviar_reporte_picks(self, JUGADAS_PATH):
        """Formatea y envía las jugadas del archivo JSON indicado."""
        if not os.path.exists(JUGADAS_PATH):
            print(f"❌ TelegramService: No se encontró el archivo de jugadas en {JUGADAS_PATH}")
            return False
            
        with open(JUGADAS_PATH, "r", encoding="utf-8") as f:
            jugadas = json.load(f)
            
        fecha = jugadas.get("fecha_jornada", "N/A")
        parleys = jugadas.get("parleys", {})
        
        msg = f"🏆 *PARLEYS MUNDIAL 2026 — JORNADA {fecha}* 🏆\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        p_seguro = parleys.get("parley_seguro", {})
        if p_seguro:
            msg += f"🟢 *{p_seguro.get('nombre', 'Combinada Segura')}*\n"
            msg += f"🔸 *Cuota Total:* `{p_seguro.get('cuota_total_estimada', 'N/A')}` | *Stake:* `{p_seguro.get('stake_sugerido', 'N/A')}`\n"
            msg += f"🔸 *Probabilidad Real:* `{p_seguro.get('probabilidad_estadistica_combinada', 'N/A')}`\n"
            msg += "📋 *Selecciones:*\n"
            for sel in p_seguro.get("selecciones", []):
                msg += f"  • _{sel.get('partido')}_: *{sel.get('pronostico')}* (Cuota: {sel.get('cuota')}) — Prob: {sel.get('probabilidad_estadistica')} 🎯\n"
            msg += f"💰 *Inversión:* $1.00 USD | *Retorno:* ${p_seguro.get('cuota_total_estimada', 0.0):.2f} USD\n\n"
            
        msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"

        p_arriesgado = parleys.get("parley_arriesgado", {})
        if p_arriesgado:
            msg += f"🔴 *{p_arriesgado.get('nombre', 'Combinada Arriesgada')}*\n"
            msg += f"🔸 *Cuota Total:* `{p_arriesgado.get('cuota_total_estimada', 'N/A')}` | *Stake:* `{p_arriesgado.get('stake_sugerido', 'N/A')}`\n"
            msg += f"🔸 *Probabilidad Real:* `{p_arriesgado.get('probabilidad_estadistica_combinada', 'N/A')}`\n"
            msg += "📋 *Selecciones:*\n"
            for sel in p_arriesgado.get("selecciones", []):
                msg += f"  • _{sel.get('partido')}_: *{sel.get('pronostico')}* (Cuota: {sel.get('cuota')}) — Prob: {sel.get('probabilidad_estadistica')} ⚡\n"
            msg += f"💰 *Inversión:* $1.00 USD | *Retorno:* ${p_arriesgado.get('cuota_total_estimada', 0.0):.2f} USD\n\n"
            
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "💡 _Verifica alineaciones oficiales 1 hora antes de los encuentros._"
        
        print("TelegramService: Enviando reporte de picks...")
        return self.enviar_mensaje(msg)

    def enviar_reporte_banca(self, HISTORIAL_PATH):
        """Formatea y envía el reporte financiero de banca."""
        if not os.path.exists(HISTORIAL_PATH):
            print(f"❌ TelegramService: No se encontró el archivo de banca en {HISTORIAL_PATH}")
            return False
            
        with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
            historial = json.load(f)
            
        banca = historial.get("banca", {})
        stats = historial.get("estadisticas_globales", {})
        activas = historial.get("apuestas_activas", [])
        
        msg = "📊 *RETO BANCA MUNDIAL 2026: $10 ➡️ $100* 📊\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"💵 *Banca Inicial:* ${banca.get('banca_inicial', 0.0):.2f} USD\n"
        msg += f"💰 *Banca Disponible:* ${banca.get('banca_actual', 0.0):.2f} USD\n"
        msg += f"🔥 *Dinero en Juego:* ${banca.get('dinero_en_juego', 0.0):.2f} USD\n"
        msg += f"📈 *Yield / Rentabilidad:* `{stats.get('rendimiento_yield', '0.0%')}`\n"
        msg += f"🎯 *Rendimiento ROI:* `{stats.get('roi', '0.0%')}`\n\n"
        
        msg += "📈 *Desglose de Partidas:*\n"
        msg += f"  • Total Jugadas: {stats.get('total_apuestas_realizadas', 0)}\n"
        msg += f"  • Ganadas: {stats.get('apuestas_ganadas', 0)} | Perdidas: {stats.get('apuestas_perdidas', 0)}\n"
        msg += f"  • Pendientes: {len(activas)} 🔄\n\n"
        
        if activas:
            msg += "📋 *Tickets en Curso:*\n"
            for tkt in activas:
                msg += f"  • [{tkt.get('tipo_parley')}]: Invertido: ${tkt.get('inversion', 0.0):.2f} USD ➡️ Retorno Potencial: ${tkt.get('retorno_potencial', 0.0):.2f} USD\n"
                
        msg += "\n━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📌 _Objetivo: Crecimiento compuesto sostenible minimizando riesgo de ruina._"
        
        print("TelegramService: Enviando reporte de banca...")
        return self.enviar_mensaje(msg)

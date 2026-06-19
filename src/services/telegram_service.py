#!/usr/bin/env python3
"""
📢 SERVICIO DE NOTIFICACIONES DE TELEGRAM (PROFESIONAL)
Envía mensajes formateados en HTML con reintentos, splitting automático
y formato premium para picks, banca y notificaciones.
"""

import os
import json
import time
import urllib.request
import urllib.error
import sys
import datetime
from src.config.settings import Settings
import src.config.encoding  # noqa: F401 — Centraliza reconfigure de stdout/stderr UTF-8

# Límite de caracteres por mensaje de Telegram
MAX_MESSAGE_LENGTH = 4000


def escape_html(text):
    """Escapa caracteres especiales para HTML de Telegram."""
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


class TelegramService:
    def __init__(self):
        self.token = Settings.TELEGRAM_BOT_TOKEN
        self.chat_id = Settings.TELEGRAM_CHAT_ID
        self._max_retries = 3
        self._base_delay = 1.0  # segundos

    def validar_configuracion(self):
        """Verifica que existan credenciales válidas y que no sean los valores por defecto."""
        if not self.token or not self.chat_id or \
           "TU_TOKEN_DE_TELEGRAM_AQUI" in self.token or \
           "TU_CHAT_ID_DE_TELEGRAM_AQUI" in self.chat_id:
            return False
        return True

    def enviar_mensaje(self, texto, parse_mode="HTML", chat_id=None):
        """
        Envía un mensaje a la API de Telegram con reintentos y splitting automático.
        - parse_mode: 'HTML' (recomendado) o 'Markdown'
        - Divide mensajes que excedan 4000 caracteres
        - Reintenta hasta 3 veces con backoff exponencial ante errores de red o rate limit
        """
        if not self.validar_configuracion():
            print("⚠️ TelegramService: Credenciales no configuradas o inválidas.")
            return False

        target_chat = chat_id or self.chat_id

        # Splitting automático si el mensaje es muy largo
        segmentos = self._dividir_mensaje(texto)
        
        exito_total = True
        for i, segmento in enumerate(segmentos):
            ok = self._enviar_con_reintentos(segmento, parse_mode, target_chat)
            if not ok:
                print(f"❌ TelegramService: Falló el envío del segmento {i+1}/{len(segmentos)}")
                exito_total = False
            # Anti rate-limit: pausa entre segmentos
            if len(segmentos) > 1 and i < len(segmentos) - 1:
                time.sleep(0.5)
                
        return exito_total

    def _enviar_con_reintentos(self, texto, parse_mode, chat_id):
        """Envía un mensaje con reintentos y backoff exponencial."""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        data = json.dumps(payload).encode("utf-8")

        for intento in range(self._max_retries):
            try:
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    res = json.loads(response.read().decode("utf-8"))
                    if res.get("ok"):
                        return True
                    else:
                        print(f"❌ TelegramService: API respondió con error: {res}")
                        # Si es error de parseo, reintentar sin formato
                        if "can't parse" in str(res).lower():
                            payload["parse_mode"] = None
                            data = json.dumps(payload).encode("utf-8")
                            
            except urllib.error.HTTPError as e:
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8")
                except Exception:
                    pass
                    
                if e.code == 429:
                    # Rate limited — extraer retry_after
                    retry_after = self._base_delay * (2 ** intento)
                    try:
                        error_data = json.loads(error_body)
                        retry_after = error_data.get("parameters", {}).get("retry_after", retry_after)
                    except Exception:
                        pass
                    print(f"⚠️ TelegramService: Rate limited (429). Esperando {retry_after}s... (intento {intento+1}/{self._max_retries})")
                    time.sleep(retry_after)
                    continue
                elif e.code == 400 and "can't parse" in error_body.lower():
                    # Error de parseo HTML/Markdown — reintentar sin formato
                    print(f"⚠️ TelegramService: Error de parseo. Reenviando sin formato...")
                    payload["parse_mode"] = None
                    data = json.dumps(payload).encode("utf-8")
                    continue
                else:
                    print(f"❌ TelegramService: HTTP {e.code}: {error_body[:300]}")
                    
            except Exception as e:
                delay = self._base_delay * (2 ** intento)
                print(f"⚠️ TelegramService: Error de red ({e}). Reintentando en {delay}s... (intento {intento+1}/{self._max_retries})")
                time.sleep(delay)
                
        return False

    def _dividir_mensaje(self, texto):
        """Divide un mensaje largo en segmentos de máximo MAX_MESSAGE_LENGTH caracteres."""
        if len(texto) <= MAX_MESSAGE_LENGTH:
            return [texto]
        
        segmentos = []
        lineas = texto.split("\n")
        segmento_actual = ""
        
        for linea in lineas:
            # Si agregar esta línea excede el límite, cortar aquí
            if len(segmento_actual) + len(linea) + 1 > MAX_MESSAGE_LENGTH:
                if segmento_actual:
                    segmentos.append(segmento_actual.rstrip())
                segmento_actual = linea + "\n"
            else:
                segmento_actual += linea + "\n"
                
        if segmento_actual.strip():
            segmentos.append(segmento_actual.rstrip())
            
        return segmentos if segmentos else [texto[:MAX_MESSAGE_LENGTH]]

    # ─── REPORTES FORMATEADOS ──────────────────────────────────────────

    def enviar_reporte_picks(self, JUGADAS_PATH):
        """Formatea y envía las jugadas del archivo JSON con formato profesional HTML."""
        if not os.path.exists(JUGADAS_PATH):
            print(f"❌ TelegramService: No se encontró el archivo de jugadas en {JUGADAS_PATH}")
            return False
            
        with open(JUGADAS_PATH, "r", encoding="utf-8") as f:
            jugadas = json.load(f)
            
        fecha = jugadas.get("fecha_jornada", "N/A")
        parleys = jugadas.get("parleys", {})

        # Obtener stats de banca para incluir contexto e inversión real
        stats_text = ""
        inversion_seguro = 1.0
        inversion_arriesgado = 1.0
        try:
            from src.services.gestor_banca_service import GestorBancaService
            banca_srv = GestorBancaService()
            datos = banca_srv.cargar_historial()
            if datos:
                b = datos.get("banca", {})
                s = datos.get("estadisticas_globales", {})
                stats_text = (
                    f"💰 Banca: <code>${b.get('banca_actual', 10.0):.2f}</code> USD"
                    f" │ ROI: <code>{s.get('roi', '0.0%')}</code>"
                    f" │ Racha: {s.get('apuestas_ganadas', 0)}W-{s.get('apuestas_perdidas', 0)}L"
                )
                # Extraer inversión real de los tickets activos
                for tkt in datos.get("apuestas_activas", []):
                    tipo = tkt.get("tipo_parley", "")
                    if "Segura" in tipo or "Valor" in tipo:
                        inversion_seguro = tkt.get("inversion", 1.0)
                    elif "Alto" in tipo or "Arriesgad" in tipo:
                        inversion_arriesgado = tkt.get("inversion", 1.0)
        except Exception:
            pass

        # Cabecera del mensaje
        msg = (
            "🏆⚽ <b>PARLEYS MUNDIAL 2026</b> ⚽🏆\n"
            f"📅 <b>Jornada {escape_html(fecha)}</b>\n"
        )
        if stats_text:
            msg += f"{stats_text}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Parley de Valor (Seguro)
        p_seguro = parleys.get("parley_seguro", {})
        if p_seguro:
            cuota_total = p_seguro.get('cuota_total_estimada', 0)
            msg += f"🟢 <b>{escape_html(p_seguro.get('nombre', 'Combinada de Valor'))}</b>\n"
            msg += f"📊 Cuota: <b>{cuota_total:.2f}x</b>"
            msg += f" │ Prob. IA: <code>{p_seguro.get('probabilidad_estadistica_combinada', 'N/A')}</code>\n"
            msg += f"💵 Stake: <code>{p_seguro.get('stake_sugerido', '5/10')}</code>\n\n"
            
            for idx, sel in enumerate(p_seguro.get("selecciones", []), 1):
                prob_est = sel.get('probabilidad_estadistica', 'N/A')
                prob_imp = sel.get('probabilidad_implicita', 'N/A')
                valor = sel.get('valor', '')
                valor_emoji = "✅" if "Sí" in str(valor) else "⚠️"
                
                msg += (
                    f"  {idx}. <b>{escape_html(sel.get('partido', ''))}</b>\n"
                    f"     ➜ {escape_html(sel.get('pronostico', ''))}\n"
                    f"     📈 Cuota: <code>{sel.get('cuota', 0)}</code>"
                    f" │ Prob: <code>{prob_est}</code>"
                    f" │ {valor_emoji} {escape_html(str(valor))}\n\n"
                )
            
            if cuota_total:
                try:
                    retorno = float(cuota_total) * inversion_seguro
                    msg += f"  💰 <b>${inversion_seguro:.2f} ➜ ${retorno:.2f} USD</b>\n\n"
                except (ValueError, TypeError):
                    pass

        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Parley Arriesgado (Bomba)
        p_arriesgado = parleys.get("parley_arriesgado", {})
        if p_arriesgado:
            cuota_total = p_arriesgado.get('cuota_total_estimada', 0)
            msg += f"🔴 <b>{escape_html(p_arriesgado.get('nombre', 'Combinada Bomba'))}</b>\n"
            msg += f"📊 Cuota: <b>{cuota_total:.2f}x</b>"
            msg += f" │ Prob. IA: <code>{p_arriesgado.get('probabilidad_estadistica_combinada', 'N/A')}</code>\n"
            msg += f"💵 Stake: <code>{p_arriesgado.get('stake_sugerido', '1/10')}</code>\n\n"
            
            for idx, sel in enumerate(p_arriesgado.get("selecciones", []), 1):
                prob_est = sel.get('probabilidad_estadistica', 'N/A')
                valor = sel.get('valor', '')
                valor_emoji = "✅" if "Sí" in str(valor) else "⚡"
                
                msg += (
                    f"  {idx}. <b>{escape_html(sel.get('partido', ''))}</b>\n"
                    f"     ➜ {escape_html(sel.get('pronostico', ''))}\n"
                    f"     📈 Cuota: <code>{sel.get('cuota', 0)}</code>"
                    f" │ Prob: <code>{prob_est}</code>"
                    f" │ {valor_emoji} {escape_html(str(valor))}\n\n"
                )
            
            if cuota_total:
                try:
                    retorno = float(cuota_total) * inversion_arriesgado
                    msg += f"  💰 <b>${inversion_arriesgado:.2f} ➜ ${retorno:.2f} USD</b>\n\n"
                except (ValueError, TypeError):
                    pass

        # Footer
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🤖 <i>Análisis generado por Agentes IA</i>\n"
        msg += "⏰ <i>Verifica alineaciones 1h antes del kickoff</i>\n"
        msg += "📌 <i>Gestiona tu banca con disciplina — No apuestes lo que no puedas perder</i>"
        
        print("📢 TelegramService: Enviando reporte de picks...")
        return self.enviar_mensaje(msg, parse_mode="HTML")

    def enviar_reporte_banca(self, historial):
        """Formatea y envía el reporte financiero de banca en HTML."""
        banca = historial.get("banca", {})
        stats = historial.get("estadisticas_globales", {})
        activas = historial.get("apuestas_activas", [])
        
        banca_actual = banca.get('banca_actual', 0.0)
        banca_inicial = banca.get('banca_inicial', 10.0)
        progreso = min(100, max(0, (banca_actual / 100.0) * 100))  # Objetivo $100
        barra = self._generar_barra_progreso(progreso)
        
        msg = (
            "📊 <b>RETO BANCA MUNDIAL 2026</b> 📊\n"
            f"🎯 $10 ➜ $100 │ {barra} {progreso:.0f}%\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            f"💵 Banca Inicial: <code>${banca_inicial:.2f} USD</code>\n"
            f"💰 <b>Banca Disponible: <code>${banca_actual:.2f} USD</code></b>\n"
            f"🔥 En Juego: <code>${banca.get('dinero_en_juego', 0.0):.2f} USD</code>\n\n"
            
            f"📈 Yield: <code>{stats.get('rendimiento_yield', '0.0%')}</code>\n"
            f"🎯 ROI: <code>{stats.get('roi', '0.0%')}</code>\n\n"
            
            "📋 <b>Desglose:</b>\n"
            f"  ✅ Ganadas: <b>{stats.get('apuestas_ganadas', 0)}</b>\n"
            f"  ❌ Perdidas: <b>{stats.get('apuestas_perdidas', 0)}</b>\n"
            f"  🔄 Anuladas: <b>{stats.get('apuestas_anuladas', 0)}</b>\n"
            f"  ⏳ En curso: <b>{len(activas)}</b>\n"
        )
        
        if activas:
            msg += "\n📋 <b>Tickets Activos:</b>\n"
            for tkt in activas:
                tipo = escape_html(tkt.get('tipo_parley', 'Combinada'))
                inversion = tkt.get('inversion', 0.0)
                retorno = tkt.get('retorno_potencial', 0.0)
                msg += f"  • {tipo}: <code>${inversion:.2f}</code> ➜ <code>${retorno:.2f}</code>\n"
                
        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "📌 <i>Crecimiento compuesto — Minimizar riesgo de ruina</i>"
        
        print("📢 TelegramService: Enviando reporte de banca...")
        return self.enviar_mensaje(msg, parse_mode="HTML")

    def _generar_barra_progreso(self, porcentaje):
        """Genera una barra de progreso visual con bloques Unicode."""
        llenos = int(porcentaje / 10)
        vacios = 10 - llenos
        return "█" * llenos + "░" * vacios

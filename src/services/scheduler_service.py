#!/usr/bin/env python3
"""
⏰ SERVICIO DE PROGRAMACIÓN AUTOMÁTICA (SCHEDULER)
Ejecuta la generación y publicación de picks a una hora configurable cada día.
Utiliza threading nativo de Python sin dependencias externas.
"""

import sys
import os
import threading
import datetime
import traceback
import src.config.encoding  # noqa: F401 — Centraliza reconfigure de stdout/stderr UTF-8

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.config.settings import Settings


class SchedulerService:
    """Servicio de scheduling que ejecuta tareas diarias a una hora configurada."""

    def __init__(self):
        self.hora = Settings.SCHEDULER_HOUR
        self.minuto = Settings.SCHEDULER_MINUTE
        self.tz_offset = Settings.SCHEDULER_TIMEZONE_OFFSET
        self.enabled = Settings.SCHEDULER_ENABLED
        self._timer = None
        self._running = False
        self._proxima_ejecucion = None
        self._ultimo_envio_exitoso = None
        self._ultimo_error = None
        self._ejecuciones_completadas = 0
        self._inicio = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=self.tz_offset)))

    @property
    def uptime(self):
        """Retorna el uptime del scheduler como string legible."""
        ahora = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=self.tz_offset)))
        delta = ahora - self._inicio
        horas, resto = divmod(int(delta.total_seconds()), 3600)
        minutos, segundos = divmod(resto, 60)
        if horas >= 24:
            dias = horas // 24
            horas = horas % 24
            return f"{dias}d {horas}h {minutos}m"
        return f"{horas}h {minutos}m {segundos}s"

    @property
    def proxima_ejecucion_str(self):
        """Retorna la próxima ejecución como string legible."""
        if self._proxima_ejecucion:
            return self._proxima_ejecucion.strftime("%Y-%m-%d %H:%M:%S (UTC%+d)" % self.tz_offset)
        return "No programada"

    def _calcular_segundos_hasta_hora(self):
        """Calcula los segundos restantes hasta la próxima hora objetivo."""
        tz = datetime.timezone(datetime.timedelta(hours=self.tz_offset))
        ahora = datetime.datetime.now(tz)
        
        # Hora objetivo de hoy
        objetivo_hoy = ahora.replace(hour=self.hora, minute=self.minuto, second=0, microsecond=0)
        
        if ahora >= objetivo_hoy:
            # Ya pasó la hora de hoy, programar para mañana
            objetivo = objetivo_hoy + datetime.timedelta(days=1)
        else:
            objetivo = objetivo_hoy
        
        self._proxima_ejecucion = objetivo
        delta = (objetivo - ahora).total_seconds()
        return max(delta, 1)  # Mínimo 1 segundo

    def _ejecutar_tarea_diaria(self):
        """Tarea que se ejecuta automáticamente cada día."""
        tz = datetime.timezone(datetime.timedelta(hours=self.tz_offset))
        ahora = datetime.datetime.now(tz)
        
        print(f"\n{'='*60}")
        print(f"⏰ [Scheduler] Ejecutando tarea programada — {ahora.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        try:
            # 1. Inicializar DB si es necesario
            from src.database.session import init_db
            from src.services.gestor_banca_service import run_async
            try:
                run_async(init_db())
            except Exception:
                pass  # Ya inicializada

            # 2. Generar picks con la IA
            from src.services.picks_generator_service import PicksGeneratorService
            gen_srv = PicksGeneratorService()
            exito, respuesta = gen_srv.generar_picks_ia()

            if exito:
                print(f"✅ [Scheduler] Picks generados y publicados con éxito: {respuesta}")
                self._ultimo_envio_exitoso = ahora
                self._ultimo_error = None
            else:
                print(f"❌ [Scheduler] Error al generar picks: {respuesta}")
                self._ultimo_error = respuesta
                
                # Enviar notificación de error al admin
                try:
                    from src.services.telegram_service import TelegramService
                    tg = TelegramService()
                    tg.enviar_mensaje(
                        "⚠️ <b>Error en Scheduler de Picks</b>\n\n"
                        f"La generación automática de las {self.hora}:{self.minuto:02d} AM falló.\n"
                        f"<code>{respuesta[:500]}</code>\n\n"
                        "Usa /generar_picks para intentar manualmente.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

            self._ejecuciones_completadas += 1

        except Exception as e:
            error_detail = traceback.format_exc()
            print(f"❌ [Scheduler] Excepción crítica en tarea diaria: {e}")
            print(error_detail)
            self._ultimo_error = str(e)

        # Reprogramar para mañana
        self._programar_siguiente()

    def _programar_siguiente(self):
        """Programa el siguiente disparo del timer."""
        if not self._running:
            return
            
        segundos = self._calcular_segundos_hasta_hora()
        horas_restantes = segundos / 3600
        
        print(f"⏰ [Scheduler] Próxima ejecución: {self._proxima_ejecucion.strftime('%Y-%m-%d %H:%M')} "
              f"(en {horas_restantes:.1f} horas)")
        
        self._timer = threading.Timer(segundos, self._ejecutar_tarea_diaria)
        self._timer.daemon = True
        self._timer.start()

    def iniciar(self):
        """Inicia el scheduler en background."""
        if not self.enabled:
            print("⏰ [Scheduler] Deshabilitado en configuración (SCHEDULER_ENABLED=false)")
            return
        
        self._running = True
        print(f"⏰ [Scheduler] Iniciado — Publicación diaria a las {self.hora}:{self.minuto:02d} AM (UTC{self.tz_offset:+d})")
        self._programar_siguiente()

    def detener(self):
        """Detiene el scheduler limpiamente."""
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        print("⏰ [Scheduler] Detenido.")

    def forzar_ejecucion(self):
        """Ejecuta la tarea inmediatamente (para testing o comando manual)."""
        print("⏰ [Scheduler] Ejecución forzada manualmente...")
        thread = threading.Thread(target=self._ejecutar_tarea_diaria, daemon=True)
        thread.start()

    def obtener_estado(self):
        """Retorna un diccionario con el estado actual del scheduler."""
        tz = datetime.timezone(datetime.timedelta(hours=self.tz_offset))
        return {
            "habilitado": self.enabled,
            "en_ejecucion": self._running,
            "hora_programada": f"{self.hora}:{self.minuto:02d} AM (UTC{self.tz_offset:+d})",
            "proxima_ejecucion": self.proxima_ejecucion_str,
            "ultimo_envio_exitoso": self._ultimo_envio_exitoso.strftime("%Y-%m-%d %H:%M") if self._ultimo_envio_exitoso else "Nunca",
            "ultimo_error": self._ultimo_error or "Ninguno",
            "ejecuciones_completadas": self._ejecuciones_completadas,
            "uptime": self.uptime
        }

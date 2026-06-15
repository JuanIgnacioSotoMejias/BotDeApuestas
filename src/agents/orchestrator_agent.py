#!/usr/bin/env python3
"""
🎛️ AGENTE ORQUESTADOR (DIRECTOR TÉCNICO)
Este agente coordina el flujo de ejecución completo (Scout -> Científico -> Periodista)
y mantiene la caché en memoria de sesión por chat_id para habilitar preguntas de seguimiento.
"""

from src.agents.scout_agent import ScoutAgent
from src.agents.cientifico_agent import CientificoAgent
from src.agents.periodista_agent import PeriodistaAgent

class OrchestratorAgent:
    def __init__(self):
        self.scout = ScoutAgent()
        self.cientifico = CientificoAgent()
        self.periodista = PeriodistaAgent()
        
        # Memoria de sesión en memoria
        # Estructura: { chat_id: { "partido_datos": dict, "analisis": str } }
        self.memoria_sesion = {}

    def guardar_en_memoria(self, chat_id, partido_datos, analisis):
        """Guarda los datos del encuentro y el último reporte en la memoria del chat."""
        self.memoria_sesion[chat_id] = {
            "partido_datos": partido_datos,
            "analisis": analisis
        }

    def tiene_contexto(self, chat_id):
        """Verifica si existe un partido analizado recientemente para este chat."""
        return chat_id in self.memoria_sesion

    def ejecutar_analisis_completo(self, chat_id, consulta):
        """
        Ejecuta el pipeline de análisis secuencial:
        1. ScoutAgent extrae y limpia los datos.
        2. CientificoAgent genera el análisis predictivo.
        3. Se guarda en memoria de sesión.
        4. PeriodistaAgent formatea y segmenta para Telegram.
        """
        print(f"🎛️ OrchestratorAgent: Iniciando pipeline para chat_id={chat_id}, consulta='{consulta}'")
        
        # 1. Obtener datos (Scout)
        datos = self.scout.buscar_datos(consulta)
        
        # 2. Analizar (Científico)
        analisis_crudo = self.cientifico.analizar_encuentro(datos)
        
        # 3. Guardar en memoria de sesión para seguimiento
        self.guardar_en_memoria(chat_id, datos, analisis_crudo)
        
        # 4. Formatear y segmentar (Periodista)
        segmentos = self.periodista.formatear_analisis(analisis_crudo)
        
        print("🎛️ OrchestratorAgent: Pipeline completado con éxito.")
        return segmentos

    def ejecutar_analisis_seguimiento(self, chat_id, pregunta_usuario):
        """
        Responde a una pregunta sobre el último partido analizado:
        1. Recupera el contexto de memoria.
        2. CientificoAgent responde contextualmente.
        3. Se actualiza el análisis en memoria con la nueva respuesta.
        4. PeriodistaAgent formatea y segmenta.
        """
        if not self.tiene_contexto(chat_id):
            print(f"⚠️ OrchestratorAgent: No hay contexto de memoria para chat_id={chat_id}")
            return None
            
        print(f"🎛️ OrchestratorAgent: Procesando seguimiento para chat_id={chat_id}")
        contexto = self.memoria_sesion[chat_id]
        datos = contexto["partido_datos"]
        analisis_previo = contexto["analisis"]
        
        # 1. Responder pregunta (Científico)
        respuesta_cruda = self.cientifico.responder_pregunta_seguimiento(datos, analisis_previo, pregunta_usuario)
        
        # 2. Actualizar el historial acumulando la conversación para la siguiente pregunta
        nuevo_analisis_acumulado = (
            f"{analisis_previo}\n\n"
            f"--- SEGUIMIENTO ---\n"
            f"Pregunta: {pregunta_usuario}\n"
            f"Respuesta: {respuesta_cruda}"
        )
        self.guardar_en_memoria(chat_id, datos, nuevo_analisis_acumulado)
        
        # 3. Formatear (Periodista)
        segmentos = self.periodista.formatear_analisis(respuesta_cruda)
        
        print("🎛️ OrchestratorAgent: Pipeline de seguimiento completado.")
        return segmentos

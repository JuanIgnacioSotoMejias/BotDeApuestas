#!/usr/bin/env python3
"""
🧠 AGENTE CIENTÍFICO DE DATOS (INTELIGENCIA ANALÍTICA)
Este agente actúa como el motor cognitivo de la aplicación. Se encarga de inyectar los datos
estadísticos en el prompt maestro y consultar al LLMService para obtener predicciones deportivas.
"""

import json
from src.services.llm_service import LLMService

class CientificoAgent:
    def __init__(self):
        self.llm_service = LLMService()

    def _convertir_datos_a_texto(self, datos_dict):
        """Convierte los datos estructurados en un bloque de texto legible para el prompt de la IA."""
        if datos_dict.get("encontrado_en_api"):
            goles = datos_dict.get("goles_torneo", {})
            goles_str = "\n".join([f"  - {team}: {goals} goles" for team, goals in goles.items()])
            
            datos_texto = (
                f"Partido: {datos_dict.get('partido')}\n"
                f"Fase/Grupo: {datos_dict.get('fase')} - {datos_dict.get('grupo')}\n"
                f"Estadio: {datos_dict.get('estadio')}\n"
                f"Fecha: {datos_dict.get('fecha')}\n"
                f"Clima: {datos_dict.get('clima')}\n"
                f"Goles anotados en el torneo:\n{goles_str}\n"
                f"Historial H2H reciente: {datos_dict.get('h2h_resumen')}\n"
            )
        else:
            datos_texto = (
                f"Partido Consultador: {datos_dict.get('partido_solicitado')} vs. Rival del Grupo\n"
                f"Nota: {datos_dict.get('nota')}\n"
            )
        return datos_texto

    def analizar_encuentro(self, datos_partido):
        """
        Recibe el diccionario de datos del Scout y le pide al LLM un análisis predictivo detallado.
        """
        print("🧠 CientificoAgent: Formateando datos y solicitando análisis predictivo...")
        datos_texto = self._convertir_datos_a_texto(datos_partido)
        analisis = self.llm_service.analizar_partido(datos_texto)
        print("🧠 CientificoAgent: Análisis recibido con éxito.")
        return analisis

    def responder_pregunta_seguimiento(self, datos_partido, analisis_previo, pregunta_usuario):
        """
        Responde contextualmente a una pregunta de seguimiento del usuario sobre el último partido analizado.
        """
        print(f"🧠 CientificoAgent: Procesando pregunta de seguimiento: '{pregunta_usuario}'...")
        datos_texto = self._convertir_datos_a_texto(datos_partido)
        
        # Construimos un prompt contextual especial que recuerda la conversación previa
        prompt_seguimiento = (
            f"El usuario te realizó previamente un análisis para el siguiente encuentro:\n\n"
            f"--- DATOS DEL ENCUENTRO ---\n{datos_texto}\n\n"
            f"--- TU ANÁLISIS PREVIO ---\n{analisis_previo}\n\n"
            f"--- NUEVA PREGUNTA DEL USUARIO ---\n"
            f"El usuario pregunta: '{pregunta_usuario}'\n\n"
            f"Responde de manera concisa, analítica y objetiva a su pregunta usando el contexto deportivo del encuentro anterior."
        )
        
        # Consultar directamente al servicio
        respuesta = self.llm_service.analizar_partido(prompt_seguimiento)
        print("🧠 CientificoAgent: Respuesta de seguimiento recibida.")
        return respuesta

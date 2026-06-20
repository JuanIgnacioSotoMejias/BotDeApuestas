#!/usr/bin/env python3
"""
🎟️ SERVICIO DE QUINIELA IA (SOLID)
Este servicio calcula la probabilidad matemática de combinaciones de quinielas (1X2).
Si no hay cuotas en vivo, utiliza el LLM de forma asíncrona para estimar las probabilidades.
"""

import heapq
import json
import os
import sys
import re
from sqlalchemy import select
from src.database.models import Evento
from src.database.session import async_session_maker
from src.services.the_odds_api_service import TheOddsAPIService
from src.services.llm_service import LLMService
from src.services.gestor_banca_service import run_async

class QuinielaService:
    def __init__(self):
        self.odds_api = TheOddsAPIService()
        self.llm = LLMService()

    async def obtener_partidos_disponibles_async(self):
        """
        Retorna la lista de partidos disponibles del día para la quiniela.
        Intenta leer de las cuotas de The Odds API y hace fallback a la base de datos de eventos pendientes.
        """
        partidos = []
        
        # 1. Intentar con The Odds API
        try:
            cuotas = self.odds_api.obtener_cuotas_deportivas()
            if cuotas:
                for match_key, val in cuotas.items():
                    partidos.append({
                        "home": val.get("home_team"),
                        "away": val.get("away_team"),
                        "fuente": "The Odds API (Cuotas en vivo)"
                    })
        except Exception as e:
            print(f"⚠️ QuinielaService: Error al leer cuotas para partidos disponibles: {e}")

        # 2. Fallback a eventos pendientes en la Base de Datos
        if not partidos:
            try:
                async with async_session_maker() as session:
                    stmt = select(Evento).where(Evento.estado == "Pendiente").limit(20)
                    res = await session.execute(stmt)
                    eventos = res.scalars().all()
                    for ev in eventos:
                        # Parsear local vs visitante del nombre "Local vs. Visitante"
                        parts = re.split(r'\s+vs\.?\s+', ev.nombre, flags=re.IGNORECASE)
                        if len(parts) == 2:
                            partidos.append({
                                "home": parts[0].strip(),
                                "away": parts[1].strip(),
                                "fuente": "Base de Datos (Eventos programados)"
                            })
            except Exception as e:
                print(f"⚠️ QuinielaService: Error al leer eventos de la base de datos: {e}")

        # 3. Fallback estático en caso de que todo falle
        if not partidos:
            partidos = [
                {"home": "España", "away": "Alemania", "fuente": "Fallback Estático"},
                {"home": "Argentina", "away": "Francia", "fuente": "Fallback Estático"},
                {"home": "Brasil", "away": "Inglaterra", "fuente": "Fallback Estático"},
                {"home": "Uruguay", "away": "Bélgica", "fuente": "Fallback Estático"},
                {"home": "Portugal", "away": "Países Bajos", "fuente": "Fallback Estático"}
            ]

        return partidos

    def obtener_partidos_disponibles(self):
        return run_async(self.obtener_partidos_disponibles_async())

    def obtener_contexto_partido(self, home, away):
        """
        Consulta ScoutAgent para obtener alineaciones, clima, lesiones, H2H, etc.
        """
        try:
            from src.agents.scout_agent import ScoutAgent
            scout = ScoutAgent()
            consulta = f"{home} vs. {away}"
            return scout.buscar_datos(consulta)
        except Exception as e:
            print(f"⚠️ QuinielaService: Error al invocar ScoutAgent: {e}")
            return {}

    def _formatear_partido_para_prompt(self, idx, p, cuotas, scout_info):
        text = f"Partido #{idx + 1}: {p['home']} vs {p['away']}\n"
        
        # 1. Cuotas
        if cuotas and cuotas.get("1X2_Home") and cuotas.get("1X2_Draw") and cuotas.get("1X2_Away"):
            text += f"  - Cuotas de Referencia (1X2): Local {cuotas['1X2_Home']}, Empate {cuotas['1X2_Draw']}, Visitante {cuotas['1X2_Away']}\n"
        else:
            text += "  - Cuotas de Referencia: No disponibles.\n"
            
        # 2. Clima y Estado del campo (Estadio)
        estadio = scout_info.get("estadio") or scout_info.get("estadio_detallado") or "Desconocido"
        clima = scout_info.get("clima") or "Despejado / Condiciones Óptimas"
        text += f"  - Estadio / Estado del Campo: {estadio}\n"
        text += f"  - Clima: {clima}\n"
        
        # 3. Árbitro
        arbitro = scout_info.get("arbitro") or "Desconocido"
        text += f"  - Árbitro: {arbitro}\n"
        
        # 4. Alineaciones / Jugadores
        alineaciones = scout_info.get("alineaciones") or scout_info.get("alineaciones_oficiales")
        if alineaciones:
            for team_info in alineaciones:
                team_name = team_info.get("equipo")
                formacion = team_info.get("formacion")
                entrenador = team_info.get("entrenador")
                titulares = ", ".join(team_info.get("titulares", [])) or "No disponibles"
                text += f"  - Alineación {team_name} (Formación {formacion}, Entrenador {entrenador}): {titulares}\n"
        else:
            text += "  - Alineaciones / Posibles Titulares: No disponibles en API (asume posibles alineaciones titulares según tu base de conocimientos).\n"
            
        # 5. Bajas / Lesiones
        bajas = scout_info.get("bajas") or scout_info.get("bajas_lesiones")
        if bajas:
            bajas_list = []
            for b in bajas:
                razon = b.get("razon", "Lesión o Sanción")
                bajas_list.append(f"{b.get('jugador')} ({b.get('equipo')} - {razon})")
            text += "  - Bajas / Lesionados: " + ", ".join(bajas_list) + "\n"
        else:
            text += "  - Bajas / Lesionados: Ninguna reportada o datos no disponibles.\n"
            
        # 6. Historial H2H
        h2h = scout_info.get("h2h") or scout_info.get("h2h_historico")
        if h2h:
            if isinstance(h2h, list):
                text += "  - Historial H2H reciente:\n"
                for h in h2h[:4]:
                    text += f"    * {h}\n"
            else:
                text += f"  - Historial H2H: {h2h}\n"
        else:
            text += "  - Historial H2H: No disponible.\n"
            
        return text

    def estimar_probabilidades_ia_avanzada(self, partidos_seleccionados):
        """
        Realiza un análisis unificado usando el LLM sobre alineaciones, clima, bajas y H2H
        para todos los partidos seleccionados.
        """
        partidos_txt_list = []
        for idx, p in enumerate(partidos_seleccionados):
            home = p["home"]
            away = p["away"]
            
            # Obtener cuotas
            cuotas = self.odds_api.obtener_cuotas_para_partido(home, away)
            
            # Obtener contexto
            scout_info = self.obtener_contexto_partido(home, away)
            
            partidos_txt_list.append(self._formatear_partido_para_prompt(idx, p, cuotas, scout_info))
            
        partidos_txt = "\n\n".join(partidos_txt_list)
        
        prompt = (
            f"Eres un Analista Cuantitativo de Apuestas Deportivas de élite y Científico de Datos Deportivo.\n"
            f"Tu tarea es analizar los siguientes partidos de fútbol y estimar las probabilidades reales (Gana Local %, Empate %, Gana Visitante %) para el mercado 1X2.\n\n"
            f"Para cada partido se te proveen datos en tiempo real (cuotas de referencia, estadio/campo, clima, árbitro, alineaciones/posibles titulares, bajas/lesiones e historial H2H).\n"
            f"Deberás realizar un análisis profundo considerando cómo influyen las alineaciones (ej. debilidad en defensa, fortaleza ofensiva, ausencias clave), "
            f"el estado del campo y el clima (ej. lluvia, calor extremo, altitud), las tendencias del árbitro y el historial H2H.\n\n"
            f"--- DATOS DE LOS PARTIDOS ---\n"
            f"{partidos_txt}\n\n"
            f"Responde estrictamente en formato JSON. No incluyas explicaciones, introducciones ni bloques de markdown fuera del JSON. El formato debe ser exactamente:\n"
            f'{{\n'
            f'  "partidos": [\n'
            f'    {{\n'
            f'      "home": "Nombre Local",\n'
            f'      "away": "Nombre Visitante",\n'
            f'      "prob_home": 45.0,\n'
            f'      "prob_draw": 30.0,\n'
            f'      "prob_away": 25.0,\n'
            f'      "analisis_contextual": "Explicación breve de 1-2 líneas sobre cómo influyen las alineaciones, clima, bajas y campo en tu predicción."\n'
            f'    }}\n'
            f'  ]\n'
            f'}}\n\n'
            f"IMPORTANTE: La suma de prob_home, prob_draw y prob_away para cada partido DEBE ser exactamente 100.0."
        )

        try:
            if hasattr(self.llm, "generar_texto_crudo"):
                response_text = self.llm.generar_texto_crudo(prompt)
            else:
                response_text = self.llm.analizar_partido(prompt)
            
            # Limpiar respuesta de markdown si el LLM lo incluyó
            if "```" in response_text:
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
                if match:
                    response_text = match.group(1)

            res_json = json.loads(response_text)
            estimados = res_json.get("partidos", [])
            
            resultados = []
            for p in partidos_seleccionados:
                est_p = next(
                    (item for item in estimados if item.get("home", "").lower() == p["home"].lower() or item.get("away", "").lower() == p["away"].lower()),
                    None
                )
                
                if est_p:
                    p_h = float(est_p.get("prob_home", 33.3))
                    p_d = float(est_p.get("prob_draw", 33.4))
                    p_a = float(est_p.get("prob_away", 33.3))
                    analisis = est_p.get("analisis_contextual", "Análisis completado a partir de alineaciones, clima y bajas.")
                    
                    # Forzar suma a 100%
                    total = p_h + p_d + p_a
                    if total > 0:
                        p_h = round((p_h / total) * 100, 2)
                        p_d = round((p_d / total) * 100, 2)
                        p_a = round((p_a / total) * 100, 2)
                else:
                    p_h, p_d, p_a = 33.33, 33.34, 33.33
                    analisis = "Estimación automática equiprobable por ausencia de respuesta de IA."

                resultados.append({
                    "home": p["home"],
                    "away": p["away"],
                    "prob_home": p_h,
                    "prob_draw": p_d,
                    "prob_away": p_a,
                    "fuente": "Análisis IA Contextual (Alineaciones, Clima, Bajas)",
                    "analisis_contextual": analisis
                })
            return resultados

        except Exception as e:
            print(f"⚠️ QuinielaService: Error al estimar probabilidades contextuales con el LLM ({e}).")
            return []

    def calcular_quiniela(self, partidos_seleccionados):
        """
        Calcula las 3 combinaciones de resultados 1X2 más probables para los partidos dados.
        Recibe: [{'home': 'Canada', 'away': 'Uruguay'}, ...]
        Retorna: { 'top_combinaciones': [...], 'probabilidades_individuales': [...] }
        """
        if not partidos_seleccionados:
            return {"top_combinaciones": [], "probabilidades_individuales": []}

        # 1. Estimar probabilidades con análisis contextual avanzado usando el LLM
        partidos_con_prob = []
        try:
            partidos_con_prob = self.estimar_probabilidades_ia_avanzada(partidos_seleccionados)
        except Exception as e:
            print(f"⚠️ QuinielaService: Error en estimar_probabilidades_ia_avanzada: {e}. Usando fallback.")
            
        # Si falló la estimación avanzada o retornó una lista incompleta, hacemos fallback manual
        if len(partidos_con_prob) < len(partidos_seleccionados):
            existentes = {f"{p['home'].lower()} vs {p['away'].lower()}" for p in partidos_con_prob}
            for p in partidos_seleccionados:
                key = f"{p['home'].lower()} vs {p['away'].lower()}"
                if key not in existentes:
                    # Intentar obtener cuotas como fallback directo
                    home = p["home"]
                    away = p["away"]
                    cuotas = self.odds_api.obtener_cuotas_para_partido(home, away)
                    if cuotas and cuotas.get("1X2_Home") and cuotas.get("1X2_Draw") and cuotas.get("1X2_Away"):
                        odd_h = float(cuotas["1X2_Home"])
                        odd_d = float(cuotas["1X2_Draw"])
                        odd_a = float(cuotas["1X2_Away"])
                        ip_h, ip_d, ip_a = 1.0 / odd_h, 1.0 / odd_d, 1.0 / odd_a
                        sum_ip = ip_h + ip_d + ip_a
                        p_h = round((ip_h / sum_ip) * 100, 2)
                        p_d = round((ip_d / sum_ip) * 100, 2)
                        p_a = round((ip_a / sum_ip) * 100, 2)
                        fuente = f"Odds API ({cuotas.get('bookmaker', 'Bet365')}) [Fallback]"
                    else:
                        p_h, p_d, p_a = 33.33, 33.34, 33.33
                        fuente = "Fallback por Defecto (Equiprobable)"
                        
                    partidos_con_prob.append({
                        "home": home,
                        "away": away,
                        "prob_home": p_h,
                        "prob_draw": p_d,
                        "prob_away": p_a,
                        "fuente": fuente,
                        "analisis_contextual": "Análisis simplificado por falta de respuesta del modelo de IA principal."
                    })

        # 3. Aplicar algoritmo Dijkstra de cola de prioridad para encontrar las Top 3 combinaciones
        # Aseguramos el orden de partidos_con_prob para coincidir con la selección original
        orden_dict = {f"{p['home'].lower()} vs {p['away'].lower()}": idx for idx, p in enumerate(partidos_seleccionados)}
        partidos_con_prob.sort(key=lambda x: orden_dict.get(f"{x['home'].lower()} vs {x['away'].lower()}", 999))

        # Estructurar la entrada del algoritmo Dijkstra
        matches_probs = []
        for p in partidos_con_prob:
            matches_probs.append({
                "1": p["prob_home"] / 100.0,
                "X": p["prob_draw"] / 100.0,
                "2": p["prob_away"] / 100.0
            })

        top_3 = self._buscar_top_combinaciones(matches_probs)

        # Formatear el resultado final de combinaciones
        formatted_combinations = []
        for rank, comb in enumerate(top_3):
            ticket_selections = []
            for idx, sel in enumerate(comb["selections"]):
                match_p = partidos_con_prob[idx]
                outcome = sel["outcome"]
                
                pronostico_str = ""
                if outcome == "1":
                    pronostico_str = f"Gana {match_p['home']}"
                elif outcome == "X":
                    pronostico_str = "Empate"
                else:
                    pronostico_str = f"Gana {match_p['away']}"

                ticket_selections.append({
                    "home": match_p["home"],
                    "away": match_p["away"],
                    "outcome": outcome,
                    "pronostico_desc": pronostico_str,
                    "probabilidad_individual": round(sel["prob"] * 100, 2)
                })

            formatted_combinations.append({
                "id_comb": rank + 1,
                "probabilidad_conjunta": round(comb["probability"] * 100, 2),
                "selections": ticket_selections
            })

        return {
            "top_combinaciones": formatted_combinations,
            "probabilidades_individuales": partidos_con_prob
        }

    def estimar_probabilidades_ia(self, partidos):
        """
        Consulta al LLM para estimar las probabilidades de 1X2 para partidos sin cuotas (Legacy).
        """
        partidos_txt = "\n".join([f"- {p['home']} vs {p['away']}" for p in partidos])
        prompt = (
            f"Eres un Analista Cuantitativo de Apuestas Deportivas de élite con conocimiento profundo de fútbol internacional.\n"
            f"Estima las probabilidades estadísticas reales del mercado 1X2 (Gana Local %, Empate %, Gana Visitante %) para los siguientes partidos:\n"
            f"{partidos_txt}\n\n"
            f"Responde estrictamente en formato JSON. No incluyas explicaciones, saludos ni bloques markdown. El formato debe ser exactamente:\n"
            f'{{"partidos": [\n'
            f'  {{"home": "Nombre Local", "away": "Nombre Visitante", "prob_home": 45.0, "prob_draw": 30.0, "prob_away": 25.0}}\n'
            f']}}\n\n'
            f"IMPORTANTE: La suma de prob_home, prob_draw y prob_away para cada partido DEBE ser exactamente 100.0."
        )

        try:
            # Añadir dinámicamente generar_texto_crudo en LLMService si está disponible, si no usar el normal
            if hasattr(self.llm, "generar_texto_crudo"):
                response_text = self.llm.generar_texto_crudo(prompt)
            else:
                response_text = self.llm.analizar_partido(prompt)
            
            # Limpiar respuesta de markdown si el LLM lo incluyó
            if "```" in response_text:
                # Extraer contenido de bloques ```json ... ``` o ``` ... ```
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL)
                if match:
                    response_text = match.group(1)

            res_json = json.loads(response_text)
            estimados = res_json.get("partidos", [])
            
            # Validar y formatear respuesta
            resultados = []
            for p in partidos:
                # Buscar en la respuesta por nombre (insensible a mayúsculas)
                est_p = next(
                    (item for item in estimados if item.get("home", "").lower() == p["home"].lower() or item.get("away", "").lower() == p["away"].lower()),
                    None
                )
                
                if est_p:
                    p_h = float(est_p.get("prob_home", 33.3))
                    p_d = float(est_p.get("prob_draw", 33.4))
                    p_a = float(est_p.get("prob_away", 33.3))
                    
                    # Forzar suma a 100%
                    total = p_h + p_d + p_a
                    if total > 0:
                        p_h = round((p_h / total) * 100, 2)
                        p_d = round((p_d / total) * 100, 2)
                        p_a = round((p_a / total) * 100, 2)
                else:
                    p_h, p_d, p_a = 33.33, 33.34, 33.33

                resultados.append({
                    "home": p["home"],
                    "away": p["away"],
                    "prob_home": p_h,
                    "prob_draw": p_d,
                    "prob_away": p_a,
                    "fuente": "Estimación Inteligencia Artificial"
                })
            return resultados

        except Exception as e:
            print(f"⚠️ QuinielaService: Error al estimar probabilidades con el LLM ({e}). Usando probabilidades por defecto.")
            return [
                {
                    "home": p["home"],
                    "away": p["away"],
                    "prob_home": 33.33,
                    "prob_draw": 33.34,
                    "prob_away": 33.33,
                    "fuente": "Fallback por Defecto (Equiprobable)"
                } for p in partidos
            ]

    def _buscar_top_combinaciones(self, matches_probs, k=3):
        """
        Algoritmo de búsqueda Dijkstra para combinaciones de quinielas (1X2).
        Retorna las Top K combinaciones de mayor a menor probabilidad.
        """
        sorted_outcomes = []
        for m in matches_probs:
            sorted_m = sorted([("1", m["1"]), ("X", m["X"]), ("2", m["2"])], key=lambda x: x[1], reverse=True)
            sorted_outcomes.append(sorted_m)
            
        m_count = len(matches_probs)
        if m_count == 0:
            return []

        initial_comb = tuple([0] * m_count)
        initial_prob = 1.0
        for i in range(m_count):
            initial_prob *= sorted_outcomes[i][0][1]
            
        heap = [(-initial_prob, initial_prob, initial_comb)]
        seen = {initial_comb}
        
        results = []
        while heap and len(results) < k:
            _, prob, comb = heapq.heappop(heap)
            
            formatted_comb = []
            for i, idx in enumerate(comb):
                outcome_char, outcome_p = sorted_outcomes[i][idx]
                formatted_comb.append({
                    "match_index": i,
                    "outcome": outcome_char,
                    "prob": outcome_p
                })
                
            results.append({
                "probability": prob,
                "selections": formatted_comb
            })
            
            for i in range(m_count):
                if comb[i] < 2:
                    neighbor = list(comb)
                    neighbor[i] += 1
                    neighbor_tuple = tuple(neighbor)
                    if neighbor_tuple not in seen:
                        seen.add(neighbor_tuple)
                        old_p = sorted_outcomes[i][comb[i]][1]
                        new_p = sorted_outcomes[i][neighbor[i]][1]
                        if old_p > 0:
                            new_prob = prob * (new_p / old_p)
                            heapq.heappush(heap, (-new_prob, new_prob, neighbor_tuple))
                            
        return results

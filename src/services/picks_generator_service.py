#!/usr/bin/env python3
"""
🤖 SERVICIO GENERADOR DE PICKS AUTOMÁTICO POR AGENTES
Este servicio coordina a los agentes de IA (Scout y Científico) para:
1. Buscar partidos programados para hoy en la API (o usar fallback).
2. Analizar estadísticamente cada partido con los agentes.
3. Generar dos combinadas estructuradas en formato JSON (Segura y Arriesgada) mediante el LLM.
4. Descontar la inversión de la banca, registrar las apuestas activas y publicar en Telegram.
"""

import os
import json
import datetime
import urllib.request
from src.config.settings import Settings
from src.agents.scout_agent import ScoutAgent
from src.services.llm_service import LLMService
from src.services.gestor_banca_service import GestorBancaService
from src.services.telegram_service import TelegramService
from src.database.models import LogGeneracion
from src.database.session import async_session_maker
from src.services.gestor_banca_service import run_async


class PicksGeneratorService:
    def __init__(self):
        self.scout = ScoutAgent()
        self.llm = LLMService()
        self.banca_srv = GestorBancaService()
        self.tg = TelegramService()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.jugadas_path = os.path.join(self.base_dir, "jugadas_lunes_15.json")

    def obtener_partidos_del_dia(self):
        """Consulta la API de la Copa del Mundo en busca de partidos programados."""
        partidos = []
        
        # 1. Intentar API de 2026 (worldcup26.ir)
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                "https://worldcup26.ir/get/games",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                data = json.loads(response.read().decode("utf-8"))
                matches = data.get("games", [])
                
            hoy_str = datetime.date.today().strftime("%m/%d/%Y") # "06/15/2026"
            
            for match in matches:
                dt_match = match.get("local_date", "")
                if hoy_str in dt_match:
                    home = match.get("home_team_name_en")
                    away = match.get("away_team_name_en")
                    if home and away:
                        # Diccionario de traducción inglés -> español para compatibilidad
                        traducciones_es = {
                            "Spain": "España",
                            "Cape Verde": "Cabo Verde",
                            "Iran": "Irán",
                            "New Zealand": "Nueva Zelanda",
                            "Uruguay": "Uruguay",
                            "Saudi Arabia": "Arabia Saudita",
                            "Belgium": "Bélgica",
                            "Egypt": "Egipto",
                            "Germany": "Alemania",
                            "France": "Francia",
                            "Brazil": "Brasil",
                            "Argentina": "Argentina",
                            "Italy": "Italia",
                            "Netherlands": "Países Bajos",
                            "Portugal": "Portugal",
                            "Mexico": "México",
                            "United States": "Estados Unidos",
                            "Canada": "Canadá",
                        }
                        home_es = traducciones_es.get(home, home)
                        away_es = traducciones_es.get(away, away)
                        partidos.append(f"{home_es} vs. {away_es}")
        except Exception as e:
            print(f"⚠️ PicksGeneratorService: No se pudo obtener partidos de la API 2026: {e}")

        # 2. Intentar API de 2022 (worldcupjson.net)
        if not partidos:
            try:
                url = Settings.SPORTS_API_URL or "https://worldcupjson.net/matches"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    matches = json.loads(response.read().decode("utf-8"))
                
                hoy_str = datetime.date.today().strftime("%Y-%m-%d")
                
                for match in matches:
                    dt_match = match.get("datetime", "")
                    if hoy_str in dt_match or not dt_match:
                        home = match.get("home_team", {}).get("name")
                        away = match.get("away_team", {}).get("name")
                        if home and away:
                            partidos.append(f"{home} vs. {away}")
            except Exception as e:
                print(f"⚠️ PicksGeneratorService: No se pudo obtener partidos de la API 2022: {e}")
        
        # Fallback si no hay partidos programados hoy en la API
        if not partidos:
            print("💡 PicksGeneratorService: Usando lista de partidos de demostración...")
            partidos = [
                "España vs. Cabo Verde",
                "Arabia Saudita vs. Uruguay",
                "Bélgica vs. Egipto",
                "Irán vs. Nueva Zelanda"
            ]
        return partidos

    def generar_picks_ia(self):
        """Orquesta a los agentes para generar las combinadas del día y registrarlas."""
        print("🤖 PicksGeneratorService: Iniciando generación automática...")
        
        # Crear log de generación inicial en la DB
        log_id = None
        async def crear_log_inicial():
            async with async_session_maker() as session:
                log = LogGeneracion(exito=False, detalles="Iniciando generación de picks por IA...")
                session.add(log)
                await session.commit()
                await session.refresh(log)
                return log.id

        try:
            log_id = run_async(crear_log_inicial())
        except Exception as e:
            print(f"⚠️ PicksGeneratorService: No se pudo guardar el log inicial en DB: {e}")

        async def actualizar_log_fallo(err_msg, prompt_usado=None):
            if log_id is None:
                return
            async with async_session_maker() as session:
                log = await session.get(LogGeneracion, log_id)
                if log:
                    log.exito = False
                    log.detalles = str(err_msg)[:500]
                    if prompt_usado:
                        log.prompt_usado = str(prompt_usado)
                    await session.commit()

        async def actualizar_log_exito(detalles_str, prompt_usado, json_resultado):
            if log_id is None:
                return
            async with async_session_maker() as session:
                log = await session.get(LogGeneracion, log_id)
                if log:
                    log.exito = True
                    log.detalles = str(detalles_str)[:500]
                    log.prompt_usado = str(prompt_usado)
                    log.json_resultado = str(json_resultado)
                    await session.commit()

        prompt_maestro = ""
        try:
            # 1. Obtener historial previo para autoalimentación (feedback loop)
            historial_previo = ""
            try:
                datos_historial = self.banca_srv.cargar_historial()
                if datos_historial:
                    archivadas = datos_historial.get("apuestas_archivadas", [])
                    if archivadas:
                        # Ordenar por fecha_jornada descendente y tomar todos los tickets archivados
                        ultimas = sorted(archivadas, key=lambda x: x.get("fecha_jornada", ""), reverse=True)
                        historial_previo += "\n=== HISTORIAL COMPLETO DE COMBINADAS Y RESULTADOS (RETROALIMENTACIÓN) ===\n"
                        historial_previo += "A continuación se muestra el resultado de todas las combinadas históricas que generaste. "
                        historial_previo += "Utiliza este historial completo para realizar autocrítica profunda, analizar qué mercados o cuotas fallaron "
                        historial_previo += "y evitar repetir selecciones que resulten perdedoras:\n\n"
                        for idx_tkt, tkt in enumerate(ultimas):
                            estado_tkt = tkt.get("estado", "Finalizada")
                            historial_previo += f"Ticket #{idx_tkt+1} - ID: {tkt.get('ticket_id')} - Estado: {estado_tkt}\n"
                            historial_previo += f"  - Tipo: {tkt.get('tipo_parley')} | Cuota: {tkt.get('cuota')}\n"
                            historial_previo += "  - Selecciones realizadas:\n"
                            for sel in tkt.get("selecciones", []):
                                est_sel = sel.get("estado_seleccion", "Pendiente")
                                emoji_sel = "✅ Ganado" if est_sel == "Ganado" else ("❌ Perdido" if est_sel == "Perdido" else "🔄 Anulado")
                                marcador = f" (Marcador: {sel.get('resultado_partido')})" if sel.get('resultado_partido') else ""
                                historial_previo += f"    * {sel.get('partido')} -> Pronóstico: {sel.get('pronostico')} (Cuota: {sel.get('cuota')}) | Resultado: {emoji_sel}{marcador}\n"
                            historial_previo += "\n"

                    predicciones = datos_historial.get("predicciones_ia", [])
                    predicciones_resueltas = [p for p in predicciones if p.get("estado") != "Pendiente"]
                    if predicciones_resueltas:
                        historial_previo += "\n=== HISTORIAL DE PREDICCIONES INDIVIDUALES ANTERIORES Y SUS RESULTADOS ===\n"
                        historial_previo += "Aquí tienes el resultado de todas las predicciones individuales propuestas por ti anteriormente. Úsalos para mejorar tus selecciones:\n\n"
                        for idx_p, p in enumerate(predicciones_resueltas):
                            emoji_p = "✅ Ganado" if p["estado"] == "Ganado" else ("❌ Perdido" if p["estado"] == "Perdido" else "🔄 Anulado")
                            marcador = f" (Marcador: {p['resultado_partido']})" if p.get("resultado_partido") else ""
                            historial_previo += f"  * Predicción #{idx_p+1}: {p['partido']} -> Pronóstico: {p['pronostico']} (Cuota: {p['cuota']}) | Tipo: {p['tipo_parley']} | Resultado: {emoji_p}{marcador}\n"
                        historial_previo += "\n"
            except Exception as e:
                print(f"⚠️ PicksGeneratorService: No se pudo cargar el historial para retroalimentación: {e}")

            partidos = self.obtener_partidos_del_dia()
            
            # 2. Recopilar estadísticas con el Scout Agent
            datos_partidos = []
            for partido in partidos:
                info = self.scout.buscar_datos(partido)
                datos_partidos.append(info)
                
            # 3. Formatear datos recopilados para el prompt
            datos_texto = ""
            for idx, datos_dict in enumerate(datos_partidos):
                datos_texto += f"\n--- PARTIDO #{idx+1} ---\n"
                if datos_dict.get("encontrado_en_api") or datos_dict.get("api_football_encontrado"):
                    local = datos_dict.get("equipo_local", "N/A")
                    visitante = datos_dict.get("equipo_visitante", "N/A")
                    datos_texto += f"Partido: {local} vs. {visitante}\n"
                    
                    if datos_dict.get("fase"):
                        datos_texto += f"Fase: {datos_dict.get('fase')}\n"
                    
                    estadio = datos_dict.get("estadio_detallado") or datos_dict.get("estadio")
                    if estadio:
                        datos_texto += f"Estadio/Sede: {estadio}\n"
                    if datos_dict.get("arbitro"):
                        datos_texto += f"Árbitro: {datos_dict.get('arbitro')}\n"
                    
                    goles = datos_dict.get("goles_torneo", {})
                    if goles:
                        goles_str = ", ".join([f"{t}: {g} goles" for t, g in goles.items()])
                        datos_texto += f"Estadísticas Goles Torneo: {goles_str}\n"
                        
                    # Detalle H2H Histórico
                    h2h = datos_dict.get("h2h_historico")
                    if h2h:
                        datos_texto += "Historial Directo Reciente (H2H):\n"
                        for match_h2h in h2h:
                            datos_texto += f"  - {match_h2h}\n"
                            
                    # Alineaciones Oficiales
                    lineups = datos_dict.get("alineaciones_oficiales")
                    if lineups:
                        datos_texto += "Alineaciones y Esquemas Tácticos:\n"
                        for team_ln in lineups:
                            titulares_str = ", ".join(team_ln.get("titulares", []))
                            datos_texto += f"  - {team_ln.get('equipo')} ({team_ln.get('formacion')}) | Entrenador: {team_ln.get('entrenador')}\n"
                            datos_texto += f"    Titulares: {titulares_str}\n"
                            
                    # Reporte de Bajas y Lesionados
                    bajas = datos_dict.get("bajas_lesiones")
                    if bajas:
                        datos_texto += "Reporte de Lesiones / Suspensiones (Bajas Oficiales):\n"
                        for b in bajas:
                            datos_texto += f"  - {b.get('jugador')} ({b.get('equipo')}) - Motivo: {b.get('razon')} [{b.get('tipo')}]\n"
                else:
                    datos_texto += f"Partido: {datos_dict.get('partido_solicitado')}\nNota: {datos_dict.get('nota')}\n"

            # 4. Prompt estructurado para forzar al LLM a retornar JSON estricto basándose en la guía de J. Carreño
            prompt_maestro = (
                "Eres el Agente Científico de Datos de un consorcio de análisis deportivo, aplicando las estrictas directrices de la guía de apuestas de J. Carreño.\n"
                f"{historial_previo}\n"
                "Dada la siguiente lista de partidos y sus estadísticas de hoy, debes generar exactamente dos combinadas (parleys):\n\n"
                f"{datos_texto}\n"
                "INSTRUCCIONES DE SELECCIÓN (FILOSOFÍA SPRO J. CARREÑO):\n"
                "1. 'parley_seguro' (Combinada Segura): Riesgo bajo. Selecciona estrictamente entre 2 and 3 eventos (la Regla SPRO prohíbe combinadas de 4 o más eventos debido al margen acumulado de la casa). Elige cuotas individuales bajas (entre 1.10 y 1.40) con alta probabilidad real (ej: doble oportunidad, hándicaps a favor o Draw No Bet/sin empate).\n"
                "2. 'parley_arriesgado' (Combinada de Alto Valor): Riesgo alto pero con ventaja matemática clara (esperanza = cuota * prob > 1). Selecciona estrictamente entre 2 y 3 eventos con cuotas individuales moderadas (entre 1.50 y 2.50), priorizando hándicaps asiáticos para mitigar el riesgo.\n"
                "3. Todas las selecciones individuales que definas deben poseer valor real (Value+) y cuotas verosímiles de casas de apuestas.\n\n"
                "Debes retornar ÚNICAMENTE un formato JSON limpio y sin bloques de código markdown (sin ```json), sin explicaciones de texto, respetando exactamente el siguiente esquema:\n"
                "{\n"
                "  \"parley_seguro\": {\n"
                "    \"nombre\": \"Combinada Segura Lunes\",\n"
                "    \"tipo_riesgo\": \"Bajo\",\n"
                "    \"stake_sugerido\": \"5/10 (Unidades)\",\n"
                "    \"selecciones\": [\n"
                "      {\n"
                "        \"partido\": \"Nombre Local vs. Nombre Visitante\",\n"
                "        \"pronostico\": \"Pronóstico Sugerido (Ej: Local o Empate o DNB)\",\n"
                "        \"cuota\": 1.25,\n"
                "        \"probabilidad_estadistica\": \"80%\"\n"
                "      }\n"
                "    ]\n"
                "  },\n"
                "  \"parley_arriesgado\": {\n"
                "    \"nombre\": \"Combinada de Alto Valor Lunes\",\n"
                "    \"tipo_riesgo\": \"Alto\",\n"
                "    \"stake_sugerido\": \"1/10 (Unidades)\",\n"
                "    \"selecciones\": [\n"
                "      {\n"
                "        \"partido\": \"Nombre Local vs. Nombre Visitante\",\n"
                "        \"pronostico\": \"Pronóstico (Ej: Hándicap Asiático +0.5 / DNB)\",\n"
                "        \"cuota\": 1.90,\n"
                "        \"probabilidad_estadistica\": \"60%\"\n"
                "      }\n"
                "    ]\n"
                "  }\n"
                "}"
            )

            # 5. Llamada al LLM y limpieza
            json_str = self.llm.analizar_partido(prompt_maestro)
            json_str = json_str.replace("```json", "").replace("```", "").strip()
            
            try:
                picks_data = json.loads(json_str)
            except Exception as e:
                print(f"❌ PicksGeneratorService: Error al parsear JSON del LLM: {e}")
                print("Bloque recibido del LLM:")
                print(json_str)
                err_msg = "La Inteligencia Artificial no devolvió un JSON en el formato requerido. Intenta de nuevo."
                run_async(actualizar_log_fallo(err_msg, prompt_maestro))
                return False, err_msg

            # 6. Completar métricas matemáticas e inyectar campos calculados
            fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
            
            # Normalizar claves si fueron desinfectadas por el filtro de seguridad de LLMService o tienen variaciones
            for old_key in list(picks_data.keys()):
                key_lower = old_key.lower()
                if "segur" in key_lower:
                    picks_data["parley_seguro"] = picks_data[old_key]
                elif any(x in key_lower for x in ["arriesga", "alto_valor", "valor"]):
                    picks_data["parley_arriesgado"] = picks_data[old_key]

            for key in ["parley_seguro", "parley_arriesgado"]:
                parley = picks_data.get(key)
                if not parley or not parley.get("selecciones"):
                    print(f"❌ PicksGeneratorService: Validación fallida para {key}.")
                    print("JSON completo recibido:")
                    print(json.dumps(picks_data, indent=2, ensure_ascii=False))
                    err_msg = f"Faltan selecciones en la sección {key}."
                    run_async(actualizar_log_fallo(err_msg, prompt_maestro))
                    return False, err_msg
                
                cuota_total = 1.0
                prob_comb = 1.0
                
                for sel in parley["selecciones"]:
                    cuota = float(sel.get("cuota", 1.5))
                    prob_est = float(str(sel.get("probabilidad_estadistica", "70%")).replace("%", "").strip())
                    
                    # Calcular probabilidad implícita de la cuota
                    prob_imp = (1.0 / cuota) * 100
                    sel["probabilidad_implicita"] = f"{prob_imp:.1f}%"
                    sel["probabilidad_estadistica"] = f"{prob_est:.1f}%"
                    sel["fuente_principal"] = "Consenso de Agentes IA"
                    
                    # Calcular valor
                    diferencia = prob_est - prob_imp
                    sel["valor"] = f"Sí (+{diferencia:.1f}%)" if diferencia > 0 else "Riesgo Ajustado"
                    
                    cuota_total *= cuota
                    prob_comb *= (prob_est / 100.0)
                    
                parley["cuota_total_estimada"] = round(cuota_total, 2)
                parley["probabilidad_implicta_cuota"] = f"{((1.0 / cuota_total) * 100):.1f}%"
                parley["probabilidad_estadistica_combinada"] = f"{(prob_comb * 100):.1f}%"

            # Estructura de jugadas del día
            datos_picks = {
                "fecha_jornada": fecha_hoy,
                "descripcion": f"Combinadas de la Jornada {fecha_hoy} generadas por Agentes IA",
                "paginas_consultadas": ["API Deportiva", "ScoutAgent DB", "Consenso de Datos LLM"],
                "parleys": {
                    "parley_seguro": picks_data["parley_seguro"],
                    "parley_arriesgado": picks_data["parley_arriesgado"]
                }
            }

            # Guardar en jugadas_lunes_15.json
            with open(self.jugadas_path, "w", encoding="utf-8") as f:
                json.dump(datos_picks, f, indent=2, ensure_ascii=False)
                
            # 7. Registrar en la base de datos de predicciones de IA (evitando redundancias/duplicados)
            async def guardar_predicciones_db():
                from decimal import Decimal
                from src.database.models import PrediccionIA
                from sqlalchemy import select
                async with async_session_maker() as session:
                    # Combinada Segura
                    p_seguro = datos_picks["parleys"]["parley_seguro"]
                    for sel in p_seguro.get("selecciones", []):
                        stmt = select(PrediccionIA).where(
                            PrediccionIA.partido == sel["partido"],
                            PrediccionIA.pronostico == sel["pronostico"],
                            PrediccionIA.tipo_parley == "Combinada Segura",
                            PrediccionIA.estado == "Pendiente"
                        )
                        res = await session.execute(stmt)
                        existing = res.scalar_one_or_none()
                        if not existing:
                            pred = PrediccionIA(
                                partido=sel["partido"],
                                pronostico=sel["pronostico"],
                                cuota=Decimal(str(sel["cuota"])),
                                probabilidad_estadistica=Decimal(str(sel.get("probabilidad_estadistica", "70%").replace("%", "").strip())),
                                probabilidad_implicita=Decimal(str(sel.get("probabilidad_implicita", "60%").replace("%", "").strip())),
                                valor=sel.get("valor", "Sí"),
                                tipo_parley="Combinada Segura",
                                estado="Pendiente"
                            )
                            session.add(pred)
                        else:
                            print(f"💡 PicksGeneratorService: Predicción duplicada omitida en Combinada Segura: {sel['partido']} -> {sel['pronostico']}")
                        
                    # Combinada de Alto Valor
                    p_arriesgado = datos_picks["parleys"]["parley_arriesgado"]
                    for sel in p_arriesgado.get("selecciones", []):
                        stmt = select(PrediccionIA).where(
                            PrediccionIA.partido == sel["partido"],
                            PrediccionIA.pronostico == sel["pronostico"],
                            PrediccionIA.tipo_parley == "Combinada de Alto Valor",
                            PrediccionIA.estado == "Pendiente"
                        )
                        res = await session.execute(stmt)
                        existing = res.scalar_one_or_none()
                        if not existing:
                            pred = PrediccionIA(
                                partido=sel["partido"],
                                pronostico=sel["pronostico"],
                                cuota=Decimal(str(sel["cuota"])),
                                probabilidad_estadistica=Decimal(str(sel.get("probabilidad_estadistica", "60%").replace("%", "").strip())),
                                probabilidad_implicita=Decimal(str(sel.get("probabilidad_implicita", "50%").replace("%", "").strip())),
                                valor=sel.get("valor", "Sí"),
                                tipo_parley="Combinada de Alto Valor",
                                estado="Pendiente"
                            )
                            session.add(pred)
                        else:
                            print(f"💡 PicksGeneratorService: Predicción duplicada omitida en Combinada de Alto Valor: {sel['partido']} -> {sel['pronostico']}")
                    await session.commit()

            try:
                run_async(guardar_predicciones_db())
                print("🤖 PicksGeneratorService: Predicciones guardadas en DB.")
            except Exception as e:
                print(f"⚠️ PicksGeneratorService: Error al guardar predicciones en DB: {e}")


            # 8. Publicar en Telegram de inmediato
            self.tg.enviar_reporte_picks(self.jugadas_path)
            
            # 9. Actualizar log de éxito
            detalles_exito = f"Picks generados y guardados con éxito para la jornada {fecha_hoy}."
            run_async(actualizar_log_exito(detalles_exito, prompt_maestro, json_str))
            
            print("🤖 PicksGeneratorService: Generación y registro completados con éxito.")
            return True, detalles_exito

        except Exception as e:
            err_msg = f"Excepción crítica durante generación: {str(e)}"
            print(f"❌ PicksGeneratorService: {err_msg}")
            run_async(actualizar_log_fallo(err_msg, prompt_maestro if prompt_maestro else "Error antes de armar prompt"))
            return False, err_msg


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
from src.services.the_odds_api_service import TheOddsAPIService


class PicksGeneratorService:
    def __init__(self):
        self.scout = ScoutAgent()
        self.llm = LLMService()
        self.banca_srv = GestorBancaService()
        self.tg = TelegramService()
        self.odds_api = TheOddsAPIService()
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def encontrar_partido_correspondiente(self, partido_propuesto, partidos_del_dia):
        if not partido_propuesto:
            return None
        import unicodedata
        
        def normalizar(s):
            s = s.lower().replace(".", "").replace(" vs ", " vs. ")
            # Quitar acentos
            s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            return s.strip()

        propuesto_norm = normalizar(partido_propuesto)
        equipos_propuestos = [normalizar(eq) for eq in propuesto_norm.split("vs.")]
        if len(equipos_propuestos) != 2:
            return None
            
        eq1_p, eq2_p = equipos_propuestos[0].strip(), equipos_propuestos[1].strip()
            
        for p_dia in partidos_del_dia:
            p_dia_norm = normalizar(p_dia)
            if p_dia_norm == propuesto_norm:
                return p_dia
                
            parts_dia = [normalizar(eq) for eq in p_dia_norm.split("vs.")]
            if len(parts_dia) == 2:
                eq1_d, eq2_d = parts_dia[0].strip(), parts_dia[1].strip()
                # Coincidencia exacta (orden original o invertido)
                if (eq1_p == eq1_d and eq2_p == eq2_d) or (eq1_p == eq2_d and eq2_p == eq1_d):
                    return p_dia
                # Coincidencia flexible (subcadenas)
                if (eq1_p in eq1_d or eq1_d in eq1_p) and (eq2_p in eq2_d or eq2_d in eq2_p):
                    return p_dia
                if (eq1_p in eq2_d or eq2_d in eq1_p) and (eq2_p in eq1_d or eq1_d in eq2_p):
                    return p_dia
                    
        return None

    def obtener_partidos_del_dia(self):
        """Consulta la API de la Copa del Mundo en busca de partidos programados."""
        partidos = []
        
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
            "Senegal": "Senegal",
            "Iraq": "Irak",
            "Norway": "Noruega",
            "Austria": "Austria",
            "Jordan": "Jordania",
            "Algeria": "Argelia",
        }
        
        # 0. Intentar desde The Odds API si está configurada (garantiza partidos con cuotas en bookmakers)
        try:
            cuotas = self.odds_api.obtener_cuotas_deportivas()
            fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")
            
            def obtener_fecha_local_utc4(commence_time_str):
                if not commence_time_str:
                    return None
                try:
                    dt = datetime.datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                    tz_offset = datetime.timezone(datetime.timedelta(hours=-4))
                    dt_local = dt.astimezone(tz_offset)
                    return dt_local.strftime("%Y-%m-%d")
                except Exception:
                    return None

            if cuotas:
                for val in cuotas.values():
                    commence = val.get("commence_time")
                    fecha_partido = obtener_fecha_local_utc4(commence)
                    
                    # Filtrar partidos que coincidan con la jornada de hoy (en UTC-4)
                    if fecha_partido == fecha_hoy:
                        home = val.get("home_team")
                        away = val.get("away_team")
                        if home and away:
                            home_es = traducciones_es.get(home, home)
                            away_es = traducciones_es.get(away, away)
                            partidos.append(f"{home_es} vs. {away_es}")
                if partidos:
                    print(f"📡 PicksGeneratorService: Obtenidos {len(partidos)} partidos del día con cuotas reales de The Odds API.")
                    return partidos
        except Exception as e:
            print(f"⚠️ PicksGeneratorService: Error al obtener partidos de The Odds API: {e}")
            
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
                
                local = datos_dict.get("equipo_local", "N/A")
                visitante = datos_dict.get("equipo_visitante", "N/A")
                
                # Intentar obtener cuotas reales
                cuotas = None
                
                # 1. Intentar desde API-Football si hay fixture_id y la clave es válida
                fixture_id = datos_dict.get("fixture_id")
                if fixture_id:
                    try:
                        cuotas = self.scout.api_football.obtener_cuotas(fixture_id)
                    except Exception as e:
                        print(f"⚠️ PicksGeneratorService: No se pudo obtener cuotas de API-Football: {e}")
                        
                # 2. Intentar desde The Odds API
                if not cuotas:
                    try:
                        cuotas = self.odds_api.obtener_cuotas_para_partido(local, visitante)
                    except Exception as e:
                        print(f"⚠️ PicksGeneratorService: No se pudo obtener cuotas de The Odds API: {e}")
                
                # Formatear cuotas si existen
                cuotas_texto = "Cuotas Reales (Bet365 / Bookmakers Oficiales):\n"
                if cuotas:
                    if cuotas.get("1X2_Home") or cuotas.get("1X2_Away") or cuotas.get("1X2_Draw"):
                        cuotas_texto += f"  - Ganador 1X2: Local={cuotas.get('1X2_Home', 'N/A')}, Empate={cuotas.get('1X2_Draw', 'N/A')}, Visitante={cuotas.get('1X2_Away', 'N/A')}\n"
                    if cuotas.get("DNB_Home") or cuotas.get("DNB_Away"):
                        cuotas_texto += f"  - Draw No Bet (DNB / Empate Anula Apuesta): Local={cuotas.get('DNB_Home', 'N/A')}, Visitante={cuotas.get('DNB_Away', 'N/A')}\n"
                    if cuotas.get("DC_Home_Draw") or cuotas.get("DC_Away_Draw") or cuotas.get("DC_Home_Away"):
                        cuotas_texto += f"  - Doble Oportunidad (DC): Local o Empate (1X)={cuotas.get('DC_Home_Draw', 'N/A')}, Visitante o Empate (X2)={cuotas.get('DC_Away_Draw', 'N/A')}, Local o Visitante (12)={cuotas.get('DC_Home_Away', 'N/A')}\n"
                    
                    ah_list = cuotas.get("Asian_Handicap") or cuotas.get("Asian Handicap")
                    if ah_list:
                        ah_str_list = []
                        for ah in ah_list[:6]: # Max 6 handicaps principales
                            if "point" in ah:
                                ah_str_list.append(f"{ah.get('name')} {ah.get('point')} (Cuota {ah.get('price')})")
                            else:
                                ah_str_list.append(f"{ah.get('name')} (Cuota {ah.get('price')})")
                        cuotas_texto += f"  - Hándicaps Asiáticos: {', '.join(ah_str_list)}\n"
                    
                    if cuotas_texto == "Cuotas Reales (Bet365 / Bookmakers Oficiales):\n":
                        cuotas_texto = "Cuotas Reales de Apuestas: No disponibles para los mercados principales en la API.\n"
                else:
                    cuotas_texto = "Cuotas Reales de Apuestas: No disponibles en este momento (API Key ausente o inactiva). Por favor, estima cuotas y probabilidades matemáticas extremadamente realistas según el nivel relativo de los equipos (ej: favorito claro tiene cuota 1.15 a 1.40, partido parejo 1.90 a 2.30, etc.).\n"

                if datos_dict.get("encontrado_en_api") or datos_dict.get("api_football_encontrado"):
                    datos_texto += f"Partido: {local} vs. {visitante}\n"
                    datos_texto += cuotas_texto
                    
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
                    datos_texto += f"Partido: {local} vs. {visitante}\n"
                    datos_texto += cuotas_texto
                    datos_texto += f"Nota: {datos_dict.get('nota')}\n"

            # 4. Prompt estructurado para forzar al LLM a retornar JSON estricto basándose en la guía de J. Carreño
            prompt_maestro = (
                "Eres un Analista Cuantitativo de Apuestas Deportivas de élite, con formación en estadística bayesiana y teoría de juegos. Tu única misión es MAXIMIZAR el retorno a largo plazo aplicando los principios de Value Betting y gestión de banca de J. Carreño.\n\n"
                f"{historial_previo}\n"
                "=== DATOS DE PARTIDOS DE HOY ===\n"
                f"{datos_texto}\n"
                "=== FRAMEWORK DE ANÁLISIS OBLIGATORIO ===\n\n"
                "Para CADA selección que propongas, debes haber evaluado mentalmente:\n"
                "  A) FORTALEZA RELATIVA: ¿Cuánto mejor es el equipo seleccionado vs. su rival? (H2H, forma reciente, calidad de plantilla)\n"
                "  B) CONTEXTO MOTIVACIONAL: ¿Necesita ganar para clasificar? ¿Ya está clasificado y rotará? ¿Es partido inaugural?\n"
                "  C) EDGE DE CUOTAS: ¿La cuota del bookmaker subestima la probabilidad real del evento? (prob_estadistica > prob_implicita = VALUE)\n"
                "  D) CORRELACIÓN: Evita seleccionar dos partidos del mismo grupo que puedan afectarse mutuamente.\n\n"
                "=== REGLAS DE CONSTRUCCIÓN DE PARLEYS ===\n\n"
                "⚠️ REGLA ABSOLUTA: Cada parley DEBE tener MÍNIMO 2 selecciones. Ideal 2-3 por parley.\n\n"
                "1. 'parley_seguro' (Combinada de Valor):\n"
                "   - OBJETIVO: Cuota combinada entre 2.00x y 4.00x\n"
                "   - MÍNIMO 2 selecciones, máximo 3\n"
                "   - Cuotas individuales entre 1.35 y 2.00\n"
                "   - MERCADOS RENTABLES (en orden de preferencia):\n"
                "     * Victoria directa (1X2) de favorito con cuota >= 1.40\n"
                "     * Draw No Bet (DNB) con cuota >= 1.35 (reduce riesgo, mantiene valor)\n"
                "     * Hándicap Asiático conservador (ej: -0.5, -1.0) con cuota >= 1.40\n"
                "     * Más de 1.5 goles (si ambos equipos atacan y la cuota es >= 1.35)\n"
                "   - PROHIBIDO: Doble oportunidad con cuota < 1.35, DNB con cuota < 1.30\n"
                "   - CLAVE: Busca equipos SÓLIDOS defensivamente como locales o con ventaja histórica clara\n\n"
                "2. 'parley_arriesgado' (Combinada Bomba):\n"
                "   - OBJETIVO: Cuota combinada MÍNIMA de 5.00x (ideal 5.00x - 15.00x)\n"
                "   - MÍNIMO 2 selecciones, máximo 3\n"
                "   - Cuotas individuales entre 1.80 y 4.50\n"
                "   - MERCADOS DE ALTO VALOR (busca edges grandes):\n"
                "     * Victoria directa del equipo infravalorado (ej: el 'underdog' que tiene mejor forma reciente)\n"
                "     * Hándicap Asiático agresivo (ej: favorito -1.5 o -2.0) cuando hay dominio aplastante\n"
                "     * Más de 2.5 goles en partidos con historial ofensivo\n"
                "     * Ambos equipos anotan (BTTS/Sí) cuando ambos tienen ataque potente\n"
                "   - PROHIBIDO: Cuotas menores a 1.80 en el parley arriesgado\n"
                "   - CLAVE: Aquí buscamos el GRAN GOLPE — selecciones donde tu análisis detecta una discrepancia grande entre la cuota del bookmaker y la probabilidad real\n\n"
                "3. REGLA DE VALOR OBLIGATORIA:\n"
                "   - Para cada selección: probabilidad_estadistica (tu estimación) > probabilidad_implicita (1/cuota × 100)\n"
                "   - Si la diferencia es < 3%, NO la incluyas. El edge mínimo debe ser 3%+\n"
                "   - Ejemplo: cuota 1.55 → prob implícita 64.5%. Tu estimación debe ser >= 67.5% para incluirla.\n\n"
                "=== ERRORES COMUNES A EVITAR ===\n"
                "- NO combines selecciones de cuota 1.10-1.30 pensando que son 'seguras'. Son trampas de valor.\n"
                "- NO pongas 3 selecciones de cuota 1.80 en el arriesgado si la combinada no llega a 5.00x.\n"
                "- NO selecciones partidos donde no tienes datos suficientes para estimar la probabilidad.\n"
                "- NO repitas el mismo partido en ambos parleys.\n"
                "- Si el historial previo muestra que un tipo de mercado ha fallado consistentemente, EVÍTALO.\n\n"
                "=== REGLAS DE FORMATO (OBLIGATORIO) ===\n"
                "1. Solo puedes pronosticar partidos de la lista de arriba. PROHIBIDO inventar partidos.\n"
                "2. El campo 'partido' debe coincidir EXACTAMENTE con uno de la lista.\n"
                "3. El campo 'pronostico' debe ser concreto y específico:\n"
                "   - Victoria directa: 'Nombre Equipo a Ganar' (ej: 'Francia a Ganar')\n"
                "   - DNB: 'DNB Nombre Equipo' (ej: 'DNB Francia')\n"
                "   - Doble Oportunidad: 'Nombre Equipo o Empate' (ej: 'Francia o Empate')\n"
                "   - Hándicap Asiático: 'Nombre Equipo -X.X Hándicap Asiático' (ej: 'Francia -1.5 Hándicap Asiático')\n"
                "   - Goles: 'Más de X.X goles' (ej: 'Más de 2.5 goles')\n"
                "   - BTTS: 'Ambos equipos anotan (Sí)' o 'Ambos equipos anotan (No)'\n"
                "4. El campo 'cuota' debe ser un número float (ej: 1.55). NUNCA texto.\n"
                "5. El campo 'probabilidad_estadistica' debe ser un porcentaje como string (ej: '72%').\n\n"
                "Retorna ÚNICAMENTE JSON puro sin bloques de código markdown, sin texto antes o después:\n"
                "{\n"
                "  \"parley_seguro\": {\n"
                "    \"nombre\": \"Combinada de Valor\",\n"
                "    \"tipo_riesgo\": \"Moderado\",\n"
                "    \"stake_sugerido\": \"5/10 (Unidades)\",\n"
                "    \"selecciones\": [\n"
                "      {\n"
                "        \"partido\": \"Equipo A vs. Equipo B\",\n"
                "        \"pronostico\": \"Equipo A a Ganar\",\n"
                "        \"cuota\": 1.55,\n"
                "        \"probabilidad_estadistica\": \"72%\"\n"
                "      },\n"
                "      {\n"
                "        \"partido\": \"Equipo C vs. Equipo D\",\n"
                "        \"pronostico\": \"DNB Equipo C\",\n"
                "        \"cuota\": 1.65,\n"
                "        \"probabilidad_estadistica\": \"68%\"\n"
                "      }\n"
                "    ]\n"
                "  },\n"
                "  \"parley_arriesgado\": {\n"
                "    \"nombre\": \"Combinada Bomba\",\n"
                "    \"tipo_riesgo\": \"Alto\",\n"
                "    \"stake_sugerido\": \"1/10 (Unidades)\",\n"
                "    \"selecciones\": [\n"
                "      {\n"
                "        \"partido\": \"Equipo E vs. Equipo F\",\n"
                "        \"pronostico\": \"Equipo E a Ganar\",\n"
                "        \"cuota\": 2.50,\n"
                "        \"probabilidad_estadistica\": \"48%\"\n"
                "      },\n"
                "      {\n"
                "        \"partido\": \"Equipo G vs. Equipo H\",\n"
                "        \"pronostico\": \"Equipo G -1.5 Hándicap Asiático\",\n"
                "        \"cuota\": 2.30,\n"
                "        \"probabilidad_estadistica\": \"50%\"\n"
                "      }\n"
                "    ]\n"
                "  }\n"
                "}"
            )

            # 5. Llamada al LLM con reintentos y validación estricta de partidos reales
            picks_data = None
            json_str = ""
            intentos = 3
            
            for intento in range(intentos):
                print(f"🧠 PicksGeneratorService: Llamando al LLM (Intento {intento+1} de {intentos})...")
                json_str = self.llm.analizar_partido(prompt_maestro)
                json_str = json_str.replace("```json", "").replace("```", "").strip()
                
                try:
                    parsed_data = json.loads(json_str)
                    
                    # Normalizar claves si fueron desinfectadas
                    for old_key in list(parsed_data.keys()):
                        key_lower = old_key.lower()
                        if "segur" in key_lower:
                            parsed_data["parley_seguro"] = parsed_data[old_key]
                        elif any(x in key_lower for x in ["arriesga", "alto_valor", "valor"]):
                            parsed_data["parley_arriesgado"] = parsed_data[old_key]
                    
                    # Validar partidos y estructura
                    valid_generation = True
                    for key in ["parley_seguro", "parley_arriesgado"]:
                        parley = parsed_data.get(key)
                        if not parley or not parley.get("selecciones"):
                            print(f"⚠️ PicksGeneratorService: Faltan selecciones para {key}")
                            valid_generation = False
                            break
                        
                        # Validar mínimo 2 selecciones por parley
                        if len(parley["selecciones"]) < 2:
                            print(f"⚠️ PicksGeneratorService: {key} tiene solo {len(parley['selecciones'])} selección(es), mínimo requerido: 2. Reintentando...")
                            valid_generation = False
                            break
                        
                        for sel in parley["selecciones"]:
                            # Validar que no contenga placeholders o nombres genéricos
                            partido_propuesto = sel.get("partido", "")
                            if any(ph in partido_propuesto.lower() for ph in ["nombre local", "x vs y", "formula roja", "evento a", "nombre visitante"]):
                                print(f"⚠️ PicksGeneratorService: Se detectó placeholder en partido: '{partido_propuesto}'")
                                valid_generation = False
                                break
                            
                            # Buscar coincidencia con partidos de la lista de hoy
                            partido_real = self.encontrar_partido_correspondiente(partido_propuesto, partidos)
                            if not partido_real:
                                print(f"⚠️ PicksGeneratorService: Partido '{partido_propuesto}' no coincide con ningún partido real de hoy {partidos}")
                                valid_generation = False
                                break
                            else:
                                # Forzar el nombre exacto de la lista de hoy para evitar inconsistencias
                                sel["partido"] = partido_real
                            
                            # Validar cuota numérica y mínimos por tipo de parley
                            try:
                                cuota = float(sel.get("cuota", 0))
                                if cuota <= 1.0:
                                    print(f"⚠️ PicksGeneratorService: Cuota inválida: {cuota}")
                                    valid_generation = False
                                    break
                                # Rechazar cuotas sin valor según el tipo de parley
                                min_cuota = 1.35 if key == "parley_seguro" else 1.80
                                if cuota < min_cuota:
                                    print(f"⚠️ PicksGeneratorService: Cuota {cuota} demasiado baja para {key} (mínimo {min_cuota}). Reintentando...")
                                    valid_generation = False
                                    break
                                
                                # Validar edge mínimo (prob_estadistica > prob_implicita + 3%)
                                try:
                                    prob_est_val = float(str(sel.get('probabilidad_estadistica', '70%')).replace('%', '').strip())
                                    prob_imp_val = (1.0 / cuota) * 100
                                    edge = prob_est_val - prob_imp_val
                                    if edge < 3.0:
                                        print(f"⚠️ PicksGeneratorService: Edge insuficiente para '{sel.get('partido')}': {edge:.1f}% (mínimo 3%). Reintentando...")
                                        valid_generation = False
                                        break
                                except (ValueError, TypeError):
                                    pass
                            except (ValueError, TypeError):
                                print(f"⚠️ PicksGeneratorService: No se pudo convertir cuota a float: {sel.get('cuota')}")
                                valid_generation = False
                                break
                                
                            # Validar probabilidad numérica
                            try:
                                prob_str = str(sel.get("probabilidad_estadistica", "70%")).replace("%", "").strip()
                                float(prob_str)
                            except (ValueError, TypeError):
                                print(f"⚠️ PicksGeneratorService: Probabilidad inválida: {sel.get('probabilidad_estadistica')}")
                                valid_generation = False
                                break
                        
                        if not valid_generation:
                            break
                            
                    if valid_generation:
                        # Validar cuotas combinadas mínimas
                        for key_check in ["parley_seguro", "parley_arriesgado"]:
                            cuota_combinada = 1.0
                            for sel in parsed_data[key_check]["selecciones"]:
                                cuota_combinada *= float(sel.get("cuota", 1.0))
                            min_combinada = 2.00 if key_check == "parley_seguro" else 5.0
                            if cuota_combinada < min_combinada:
                                print(f"⚠️ PicksGeneratorService: Cuota combinada de {key_check} es {cuota_combinada:.2f}x, mínimo requerido {min_combinada}x. Reintentando...")
                                valid_generation = False
                                break
                        
                        # Validar que no se repita el mismo partido en ambos parleys
                        if valid_generation:
                            partidos_seguro = {sel.get('partido') for sel in parsed_data['parley_seguro']['selecciones']}
                            partidos_arriesgado = {sel.get('partido') for sel in parsed_data['parley_arriesgado']['selecciones']}
                            repetidos = partidos_seguro & partidos_arriesgado
                            if repetidos:
                                print(f"⚠️ PicksGeneratorService: Partidos repetidos entre parleys: {repetidos}. Reintentando...")
                                valid_generation = False
                    
                    if valid_generation:
                        picks_data = parsed_data
                        print("✅ PicksGeneratorService: Generación validada correctamente!")
                        break
                    else:
                        print("⚠️ PicksGeneratorService: Los datos generados no pasaron los filtros de validación.")
                except Exception as e:
                    print(f"⚠️ PicksGeneratorService: Excepción al parsear/validar JSON del LLM: {e}")
                    print("JSON recibido:")
                    print(json_str[:1000])
                    
            if not picks_data:
                err_msg = "La IA no devolvió picks válidos para los partidos reales de hoy tras 3 intentos."
                run_async(actualizar_log_fallo(err_msg, prompt_maestro))
                return False, err_msg

            # 6. Completar métricas matemáticas e inyectar campos calculados
            fecha_hoy = datetime.date.today().strftime("%Y-%m-%d")

            for key in ["parley_seguro", "parley_arriesgado"]:
                parley = picks_data[key]
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

            # Guardar en jugadas_YYYY-MM-DD.json (nombre dinámico)
            jugadas_path = Settings.jugadas_path(fecha_hoy)
            with open(jugadas_path, "w", encoding="utf-8") as f:
                json.dump(datos_picks, f, indent=2, ensure_ascii=False)
                
            # 7. Registrar en la base de datos de predicciones de IA (evitando redundancias/duplicados)
            async def guardar_predicciones_db():
                from decimal import Decimal
                from src.database.models import PrediccionIA
                from sqlalchemy import select, delete
                async with async_session_maker() as session:
                    # Limpiar predicciones pendientes anteriores para evitar duplicaciones
                    await session.execute(
                        delete(PrediccionIA).where(PrediccionIA.estado == "Pendiente")
                    )
                    
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
            self.tg.enviar_reporte_picks(jugadas_path)
            
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


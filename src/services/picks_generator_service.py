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
        try:
            url = Settings.SPORTS_API_URL or "https://worldcupjson.net/matches"
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
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
            print(f"⚠️ PicksGeneratorService: No se pudo obtener partidos de la API: {e}")
        
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
        partidos = self.obtener_partidos_del_dia()
        
        # 1. Recopilar estadísticas con el Scout Agent
        datos_partidos = []
        for partido in partidos:
            info = self.scout.buscar_datos(partido)
            datos_partidos.append(info)
            
        # 2. Formatear datos recopilados para el prompt
        datos_texto = ""
        for idx, datos_dict in enumerate(datos_partidos):
            datos_texto += f"\n--- PARTIDO #{idx+1} ---\n"
            if datos_dict.get("encontrado_en_api"):
                goles = datos_dict.get("goles_torneo", {})
                goles_str = ", ".join([f"{t}: {g} goles" for t, g in goles.items()])
                datos_texto += (
                    f"Partido: {datos_dict.get('partido')}\n"
                    f"Fase: {datos_dict.get('fase')} | Estadio: {datos_dict.get('estadio')}\n"
                    f"Estadísticas Goles Torneo: {goles_str}\n"
                )
            else:
                datos_texto += f"Partido: {datos_dict.get('partido_solicitado')}\nNota: {datos_dict.get('nota')}\n"

        # 3. Prompt estructurado para forzar al LLM a retornar JSON estricto basándose en la guía de J. Carreño
        prompt_maestro = (
            "Eres el Agente Científico de Datos de un consorcio de análisis deportivo, aplicando las estrictas directrices de la guía de apuestas de J. Carreño.\n"
            "Dada la siguiente lista de partidos y sus estadísticas de hoy, debes generar exactamente dos combinadas (parleys):\n\n"
            f"{datos_texto}\n"
            "INSTRUCCIONES DE SELECCIÓN (FILOSOFÍA SPRO J. CARREÑO):\n"
            "1. 'parley_seguro' (Combinada Segura): Riesgo bajo. Selecciona estrictamente entre 2 y 3 eventos (la Regla SPRO prohíbe combinadas de 4 o más eventos debido al margen acumulado de la casa). Elige cuotas individuales bajas (entre 1.10 y 1.40) con alta probabilidad real (ej: doble oportunidad, hándicaps a favor o Draw No Bet/sin empate).\n"
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

        # 4. Llamada al LLM y limpieza
        json_str = self.llm.analizar_partido(prompt_maestro)
        json_str = json_str.replace("```json", "").replace("```", "").strip()
        
        try:
            picks_data = json.loads(json_str)
        except Exception as e:
            print(f"❌ PicksGeneratorService: Error al parsear JSON del LLM: {e}")
            print("Bloque recibido del LLM:")
            print(json_str)
            return False, "La Inteligencia Artificial no devolvió un JSON en el formato requerido. Intenta de nuevo."

        # 5. Completar métricas matemáticas e inyectar campos calculados
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
                return False, f"Faltan selecciones en la sección {key}."
            
            cuota_total = 1.0
            prob_comb = 1.0
            
            for sel in parley["selecciones"]:
                cuota = float(sel.get("cuota", 1.5))
                prob_est = float(sel.get("probabilidad_estadistica", "70%").replace("%", "").strip())
                
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
            
        # 6. Registrar en la base de datos de banca descontando inversión
        datos_banca = self.banca_srv.cargar_historial()
        if datos_banca:
            tkt_seguro_id = f"TKT-{fecha_hoy.replace('-', '')}-01"
            tkt_arriesgado_id = f"TKT-{fecha_hoy.replace('-', '')}-02"
            
            # Quitar previos del día para evitar colisiones
            datos_banca["apuestas_activas"] = [
                tkt for tkt in datos_banca.get("apuestas_activas", [])
                if tkt.get("ticket_id") not in [tkt_seguro_id, tkt_arriesgado_id]
            ]
            
            p_seguro = datos_picks["parleys"]["parley_seguro"]
            p_arriesgado = datos_picks["parleys"]["parley_arriesgado"]
            
            # Combinada Segura
            datos_banca["apuestas_activas"].append({
                "ticket_id": tkt_seguro_id,
                "fecha_registro": datetime.datetime.now().isoformat(),
                "fecha_jornada": fecha_hoy,
                "tipo_parley": "Combinada Segura",
                "cuota": p_seguro["cuota_total_estimada"],
                "inversion": 1.0,
                "retorno_potencial": p_seguro["cuota_total_estimada"],
                "estado": "Pendiente",
                "selecciones": [{
                    "partido": sel["partido"],
                    "pronostico": sel["pronostico"],
                    "cuota": sel["cuota"],
                    "estado_seleccion": "Pendiente",
                    "resultado_partido": None
                } for sel in p_seguro["selecciones"]]
            })
            
            # Combinada Arriesgada
            datos_banca["apuestas_activas"].append({
                "ticket_id": tkt_arriesgado_id,
                "fecha_registro": datetime.datetime.now().isoformat(),
                "fecha_jornada": fecha_hoy,
                "tipo_parley": "Combinada de Alto Valor",
                "cuota": p_arriesgado["cuota_total_estimada"],
                "inversion": 1.0,
                "retorno_potencial": p_arriesgado["cuota_total_estimada"],
                "estado": "Pendiente",
                "selecciones": [{
                    "partido": sel["partido"],
                    "pronostico": sel["pronostico"],
                    "cuota": sel["cuota"],
                    "estado_seleccion": "Pendiente",
                    "resultado_partido": None
                } for sel in p_arriesgado["selecciones"]]
            })
            
            # Descontar saldo de banca ($2.00 en total)
            banca = datos_banca.get("banca", {})
            banca["banca_actual"] = round(banca.get("banca_actual", 10.0) - 2.0, 2)
            banca["dinero_en_juego"] = round(banca.get("dinero_en_juego", 0.0) + 2.0, 2)
            
            self.banca_srv.guardar_historial(datos_banca)

        # 7. Publicar en Telegram de inmediato
        self.tg.enviar_reporte_picks(self.jugadas_path)
        
        print("🤖 PicksGeneratorService: Generación y registro completados con éxito.")
        return True, f"Picks generados y publicados con éxito para la jornada {fecha_hoy}."

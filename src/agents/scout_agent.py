#!/usr/bin/env python3
"""
📡 AGENTE SCOUT (EXTRACTOR DE DATOS DEPORTIVOS)
Este agente se especializa en interactuar con los servicios de datos externos,
limpiar las respuestas y empaquetar la información en un formato estructurado (JSON/dict).
"""

from src.services.sports_data_service import SportsDataService
from src.services.api_football_service import APIFootballService

class ScoutAgent:
    def __init__(self):
        self.sports_service = SportsDataService()
        self.api_football = APIFootballService()

    def buscar_datos(self, consulta):
        """
        Busca las estadísticas reales de un partido para la consulta dada.
        Retorna un diccionario limpio con la información estructurada del encuentro.
        """
        print(f"📡 ScoutAgent: Buscando estadísticas para '{consulta}'...")
        partido_data = self.sports_service.obtener_datos_partido(consulta)
        
        datos_limpios = {}
        local_name = ""
        visitante_name = ""
        
        if partido_data:
            home = partido_data.get("home_team", {})
            away = partido_data.get("away_team", {})
            local_name = home.get("name", "N/A")
            visitante_name = away.get("name", "N/A")
            
            # Limpiar y estructurar los datos del partido básicos
            datos_limpios = {
                "encontrado_en_api": True,
                "partido": f"{local_name} vs. {visitante_name}",
                "equipo_local": local_name,
                "equipo_visitante": visitante_name,
                "fase": partido_data.get("stage_name", "Fase de Grupos"),
                "grupo": partido_data.get("group_name", "N/A"),
                "estadio": partido_data.get("venue", "N/A"),
                "fecha": partido_data.get("datetime", "N/A"),
                "clima": partido_data.get("weather", "Despejado / Condiciones Óptimas"),
                "goles_torneo": {
                    local_name: home.get("goals", 0),
                    away.get("name", "Visitante"): away.get("goals", 0)
                },
                "h2h_resumen": "Coincidencias estadísticas medias de fase de clasificación."
            }
        else:
            # Si no se encontró en la API general de torneos, extraemos nombres de la consulta
            if " vs. " in consulta:
                parts = consulta.split(" vs. ", 1)
                local_name, visitante_name = parts[0].strip(), parts[1].strip()
            elif " vs " in consulta:
                parts = consulta.split(" vs ", 1)
                local_name, visitante_name = parts[0].strip(), parts[1].strip()
            else:
                local_name, visitante_name = consulta, ""
                
            datos_limpios = {
                "encontrado_en_api": False,
                "partido_solicitado": consulta,
                "equipo_local": local_name,
                "equipo_visitante": visitante_name,
                "nota": f"El partido no se halló en la API en vivo. Infiere estadísticas e historial H2H para '{consulta}'."
            }

        # Intentar enriquecer los datos consultando API-Football si tenemos ambos equipos
        if local_name and visitante_name:
            try:
                info_extra = self.api_football.conseguir_contexto_enriquecido(local_name, visitante_name)
                if info_extra:
                    print(f"📡 ScoutAgent: Datos avanzados de API-Football incorporados para '{local_name} vs {visitante_name}'")
                    datos_limpios["api_football_encontrado"] = True
                    datos_limpios["arbitro"] = info_extra.get("arbitro")
                    datos_limpios["estadio_detallado"] = info_extra.get("estadio")
                    datos_limpios["alineaciones_oficiales"] = info_extra.get("alineaciones")
                    datos_limpios["bajas_lesiones"] = info_extra.get("bajas")
                    datos_limpios["h2h_historico"] = info_extra.get("h2h")
            except Exception as e:
                print(f"⚠️ ScoutAgent: Error al intentar enriquecer con API-Football: {e}")
            
        print(f"📡 ScoutAgent: Datos estructurados listos.")
        return datos_limpios

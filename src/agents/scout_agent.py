#!/usr/bin/env python3
"""
📡 AGENTE SCOUT (EXTRACTOR DE DATOS DEPORTIVOS)
Este agente se especializa en interactuar con los servicios de datos externos,
limpiar las respuestas y empaquetar la información en un formato estructurado (JSON/dict).
"""

from src.services.sports_data_service import SportsDataService

class ScoutAgent:
    def __init__(self):
        self.sports_service = SportsDataService()

    def buscar_datos(self, consulta):
        """
        Busca las estadísticas reales de un partido para la consulta dada.
        Retorna un diccionario limpio con la información estructurada del encuentro.
        """
        print(f"📡 ScoutAgent: Buscando estadísticas para '{consulta}'...")
        partido_data = self.sports_service.obtener_datos_partido(consulta)
        
        if partido_data:
            home = partido_data.get("home_team", {})
            away = partido_data.get("away_team", {})
            
            # Limpiar y estructurar los datos del partido
            datos_limpios = {
                "encontrado_en_api": True,
                "partido": f"{home.get('name', 'N/A')} vs. {away.get('name', 'N/A')}",
                "equipo_local": home.get("name", "N/A"),
                "equipo_visitante": away.get("name", "N/A"),
                "fase": partido_data.get("stage_name", "Fase de Grupos"),
                "grupo": partido_data.get("group_name", "N/A"),
                "estadio": partido_data.get("venue", "N/A"),
                "fecha": partido_data.get("datetime", "N/A"),
                "clima": partido_data.get("weather", "Despejado / Condiciones Óptimas"),
                "goles_torneo": {
                    home.get("name", "Local"): home.get("goals", 0),
                    away.get("name", "Visitante"): away.get("goals", 0)
                },
                "h2h_resumen": "Coincidencias estadísticas medias de fase de clasificación."
            }
        else:
            # Estructurar fallback de consulta manual
            datos_limpios = {
                "encontrado_en_api": False,
                "partido_solicitado": consulta,
                "nota": f"El partido no se halló en la API en vivo. Infiere estadísticas e historial H2H para '{consulta}'."
            }
            
        print(f"📡 ScoutAgent: Datos estructurados listos.")
        return datos_limpios

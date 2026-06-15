#!/usr/bin/env python3
"""
📡 CLIENTE DE LA API DEPORTIVA (SOLID - INTERFACE & IMPLEMENTATION)
Define una clase base abstracta y un cliente HTTP concreto resiliente
que extrae estadísticas de partidos deportivos.
"""

from abc import ABC, abstractmethod
import json
import urllib.request
import urllib.error
from src.config.settings import Settings

# Interfaz abstracta (Contrato de servicios)
class SportsDataInterface(ABC):
    @abstractmethod
    def obtener_datos_partido(self, id_partido):
        """
        Retorna las estadísticas crudas de un partido en formato JSON/dict
        o lanza un error en caso de fallo crítico.
        """
        pass

# Cliente concreto que consume la API de la Copa del Mundo
class SportsDataService(SportsDataInterface):
    def __init__(self, api_url=None):
        if api_url is None:
            base_url = Settings.SPORTS_API_URL or "https://worldcupjson.net"
            if not base_url.endswith("/matches") and not base_url.endswith("/matches/"):
                self.api_url = f"{base_url.rstrip('/')}/matches"
            else:
                self.api_url = base_url
        else:
            self.api_url = api_url

    def obtener_datos_partido(self, id_partido):
        """
        Consulta las estadísticas del partido por ID o nombres en la API pública de la Copa del Mundo.
        Implementa try-catch para capturar errores de red y evitar la caída del bot.
        """
        # La API de la Copa del Mundo soporta obtener todos los partidos y filtrar localmente,
        # o llamar a endpoints específicos. Haremos una llamada resiliente.
        # Si el id_partido es numérico, intentaremos buscarlo en la lista de partidos.
        url = self.api_url
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                matches = json.loads(response.read().decode("utf-8"))
            
            # Buscar el partido coincidente por ID o equipo
            for match in matches:
                # El id de la API de worldcupjson suele estar en el campo 'id' o 'id_partido'
                fid = str(match.get("id", ""))
                home_team = match.get("home_team", {}).get("name", "")
                away_team = match.get("away_team", {}).get("name", "")
                
                # Coincidencia si el ID coincide o si pasamos el nombre del equipo como id_partido
                if fid == str(id_partido) or \
                   id_partido.lower() in home_team.lower() or \
                   id_partido.lower() in away_team.lower():
                    print(f"📡 SportsDataService: Encontrado partido '{home_team} vs {away_team}'")
                    return match
            
            print(f"⚠️ SportsDataService: No se encontró partido para la consulta '{id_partido}'")
            return None
            
        except urllib.error.HTTPError as e:
            print(f"❌ SportsDataService: Error HTTP de la API ({e.code}): {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"❌ SportsDataService: Error de red o conexión: {e.reason}")
            return None
        except Exception as e:
            print(f"❌ SportsDataService: Error inesperado en el servicio de datos: {e}")
            return None

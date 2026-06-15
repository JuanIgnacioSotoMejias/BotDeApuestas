#!/usr/bin/env python3
"""
⚽ SERVICIO DE API-FOOTBALL (SOLID)
Este servicio consulta alineaciones, lesionados, árbitros e historial cara a cara (H2H)
desde API-Football, con soporte para caché local para ahorrar requests.
"""

import os
import json
import urllib.request
import urllib.parse
import datetime
import time
from src.config.settings import Settings

class APIFootballService:
    def __init__(self):
        self.api_key = Settings.API_FOOTBALL_KEY
        self.api_url = Settings.API_FOOTBALL_URL or "https://v3.football.api-sports.io"
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.cache_path = os.path.join(self.base_dir, "cache_api_football.json")
        self.cache_ttl = 7200  # 2 horas de caché en segundos

    def _cargar_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _guardar_cache(self, cache):
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ APIFootballService: No se pudo escribir el archivo de caché: {e}")

    def _obtener_headers(self):
        if not self.api_key:
            return {}
        
        # Si la URL contiene rapidapi, usa headers de RapidAPI
        if "rapidapi" in self.api_url.lower():
            return {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
                "User-Agent": "Mozilla/5.0"
            }
        else:
            # Por defecto usa headers directos de API-Sports
            return {
                "x-apisports-key": self.api_key,
                "User-Agent": "Mozilla/5.0"
            }

    def _request_api(self, endpoint, params=None):
        if not self.api_key:
            print("⚠️ APIFootballService: API Key no configurada. Saltando consulta.")
            return None

        # Construir URL con parámetros
        query_string = ""
        if params:
            query_string = "?" + urllib.parse.urlencode(params)
        
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}{query_string}"
        headers = self._obtener_headers()

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                
                # Manejar errores que vengan formateados en la respuesta exitosa (API-Football retorna errores en body a veces)
                if data.get("errors"):
                    print(f"❌ API-Football Error en respuesta: {data.get('errors')}")
                    return None
                
                return data.get("response", [])
        except Exception as e:
            print(f"⚠️ APIFootballService Error al consultar {endpoint}: {e}")
            return None

    def buscar_fixture_id(self, local, visitante, fecha_str=None):
        """Busca el fixture de hoy para obtener IDs de equipos y partido."""
        if not fecha_str:
            fecha_str = datetime.date.today().strftime("%Y-%m-%d")

        # Intentar obtener todos los fixtures de la fecha indicada
        response = self._request_api("fixtures", {"date": fecha_str})
        if not response:
            # Fallback secundario: buscar por liga si es fecha especial o no hay fixtures directos
            return None

        local_low = local.lower()
        visitante_low = visitante.lower()

        for item in response:
            teams = item.get("teams", {})
            home_name = teams.get("home", {}).get("name", "").lower()
            away_name = teams.get("away", {}).get("name", "").lower()

            # Búsqueda parcial difusa
            if (local_low in home_name or home_name in local_low) and \
               (visitante_low in away_name or away_name in visitante_low):
                fixture = item.get("fixture", {})
                
                return {
                    "fixture_id": fixture.get("id"),
                    "home_id": teams.get("home", {}).get("id"),
                    "away_id": teams.get("away", {}).get("id"),
                    "arbitro": fixture.get("referee", "Desconocido"),
                    "estadio": fixture.get("venue", {}).get("name", "Desconocido"),
                    "ciudad": fixture.get("venue", {}).get("city", "Desconocido")
                }
        return None

    def obtener_alineaciones(self, fixture_id):
        """Obtiene las alineaciones de un fixture."""
        return self._request_api("fixtures/lineups", {"fixture": fixture_id})

    def obtener_h2h(self, team1_id, team2_id):
        """Obtiene el historial directo de enfrentamientos."""
        return self._request_api("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": 5})

    def obtener_bajas(self, fixture_id):
        """Obtiene la lista de lesionados o suspendidos."""
        return self._request_api("injuries", {"fixture": fixture_id})

    def conseguir_contexto_enriquecido(self, local, visitante):
        """
        Devuelve el contexto completo y formateado del partido.
        Aplica caché local para evitar requests duplicados.
        """
        cache_key = f"{local.lower()}_vs_{visitante.lower()}"
        cache = self._cargar_cache()

        # Verificar si está en caché y no ha expirado
        if cache_key in cache:
            cached_data = cache[cache_key]
            timestamp = cached_data.get("timestamp", 0)
            if time.time() - timestamp < self.cache_ttl:
                print(f"💾 APIFootballService: Recuperado de caché para '{local} vs {visitante}'")
                return cached_data.get("data")

        print(f"📡 APIFootballService: Buscando datos frescos para '{local} vs {visitante}'...")
        fixture_info = self.buscar_fixture_id(local, visitante)
        if not fixture_info:
            print(f"⚠️ APIFootballService: No se encontró fixture_id en vivo para {local} vs {visitante}")
            return None

        fixture_id = fixture_info["fixture_id"]
        home_id = fixture_info["home_id"]
        away_id = fixture_info["away_id"]

        # Obtener alineaciones, bajas y H2H
        alineaciones = self.obtener_alineaciones(fixture_id) or []
        bajas = self.obtener_bajas(fixture_id) or []
        h2h = self.obtener_h2h(home_id, away_id) or []

        # Estructurar contexto final simplificado para el LLM
        lineups_fmt = []
        for team in alineaciones:
            team_name = team.get("team", {}).get("name")
            formation = team.get("formation", "N/A")
            coach = team.get("coach", {}).get("name", "N/A")
            titulares = [p.get("player", {}).get("name") for p in team.get("startXI", [])]
            lineups_fmt.append({
                "equipo": team_name,
                "formacion": formation,
                "entrenador": coach,
                "titulares": titulares
            })

        bajas_fmt = []
        for b in bajas:
            bajas_fmt.append({
                "jugador": b.get("player", {}).get("name"),
                "equipo": b.get("team", {}).get("name"),
                "tipo": b.get("player", {}).get("type", "Baja"),
                "razon": b.get("player", {}).get("reason", "Lesión o Sanción")
            })

        h2h_fmt = []
        for h in h2h:
            teams = h.get("teams", {})
            goals = h.get("goals", {})
            fixture_date = h.get("fixture", {}).get("date", "")[:10]
            h2h_fmt.append(
                f"[{fixture_date}] {teams.get('home', {}).get('name')} {goals.get('home')}-{goals.get('away')} {teams.get('away', {}).get('name')}"
            )

        contexto = {
            "fixture_id": fixture_id,
            "arbitro": fixture_info["arbitro"],
            "estadio": f"{fixture_info['estadio']} ({fixture_info['ciudad']})",
            "alineaciones": lineups_fmt,
            "bajas": bajas_fmt,
            "h2h": h2h_fmt
        }

        # Guardar en caché
        cache[cache_key] = {
            "timestamp": time.time(),
            "data": contexto
        }
        self._guardar_cache(cache)

        return contexto

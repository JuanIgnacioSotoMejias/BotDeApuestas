#!/usr/bin/env python3
"""
🏀 SERVICIO DE THE ODDS API (SOLID)
Este servicio se conecta a the-odds-api.com para buscar cuotas de fútbol reales.
"""

import os
import json
import urllib.request
import urllib.parse
import time
from src.config.settings import Settings

class TheOddsAPIService:
    def __init__(self):
        self.api_key = Settings.THE_ODDS_API_KEY
        self.base_url = "https://api.the-odds-api.com/v4"
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.cache_path = os.path.join(self.base_dir, "cache_the_odds_api.json")
        self.cache_ttl = 7200  # 2 horas de caché

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
            print(f"⚠️ TheOddsAPIService: No se pudo escribir caché: {e}")

    def obtener_cuotas_deportivas(self):
        """Busca todas las cuotas de fútbol para torneos de hoy."""
        if not self.api_key or self.api_key.strip() == "" or "TU_" in self.api_key:
            print("⚠️ TheOddsAPIService: THE_ODDS_API_KEY no configurada.")
            return None

        # Usar caché si no ha expirado
        cache = self._cargar_cache()
        if "soccer_odds" in cache:
            cached_data = cache["soccer_odds"]
            if time.time() - cached_data.get("timestamp", 0) < self.cache_ttl:
                print("💾 TheOddsAPIService: Recuperado de caché de The Odds API.")
                return cached_data.get("data")

        # Intentar obtener los deportes activos
        sports_url = f"{self.base_url}/sports/?apiKey={self.api_key.strip()}"
        active_soccer_keys = ["soccer_fifa_world_cup"] # fallback
        try:
            req = urllib.request.Request(sports_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                sports_data = json.loads(response.read().decode("utf-8"))
                active_soccer_keys = [s["key"] for s in sports_data if s.get("group") == "Soccer" and s.get("active")]
        except Exception as e:
            print(f"⚠️ TheOddsAPIService: No se pudo obtener lista de deportes ({e}). Usando fallback.")

        # Consultar odds para cada soccer key activo
        todas_cuotas = {}
        for sport_key in active_soccer_keys[:5]:  # limitar a max 5 para no consumir toda la cuota
            url = (
                f"{self.base_url}/sports/{sport_key}/odds/"
                f"?apiKey={self.api_key.strip()}"
                f"&regions=eu&markets=h2h,spreads"
            )
            try:
                print(f"📡 TheOddsAPIService: Consultando cuotas para '{sport_key}'...")
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as response:
                    events = json.loads(response.read().decode("utf-8"))
                    
                    for event in events:
                        home_team = event.get("home_team")
                        away_team = event.get("away_team")
                        if not home_team or not away_team:
                            continue
                            
                        match_key = f"{home_team.lower()} vs {away_team.lower()}"
                        
                        # Extraer cuotas del primer bookmaker
                        bookmakers = event.get("bookmakers", [])
                        if not bookmakers:
                            continue
                            
                        # Buscar Bet365 o usar el primero
                        bm = next((b for b in bookmakers if b.get("key") == "bet365"), bookmakers[0])
                        
                        cuotas_match = {
                            "home_team": home_team,
                            "away_team": away_team,
                            "bookmaker": bm.get("title"),
                            "1X2_Home": None,
                            "1X2_Away": None,
                            "1X2_Draw": None,
                            "DNB_Home": None,
                            "DNB_Away": None,
                            "Asian_Handicap": []
                        }
                        
                        for market in bm.get("markets", []):
                            m_key = market.get("key")
                            outcomes = market.get("outcomes", [])
                            
                            if m_key == "h2h":
                                for out in outcomes:
                                    name = out.get("name")
                                    price = out.get("price")
                                    if name == home_team:
                                        cuotas_match["1X2_Home"] = float(price)
                                    elif name == away_team:
                                        cuotas_match["1X2_Away"] = float(price)
                                    elif name.lower() in ["draw", "empate"]:
                                        cuotas_match["1X2_Draw"] = float(price)
                                        
                            elif m_key == "spreads":
                                for out in outcomes:
                                    cuotas_match["Asian_Handicap"].append({
                                        "name": out.get("name"),
                                        "point": out.get("point"),
                                        "price": float(out.get("price"))
                                    })
                        
                        # Calcular DNB matemáticamente a partir de las cuotas 1X2
                        if cuotas_match["1X2_Home"] and cuotas_match["1X2_Draw"]:
                            try:
                                odd_home = cuotas_match["1X2_Home"]
                                odd_draw = cuotas_match["1X2_Draw"]
                                if odd_draw > 1.0:
                                    cuotas_match["DNB_Home"] = round(odd_home * (1.0 - 1.0 / odd_draw), 2)
                            except Exception:
                                pass
                                
                        if cuotas_match["1X2_Away"] and cuotas_match["1X2_Draw"]:
                            try:
                                odd_away = cuotas_match["1X2_Away"]
                                odd_draw = cuotas_match["1X2_Draw"]
                                if odd_draw > 1.0:
                                    cuotas_match["DNB_Away"] = round(odd_away * (1.0 - 1.0 / odd_draw), 2)
                            except Exception:
                                pass
                                    
                        todas_cuotas[match_key] = cuotas_match
            except Exception as e:
                print(f"⚠️ TheOddsAPIService: Error al consultar cuotas para '{sport_key}': {e}")
                
        # Guardar en caché
        if todas_cuotas:
            cache["soccer_odds"] = {
                "timestamp": time.time(),
                "data": todas_cuotas
            }
            self._guardar_cache(cache)
            
        return todas_cuotas

    def obtener_cuotas_para_partido(self, local, visitante):
        """Busca cuotas para un partido específico normalizando nombres de equipo."""
        cuotas = self.obtener_cuotas_deportivas()
        if not cuotas:
            return None
            
        import unicodedata
        def normalizar(s):
            s = s.lower()
            s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
            # Mapeos comunes
            mapeo = {
                "irak": "iraq",
                "noruega": "norway",
                "argelia": "algeria",
                "arabia saudita": "saudi arabia",
                "arabia saudi": "saudi arabia",
                "espana": "spain",
                "cabo verde": "cape verde",
                "belgica": "belgium",
                "egipto": "egypt",
                "francia": "france",
                "senegal": "senegal",
                "austria": "austria",
                "jordania": "jordan",
            }
            return mapeo.get(s, s)

        l_norm = normalizar(local)
        v_norm = normalizar(visitante)

        for match_key, val in cuotas.items():
            parts = match_key.split(" vs ")
            if len(parts) != 2:
                continue
            h_norm = normalizar(parts[0])
            a_norm = normalizar(parts[1])

            # Coincidencia directa o invertida
            if (l_norm == h_norm and v_norm == a_norm) or (l_norm == a_norm and v_norm == h_norm):
                return val

        return None

#!/usr/bin/env python3
"""
📡 SERVICIO DE EXTRACCIÓN DE RESULTADOS Y MARCADORES (SOLID)
Este servicio se encarga exclusivamente de consultar marcadores deportivos de partidos
del Mundial 2026 desde APIs públicas libres (como worldcupjson.net) y cuenta con un
mecanismo de fallback para parsear marcadores.
"""

import json
import urllib.request
import urllib.parse
import sys
import src.config.encoding  # noqa: F401 — Centraliza reconfigure de stdout/stderr UTF-8

def normalizar_equipo(nombre):
    if not nombre:
        return ""
    import unicodedata
    # Quitar tildes y diacríticos y normalizar conectores comunes y guiones
    nombre_norm = "".join(
        c for c in unicodedata.normalize('NFD', nombre)
        if unicodedata.category(c) != 'Mn'
    ).lower().replace("&", "and").replace(" y ", " and ").replace("-", " ").strip()
    
    # Tabla de traducción manual de español e inglés a una clave única
    traducciones = {
        "bosnia and herzegovina": "bosnia and herzegovina",
        "bosnia & herzegovina": "bosnia and herzegovina",
        "bosnia y herzegovina": "bosnia and herzegovina",
        "bosnia herzegovina": "bosnia and herzegovina",
        "bosnia": "bosnia and herzegovina",
        "espana": "spain",
        "cabo verde": "cape verde",
        "iran": "iran",
        "nueva zelanda": "new zealand",
        "nueva zelandia": "new zealand",
        "arabia saudita": "saudi arabia",
        "arabia saudi": "saudi arabia",
        "estados unidos": "united states",
        "eeuu": "united states",
        "ee.uu.": "united states",
        "alemania": "germany",
        "costa de marfil": "ivory coast",
        "paises bajos": "netherlands",
        "holanda": "netherlands",
        "suecia": "sweden",
        "francia": "france",
        "irak": "iraq",
        "noruega": "norway",
        "senegal": "senegal",
        "japon": "japan",
        "turquia": "turkey",
        "catar": "qatar",
        "qatar": "qatar",
        "suiza": "switzerland",
        "haiti": "haiti",
        "escocia": "scotland",
        "inglaterra": "england",
        "croacia": "croatia",
        "jordania": "jordan",
        "argelia": "algeria",
        "portugal": "portugal",
        "uzbekistan": "uzbekistan",
        "panama": "panama",
        "republica checa": "czech republic",
        "tunez": "tunisia",
        "tunisia": "tunisia",
        "republica democratica del congo": "democratic republic of the congo",
        "rd congo": "democratic republic of the congo",
        "dr congo": "democratic republic of the congo",
        "congo dr": "democratic republic of the congo",
        "sudafrica": "south africa",
        "marruecos": "morocco",
        "ecuador": "ecuador",
        "curazao": "curaçao",
        "curacao": "curaçao",
        "belgica": "belgium",
        "mexico": "mexico",
        "corea del sur": "south korea",
        "paraguay": "paraguay",
        "corea del norte": "north korea",
        "gales": "wales",
        "polonia": "poland",
        "dinamarca": "denmark",
        "ucrania": "ukraine",
        "austria": "austria",
        "camerun": "cameroon",
        "ghana": "ghana",
        "serbia": "serbia",
        "suiza": "switzerland",
        "costa rica": "costa rica",
        "canada": "canada",
        "brasil": "brazil",
        "brazil": "brazil",
        "egipto": "egypt",
        "egypt": "egypt",
    }
    
    return traducciones.get(nombre_norm, nombre_norm)

def coinciden_equipos(eq1, eq2):
    if not eq1 or not eq2:
        return False
    n1 = normalizar_equipo(eq1)
    n2 = normalizar_equipo(eq2)
    return n1 == n2 or n1 in n2 or n2 in n1

class ResultadosAPIService:
    def __init__(self):
        # API pública gratuita para la Copa del Mundo (sin requerimiento de API Key)
        self.api_url = "https://worldcupjson.net/matches"
        
    def obtener_marcador_api(self, equipo_local, equipo_visitante):
        """
        Consulta la API de la Copa del Mundo en busca del marcador de un partido específico.
        Intenta primero la API de 2026 (worldcup26.ir) y luego la API de 2022 (worldcupjson.net).
        Retorna una tupla: (goles_local, goles_visitante, finalizado) o (None, None, False) si no se halla.
        """
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
            with urllib.request.urlopen(req, timeout=20, context=ctx) as response:
                data = json.loads(response.read().decode("utf-8"))
                matches = data.get("games", [])
                
            for match in matches:
                home_team = match.get("home_team_name_en", "")
                away_team = match.get("away_team_name_en", "")
                
                # Caso 1: Orden normal
                if coinciden_equipos(equipo_local, home_team) and coinciden_equipos(equipo_visitante, away_team):
                    finished = match.get("finished", "").upper() == "TRUE" or match.get("time_elapsed", "").lower() == "finished"
                    goles_local = match.get("home_score")
                    goles_visitante = match.get("away_score")
                    if goles_local is not None and goles_visitante is not None:
                        try:
                            return int(goles_local), int(goles_visitante), finished
                        except ValueError:
                            pass
                # Caso 2: Orden invertido (swapped)
                elif coinciden_equipos(equipo_local, away_team) and coinciden_equipos(equipo_visitante, home_team):
                    finished = match.get("finished", "").upper() == "TRUE" or match.get("time_elapsed", "").lower() == "finished"
                    goles_local = match.get("away_score")
                    goles_visitante = match.get("home_score")
                    if goles_local is not None and goles_visitante is not None:
                        try:
                            return int(goles_local), int(goles_visitante), finished
                        except ValueError:
                            pass
        except Exception as e:
            print(f"⚠️ Error al conectar con la API de 2026 (worldcup26.ir): {e}")

        # 2. Intentar API de 2022 (worldcupjson.net)
        try:
            req = urllib.request.Request(
                "https://worldcupjson.net/matches",
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                matches = json.loads(response.read().decode("utf-8"))
                
            for match in matches:
                home_team = match.get("home_team", {}).get("name", "")
                away_team = match.get("away_team", {}).get("name", "")
                
                # Caso 1: Orden normal
                if coinciden_equipos(equipo_local, home_team) and coinciden_equipos(equipo_visitante, away_team):
                    status = match.get("status", "")
                    finalizado = status.lower() in ["completed", "final", "finished"]
                    goles_local = match.get("home_team", {}).get("goals")
                    goles_visitante = match.get("away_team", {}).get("goals")
                    return goles_local, goles_visitante, finalizado
                # Caso 2: Orden invertido (swapped)
                elif coinciden_equipos(equipo_local, away_team) and coinciden_equipos(equipo_visitante, home_team):
                    status = match.get("status", "")
                    finalizado = status.lower() in ["completed", "final", "finished"]
                    goles_local = match.get("away_team", {}).get("goals")
                    goles_visitante = match.get("home_team", {}).get("goals")
                    return goles_local, goles_visitante, finalizado
        except Exception as e:
            print(f"⚠️ Error al conectar con la API de 2022 (worldcupjson): {e}")
            
        return None, None, False
 
    def obtener_marcador_fallback(self, equipo_local, equipo_visitante):
        """
        Mecanismo de fallback interactivo o de simulación para cuando la API no responde o
        durante pruebas locales antes del torneo.
        """
        # Evitar bloquear hilos en producción si no es una consola interactiva (TTY)
        if not sys.stdin or not sys.stdin.isatty():
            return None, None, False
            
        print(f"\n🔄 Fallback: API no disponible para el partido '{equipo_local} vs. {equipo_visitante}'.")
        marcador = input(f"📝 Digite marcador real de '{equipo_local} vs. {equipo_visitante}' (Ej: 2-1) [Enter si no ha jugado]: ").strip()
        if not marcador or "-" not in marcador:
            return None, None, False
        try:
            goles_l, goles_v = map(int, marcador.split("-"))
            return goles_l, goles_v, True
        except ValueError:
            print("⚠️ Formato incorrecto. Debe ser goles-goles (ej: 2-0).")
            return None, None, False
 
    def conseguir_marcador(self, equipo_local, equipo_visitante):
        """
        Intenta obtener el marcador mediante API pública y, en caso de fallo, usa el método fallback.
        Retorna (goles_local, goles_visitante, finalizado).
        """
        # 1. Intentar API
        g_l, g_v, fin = self.obtener_marcador_api(equipo_local, equipo_visitante)
        if fin and g_l is not None and g_v is not None:
            print(f"📡 API exitosa: Marcador para {equipo_local} vs {equipo_visitante} es {g_l}-{g_v} (Finalizado)")
            return g_l, g_v, True
            
        # 2. Si no se obtuvo de la API, recurrir a fallback
        return self.obtener_marcador_fallback(equipo_local, equipo_visitante)
 
# Prueba local del módulo
if __name__ == "__main__":
    service = ResultadosAPIService()
    # Simulación
    goles_l, goles_v, finalizado = service.conseguir_marcador("España", "Cabo Verde")
    print(f"Resultado final obtenido: Local={goles_l}, Visitante={goles_v}, Finalizado={finalizado}")

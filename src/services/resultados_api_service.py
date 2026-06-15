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

# Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

class ResultadosAPIService:
    def __init__(self):
        # API pública gratuita para la Copa del Mundo (sin requerimiento de API Key)
        self.api_url = "https://worldcupjson.net/matches"
        
    def obtener_marcador_api(self, equipo_local, equipo_visitante):
        """
        Consulta la API de la Copa del Mundo en busca del marcador de un partido específico.
        Retorna una tupla: (goles_local, goles_visitante, finalizado) o (None, None, False) si no se halla.
        """
        try:
            req = urllib.request.Request(
                self.api_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                matches = json.loads(response.read().decode("utf-8"))
                
            for match in matches:
                home_team = match.get("home_team", {}).get("name", "").lower()
                away_team = match.get("away_team", {}).get("name", "").lower()
                
                # Comprobar coincidencia de nombres (búsqueda parcial)
                if (equipo_local.lower() in home_team or home_team in equipo_local.lower()) and \
                   (equipo_visitante.lower() in away_team or away_team in equipo_visitante.lower()):
                    
                    status = match.get("status", "")
                    finalizado = status.lower() in ["completed", "final", "finished"]
                    
                    # Extraer goles
                    goles_local = match.get("home_team", {}).get("goals")
                    goles_visitante = match.get("away_team", {}).get("goals")
                    
                    return goles_local, goles_visitante, finalizado
        except Exception as e:
            print(f"⚠️ Error al conectar con la API de resultados: {e}")
            
        return None, None, False
 
    def obtener_marcador_fallback(self, equipo_local, equipo_visitante):
        """
        Mecanismo de fallback interactivo o de simulación para cuando la API no responde o
        durante pruebas locales antes del torneo.
        """
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

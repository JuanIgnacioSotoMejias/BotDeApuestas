#!/usr/bin/env python3
import os
import sys

# Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Agregar la ruta absoluta del workspace al path
WORKSPACE_DIR = r"c:\Users\sotox\Music\apuestas"
sys.path.append(WORKSPACE_DIR)
os.chdir(WORKSPACE_DIR)

from src.services.api_football_service import APIFootballService

from src.agents.scout_agent import ScoutAgent
from src.config.settings import Settings

def test_api_football():
    print("🚀 Iniciando prueba del módulo API-Football...")
    print(f"URL Configurador: {Settings.API_FOOTBALL_URL}")
    print(f"Key Configurada: {'***' + Settings.API_FOOTBALL_KEY[-4:] if Settings.API_FOOTBALL_KEY else 'Ninguna'}")
    
    # 1. Instanciar servicio
    service = APIFootballService()
    
    # 2. Intentar consulta de contexto enriquecido
    equipo_a = "España"
    equipo_b = "Cabo Verde"
    print(f"\n🔍 Consultando contexto para '{equipo_a} vs {equipo_b}'...")
    contexto = service.conseguir_contexto_enriquecido(equipo_a, equipo_b)
    
    if contexto:
        print("✅ Contexto obtenido con éxito:")
        print(f"  - Árbitro: {contexto.get('arbitro')}")
        print(f"  - Estadio: {contexto.get('estadio')}")
        print(f"  - Cantidad alineaciones: {len(contexto.get('alineaciones', []))}")
        print(f"  - Cantidad bajas: {len(contexto.get('bajas', []))}")
        print(f"  - H2H: {contexto.get('h2h', [])}")
    else:
        print("⚠️ No se obtuvo contexto en caliente (API Key vacía o partido no programado hoy).")
        print("Esto es normal si no tienes una clave API cargada en tu archivo .env.")

    # 3. Validar integración con ScoutAgent
    print("\n🔍 Probando integración directa con ScoutAgent...")
    scout = ScoutAgent()
    info = scout.buscar_datos("España vs. Cabo Verde")
    print(f"Claves devueltas por ScoutAgent: {list(info.keys())}")
    if info.get("api_football_encontrado"):
        print("✅ ScoutAgent integró exitosamente las estadísticas avanzadas.")
    else:
        print("💡 ScoutAgent retornó de forma segura el fallback estándar.")

if __name__ == "__main__":
    test_api_football()

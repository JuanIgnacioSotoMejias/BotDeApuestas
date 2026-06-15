#!/usr/bin/env python3
"""
🚀 ORQUESTADOR PRINCIPAL - RETO APUESTAS ELITE
Este script unifica y coordina todos los servicios (SOLID) del sistema.
Puede ejecutarse de forma interactiva o automática (vía Cron/Schedule):
- `--publish`: Publica picks del día a Telegram.
- `--settle`: Consulta resultados (API + Fallback) y liquida apuestas archivando el ticket y notificando.
"""

import sys
import os

# Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

from src.services.telegram_service import TelegramService
from src.services.gestor_banca_service import GestorBancaService
from src.services.resultados_api_service import ResultadosAPIService

# Rutas globales de archivos
JUGADAS_PATH = os.path.join(BASE_DIR, "jugadas_lunes_15.json")

def parsear_ganador_seleccion(pronostico, home_name, away_name, g_home, g_away):
    """
    Evalúa si un pronóstico se cumple según las estadísticas de goles.
    Retorna: 'Ganado', 'Perdido', o 'Anulado'.
    """
    pronostico_lower = pronostico.lower()
    
    # 1. Caso: Más de X goles (Overs)
    if "más de" in pronostico_lower or "over" in pronostico_lower:
        # Extraer el número (ej: 1.5)
        for token in pronostico_lower.split():
            try:
                linea = float(token.replace("goles", "").strip())
                if (g_home + g_away) > linea:
                    return "Ganado"
                else:
                    return "Perdido"
            except ValueError:
                continue
                
    # 2. Caso: Ambos anotan
    if "ambos equipos anotan" in pronostico_lower or "ambos anotan" in pronostico_lower:
        if g_home > 0 and g_away > 0:
            return "Ganado"
        else:
            return "Perdido"
            
    # 3. Caso: Hándicap Asiático (ej: España -2.0)
    if "hándicap" in pronostico_lower or "handicap" in pronostico_lower:
        # Determinar a qué equipo aplica
        es_home = False
        es_away = False
        if home_name.lower() in pronostico_lower:
            es_home = True
        elif away_name.lower() in pronostico_lower:
            es_away = True
            
        # Extraer el valor del hándicap (ej: -2.0)
        hc_valor = 0.0
        for token in pronostico_lower.split():
            if token.startswith("-") or token.startswith("+"):
                try:
                    hc_valor = float(token.replace("a", "").strip())
                    break
                except ValueError:
                    continue
                    
        if es_home:
            diff = g_home - g_away + hc_valor
        elif es_away:
            diff = g_away - g_home + hc_valor
        else:
            return "Anulado"  # Fallback
            
        if diff > 0:
            return "Ganado"
        elif diff == 0:
            return "Anulado"
        else:
            return "Perdido"

    # 4. Caso: Doble Oportunidad (ej: Irán o Empate)
    if "o empate" in pronostico_lower or "doble oportunidad" in pronostico_lower:
        if "empate" in pronostico_lower:
            # Encontrar el equipo
            if home_name.lower() in pronostico_lower:
                return "Ganado" if g_home >= g_away else "Perdido"
            elif away_name.lower() in pronostico_lower:
                return "Ganado" if g_away >= g_home else "Perdido"

    # 5. Caso: Victoria directa (1X2)
    # Por ejemplo "España a Ganador", "Uruguay a Ganador"
    if home_name.lower() in pronostico_lower:
        return "Ganado" if g_home > g_away else "Perdido"
    elif away_name.lower() in pronostico_lower:
        return "Ganado" if g_away > g_home else "Perdido"
        
    # Si no se reconoce el patrón, requerir confirmación manual (asumiendo Anulado por seguridad)
    return "Anulado"

def main():
    # Inicializar servicios
    tg = TelegramService()
    banca_srv = GestorBancaService()
    api_srv = ResultadosAPIService()
    
    # Validar configuraciones
    if not tg.validar_configuracion():
        print("⚠️ Advertencia: Credenciales de Telegram no configuradas en el .env.")
        
    modo = "--all"
    if len(sys.argv) > 1:
        modo = sys.argv[1].lower()
        
    # --- PROCESAMIENTO MODO BANK ---
    if modo == "--bank":
        print("🚀 [MODO BANK] Enviando reporte de banca...")
        tg.enviar_reporte_banca(banca_srv.historial_path)
        sys.exit(0)

    # --- PROCESAMIENTO MODO PUBLISH ---
    if modo in ["--publish", "--all"]:
        print("🚀 [MODO PUBLISH] Iniciando envío de combinadas...")
        tg.enviar_reporte_picks(JUGADAS_PATH)
        
    # --- PROCESAMIENTO MODO SETTLE ---
    if modo in ["--settle", "--all"]:
        print("\n🚀 [MODO SETTLE] Iniciando liquidación automática...")
        datos = banca_srv.cargar_historial()
        if not datos:
            sys.exit(1)
            
        activas = list(datos.get("apuestas_activas", []))
        if not activas:
            print("💡 No hay apuestas activas por liquidar en el historial.")
            sys.exit(0)
            
        for tkt in activas:
            ticket_id = tkt.get("ticket_id")
            print(f"\n🎫 Procesando Ticket: {ticket_id} ({tkt.get('tipo_parley')})")
            
            resultados_tkt = {}
            error_obtencion = False
            
            for sel in tkt.get("selecciones", []):
                partido = sel.get("partido")
                # Separar nombres de equipos
                if " vs. " in partido:
                    home, away = partido.split(" vs. ", 1)
                elif " vs " in partido:
                    home, away = partido.split(" vs ", 1)
                else:
                    home, away = partido, ""
                    
                print(f"  🔍 Buscando marcador de '{partido}'...")
                g_home, g_away, finalizado = api_srv.conseguir_marcador(home, away)
                
                if finalizado and g_home is not None and g_away is not None:
                    marcador_str = f"{g_home}-{g_away}"
                    estado_sel = parsear_ganador_seleccion(sel.get("pronostico"), home, away, g_home, g_away)
                    
                    # Mostrar veredicto intermedio
                    emoji = "✅" if estado_sel == "Ganado" else ("❌" if estado_sel == "Perdido" else "🔄")
                    print(f"  📊 Marcador: {marcador_str} | Veredicto: {emoji} {estado_sel}")
                    
                    resultados_tkt[partido] = {
                        "estado": estado_sel,
                        "marcador": marcador_str
                    }
                else:
                    print(f"  ⚠️ No se pudo obtener el resultado para '{partido}'. Se saltará este ticket.")
                    error_obtencion = True
                    break
                    
            if not error_obtencion:
                # Liquidar el ticket completo
                exito = banca_srv.asentar_ticket(datos, ticket_id, resultados_tkt)
                if exito:
                    print(f"🎉 Ticket {ticket_id} liquidado con éxito.")
            else:
                print(f"⏭️ Ticket {ticket_id} pospuesto por falta de resultados oficiales.")
                
        # Guardar cambios
        banca_srv.guardar_historial(datos)
        
        # Enviar reporte actualizado a Telegram
        tg.enviar_reporte_banca(banca_srv.historial_path)

if __name__ == "__main__":
    from src.database.session import init_db
    from src.services.gestor_banca_service import run_async
    print("🗄️ Inicializando base de datos en orquestador...")
    run_async(init_db())
    main()


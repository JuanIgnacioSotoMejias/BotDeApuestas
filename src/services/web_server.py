#!/usr/bin/env python3
"""
📡 SERVIDOR DE API Y DASHBOARD WEB
Este servidor sirve los archivos estáticos de la carpeta /dashboard/
y expone una API REST local para gestionar la banca y los picks de apuestas
sin necesidad de comandos de consola.
"""

import os
import json
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

# Asegurar codificación UTF-8 para consola en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Agregar raíz al PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from src.services.gestor_banca_service import GestorBancaService
from src.services.telegram_service import TelegramService

PORT = 8000
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")

class DashboardAPIHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Habilitar CORS para peticiones fetch del frontend
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        # API GET: Retornar historial completo de banca
        if self.path == "/api/banca":
            banca_srv = GestorBancaService()
            datos = banca_srv.cargar_historial()
            if datos:
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(datos, ensure_ascii=False).encode("utf-8"))
            else:
                self.send_error(500, "Error al cargar la base de datos de apuestas.")
            return

        # Limpiar query parameters del path
        clean_path = self.path.split("?", 1)[0]
        
        # Redirigir por defecto al index.html del dashboard con redirección real
        if clean_path in ["/", "/dashboard", "/dashboard/"]:
            self.send_response(302)
            self.send_header("Location", "/dashboard/index.html")
            self.end_headers()
            return

        # Servir recursos estáticos de /dashboard/
        if clean_path.startswith("/dashboard/"):
            relative_file = clean_path.replace("/dashboard/", "", 1)
            if not relative_file:
                relative_file = "index.html"
                
            file_path = os.path.join(DASHBOARD_DIR, relative_file)
            
            # Impedir saltos de directorio (Seguridad)
            if not os.path.abspath(file_path).startswith(os.path.abspath(DASHBOARD_DIR)):
                self.send_error(403, "Acceso Denegado.")
                return

            if os.path.exists(file_path) and os.path.isfile(file_path):
                # Determinar MIME Type
                content_type = "text/plain"
                if file_path.endswith(".html"):
                    content_type = "text/html; charset=utf-8"
                elif file_path.endswith(".css"):
                    content_type = "text/css; charset=utf-8"
                elif file_path.endswith(".js"):
                    content_type = "application/javascript; charset=utf-8"
                elif file_path.endswith(".json"):
                    content_type = "application/json; charset=utf-8"
                elif file_path.endswith(".png"):
                    content_type = "image/png"
                elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                    content_type = "image/jpeg"

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                
                try:
                    with open(file_path, "rb") as f:
                        self.wfile.write(f.read())
                except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                    # Ignorar desconexión abrupta del cliente/navegador
                    pass
            else:
                self.send_error(404, f"Archivo no encontrado: {relative_file}")
            return
        
        # Redirección de emergencia
        self.send_response(302)
        self.send_header("Location", "/dashboard/index.html")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""
        
        try:
            body = json.loads(post_data) if post_data.strip() else {}
        except Exception:
            self.send_error(400, "Cuerpo de petición no es un JSON válido.")
            return

        # API POST: Liquidación rápida de apuestas activas
        if self.path == "/api/liquidar":
            ticket_id = body.get("ticket_id")
            estado = body.get("estado")
            
            if not ticket_id or estado not in ["Ganada", "Perdida", "Anulada"]:
                self.send_error(400, "Se requiere 'ticket_id' y un 'estado' válido (Ganada/Perdida/Anulada).")
                return
                
            banca_srv = GestorBancaService()
            datos = banca_srv.cargar_historial()
            if not datos:
                self.send_error(500, "Error al leer historial_apuestas.json.")
                return
                
            exito = banca_srv.asentar_ticket_directo(datos, ticket_id, estado)
            if exito:
                banca_srv.guardar_historial(datos)
                # Reportar estado financiero a Telegram
                tg = TelegramService()
                tg.enviar_reporte_banca(banca_srv.historial_path)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "message": f"Ticket {ticket_id} asentado."}).encode("utf-8"))
            else:
                self.send_error(404, "El ticket no se encontró en las apuestas activas.")
            return

        # API POST: Creación de Picks y registro de apuestas
        if self.path == "/api/crear_picks":
            fecha = body.get("fecha")
            descripcion = body.get("descripcion")
            p_seguro = body.get("parley_seguro")
            p_arriesgado = body.get("parley_arriesgado")
            
            if not fecha or not p_seguro or not p_arriesgado:
                self.send_error(400, "Faltan campos obligatorios para registrar la combinada.")
                return
                
            # Formatear JSON para picks del día
            datos_picks = {
                "fecha_jornada": fecha,
                "descripcion": descripcion or f"Combinadas de la Jornada {fecha}",
                "paginas_consultadas": ["VegasInsider", "Covers", "Action Network"],
                "parleys": {
                    "parley_seguro": p_seguro,
                    "parley_arriesgado": p_arriesgado
                }
            }
            
            # Guardar jugadas_lunes_15.json
            jugadas_path = os.path.join(BASE_DIR, "jugadas_lunes_15.json")
            with open(jugadas_path, "w", encoding="utf-8") as f:
                json.dump(datos_picks, f, indent=2, ensure_ascii=False)
                
            # Registrar apuestas activas
            banca_srv = GestorBancaService()
            datos_banca = banca_srv.cargar_historial()
            
            if datos_banca:
                tkt_seguro_id = f"TKT-{fecha.replace('-', '')}-01"
                tkt_arriesgado_id = f"TKT-{fecha.replace('-', '')}-02"
                
                # Eliminar duplicados previos si existieran
                datos_banca["apuestas_activas"] = [
                    tkt for tkt in datos_banca.get("apuestas_activas", [])
                    if tkt.get("ticket_id") not in [tkt_seguro_id, tkt_arriesgado_id]
                ]
                
                # Insertar los dos nuevos tickets activos
                datos_banca["apuestas_activas"].append({
                    "ticket_id": tkt_seguro_id,
                    "fecha_registro": datetime.datetime.now().isoformat(),
                    "fecha_jornada": fecha,
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
                
                datos_banca["apuestas_activas"].append({
                    "ticket_id": tkt_arriesgado_id,
                    "fecha_registro": datetime.datetime.now().isoformat(),
                    "fecha_jornada": fecha,
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
                
                # Descontar inversión de la banca disponible ($2.00 en total)
                banca = datos_banca.get("banca", {})
                banca["banca_actual"] = round(banca.get("banca_actual", 10.0) - 2.0, 2)
                banca["dinero_en_juego"] = round(banca.get("dinero_en_juego", 0.0) + 2.0, 2)
                
                # Guardar
                banca_srv.guardar_historial(datos_banca)
                
            # Publicar picks al canal
            tg = TelegramService()
            tg.enviar_reporte_picks(jugadas_path)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "message": "Picks creados y publicados en Telegram."}).encode("utf-8"))
            return

        # API POST: Generación Automática de Picks mediante IA de Agentes
        if self.path == "/api/generar_picks_ia":
            try:
                from src.services.picks_generator_service import PicksGeneratorService
                gen_srv = PicksGeneratorService()
                exito, msg = gen_srv.generar_picks_ia()
                if exito:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"ok": True, "message": msg}).encode("utf-8"))
                else:
                    self.send_error(500, f"Error al generar picks: {msg}")
            except Exception as e:
                self.send_error(500, f"Error interno del servidor: {str(e)}")
            return
            
        self.send_error(404, "Endpoint de API no encontrado.")

def run_server():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, DashboardAPIHandler)
    print(f"📡 Servidor API del Dashboard iniciado en http://localhost:{PORT} ...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🧹 Cerrando el servidor web...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()

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

PORT = int(os.environ.get("PORT", 8000))
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
            try:
                banca_srv = GestorBancaService()
                datos = banca_srv.cargar_historial()
                if datos:
                    # Inyectar propuestas de hoy leídas desde el JSON
                    propuestas_hoy = None
                    jugadas_path = os.path.join(BASE_DIR, "jugadas_lunes_15.json")
                    if os.path.exists(jugadas_path):
                        try:
                            with open(jugadas_path, "r", encoding="utf-8") as f:
                                propuestas_hoy = json.load(f)
                        except Exception as e:
                            print(f"⚠️ Error al leer {jugadas_path}: {e}")
                    datos["propuestas_hoy"] = propuestas_hoy

                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps(datos, ensure_ascii=False).encode("utf-8"))
                else:
                    self.send_error(500, "Error al cargar la base de datos de apuestas.")
            except Exception as e:
                import traceback
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                err_info = {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
                self.wfile.write(json.dumps(err_info, ensure_ascii=False).encode("utf-8"))
            return

        # API GET: Debug logs de generaciones para auditoría
        if self.path == "/api/debug/logs":
            try:
                from src.database.session import async_session_maker
                from src.database.models import LogGeneracion
                from sqlalchemy import select
                from src.services.gestor_banca_service import run_async
                
                async def obtener_logs():
                    async with async_session_maker() as session:
                        stmt = select(LogGeneracion).order_by(LogGeneracion.fecha.desc()).limit(5)
                        res = await session.execute(stmt)
                        logs = res.scalars().all()
                        return [{
                            "id": l.id,
                            "fecha": l.fecha.isoformat(),
                            "exito": l.exito,
                            "detalles": l.detalles,
                            "json_resultado": l.json_resultado[:200] if l.json_resultado else None
                        } for l in logs]
                
                log_data = run_async(obtener_logs())
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(log_data).encode("utf-8"))
            except Exception as e:
                self.send_error(500, f"Error al cargar logs: {str(e)}")
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

        # API POST: Colocación de apuesta interactiva
        if self.path == "/api/jugar_ticket":
            tipo_parley = body.get("tipo_parley")
            inversion = body.get("inversion")
            cuota = body.get("cuota")
            selecciones = body.get("selecciones")
            
            if not tipo_parley or not inversion or not cuota or not selecciones:
                self.send_error(400, "Faltan campos obligatorios (tipo_parley, inversion, cuota, selecciones).")
                return
                
            try:
                inversion_val = float(inversion)
                cuota_val = float(cuota)
            except ValueError:
                self.send_error(400, "Inversión y Cuota deben ser números válidos.")
                return

            # Validar que ningún partido de la combinada haya finalizado en la BD de predicciones
            try:
                from sqlalchemy import select
                from src.database.models import PrediccionIA
                from src.services.gestor_banca_service import run_async
                from src.database.session import async_session_maker

                async def validar_partidos():
                    async with async_session_maker() as session:
                        partidos_names = [sel["partido"] for sel in selecciones]
                        stmt = select(PrediccionIA).where(
                            PrediccionIA.partido.in_(partidos_names),
                            PrediccionIA.estado != "Pendiente"
                        )
                        res = await session.execute(stmt)
                        return res.scalars().all()

                finalizados = run_async(validar_partidos())
                if finalizados:
                    partidos_finalizados_nombres = ", ".join([p.partido for p in finalizados])
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "ok": False,
                        "error": f"No se puede jugar el parley. Los siguientes partidos ya finalizaron: {partidos_finalizados_nombres}"
                    }).encode("utf-8"))
                    return
            except Exception as e:
                print(f"⚠️ Error al validar partidos finalizados en /api/jugar_ticket: {e}")

            banca_srv = GestorBancaService()
            datos = banca_srv.cargar_historial()
            if not datos:
                self.send_error(500, "Error al cargar la base de datos de apuestas.")
                return
                
            banca_actual = datos["banca"]["banca_actual"]
            if banca_actual < inversion_val:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": "Saldo insuficiente en banca."}).encode("utf-8"))
                return
                
            tkt_id = f"TKT-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            datos["apuestas_activas"].append({
                "ticket_id": tkt_id,
                "fecha_registro": datetime.datetime.now().isoformat(),
                "fecha_jornada": datetime.date.today().strftime("%Y-%m-%d"),
                "tipo_parley": tipo_parley,
                "cuota": cuota_val,
                "inversion": inversion_val,
                "retorno_potencial": round(inversion_val * cuota_val, 2),
                "estado": "Pendiente",
                "selecciones": [{
                    "partido": sel["partido"],
                    "pronostico": sel["pronostico"],
                    "cuota": float(sel["cuota"]),
                    "estado_seleccion": "Pendiente",
                    "resultado_partido": None
                } for sel in selecciones]
            })
            
            datos["banca"]["banca_actual"] = round(banca_actual - inversion_val, 2)
            datos["banca"]["dinero_en_juego"] = round(datos["banca"].get("dinero_en_juego", 0.0) + inversion_val, 2)
            
            banca_srv.guardar_historial(datos)
            
            tg = TelegramService()
            tg.enviar_reporte_banca(datos)
            tg.enviar_mensaje(f"🟢 *Nueva Apuesta Colocada!* 🟢\n"
                              f"━━━━━━━━━━━━━━━━━━━━━\n"
                              f"• *Ticket:* `{tkt_id}`\n"
                              f"• *Tipo:* `{tipo_parley}`\n"
                              f"• *Inversión:* `${inversion_val:.2f} USD`\n"
                              f"• *Cuota Total:* `{cuota_val:.2f}`\n"
                              f"• *Retorno Potencial:* `${(inversion_val * cuota_val):.2f} USD`\n"
                              f"━━━━━━━━━━━━━━━━━━━━━")
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "message": f"Apuesta colocada con éxito. Ticket: {tkt_id}", "ticket_id": tkt_id}).encode("utf-8"))
            return

        # API POST: Ajuste de banca (Depósitos / Retiros)
        if self.path == "/api/banca/ajustar":
            tipo = body.get("tipo")
            monto = body.get("monto")
            descripcion = body.get("descripcion")
            
            if tipo not in ["Deposito", "Retiro"] or not monto:
                self.send_error(400, "Se requiere 'tipo' (Deposito/Retiro) y 'monto' válido.")
                return
                
            try:
                monto_val = float(monto)
                if monto_val <= 0:
                    raise ValueError()
            except ValueError:
                self.send_error(400, "Monto debe ser un número positivo.")
                return
                
            banca_srv = GestorBancaService()
            try:
                datos = banca_srv.ajustar_banca(tipo, monto_val, descripcion)
                
                tg = TelegramService()
                tg.enviar_reporte_banca(datos)
                tg.enviar_mensaje(f"💵 *Ajuste de Banca Realizado* 💵\n"
                                  f"━━━━━━━━━━━━━━━━━━━━━\n"
                                  f"• *Tipo:* {tipo}\n"
                                  f"• *Monto:* ${monto_val:.2f} USD\n"
                                  f"• *Descripción:* {descripcion or 'N/A'}\n"
                                  f"• *Nuevo Saldo:* ${datos['banca']['banca_actual']:.2f} USD\n"
                                  f"━━━━━━━━━━━━━━━━━━━━━")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "message": f"Ajuste de banca de ${monto_val:.2f} completado con éxito.", "banca": datos["banca"]}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, f"Error al procesar el ajuste de banca: {str(e)}")
            return

        # API POST: Actualización de marcadores y resultados
        if self.path == "/api/actualizar_resultados":
            banca_srv = GestorBancaService()
            try:
                resumen = banca_srv.actualizar_resultados_deportivos()
                
                if resumen.get("apuestas_liquidadas"):
                    datos = banca_srv.cargar_historial()
                    tg = TelegramService()
                    tg.enviar_reporte_banca(datos)
                    tg.enviar_mensaje(f"🔄 *Resultados Deportivos Sincronizados* 🔄\n"
                                      f"━━━━━━━━━━━━━━━━━━━━━\n"
                                      f"• *Apuestas Liquidadas:* {', '.join(resumen['apuestas_liquidadas'])}\n"
                                      f"• *Predicciones Liquidadas:* {len(resumen['predicciones_liquidadas'])}\n"
                                      f"━━━━━━━━━━━━━━━━━━━━━")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "resumen": resumen}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, f"Error al actualizar resultados: {str(e)}")
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
                tg.enviar_reporte_banca(datos)

                
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

        # API POST: Limpiar Predicciones de IA de la Base de Datos
        if self.path == "/api/predicciones/limpiar":
            try:
                from sqlalchemy import delete
                from src.database.session import async_session_maker
                from src.database.models import PrediccionIA
                from src.services.gestor_banca_service import run_async
                
                async def limpiar_db():
                    async with async_session_maker() as session:
                        stmt = delete(PrediccionIA)
                        await session.execute(stmt)
                        await session.commit()
                
                run_async(limpiar_db())
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "message": "Todas las predicciones de IA han sido eliminadas con éxito."}).encode("utf-8"))
            except Exception as e:
                self.send_error(500, f"Error al eliminar predicciones de la base de datos: {str(e)}")
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



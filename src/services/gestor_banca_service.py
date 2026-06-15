#!/usr/bin/env python3
"""
📊 SERVICIO DE GESTIÓN DE BANCA Y APUESTAS (SQLAlchemy / PostgreSQL / SQLite)
Este servicio encapsula toda la lógica matemática de apuestas.
Está totalmente adaptado para almacenar datos en base de datos relacional
asíncrona mediante SQLAlchemy, conservando una interfaz síncrona mediante
un envoltorio (async-to-sync) para total compatibilidad con el código actual.
"""

import os
import json
import shutil
import sys
import asyncio
import datetime
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.config.settings import Settings
from src.database.session import async_session_maker, init_db
from src.database.models import Usuario, Evento, Ticket, TicketSeleccion, Transaccion

# Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')


def run_async(coro):
    """Ejecuta una corrutina de forma sincrónica sin importar si ya hay un loop de asyncio activo."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    
    # Si hay un loop corriendo en el hilo actual
    try:
        import nest_asyncio
        nest_asyncio.apply()
    except Exception:
        pass
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


class GestorBancaService:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.log_path = os.path.join(self.base_dir, "logs_apuestas.md")



    # --- WRAPPERS SÍNCRONOS PÚBLICOS ---
    def cargar_historial(self):
        return run_async(self.cargar_historial_async())

    def guardar_historial(self, datos):
        return run_async(self.guardar_historial_async(datos))

    def asentar_ticket(self, datos, ticket_id, resultados_selecciones):
        """Asienta un ticket evaluando los resultados de cada selección."""
        # Operamos localmente sobre el dict 'datos' en memoria para mantener compatibilidad
        banca = datos.get("banca", {})
        activas = datos.get("apuestas_activas", [])
        archivadas = datos.get("apuestas_archivadas", [])
        
        ticket_target = None
        for tkt in activas:
            if tkt.get("ticket_id") == ticket_id:
                ticket_target = tkt
                break
                
        if not ticket_target:
            return False
            
        cuota_final = 1.0
        ticket_perdido = False
        todo_anulado = True
        
        for sel in ticket_target.get("selecciones", []):
            partido = sel.get("partido")
            res = resultados_selecciones.get(partido, {})
            
            estado = res.get("estado", "Anulado")
            marcador = res.get("marcador")
            
            sel["estado_seleccion"] = estado
            if marcador:
                sel["resultado_partido"] = marcador
                
            if estado == "Ganado":
                cuota_final *= sel.get("cuota", 1.0)
                todo_anulado = False
            elif estado == "Perdido":
                ticket_perdido = True
                todo_anulado = False
            elif estado == "Anulado":
                cuota_final *= 1.0
                
        # Estado final del ticket
        if ticket_perdido:
            ticket_target["estado"] = "Perdida"
            ticket_target["cuota_final_asentada"] = 0.0
            ticket_target["retorno_realizado"] = 0.0
        elif todo_anulado:
            ticket_target["estado"] = "Anulada"
            ticket_target["cuota_final_asentada"] = 1.0
            ticket_target["retorno_realizado"] = ticket_target.get("inversion", 0.0)
            banca["banca_actual"] = round(banca.get("banca_actual", 10.0) + ticket_target.get("inversion", 0.0), 2)
        else:
            ticket_target["estado"] = "Ganada"
            ticket_target["cuota_final_asentada"] = round(cuota_final, 2)
            retorno = round(ticket_target.get("inversion", 0.0) * cuota_final, 2)
            ticket_target["retorno_realizado"] = retorno
            banca["banca_actual"] = round(banca.get("banca_actual", 10.0) + retorno, 2)
            
        # Mover de activas a archivadas
        activas.remove(ticket_target)
        archivadas.append(ticket_target)
        
        datos["apuestas_activas"] = activas
        datos["apuestas_archivadas"] = archivadas
        
        self.calcular_estadisticas_globales(datos)
        return True

    def asentar_ticket_directo(self, datos, ticket_id, estado_final):
        """Asienta un ticket de forma directa (Ganada, Perdida o Anulada) recalculando la banca."""
        banca = datos.get("banca", {})
        activas = datos.get("apuestas_activas", [])
        archivadas = datos.get("apuestas_archivadas", [])
        
        ticket_target = None
        for tkt in activas:
            if tkt.get("ticket_id") == ticket_id:
                ticket_target = tkt
                break
                
        if not ticket_target:
            return False
            
        inversion = ticket_target.get("inversion", 0.0)
        cuota = ticket_target.get("cuota", 1.0)
        
        ticket_target["estado"] = estado_final
        
        if estado_final == "Ganada":
            ticket_target["cuota_final_asentada"] = cuota
            retorno = round(inversion * cuota, 2)
            ticket_target["retorno_realizado"] = retorno
            banca["banca_actual"] = round(banca.get("banca_actual", 10.0) + retorno, 2)
            
            # Sincronizar selecciones
            for sel in ticket_target.get("selecciones", []):
                sel["estado_seleccion"] = "Ganado"
                
        elif estado_final == "Perdida":
            ticket_target["cuota_final_asentada"] = 0.0
            ticket_target["retorno_realizado"] = 0.0
            
            # Sincronizar selecciones
            for sel in ticket_target.get("selecciones", []):
                sel["estado_seleccion"] = "Perdido"
                
        elif estado_final == "Anulada":
            ticket_target["cuota_final_asentada"] = 1.0
            ticket_target["retorno_realizado"] = inversion
            banca["banca_actual"] = round(banca.get("banca_actual", 10.0) + inversion, 2)
            
            # Sincronizar selecciones
            for sel in ticket_target.get("selecciones", []):
                sel["estado_seleccion"] = "Anulado"
                
        # Mover de activas a archivadas
        activas.remove(ticket_target)
        archivadas.append(ticket_target)
        
        datos["apuestas_activas"] = activas
        datos["apuestas_archivadas"] = archivadas
        
        self.calcular_estadisticas_globales(datos)
        return True

    def calcular_estadisticas_globales(self, datos):
        """Recalcula de forma matemática exacta el ROI y el Yield en memoria."""
        banca = datos.get("banca", {})
        archivadas = datos.get("apuestas_archivadas", [])
        
        inversion_total_settled = 0.0
        retorno_total_settled = 0.0
        ganadas = 0
        perdidas = 0
        anuladas = 0
        
        for tkt in archivadas:
            child_estado = tkt.get("estado")
            inversion = tkt.get("inversion", 0.0)
            retorno = tkt.get("retorno_realizado", 0.0)
            
            inversion_total_settled += inversion
            retorno_total_settled += retorno
            
            if child_estado == "Ganada":
                ganadas += 1
            elif child_estado == "Perdida":
                perdidas += 1
            elif child_estado == "Anulada":
                anuladas += 1
                
        # Calcular Yield
        if inversion_total_settled > 0:
            yield_pct = ((retorno_total_settled - inversion_total_settled) / inversion_total_settled) * 100
            yield_str = f"{yield_pct:+.2f}%"
        else:
            yield_str = "0.0%"
            
        # Calcular ROI
        banca_inicial = banca.get("banca_inicial", 10.0)
        banca_actual = banca.get("banca_actual", 10.0)
        roi_pct = ((banca_actual - banca_inicial) / banca_inicial) * 100
        roi_str = f"{roi_pct:+.2f}%"
        
        # Sincronizar stats
        stats = datos.get("estadisticas_globales", {})
        stats["total_apuestas_realizadas"] = len(archivadas) + len(datos.get("apuestas_activas", []))
        stats["apuestas_ganadas"] = ganadas
        stats["apuestas_perdidas"] = perdidas
        stats["apuestas_anuladas"] = anuladas
        stats["rendimiento_yield"] = yield_str
        stats["roi"] = roi_str
        
        # Dinero en juego
        activas = datos.get("apuestas_activas", [])
        banca["dinero_en_juego"] = sum(tkt.get("inversion", 0.0) for tkt in activas)

    # --- IMPLEMENTACIÓN DE OPERACIONES ASÍNCRONAS EN BASE DE DATOS ---
    async def cargar_historial_async(self):
        """Consulta la base de datos relacional y formatea la salida como el JSON histórico."""
        async with async_session_maker() as session:
            user_id = int(Settings.TELEGRAM_CHAT_ID or 1234567)
            
            # Cargar o inicializar el usuario
            result = await session.execute(select(Usuario).where(Usuario.id == user_id))
            usuario = result.scalar_one_or_none()
            if not usuario:
                usuario = Usuario(id=user_id, username="admin", saldo=Decimal("10.00"))
                session.add(usuario)
                trans = Transaccion(
                    usuario_id=user_id,
                    tipo="Deposito",
                    monto=Decimal("10.00"),
                    descripcion="Carga inicial de banca automática"
                )
                session.add(trans)
                await session.commit()
                await session.refresh(usuario)
                
            # Consultar todos los tickets con sus selecciones y eventos
            stmt = select(Ticket).where(Ticket.usuario_id == user_id).options(
                selectinload(Ticket.selecciones).selectinload(TicketSeleccion.evento)
            )
            res_tickets = await session.execute(stmt)
            tickets = res_tickets.scalars().all()
            
            apuestas_activas = []
            apuestas_archivadas = []
            
            for tkt in tickets:
                selecciones_json = []
                for sel in tkt.selecciones:
                    selecciones_json.append({
                        "partido": sel.evento.nombre,
                        "pronostico": sel.pronostico,
                        "cuota": float(sel.cuota),
                        "estado_seleccion": sel.estado,
                        "resultado_partido": sel.evento.resultado_final
                    })
                    
                tkt_json = {
                    "ticket_id": tkt.ticket_id,
                    "fecha_registro": tkt.fecha_registro.isoformat(),
                    "fecha_jornada": tkt.fecha_registro.strftime("%Y-%m-%d"),
                    "tipo_parley": tkt.tipo_ticket,
                    "cuota": float(tkt.cuota_total),
                    "inversion": float(tkt.monto_apostado),
                    "retorno_potencial": float(tkt.retorno_potencial),
                    "estado": tkt.estado,
                    "selecciones": selecciones_json
                }
                
                if tkt.estado != "Pendiente":
                    if tkt.estado == "Ganada":
                        tkt_json["cuota_final_asentada"] = float(tkt.cuota_total)
                        tkt_json["retorno_realizado"] = float(tkt.retorno_potencial)
                    elif tkt.estado == "Anulada":
                        tkt_json["cuota_final_asentada"] = 1.0
                        tkt_json["retorno_realizado"] = float(tkt.monto_apostado)
                    else: # Perdida
                        tkt_json["cuota_final_asentada"] = 0.0
                        tkt_json["retorno_realizado"] = 0.0
                    apuestas_archivadas.append(tkt_json)
                else:
                    apuestas_activas.append(tkt_json)
                    
            banca = {
                "moneda": "USD",
                "banca_inicial": 10.0,
                "banca_actual": float(usuario.saldo),
                "dinero_en_juego": sum(tkt["inversion"] for tkt in apuestas_activas)
            }
            
            # Recalcular estadísticas
            stats = self.calcular_estadisticas_globales_dict(banca, apuestas_archivadas, len(tickets))
            
            # Cargar predicciones de IA históricas (tabla predicciones_ia)
            from src.database.models import PrediccionIA
            stmt_preds = select(PrediccionIA).order_by(PrediccionIA.fecha.desc()).limit(30)
            res_preds = await session.execute(stmt_preds)
            preds = res_preds.scalars().all()
            predicciones_json = []
            for p in preds:
                predicciones_json.append({
                    "id": p.id,
                    "fecha": p.fecha.isoformat(),
                    "partido": p.partido,
                    "pronostico": p.pronostico,
                    "cuota": float(p.cuota),
                    "probabilidad_estadistica": float(p.probabilidad_estadistica),
                    "probabilidad_implicita": float(p.probabilidad_implicita),
                    "valor": p.valor,
                    "tipo_parley": p.tipo_parley,
                    "estado": p.estado,
                    "resultado_partido": p.resultado_partido
                })
            
            return {
                "banca": banca,
                "estadisticas_globales": stats,
                "apuestas_activas": apuestas_activas,
                "apuestas_archivadas": apuestas_archivadas,
                "predicciones_ia": predicciones_json
            }


    def calcular_estadisticas_globales_dict(self, banca, archivadas, total_len):
        inversion_total_settled = 0.0
        retorno_total_settled = 0.0
        ganadas = 0
        perdidas = 0
        anuladas = 0
        
        for tkt in archivadas:
            child_estado = tkt.get("estado")
            inversion = tkt.get("inversion", 0.0)
            retorno = tkt.get("retorno_realizado", 0.0)
            
            inversion_total_settled += inversion
            retorno_total_settled += retorno
            
            if child_estado == "Ganada":
                ganadas += 1
            elif child_estado == "Perdida":
                perdidas += 1
            elif child_estado == "Anulada":
                anuladas += 1
                
        if inversion_total_settled > 0:
            yield_pct = ((retorno_total_settled - inversion_total_settled) / inversion_total_settled) * 100
            yield_str = f"{yield_pct:+.2f}%"
        else:
            yield_str = "0.0%"
            
        banca_inicial = banca.get("banca_inicial", 10.0)
        banca_actual = banca.get("banca_actual", 10.0)
        roi_pct = ((banca_actual - banca_inicial) / banca_inicial) * 100
        roi_str = f"{roi_pct:+.2f}%"
        
        return {
            "total_apuestas_realizadas": total_len,
            "apuestas_ganadas": ganadas,
            "apuestas_perdidas": perdidas,
            "apuestas_anuladas": anuladas,
            "rendimiento_yield": yield_str,
            "roi": roi_str
        }

    async def guardar_historial_async(self, datos):
        """Sincroniza el diccionario del historial de apuestas con las tablas relacionales de la DB."""
        async with async_session_maker() as session:
            user_id = int(Settings.TELEGRAM_CHAT_ID or 1234567)
            
            # Cargar usuario
            result = await session.execute(select(Usuario).where(Usuario.id == user_id))
            usuario = result.scalar_one_or_none()
            if not usuario:
                usuario = Usuario(id=user_id, username="admin", saldo=Decimal("10.00"))
                session.add(usuario)
                await session.flush()
                
            # Actualizar saldo del usuario
            banca_actual = Decimal(f"{datos['banca']['banca_actual']:.2f}")
            if usuario.saldo != banca_actual:
                usuario.saldo = banca_actual
                
            # Combinar activas y archivadas para sincronizar en lote
            todas_las_apuestas = datos.get("apuestas_activas", []) + datos.get("apuestas_archivadas", [])
            
            for tkt_dict in todas_las_apuestas:
                t_id = tkt_dict["ticket_id"]
                
                # Buscar ticket en DB
                tkt_result = await session.execute(select(Ticket).where(Ticket.ticket_id == t_id))
                tkt = tkt_result.scalar_one_or_none()
                
                if not tkt:
                    # Crear nuevo ticket en DB
                    tkt = Ticket(
                        ticket_id=t_id,
                        usuario_id=user_id,
                        tipo_ticket=tkt_dict["tipo_parley"],
                        cuota_total=Decimal(str(tkt_dict["cuota"])),
                        monto_apostado=Decimal(str(tkt_dict["inversion"])),
                        retorno_potencial=Decimal(str(tkt_dict["retorno_potencial"])),
                        estado=tkt_dict["estado"]
                    )
                    session.add(tkt)
                    await session.flush()
                    
                    # Transacción de descuento
                    trans_ap = Transaccion(
                        usuario_id=user_id,
                        tipo="Apuesta",
                        monto=-Decimal(str(tkt_dict["inversion"])),
                        descripcion=f"Colocación de ticket {t_id}"
                    )
                    session.add(trans_ap)
                    
                    # Registrar selecciones y crear eventos asociados
                    for sel_dict in tkt_dict.get("selecciones", []):
                        ev_name = sel_dict["partido"]
                        
                        ev_result = await session.execute(select(Evento).where(Evento.nombre == ev_name))
                        evento = ev_result.scalar_one_or_none()
                        
                        if not evento:
                            evento = Evento(
                                nombre=ev_name,
                                estado="Pendiente" if tkt_dict["estado"] == "Pendiente" else "Finalizado",
                                resultado_final=sel_dict.get("resultado_partido")
                            )
                            session.add(evento)
                            await session.flush()
                            
                        sel = TicketSeleccion(
                            ticket_id=tkt.id,
                            evento_id=evento.id,
                            pronostico=sel_dict["pronostico"],
                            cuota=Decimal(str(sel_dict["cuota"])),
                            estado=sel_dict["estado_seleccion"]
                        )
                        session.add(sel)
                else:
                    # El ticket ya existe, verificar si cambió su estado (liquidación)
                    nuevo_estado = tkt_dict["estado"]
                    if tkt.estado != nuevo_estado:
                        tkt.estado = nuevo_estado
                        
                        # Transacciones de ganancias o devoluciones
                        if nuevo_estado == "Ganada":
                            ret_real = Decimal(str(tkt_dict.get("retorno_realizado", 0.0)))
                            trans_w = Transaccion(
                                usuario_id=user_id,
                                tipo="Premio",
                                monto=ret_real,
                                descripcion=f"Cobro de premio por ticket {t_id}"
                            )
                            session.add(trans_w)
                        elif nuevo_estado == "Anulada":
                            ret_real = Decimal(str(tkt_dict.get("retorno_realizado", tkt_dict["inversion"])))
                            trans_r = Transaccion(
                                usuario_id=user_id,
                                tipo="Reembolso",
                                monto=ret_real,
                                descripcion=f"Reembolso por anulación de ticket {t_id}"
                            )
                            session.add(trans_r)
                            
                        # Cargar y actualizar selecciones asociadas
                        tkt_full_res = await session.execute(
                            select(Ticket).where(Ticket.id == tkt.id).options(
                                selectinload(Ticket.selecciones).selectinload(TicketSeleccion.evento)
                            )
                        )
                        tkt_full = tkt_full_res.scalar_one()
                        
                        for db_sel in tkt_full.selecciones:
                            for dict_sel in tkt_dict.get("selecciones", []):
                                if db_sel.evento.nombre == dict_sel["partido"]:
                                    db_sel.estado = dict_sel["estado_seleccion"]
                                    if dict_sel.get("resultado_partido"):
                                        db_sel.evento.resultado_final = dict_sel["resultado_partido"]
                                        db_sel.evento.estado = "Finalizado"
                                    break
            await session.commit()
            
        # Exportar bitácora en Markdown
        self.exportar_bitacora(datos)
        return True

    def exportar_bitacora(self, datos):
        """Genera un archivo legible en Markdown con el historial de apuestas y estadísticas."""
        banca = datos.get("banca", {})
        stats = datos.get("estadisticas_globales", {})
        archivadas = datos.get("apuestas_archivadas", [])
        
        md = "# 📋 Bitácora Histórica de Apuestas - Reto Mundial 2026\n\n"
        md += "## 📊 Estadísticas Consolidadas\n\n"
        md += f"*   **Banca Inicial:** ${banca.get('banca_inicial', 10.0):.2f} USD\n"
        md += f"*   **Banca Actual:** ${banca.get('banca_actual', 10.0):.2f} USD\n"
        md += f"*   **Dinero en Juego:** ${banca.get('dinero_en_juego', 0.0):.2f} USD\n"
        md += f"*   **Yield / Rentabilidad:** `{stats.get('rendimiento_yield', '0.0%')}`\n"
        md += f"*   **ROI:** `{stats.get('roi', '0.0%')}`\n"
        md += f"*   **Efectividad (Ganadas/Perdidas/Anuladas):** {stats.get('apuestas_ganadas', 0)} ✅ / {stats.get('apuestas_perdidas', 0)} ❌ / {stats.get('apuestas_anuladas', 0)} 🔄\n\n"
        
        md += "## 🎫 Historial de Tickets Asentados\n\n"
        md += "| ID Ticket | Fecha Jornada | Tipo | Inversión | Cuota Asentada | Retorno | Estado |\n"
        md += "| :--- | :---: | :--- | :---: | :---: | :---: | :---: |\n"
        
        for tkt in sorted(archivadas, key=lambda x: x.get("fecha_jornada", ""), reverse=True):
            estado = tkt.get("estado")
            emoji = "✅ Ganada" if estado == "Ganada" else ("❌ Perdida" if estado == "Perdida" else "🔄 Anulada")
            md += f"| `{tkt.get('ticket_id')}` | {tkt.get('fecha_jornada')} | {tkt.get('tipo_parley')} | ${tkt.get('inversion', 0.0):.2f} USD | {tkt.get('cuota_final_asentada', 0.0)} | ${tkt.get('retorno_realizado', 0.0):.2f} USD | {emoji} |\n"
            
        md += "\n\n### 📝 Detalle de Selecciones por Ticket\n\n"
        for tkt in sorted(archivadas, key=lambda x: x.get("fecha_jornada", ""), reverse=True):
            md += f"#### Ticket `{tkt.get('ticket_id')}` ({tkt.get('tipo_parley')}) — Estado: {tkt.get('estado')}\n"
            md += f"*   **Cuota Original:** {tkt.get('cuota')} | **Cuota Asentada:** {tkt.get('cuota_final_asentada')}\n"
            md += "*   **Selecciones:**\n"
            for sel in tkt.get("selecciones", []):
                estado_sel = sel.get("estado_seleccion")
                emoji_sel = "✅" if estado_sel == "Ganado" else ("❌" if estado_sel == "Perdido" else "🔄")
                marcador = f" (Marcador: {sel.get('resultado_partido')})" if sel.get("resultado_partido") else ""
                md += f"    * {emoji_sel} _{sel.get('partido')}_ — **{sel.get('pronostico')}** (Cuota: {sel.get('cuota')}){marcador}\n"
            md += "\n---\n\n"
            
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(md)

    # --- MÉTODOS DE AJUSTE DE BANCA Y ACTUALIZACIÓN DE RESULTADOS ---
    async def ajustar_banca_async(self, tipo, monto, descripcion):
        """Deposita o retira fondos de la banca del usuario en base de datos."""
        from decimal import Decimal
        monto_dec = Decimal(str(monto))
        if tipo == "Retiro":
            monto_dec = -monto_dec
            
        async with async_session_maker() as session:
            user_id = int(Settings.TELEGRAM_CHAT_ID or 1234567)
            result = await session.execute(select(Usuario).where(Usuario.id == user_id))
            usuario = result.scalar_one_or_none()
            if not usuario:
                usuario = Usuario(id=user_id, username="admin", saldo=Decimal("10.00"))
                session.add(usuario)
                await session.flush()
                
            usuario.saldo = round(usuario.saldo + monto_dec, 2)
            
            # Guardar transacción
            trans = Transaccion(
                usuario_id=user_id,
                tipo=tipo,
                monto=monto_dec,
                descripcion=descripcion or f"Ajuste de banca: {tipo}"
            )
            session.add(trans)
            await session.commit()
            
            # Recargar y guardar bitácora
            datos = await self.cargar_historial_async()
            self.exportar_bitacora(datos)
            return datos
            
    def ajustar_banca(self, tipo, monto, descripcion):
        return run_async(self.ajustar_banca_async(tipo, monto, descripcion))

    async def actualizar_resultados_deportivos_async(self):
        """
        Consulta la API de resultados deportivos y liquida tanto las apuestas activas
        como las predicciones de IA pendientes.
        """
        from src.services.resultados_api_service import ResultadosAPIService
        api_srv = ResultadosAPIService()
        
        resumen = {
            "apuestas_liquidadas": [],
            "predicciones_liquidadas": [],
            "errores": []
        }
        
        datos = await self.cargar_historial_async()
        activas = list(datos.get("apuestas_activas", []))
        
        # 1. Liquidar apuestas activas
        for tkt in activas:
            tkt_id = tkt.get("ticket_id")
            resultados_tkt = {}
            error_obtencion = False
            
            for sel in tkt.get("selecciones", []):
                partido = sel.get("partido")
                if " vs. " in partido:
                    home, away = partido.split(" vs. ", 1)
                elif " vs " in partido:
                    home, away = partido.split(" vs ", 1)
                else:
                    home, away = partido, ""
                    
                g_home, g_away, finalizado = api_srv.conseguir_marcador(home, away)
                if finalizado and g_home is not None and g_away is not None:
                    marcador_str = f"{g_home}-{g_away}"
                    estado_sel = evaluar_pronostico(sel.get("pronostico"), home, away, g_home, g_away)
                    resultados_tkt[partido] = {
                        "estado": estado_sel,
                        "marcador": marcador_str
                    }
                else:
                    error_obtencion = True
                    break
                    
            if not error_obtencion:
                exito = self.asentar_ticket(datos, tkt_id, resultados_tkt)
                if exito:
                    resumen["apuestas_liquidadas"].append(tkt_id)
                    
        # Guardar cambios financieros si hubo liquidación
        if resumen["apuestas_liquidadas"]:
            await self.guardar_historial_async(datos)
            
        # 2. Liquidar predicciones de IA pendientes
        from src.database.models import PrediccionIA
        async with async_session_maker() as session:
            stmt = select(PrediccionIA).where(PrediccionIA.estado == "Pendiente")
            res_preds = await session.execute(stmt)
            pending_preds = res_preds.scalars().all()
            
            for pred in pending_preds:
                partido = pred.partido
                if " vs. " in partido:
                    home, away = partido.split(" vs. ", 1)
                elif " vs " in partido:
                    home, away = partido.split(" vs ", 1)
                else:
                    home, away = partido, ""
                    
                g_home, g_away, finalizado = api_srv.conseguir_marcador(home, away)
                if finalizado and g_home is not None and g_away is not None:
                    marcador_str = f"{g_home}-{g_away}"
                    estado_pred = evaluar_pronostico(pred.pronostico, home, away, g_home, g_away)
                    
                    pred.estado = "Ganado" if estado_pred == "Ganado" else ("Perdido" if estado_pred == "Perdido" else "Anulado")
                    pred.resultado_partido = marcador_str
                    resumen["predicciones_liquidadas"].append(f"{pred.partido} ({pred.pronostico}) -> {pred.estado}")
            await session.commit()
            
        return resumen

    def actualizar_resultados_deportivos(self):
        return run_async(self.actualizar_resultados_deportivos_async())


def evaluar_pronostico(pronostico, home_name, away_name, g_home, g_away):
    """
    Evalúa si un pronóstico se cumple según las estadísticas de goles.
    Retorna: 'Ganado', 'Perdido', o 'Anulado'.
    """
    pronostico_lower = pronostico.lower()
    
    # 1. Caso: Más de X goles (Overs)
    if "más de" in pronostico_lower or "over" in pronostico_lower:
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
        es_home = False
        es_away = False
        if home_name.lower() in pronostico_lower:
            es_home = True
        elif away_name.lower() in pronostico_lower:
            es_away = True
            
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
            return "Anulado"
            
        if diff > 0:
            return "Ganado"
        elif diff == 0:
            return "Anulado"
        else:
            return "Perdido"

    # 4. Caso: Doble Oportunidad (ej: Irán o Empate)
    if "o empate" in pronostico_lower or "doble oportunidad" in pronostico_lower:
        if "empate" in pronostico_lower:
            if home_name.lower() in pronostico_lower:
                return "Ganado" if g_home >= g_away else "Perdido"
            elif away_name.lower() in pronostico_lower:
                return "Ganado" if g_away >= g_home else "Perdido"

    # 5. Caso: Victoria directa (1X2)
    if home_name.lower() in pronostico_lower:
        return "Ganado" if g_home > g_away else "Perdido"
    elif away_name.lower() in pronostico_lower:
        return "Ganado" if g_away > g_home else "Perdido"
        
    return "Anulado"


#!/usr/bin/env python3
"""
🎛️ CONTROLADOR CENTRAL DE TELEGRAM (SOLID - ROUTER)
Este archivo se encarga de enrutar los eventos, comandos y callbacks de Telegram.
Implementa el Panel de Control Administrativo (Opción A) mediante Botoneras Inline
y un Creador de Picks Conversacional paso a paso.
"""

import os
import json
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.commands.start import StartCommand
from src.commands.analisis import AnalisisCommand
from src.services.gestor_banca_service import GestorBancaService

from src.config.settings import Settings

class TelegramController:
    def __init__(self, bot):
        self.bot = bot
        self.commands = {
            "start": StartCommand(),
            "analisis": AnalisisCommand()
        }
        # Caché temporal para el creador de picks conversacional
        self.creacion_estado = {}
        self._configurar_comandos()
        self._registrar_rutas()

    def _es_admin(self, chat_id):
        """Comprueba si el chat_id corresponde a un administrador whitelisteado."""
        return chat_id in Settings.TELEGRAM_ADMIN_IDS

    def _configurar_comandos(self):
        """Configura dinámicamente el menú de comandos en Telegram según el rol del usuario."""
        try:
            from telebot.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
            
            # Comandos para Amigos / Públicos
            comandos_publicos = [
                BotCommand("start", "Ver bienvenida y ayuda"),
                BotCommand("analisis", "Análisis de IA para un equipo"),
                BotCommand("banca", "Ver rendimiento de banca"),
                BotCommand("picks", "Ver combinadas oficiales de hoy")
            ]
            self.bot.set_my_commands(comandos_publicos, scope=BotCommandScopeDefault())
            
            # Comandos para Administradores
            comandos_admin = comandos_publicos + [
                BotCommand("admin", "Panel para liquidar apuestas"),
                BotCommand("crear_picks", "Registrar picks manualmente"),
                BotCommand("generar_picks", "Generar picks con agentes IA")
            ]
            for admin_id in Settings.TELEGRAM_ADMIN_IDS:
                try:
                    self.bot.set_my_commands(comandos_admin, scope=BotCommandScopeChat(admin_id))
                except Exception as e_cmd:
                    print(f"⚠️ TelegramController: No se pudo configurar comandos para admin_id={admin_id}: {e_cmd}")
        except Exception as e:
            print(f"⚠️ TelegramController: Error configurando comandos en telebot: {e}")


    def _registrar_rutas(self):
        """Asocia los decoradores de pyTelegramBotAPI con la lógica de los comandos."""
        
        # --- COMANDOS ESTÁNDAR ---
        @self.bot.message_handler(commands=["start"])
        def handle_start(message):
            print(f"🎛️ TelegramController: Recibido comando /start de chat_id={message.chat.id}")
            self.commands["start"].ejecutar(self.bot, message, [])

        @self.bot.message_handler(commands=["analisis"])
        def handle_analisis(message):
            partes = message.text.split()
            args = partes[1:] if len(partes) > 1 else []
            print(f"🎛️ TelegramController: Recibido comando /analisis con args={args}")
            self.commands["analisis"].ejecutar(self.bot, message, args)

        # --- COMANDOS ADMINISTRATIVOS (BOTONERA INLINE) ---
        @self.bot.message_handler(commands=["liquidar", "admin"])
        def handle_liquidar_command(message):
            chat_id = message.chat.id
            if not self._es_admin(chat_id):
                self.bot.send_message(chat_id, "⚠️ Este comando es de acceso exclusivo para administradores.")
                return
            print(f"🎛️ TelegramController: Comando /liquidar recibido de chat_id={chat_id}")
            self.enviar_botonera_liquidar(chat_id)

        # --- CREADOR DE PICKS CONVERSACIONAL ---
        @self.bot.message_handler(commands=["crear_picks"])
        def handle_crear_picks(message):
            chat_id = message.chat.id
            if not self._es_admin(chat_id):
                self.bot.send_message(chat_id, "⚠️ Este comando es de acceso exclusivo para administradores.")
                return
            print(f"🎛️ TelegramController: Iniciando creador de picks conversacional en chat_id={chat_id}")
            
            # Inicializar estructura temporal del parley en memoria
            self.creacion_estado[chat_id] = {
                "fecha": "",
                "descripcion": "",
                "tipo_actual": "seguro",
                "parley_seguro": {
                    "nombre": "Combinada Segura",
                    "tipo_riesgo": "Bajo",
                    "cuota_total_estimada": 1.0,
                    "stake_sugerido": "5/10 (Unidades)",
                    "probabilidad_implicta_cuota": "0.0%",
                    "probabilidad_estadistica_combinada": "0.0%",
                    "selecciones": []
                },
                "parley_arriesgado": {
                    "nombre": "Combinada de Alto Valor",
                    "tipo_riesgo": "Alto",
                    "cuota_total_estimada": 1.0,
                    "stake_sugerido": "1/10 (Unidades)",
                    "probabilidad_implicta_cuota": "0.0%",
                    "probabilidad_estadistica_combinada": "0.0%",
                    "selecciones": []
                }
            }
            
            msg = (
                "📅 *Creador de Picks Conversacional*\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Por favor, ingresa la fecha para esta jornada de apuestas en formato `AAAA-MM-DD` "
                "(Ejemplo: `2026-06-15`).\n\n"
                "_(Responde con la palabra 'hoy' para auto-configurar la fecha del servidor)_"
            )
            sent_msg = self.bot.send_message(chat_id, msg, parse_mode="Markdown")
            self.bot.register_next_step_handler(sent_msg, self._step_fecha)

        # --- COMANDOS PÚBLICOS PARA AMIGOS (Fase 1/2) ---
        @self.bot.message_handler(commands=["banca"])
        def handle_banca(message):
            chat_id = message.chat.id
            print(f"🎛️ TelegramController: Comando /banca recibido de chat_id={chat_id}")
            banca_srv = GestorBancaService()
            datos = banca_srv.cargar_historial()
            if not datos:
                self.bot.send_message(chat_id, "❌ Error al cargar el historial de banca.")
                return
            
            b = datos.get("banca", {})
            s = datos.get("estadisticas_globales", {})
            
            reporte = (
                "🏆 *Reto de Banca Mundial 2026*\n"
                "━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💵 *Banca Inicial:* `${b.get('banca_inicial', 10.0):.2f} USD`\n"
                f"💰 *Banca Disponible:* `${b.get('banca_actual', 10.0):.2f} USD`\n"
                f"🔥 *Dinero en Juego:* `${b.get('dinero_en_juego', 0.0):.2f} USD`\n\n"
                f"📈 *Yield Acumulado:* `{s.get('rendimiento_yield', '0.0%')}`\n"
                f"🎯 *ROI Actual:* `{s.get('roi', '0.0%')}`\n"
                f"📊 *Efectividad:* {s.get('apuestas_ganadas', 0)} ✅ | {s.get('apuestas_perdidas', 0)} ❌ | {s.get('apuestas_anuladas', 0)} 🔄\n\n"
                f"💡 _Nota: Este balance es público y compartido con mis amigos del reto._"
            )
            self.bot.send_message(chat_id, reporte, parse_mode="Markdown")

        @self.bot.message_handler(commands=["picks"])
        def handle_picks(message):
            chat_id = message.chat.id
            print(f"🎛️ TelegramController: Comando /picks recibido de chat_id={chat_id}")
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            JUGADAS_PATH = os.path.join(base_dir, "jugadas_lunes_15.json")
            
            if not os.path.exists(JUGADAS_PATH):
                self.bot.send_message(chat_id, "💡 *No hay picks oficiales registrados para la jornada de hoy todavía.*", parse_mode="Markdown")
                return
                
            try:
                with open(JUGADAS_PATH, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                
                fecha = datos.get("fecha_jornada", "N/A")
                desc = datos.get("descripcion", "")
                parleys = datos.get("parleys", {})
                
                reporte = (
                    f"📅 *Combinadas Oficiales:* `{fecha}`\n"
                    f"📝 *Detalle:* _{desc}_\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                )
                
                for p_key, p_val in parleys.items():
                    nombre = p_val.get("nombre", p_key)
                    cuota = p_val.get("cuota_total_estimada", 1.0)
                    stake = p_val.get("stake_sugerido", "1/10")
                    prob = p_val.get("probabilidad_estadistica_combinada", "N/A")
                    
                    reporte += f"🔥 *{nombre.upper()}* (Cuota: *@{cuota:.2f}* | Stake: `{stake}`)\n"
                    reporte += f"📈 Probabilidad IA: `{prob}`\n"
                    for sel in p_val.get("selecciones", []):
                        reporte += f"  • _{sel.get('partido')}_ — *{sel.get('pronostico')}* (@{sel.get('cuota')})\n"
                    reporte += "\n"
                    
                self.bot.send_message(chat_id, reporte, parse_mode="Markdown")
            except Exception as e:
                print(f"Error cargando picks para telegram: {e}")
                self.bot.send_message(chat_id, "❌ Error al leer las combinadas de hoy.")

        # --- COMANDO DE GENERACIÓN AUTOMÁTICA POR AGENTES IA ---
        @self.bot.message_handler(commands=["generar_picks"])
        def handle_generar_picks(message):
            chat_id = message.chat.id
            if not self._es_admin(chat_id):
                self.bot.send_message(chat_id, "⚠️ Este comando es de acceso exclusivo para administradores.")
                return
                
            print(f"🎛️ TelegramController: Comando /generar_picks recibido de chat_id={chat_id}")
            loading_msg = self.bot.send_message(chat_id, "🤖 *Iniciando el equipo de agentes deportivos de IA para generar los picks de hoy...*", parse_mode="Markdown")
            
            try:
                from src.services.picks_generator_service import PicksGeneratorService
                gen_srv = PicksGeneratorService()
                exito, respuesta = gen_srv.generar_picks_ia()
                
                if exito:
                    self.bot.edit_message_text(chat_id=chat_id, message_id=loading_msg.message_id, text=f"✅ *{respuesta}*", parse_mode="Markdown")
                else:
                    self.bot.edit_message_text(chat_id=chat_id, message_id=loading_msg.message_id, text=f"❌ Error al generar picks: {respuesta}")
            except Exception as e:
                print(f"Error generando picks por IA: {e}")
                self.bot.edit_message_text(chat_id=chat_id, message_id=loading_msg.message_id, text=f"❌ Error crítico: {str(e)}")

        # --- CALLBACK QUERY HANDLER (CLICS EN BOTONES INLINE) ---
        @self.bot.callback_query_handler(func=lambda call: True)
        def handle_callback_query(call):
            chat_id = call.message.chat.id
            message_id = call.message.message_id
            data = call.data
            
            # Verificar Whitelist de Administradores para callbacks
            if data.startswith("liquidar_tkt:") or data.startswith("settle_tkt:") or data in ["publicar_picks", "cancelar_picks", "admin_list"]:
                if not self._es_admin(chat_id):
                    self.bot.answer_callback_query(call.id, "⚠️ No tienes permisos de administrador para realizar esta acción.", show_alert=True)
                    return
            
            banca_srv = GestorBancaService()
            datos = banca_srv.cargar_historial()
            
            if data == "admin_list":
                self.enviar_botonera_liquidar(chat_id, message_id)
                
            elif data.startswith("liquidar_tkt:"):
                tkt_id = data.split(":", 1)[1]
                # Mostrar estados de liquidación directa
                markup = InlineKeyboardMarkup()
                markup.row(
                    InlineKeyboardButton("✅ Ganado", callback_data=f"settle_tkt:{tkt_id}:Ganada"),
                    InlineKeyboardButton("❌ Perdido", callback_data=f"settle_tkt:{tkt_id}:Perdida"),
                    InlineKeyboardButton("🔄 Anulado", callback_data=f"settle_tkt:{tkt_id}:Anulada")
                )
                markup.row(InlineKeyboardButton("🔙 Volver al Listado", callback_data="admin_list"))
                
                self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🎫 *Asentamiento Directo - Ticket:* `{tkt_id}`\n\nSelecciona el resultado final de la apuesta:",
                    reply_markup=markup,
                    parse_mode="Markdown"
                )
                
            elif data.startswith("settle_tkt:"):
                parts = data.split(":")
                tkt_id = parts[1]
                estado_final = parts[2]
                
                exito = banca_srv.asentar_ticket_directo(datos, tkt_id, estado_final)
                if exito:
                    banca_srv.guardar_historial(datos)
                    self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"🎉 *¡Ticket {tkt_id} liquidado como {estado_final.upper()} con éxito!*\n\nEl balance del reto y las métricas de rendimiento han sido recalculadas.",
                        parse_mode="Markdown"
                    )
                    # Enviar notificación del reporte de banca actualizado en Telegram
                    from src.services.telegram_service import TelegramService
                    tg_service = TelegramService()
                    tg_service.enviar_reporte_banca(banca_srv.historial_path)
                else:
                    self.bot.answer_callback_query(call.id, "❌ Error: El ticket no se encontró o no pudo ser liquidado.")
                    
            elif data == "publicar_picks":
                # Publicar picks generados en el canal/grupo
                from src.services.telegram_service import TelegramService
                tg_service = TelegramService()
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                JUGADAS_PATH = os.path.join(base_dir, "jugadas_lunes_15.json")
                
                exito = tg_service.enviar_reporte_picks(JUGADAS_PATH)
                if exito:
                    self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="✅ *¡El reporte de Combinadas fue publicado con éxito en Telegram!*",
                        parse_mode="Markdown"
                    )
                else:
                    self.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text="❌ *Error al intentar publicar los picks. Revisa la configuración del canal.*",
                        parse_mode="Markdown"
                    )
                    
            elif data == "cancelar_picks":
                self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="❌ *Picks descartados.* No se realizó ninguna acción.",
                    parse_mode="Markdown"
                )


        # --- FALLBACK Y PREGUNTAS DE SEGUIMIENTO ---
        @self.bot.message_handler(func=lambda message: True)
        def handle_fallback(message):
            chat_id = message.chat.id
            analisis_cmd = self.commands.get("analisis")
            
            if analisis_cmd and hasattr(analisis_cmd, "orchestrator") and analisis_cmd.orchestrator.tiene_contexto(chat_id):
                print(f"🎛️ TelegramController: Detectada pregunta de seguimiento en chat_id={chat_id}")
                loading_msg = self.bot.reply_to(
                    message, 
                    "🤔 *Analizando tu pregunta de seguimiento con el equipo de agentes...*", 
                    parse_mode="Markdown"
                )
                
                try:
                    segmentos = analisis_cmd.orchestrator.ejecutar_analisis_seguimiento(chat_id, message.text)
                    if segmentos:
                        for seg in segmentos:
                            try:
                                self.bot.send_message(chat_id, seg, parse_mode="Markdown")
                            except Exception as e_parse:
                                print(f"⚠️ TelegramController: Error de Markdown ({e_parse}). Reenviando en texto plano...")
                                self.bot.send_message(chat_id, seg)
                    else:
                        self.bot.reply_to(message, "❌ No se pudo procesar la respuesta.")
                except Exception as e:
                    print(f"❌ Error en seguimiento: {e}")
                    self.bot.reply_to(message, "❌ Error al procesar tu pregunta de seguimiento.")
                finally:
                    try:
                        self.bot.delete_message(chat_id, loading_msg.message_id)
                    except Exception:
                        pass
            else:
                msg = (
                    "🤖 *Lo siento, no reconozco ese comando.*\n\n"
                    "• Para analizar un partido usa:\n"
                    "`/analisis <nombre_equipo>`\n\n"
                    "• Para crear picks e ingresar jugadas usa:\n"
                    "`/crear_picks`\n\n"
                    "• Para liquidar tickets activos usa:\n"
                    "`/liquidar`\n\n"
                    "Usa `/start` para ver la lista completa."
                )
                self.bot.reply_to(message, msg, parse_mode="Markdown")

    # --- MÉTODOS DE LA BOTONERA DE LIQUIDACIÓN ---
    def enviar_botonera_liquidar(self, chat_id, edit_message_id=None):
        """Muestra de forma visual las apuestas activas para liquidarlas mediante un clic."""
        banca_srv = GestorBancaService()
        datos = banca_srv.cargar_historial()
        activas = datos.get("apuestas_activas", [])
        
        if not activas:
            msg = "💡 *No tienes apuestas activas pendientes de liquidación en tu historial.*"
            if edit_message_id:
                self.bot.edit_message_text(chat_id=chat_id, message_id=edit_message_id, text=msg, parse_mode="Markdown")
            else:
                self.bot.send_message(chat_id, msg, parse_mode="Markdown")
            return
            
        markup = InlineKeyboardMarkup()
        for tkt in activas:
            tkt_id = tkt.get("ticket_id")
            tipo = tkt.get("tipo_parley")
            inversion = tkt.get("inversion", 0.0)
            cuota = tkt.get("cuota", 1.0)
            btn_text = f"🎫 {tkt_id}: {tipo} (${inversion:.2f} @{cuota})"
            markup.row(InlineKeyboardButton(btn_text, callback_data=f"liquidar_tkt:{tkt_id}"))
            
        msg = "📋 *Panel de Liquidación Directa*\n\nSelecciona la jugada activa que deseas asentar:"
        if edit_message_id:
            self.bot.edit_message_text(chat_id=chat_id, message_id=edit_message_id, text=msg, reply_markup=markup, parse_mode="Markdown")
        else:
            self.bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")

    # --- DETALLES DE CREADOR CONVERSACIONAL ---
    def _step_fecha(self, message):
        chat_id = message.chat.id
        texto = message.text.strip().lower()
        
        if texto == "hoy" or not texto:
            fecha = datetime.date.today().strftime("%Y-%m-%d")
        else:
            fecha = message.text.strip()
            
        self.creacion_estado[chat_id]["fecha"] = fecha
        
        msg = "📝 Excelente. Ingresa una breve descripción de la jornada (ej: 'Mundial Jornada 4'):"
        sent_msg = self.bot.send_message(chat_id, msg)
        self.bot.register_next_step_handler(sent_msg, self._step_descripcion)

    def _step_descripcion(self, message):
        chat_id = message.chat.id
        self.creacion_estado[chat_id]["descripcion"] = message.text.strip()
        
        msg = (
            "🟢 *Creación de la COMBINADA SEGURA*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Escribe la *primera selección* con el formato exacto:\n"
            "`Partido | Pronóstico | Cuota | Probabilidad`\n\n"
            "Ejemplo: `España vs. Cabo Verde | España a Ganar | 1.15 | 85%`\n\n"
            "_(Cuando termines de añadir selecciones a este ticket, escribe 'fin')_"
        )
        sent_msg = self.bot.send_message(chat_id, msg, parse_mode="Markdown")
        self.bot.register_next_step_handler(sent_msg, self._step_agregar_seleccion)

    def _step_agregar_seleccion(self, message):
        chat_id = message.chat.id
        texto = message.text.strip()
        estado = self.creacion_estado.get(chat_id)
        
        if not estado:
            self.bot.send_message(chat_id, "❌ Error de sesión de creación. Por favor inicia de nuevo con `/crear_picks`.")
            return

        tipo = estado["tipo_actual"]
        parley = estado[f"parley_{tipo}"]
        
        if texto.lower() == "fin":
            if not parley["selecciones"]:
                sent_msg = self.bot.send_message(chat_id, "⚠️ Debes agregar al menos una selección antes de escribir 'fin'. Escribe una:")
                self.bot.register_next_step_handler(sent_msg, self._step_agregar_seleccion)
                return
                
            # Calcular cuotas y probabilidades finales del parley actual
            parley["cuota_total_estimada"] = round(parley["cuota_total_estimada"], 2)
            parley["probabilidad_implicta_cuota"] = f"{(1.0 / parley['cuota_total_estimada']) * 100:.1f}%"
            
            # Cambiar a la combinada arriesgada si acabamos la segura
            if tipo == "seguro":
                estado["tipo_actual"] = "arriesgado"
                msg = (
                    "🔴 *Creación de la COMBINADA DE ALTO VALOR*\n"
                    "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "Escribe la *primera selección* para tu combinada arriesgada en el mismo formato:\n"
                    "`Partido | Pronóstico | Cuota | Probabilidad`\n\n"
                    "Ejemplo: `Arabia vs. Uruguay | Uruguay gana y -3.5 goles | 1.95 | 60%`\n\n"
                    "_(Escribe 'fin' para concluir la combinada y guardar)_"
                )
                sent_msg = self.bot.send_message(chat_id, msg, parse_mode="Markdown")
                self.bot.register_next_step_handler(sent_msg, self._step_agregar_seleccion)
            else:
                # Terminamos ambos parleys. Guardar en JSON
                self._finalizar_creacion_picks(chat_id)
            return

        # Procesar entrada formateada: Partido | Pronóstico | Cuota | Probabilidad
        partes = [p.strip() for p in texto.split("|")]
        if len(partes) != 4:
            msg_err = (
                "⚠️ *Formato incorrecto.*\n"
                "Usa exactamente las barras verticales: `Partido | Pronóstico | Cuota | Probabilidad`\n"
                "Intenta de nuevo:"
            )
            sent_msg = self.bot.send_message(chat_id, msg_err, parse_mode="Markdown")
            self.bot.register_next_step_handler(sent_msg, self._step_agregar_seleccion)
            return
            
        partido, pronostico, cuota_str, prob_str = partes
        try:
            cuota = float(cuota_str)
            prob_real_val = float(prob_str.replace("%", "").strip())
        except ValueError:
            msg_err = "⚠️ *Error de formato numérico.* Asegúrate de que la cuota (ej: 1.85) y probabilidad (ej: 65%) sean números. Reintenta:"
            sent_msg = self.bot.send_message(chat_id, msg_err, parse_mode="Markdown")
            self.bot.register_next_step_handler(sent_msg, self._step_agregar_seleccion)
            return

        # Calcular valor implicito
        prob_imp_val = (1.0 / cuota) * 100
        prob_implicita_str = f"{prob_imp_val:.1f}%"
        diferencia = prob_real_val - prob_imp_val
        valor_str = f"Sí (+{diferencia:.1f}%)" if diferencia > 0 else "Riesgo Ajustado"

        seleccion = {
            "partido": partido,
            "pronostico": pronostico,
            "cuota": cuota,
            "probabilidad_implicita": prob_implicita_str,
            "probabilidad_estadistica": f"{prob_real_val:.1f}%",
            "fuente_principal": "Consenso del Analista",
            "valor": valor_str
        }
        
        parley["selecciones"].append(seleccion)
        parley["cuota_total_estimada"] *= cuota
        
        # Calcular probabilidad estadística combinada multiplicando probabilidades de eventos
        prob_actual_combinada = 1.0
        for sel in parley["selecciones"]:
            p_val = float(sel["probabilidad_estadistica"].replace("%", "")) / 100.0
            prob_actual_combinada *= p_val
        parley["probabilidad_estadistica_combinada"] = f"{prob_actual_combinada * 100:.1f}%"
        
        msg_ok = f"✅ Selección #{len(parley['selecciones'])} agregada con éxito.\nEscribe la siguiente selección (o digita `fin` para continuar):"
        sent_msg = self.bot.send_message(chat_id, msg_ok)
        self.bot.register_next_step_handler(sent_msg, self._step_agregar_seleccion)

    def _finalizar_creacion_picks(self, chat_id):
        estado = self.creacion_estado.get(chat_id)
        if not estado:
            return
            
        p_seguro = estado["parley_seguro"]
        p_arriesgado = estado["parley_arriesgado"]
        
        datos_json = {
            "fecha_jornada": estado["fecha"],
            "descripcion": estado["descripcion"],
            "paginas_consultadas": ["VegasInsider", "Covers", "Action Network"],
            "parleys": {
                "parley_seguro": p_seguro,
                "parley_arriesgado": p_arriesgado
            }
        }
        
        # Guardar en archivo jugadas_lunes_15.json en la raíz
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        JUGADAS_PATH = os.path.join(base_dir, "jugadas_lunes_15.json")
        
        # Primero registrar el ticket activo en la base de datos de banca
        banca_srv = GestorBancaService()
        historial_datos = banca_srv.cargar_historial()
        
        if historial_datos:
            # Crear ID de tickets nuevos
            tkt_seguro_id = f"TKT-{estado['fecha'].replace('-', '')}-01"
            tkt_arriesgado_id = f"TKT-{estado['fecha'].replace('-', '')}-02"
            
            # Evitar duplicados eliminando previos con el mismo ID si existen
            historial_datos["apuestas_activas"] = [
                tkt for tkt in historial_datos.get("apuestas_activas", []) 
                if tkt.get("ticket_id") not in [tkt_seguro_id, tkt_arriesgado_id]
            ]
            
            # Mapear e inyectar apuestas activas
            historial_datos["apuestas_activas"].append({
                "ticket_id": tkt_seguro_id,
                "fecha_registro": datetime.datetime.now().isoformat(),
                "fecha_jornada": estado["fecha"],
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
            
            historial_datos["apuestas_activas"].append({
                "ticket_id": tkt_arriesgado_id,
                "fecha_registro": datetime.datetime.now().isoformat(),
                "fecha_jornada": estado["fecha"],
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
            
            # Guardar balance descontando la inversión de las 2 nuevas jugadas ($2.00 en total)
            banca = historial_datos.get("banca", {})
            banca["banca_actual"] = round(banca.get("banca_actual", 10.0) - 2.0, 2)
            banca["dinero_en_juego"] = round(banca.get("dinero_en_juego", 0.0) + 2.0, 2)
            
            # Guardar historial y actualizar markdown
            banca_srv.guardar_historial(historial_datos)
            
        with open(JUGADAS_PATH, "w", encoding="utf-8") as f:
            json.dump(datos_json, f, indent=2, ensure_ascii=False)
            
        # Liberar estado
        if chat_id in self.creacion_estado:
            del self.creacion_estado[chat_id]
            
        # Mostrar resumen con botones para publicar de inmediato
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("📢 Publicar a Telegram", callback_data="publicar_picks"),
            InlineKeyboardButton("❌ Cancelar Envío", callback_data="cancelar_picks")
        )
        
        preview = (
            "🎉 *¡Picks y Tickets creados con éxito!*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📅 *Jornada:* `{estado['fecha']}`\n"
            f"🟢 *Seguro:* `{len(p_seguro['selecciones'])} selecciones` (@{p_seguro['cuota_total_estimada']})\n"
            f"🔴 *Arriesgado:* `{len(p_arriesgado['selecciones'])} selecciones` (@{p_arriesgado['cuota_total_estimada']})\n\n"
            "Los tickets han sido registrados como *apuestas activas* y se debitó $2.00 USD de tu banca disponible.\n\n"
            "¿Deseas publicar este nuevo reporte estético en tu canal de Telegram ahora mismo?"
        )
        self.bot.send_message(chat_id, preview, reply_markup=markup, parse_mode="Markdown")

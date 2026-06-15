#!/usr/bin/env python3
"""
📰 AGENTE PERIODISTA (FORMATEADOR Y REDACTOR DE CONTENIDOS)
Este agente se encarga de dar formato estético a los análisis de la IA para adaptarlos a móviles.
También asegura que los mensajes cumplan con las especificaciones de Telegram (límites de caracteres).
"""

class PeriodistaAgent:
    def __init__(self, limite_caracteres=4000):
        self.limite = limite_caracteres

    def segmentar_mensaje(self, texto):
        """
        Divide un bloque largo de texto en segmentos lógicos inferiores al límite,
        intentando no romper párrafos o bloques de código a la mitad.
        """
        if len(texto) <= self.limite:
            return [texto]
            
        print(f"📰 PeriodistaAgent: Segmentando mensaje largo ({len(texto)} caracteres)...")
        segmentos = []
        parrafos = texto.split("\n\n")
        segmento_actual = ""
        
        # Estado de si estamos dentro de un bloque de código markdown (```)
        en_bloque_codigo = False
        
        for parrafo in parrafos:
            # Contar los delimitadores de código de tres comillas invertidas para saber si abrimos/cerramos
            en_bloque_codigo_parrafo = parrafo.count("```") % 2 != 0
            
            # Si añadir este párrafo excede el límite del segmento actual
            if len(segmento_actual) + len(parrafo) + 2 > self.limite:
                # Si estamos dentro de un bloque de código, cerramos el bloque en el segmento actual
                # y lo reabrimos en el siguiente segmento para evitar romper el formato.
                if en_bloque_codigo:
                    segmento_actual += "\n```"
                    
                segmentos.append(segmento_actual.strip())
                
                # Iniciar nuevo segmento
                if en_bloque_codigo:
                    segmento_actual = "```text\n" + parrafo
                else:
                    segmento_actual = parrafo
            else:
                if segmento_actual:
                    segmento_actual += "\n\n" + parrafo
                else:
                    segmento_actual = parrafo
            
            if en_bloque_codigo_parrafo:
                en_bloque_codigo = not en_bloque_codigo
                
        if segmento_actual:
            segmentos.append(segmento_actual.strip())
            
        print(f"📰 PeriodistaAgent: Mensaje segmentado en {len(segmentos)} partes.")
        return segmentos

    def formatear_analisis(self, analisis_crudo):
        """
        Aplica mejoras de estilo visual y emojis al análisis si es necesario,
        y luego segmenta el reporte para su envío seguro en Telegram.
        """
        print("📰 PeriodistaAgent: Dando formato final al reporte...")
        
        # Proactivamente limpiar LaTeX matemático que hace crashear el parser de Telegram
        texto_limpio = analisis_crudo
        texto_limpio = texto_limpio.replace("\\[", "").replace("\\]", "")
        texto_limpio = texto_limpio.replace("$$", "")
        texto_limpio = texto_limpio.replace("\\times", "x").replace("\\cdot", "*")
        texto_limpio = texto_limpio.replace("\\sim", "~").replace("\\approx", "~")
        texto_limpio = texto_limpio.replace("\\leq", "<=").replace("\\geq", ">=")
        texto_limpio = texto_limpio.replace("\\mathbf", "")
        
        # Corregir títulos Markdown comunes
        texto_limpio = texto_limpio.replace("#### ", "🔸 ").replace("### ", "📌 ")
        
        # Segmentar
        segmentos = self.segmentar_mensaje(texto_limpio)
        return segmentos

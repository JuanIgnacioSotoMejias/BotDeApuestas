#!/usr/bin/env python3
"""
✍️ CREADOR INTERACTIVO DE PRONÓSTICOS (PICKS)
Este script facilita la creación del archivo de jugadas (jugadas_lunes_15.json)
a través de prompts en consola, calculando automáticamente las probabilidades
implícitas de las cuotas y permitiendo publicar a Telegram de inmediato.
"""

import os
import json
import sys
import subprocess

# Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JUGADAS_PATH = os.path.join(BASE_DIR, "jugadas_lunes_15.json")
RUNNER_SCRIPT_PATH = os.path.join(BASE_DIR, "main_runner.py")

def solicitar_flotante(mensaje, minimo=1.01):
    while True:
        try:
            valor = float(input(mensaje).strip())
            if valor >= minimo:
                return valor
            print(f"⚠️ El valor debe ser mayor o igual a {minimo}.")
        except ValueError:
            print("⚠️ Entrada inválida. Ingresa un número decimal.")

def solicitar_porcentaje(mensaje):
    while True:
        try:
            entrada = input(mensaje).strip().replace("%", "")
            valor = float(entrada)
            if 0 <= valor <= 100:
                return f"{valor:.1f}%"
            print("⚠️ El porcentaje debe estar entre 0% y 100%.")
        except ValueError:
            print("⚠️ Entrada inválida. Ingresa un número decimal.")

def capturar_parley(nombre_parley):
    print(f"\n--- 📋 CONFIGURACIÓN DE {nombre_parley.upper()} ---")
    
    parley = {
        "nombre": nombre_parley,
        "tipo_riesgo": "Bajo" if "seguro" in nombre_parley.lower() else "Alto",
        "cuota_total_estimada": 1.0,
        "stake_sugerido": "5/10 (Unidades)" if "seguro" in nombre_parley.lower() else "1/10 (Unidades)",
        "probabilidad_implicta_cuota": "0.0%",
        "probabilidad_estadistica_combinada": "0.0%",
        "selecciones": []
    }
    
    # Para estimar la probabilidad combinada multiplicando las individuales
    prob_combinada_acumulada = 1.0
    
    index = 1
    while True:
        print(f"\n🔹 Selección #{index}")
        partido = input("⚽ Nombre del partido (Ej: España vs. Cabo Verde) [Enter para terminar]: ").strip()
        if not partido:
            if index == 1:
                print("⚠️ Debes agregar al menos una selección.")
                continue
            break
            
        pronostico = input("🎯 Pronóstico/Selección exacta (Ej: España a Ganador (1X2)): ").strip()
        cuota = solicitar_flotante("💰 Cuota de la casa de apuestas (Ej: 1.85): ")
        prob_real_str = solicitar_porcentaje("📈 Probabilidad estadística calculada (Ej: 65%): ")
        
        fuente = input("🔎 Fuente principal consultada (Ej: Covers): ").strip()
        if not fuente:
            fuente = "Consenso del Analista"
            
        # Calcular probabilidad implícita
        prob_imp_val = (1.0 / cuota) * 100
        prob_implicita_str = f"{prob_imp_val:.1f}%"
        
        # Calcular valor (Value)
        prob_real_val = float(prob_real_str.replace("%", ""))
        diferencia_val = prob_real_val - prob_imp_val
        valor_str = f"Sí (+{diferencia_val:.1f}%)" if diferencia_val > 0 else "Riesgo Ajustado"
        
        seleccion = {
            "partido": partido,
            "pronostico": pronostico,
            "cuota": cuota,
            "probabilidad_implicita": prob_implicita_str,
            "probabilidad_estadistica": prob_real_str,
            "fuente_principal": fuente,
            "valor": valor_str
        }
        
        parley["selecciones"].append(seleccion)
        parley["cuota_total_estimada"] *= cuota
        prob_combinada_acumulada *= (prob_real_val / 100.0)
        
        index += 1
        
    parley["cuota_total_estimada"] = round(parley["cuota_total_estimada"], 2)
    parley["probabilidad_implicta_cuota"] = f"{(1.0 / parley['cuota_total_estimada']) * 100:.1f}%"
    parley["probabilidad_estadistica_combinada"] = f"{prob_combinada_acumulada * 100:.1f}%"
    
    return parley

def crear_picks():
    print("=" * 60)
    print("✍️ CREADOR INTERACTIVO DE PRONÓSTICOS Y PARLEYS")
    print("=" * 60)
    
    fecha = input("📅 Fecha de la jornada (Ej: 2026-06-15) [Enter para usar hoy]: ").strip()
    if not fecha:
        import datetime
        fecha = datetime.date.today().strftime("%Y-%m-%d")
        
    descripcion = input("📝 Breve descripción de la jornada [Enter para omitir]: ").strip()
    if not descripcion:
        descripcion = f"Combinadas de Fase de Grupos - Jornada {fecha}"
        
    # Capturar las combinadas
    p_seguro = capturar_parley("Combinada Segura")
    p_arriesgado = capturar_parley("Combinada de Alto Valor")
    
    # Estructura del JSON final
    datos = {
        "fecha_jornada": fecha,
        "descripcion": descripcion,
        "paginas_consultadas": [
            "VegasInsider",
            "Covers",
            "Action Network",
            "WhoScored",
            "Forebet",
            "SportsLine"
        ],
        "parleys": {
            "parley_seguro": p_seguro,
            "parley_arriesgado": p_arriesgado
        }
    }
    
    # Guardar archivo
    with open(JUGADAS_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
        
    print("\n" + "=" * 60)
    print(f"🎉 Archivo guardado con éxito en {JUGADAS_PATH}")
    print("=" * 60)
    
    # Ofrecer publicación a Telegram
    publicar = input("\n🔔 ¿Deseas enviar este nuevo reporte de combinadas a tu Telegram de inmediato? (S/N): ").strip().lower()
    if publicar == 's':
        if os.path.exists(RUNNER_SCRIPT_PATH):
            print("Publicando en Telegram...")
            subprocess.run([sys.executable, RUNNER_SCRIPT_PATH, "--publish"])
        else:
            print("❌ Error: No se encontró main_runner.py en el directorio.")

if __name__ == "__main__":
    crear_picks()

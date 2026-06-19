#!/usr/bin/env python3
"""
🔤 CONFIGURACIÓN CENTRALIZADA DE CODIFICACIÓN
Reconfigurar salida estándar para evitar errores de codificación con emojis en Windows.
Importar este módulo una vez es suficiente.
"""
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

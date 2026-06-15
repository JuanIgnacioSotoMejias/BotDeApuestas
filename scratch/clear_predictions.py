#!/usr/bin/env python3
import os
import sys
from sqlalchemy import delete

# Configurar path de trabajo
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(WORKSPACE_DIR)
os.chdir(WORKSPACE_DIR)

from src.database.session import async_session_maker
from src.database.models import PrediccionIA
from src.services.gestor_banca_service import run_async

async def limpiar_predicciones():
    print("🧹 Conectando a la base de datos para limpiar predicciones...")
    async with async_session_maker() as session:
        stmt = delete(PrediccionIA)
        resultado = await session.execute(stmt)
        await session.commit()
        print(f"✅ ¡Operación completada! Se eliminaron los registros de la tabla 'predicciones_ia'.")

if __name__ == "__main__":
    run_async(limpiar_predicciones())

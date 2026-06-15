from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config.settings import Settings
from src.database.models import Base

# Determinar si es SQLite para inyectar argumentos específicos del hilo
connect_args = {}
if Settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

from sqlalchemy.pool import NullPool

# Crear el motor de base de datos asíncrono
async_engine = create_async_engine(
    Settings.DATABASE_URL,
    connect_args=connect_args,
    poolclass=NullPool,
    echo=False
)


# Fábrica de sesiones asíncronas
async_session_maker = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """Generador para obtener sesiones de base de datos."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """Inicializa la base de datos creando las tablas si no existen."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

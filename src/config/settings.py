import os

# Cargar variables de entorno del archivo .env de forma segura
class Settings:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ENV_PATH = os.path.join(BASE_DIR, ".env")
    
    TELEGRAM_BOT_TOKEN = None
    TELEGRAM_CHAT_ID = None
    GEMINI_API_KEY = None
    LLM_PROVIDER = "manual"
    OPENROUTER_API_KEY = None
    OPENROUTER_MODEL = "google/gemma-2-9b-it:free"
    OLLAMA_URL = "http://localhost:11434"
    OLLAMA_MODEL = "llama3"
    SPORTS_API_KEY = None
    SPORTS_API_URL = "https://worldcupjson.net"
    TELEGRAM_ADMIN_IDS = []
    DATABASE_URL = "sqlite+aiosqlite:///db.sqlite3"
    API_FOOTBALL_KEY = None
    API_FOOTBALL_URL = "https://v3.football.api-sports.io"
    THE_ODDS_API_KEY = None
    SCHEDULER_ENABLED = True
    SCHEDULER_HOUR = 8
    SCHEDULER_MINUTE = 0
    SCHEDULER_TIMEZONE_OFFSET = -4  # UTC-4 (Hora del Este)
    
    @classmethod
    def load(cls):
        if os.path.exists(cls.ENV_PATH):
            with open(cls.ENV_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        val = val.strip().strip('"').strip("'")
                        if key.strip() == "TELEGRAM_BOT_TOKEN":
                            cls.TELEGRAM_BOT_TOKEN = val
                        elif key.strip() == "TELEGRAM_CHAT_ID":
                            cls.TELEGRAM_CHAT_ID = val
                        elif key.strip() == "TELEGRAM_ADMIN_IDS":
                            cls.TELEGRAM_ADMIN_IDS = [int(x.strip()) for x in val.split(",") if x.strip().isdigit()]
                        elif key.strip() == "GEMINI_API_KEY":
                            cls.GEMINI_API_KEY = val
                        elif key.strip() == "LLM_PROVIDER":
                            cls.LLM_PROVIDER = val
                        elif key.strip() == "OPENROUTER_API_KEY":
                            cls.OPENROUTER_API_KEY = val
                        elif key.strip() == "OPENROUTER_MODEL":
                            cls.OPENROUTER_MODEL = val
                        elif key.strip() == "OLLAMA_URL":
                            cls.OLLAMA_URL = val
                        elif key.strip() == "OLLAMA_MODEL":
                            cls.OLLAMA_MODEL = val
                        elif key.strip() == "SPORTS_API_KEY":
                            cls.SPORTS_API_KEY = val
                        elif key.strip() == "SPORTS_API_URL":
                            cls.SPORTS_API_URL = val
                        elif key.strip() == "API_FOOTBALL_KEY":
                            cls.API_FOOTBALL_KEY = val
                        elif key.strip() == "API_FOOTBALL_URL":
                            cls.API_FOOTBALL_URL = val
                        elif key.strip() == "THE_ODDS_API_KEY":
                            cls.THE_ODDS_API_KEY = val
                        elif key.strip() == "SCHEDULER_ENABLED":
                            cls.SCHEDULER_ENABLED = val.lower() in ("true", "1", "yes", "si", "sí")
                        elif key.strip() == "SCHEDULER_HOUR":
                            cls.SCHEDULER_HOUR = int(val)
                        elif key.strip() == "SCHEDULER_MINUTE":
                            cls.SCHEDULER_MINUTE = int(val)
                        elif key.strip() == "SCHEDULER_TIMEZONE_OFFSET":
                            cls.SCHEDULER_TIMEZONE_OFFSET = int(val)
                        elif key.strip() == "DATABASE_URL":
                            if val.startswith("postgresql://"):
                                val = val.replace("postgresql://", "postgresql+asyncpg://", 1)
                            cls.DATABASE_URL = val
                            
        # Permitir cargar desde variables de entorno del sistema operativo si .env está ausente
        if not cls.TELEGRAM_BOT_TOKEN:
            cls.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID:
            cls.TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
        
        env_admin_ids = os.getenv("TELEGRAM_ADMIN_IDS")
        if env_admin_ids:
            cls.TELEGRAM_ADMIN_IDS = [int(x.strip()) for x in env_admin_ids.split(",") if x.strip().isdigit()]
            
        if not cls.GEMINI_API_KEY:
            cls.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        if not os.getenv("LLM_PROVIDER") is None:
            cls.LLM_PROVIDER = os.getenv("LLM_PROVIDER")
        if not os.getenv("OPENROUTER_API_KEY") is None:
            cls.OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
        if not os.getenv("OPENROUTER_MODEL") is None:
            cls.OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL")
        if not os.getenv("OLLAMA_URL") is None:
            cls.OLLAMA_URL = os.getenv("OLLAMA_URL")
        if not os.getenv("OLLAMA_MODEL") is None:
            cls.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
        if not os.getenv("SPORTS_API_KEY") is None:
            cls.SPORTS_API_KEY = os.getenv("SPORTS_API_KEY")
        if not os.getenv("SPORTS_API_URL") is None:
            cls.SPORTS_API_URL = os.getenv("SPORTS_API_URL")
        if not os.getenv("API_FOOTBALL_KEY") is None:
            cls.API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
        if not os.getenv("API_FOOTBALL_URL") is None:
            cls.API_FOOTBALL_URL = os.getenv("API_FOOTBALL_URL")
        if not os.getenv("THE_ODDS_API_KEY") is None:
            cls.THE_ODDS_API_KEY = os.getenv("THE_ODDS_API_KEY")
        if not os.getenv("DATABASE_URL") is None:
            db_url = os.getenv("DATABASE_URL")
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            cls.DATABASE_URL = db_url
            
        # Fallback de seguridad si no hay admins definidos
        if not cls.TELEGRAM_ADMIN_IDS and cls.TELEGRAM_CHAT_ID:
            try:
                cls.TELEGRAM_ADMIN_IDS = [int(cls.TELEGRAM_CHAT_ID)]
            except Exception:
                pass

    @classmethod
    def jugadas_path(cls, fecha=None):
        """Retorna la ruta del archivo de jugadas para una fecha dada (default: hoy).
        Formato: jugadas_YYYY-MM-DD.json
        """
        import datetime
        if fecha is None:
            fecha = datetime.date.today().strftime("%Y-%m-%d")
        return os.path.join(cls.BASE_DIR, f"jugadas_{fecha}.json")

    @classmethod
    def jugadas_path_mas_reciente(cls):
        """Busca el archivo de jugadas más reciente en el directorio raíz.
        Retorna la ruta del archivo más reciente o None si no existe ninguno.
        """
        import glob
        patron = os.path.join(cls.BASE_DIR, "jugadas_*.json")
        archivos = glob.glob(patron)
        if not archivos:
            # Fallback al nombre legacy por compatibilidad
            legacy = os.path.join(cls.BASE_DIR, "jugadas_lunes_15.json")
            return legacy if os.path.exists(legacy) else None
        # Ordenar por nombre (YYYY-MM-DD ordena lexicográficamente)
        archivos.sort(reverse=True)
        return archivos[0]


# Cargar inmediatamente al importar
Settings.load()

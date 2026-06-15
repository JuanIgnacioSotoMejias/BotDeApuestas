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
                        elif key.strip() == "DATABASE_URL":
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
        if not os.getenv("DATABASE_URL") is None:
            cls.DATABASE_URL = os.getenv("DATABASE_URL")
            
        # Fallback de seguridad si no hay admins definidos
        if not cls.TELEGRAM_ADMIN_IDS and cls.TELEGRAM_CHAT_ID:
            try:
                cls.TELEGRAM_ADMIN_IDS = [int(cls.TELEGRAM_CHAT_ID)]
            except Exception:
                pass


# Cargar inmediatamente al importar
Settings.load()

"""Конфигурация приложения."""
import os
from dotenv import load_dotenv

load_dotenv()


def _get_int_env(key: str, default: int = 0) -> int:
    """Получение целочисленного значения из переменной окружения."""
    value = os.getenv(key, str(default))
    try:
        return int(value)
    except ValueError:
        return default


# Telegram API credentials для user bot
API_ID = _get_int_env("API_ID", 0)
API_HASH = os.getenv("API_HASH", "")

# Classic bot token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

def validate_config():
    """Проверка заполненности обязательных параметров."""
    warnings = []
    if API_ID == 0:
        warnings.append("API_ID не заполнен в .env файле! Получите на https://my.telegram.org/apps")
    if not API_HASH or API_HASH == "your_api_hash":
        warnings.append("API_HASH не заполнен в .env файле! Получите на https://my.telegram.org/apps")
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token":
        warnings.append("BOT_TOKEN не заполнен в .env файле! Получите от @BotFather в Telegram")
    
    if warnings:
        print("ВНИМАНИЕ: Обнаружены проблемы с конфигурацией:")
        for warning in warnings:
            print(f"   - {warning}")
        return False
    return True

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost/dbname")

SEMANTIC_PROVIDER = os.getenv("SEMANTIC_PROVIDER", "local")
SEMANTIC_MODEL = os.getenv("SEMANTIC_MODEL", "ai-forever/sbert_large_nlu_ru")
SEMANTIC_THRESHOLD = float(os.getenv("SEMANTIC_THRESHOLD", "0.25"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "text-embedding-3-small")




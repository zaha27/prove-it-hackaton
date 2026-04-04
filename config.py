"""
config.py — Load environment variables and expose app-wide constants.
"""
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Legacy keys (kept for backward compat with data/ai_engine.py fallback path)
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
NEWS_API_KEY: str      = os.getenv("NEWS_API_KEY", "")
GDELT_ENABLED: bool    = os.getenv("GDELT_ENABLED", "false").lower() == "true"

# Primary LLM (DeepSeek via backend)
DEEPSEEK_API_KEY: str  = os.getenv("DEEPSEEK_API_KEY", "")
BACKEND_URL: str       = os.getenv("BACKEND_URL", "http://localhost:8000")

DEFAULT_SYMBOL: str    = os.getenv("DEFAULT_SYMBOL", "GC=F")
LLM_MODEL: str         = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_MAX_TOKENS: int    = int(os.getenv("LLM_MAX_TOKENS", "1024"))

SYMBOLS: dict[str, str] = {
    "GC=F": "Gold",
    "SI=F": "Silver",
    "CL=F": "Crude Oil",
    "NG=F": "Natural Gas",
    "ZW=F": "Wheat",
    "HG=F": "Copper",
}

if not DEEPSEEK_API_KEY:
    logger.warning("DEEPSEEK_API_KEY not set — AI insights will use Ollama fallback")

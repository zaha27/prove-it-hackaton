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

ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
GDELT_ENABLED: bool = os.getenv("GDELT_ENABLED", "false").lower() == "true"
DEFAULT_SYMBOL: str = os.getenv("DEFAULT_SYMBOL", "GC=F")
REFRESH_INTERVAL_SEC: int = int(os.getenv("REFRESH_INTERVAL_SEC", "30"))
LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

SYMBOLS: dict[str, str] = {
    "GC=F": "Gold",
    "SI=F": "Silver",
    "CL=F": "Crude Oil",
    "NG=F": "Natural Gas",
    "ZW=F": "Wheat",
    "HG=F": "Copper",
}

if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY not set — LLM calls will fail unless --mock is used")

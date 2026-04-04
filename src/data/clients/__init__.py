"""API clients for external data sources.

NOTE: NewsAPI removed - using Yahoo Finance only.
"""

from src.data.clients.deepseek_client import DeepSeekClient
from src.data.clients.yfinance_client import YFinanceClient

__all__ = ["YFinanceClient", "DeepSeekClient"]

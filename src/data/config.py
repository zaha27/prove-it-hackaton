"""Configuration management for the data module."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from config/.env
env_path = Path(__file__).parent.parent.parent / "config" / ".env"
load_dotenv(env_path)


@dataclass(frozen=True)
class Config:
    """Application configuration."""

    # DeepSeek API
    deepseek_api_key: str
    deepseek_base_url: str

    # Gemini API
    gemini_api_key: str

    # Qdrant
    qdrant_url: str
    qdrant_collection: str

    # Commodity symbols mapping (yfinance)
    commodity_symbols: dict[str, str]

    # Embedding model
    embedding_model: str

    # Backtesting Parameters
    backtest_min_sample_size: int
    backtest_lookback_days: int
    backtest_confidence_level: float

    # Strategy Thresholds
    min_win_rate: float
    min_sharpe_ratio: float
    max_drawdown_pct: float
    min_expectancy: float

    # Emergency Detection
    emergency_price_move_pct: float
    emergency_volume_multiplier: float
    emergency_news_sentiment_spike: float

    # RL Parameters
    rl_outcome_evaluation_days: int
    rl_success_threshold: float
    rl_failure_threshold: float

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=os.getenv(
                "DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"
            ),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),

            qdrant_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            qdrant_collection=os.getenv("QDRANT_COLLECTION", "commodity_news"),
            commodity_symbols={
                # Precious Metals
                "GOLD": "GC=F",  # Gold Futures
                "SILVER": "SI=F",  # Silver Futures
                "PLATINUM": "PL=F",  # Platinum Futures
                "PALLADIUM": "PA=F",  # Palladium Futures
                # Energy
                "OIL": "CL=F",  # Crude Oil Futures (WTI)
                "BRENT": "BZ=F",  # Brent Crude Futures
                "NATURAL_GAS": "NG=F",  # Natural Gas Futures
                # Forex
                "EURUSD": "EURUSD=X",  # Euro/USD
                "GBPUSD": "GBPUSD=X",  # GBP/USD
                "USDJPY": "JPY=X",  # USD/JPY
                "USDCHF": "CHF=X",  # USD/CHF
                "AUDUSD": "AUDUSD=X",  # AUD/USD
                "USDCAD": "CAD=X",  # USD/CAD
                "NZDUSD": "NZDUSD=X",  # NZD/USD
                "EURGBP": "EURGBP=X",  # EUR/GBP
                # Indices
                "SP500": "^GSPC",  # S&P 500
                "NASDAQ": "^IXIC",  # NASDAQ
                "DOW": "^DJI",  # Dow Jones
                "VIX": "^VIX",  # Volatility Index
                # Crypto
                "BTC": "BTC-USD",  # Bitcoin
                "ETH": "ETH-USD",  # Ethereum
                # Commodities
                "COPPER": "HG=F",  # Copper Futures
                "WHEAT": "ZW=F",  # Wheat Futures
                "CORN": "ZC=F",  # Corn Futures
                "SOYBEAN": "ZS=F",  # Soybean Futures
                "COFFEE": "KC=F",  # Coffee Futures
            },
            embedding_model="all-MiniLM-L6-v2",
            # Backtesting
            backtest_min_sample_size=int(
                os.getenv("BACKTEST_MIN_SAMPLE_SIZE", "20")
            ),
            backtest_lookback_days=int(
                os.getenv("BACKTEST_LOOKBACK_DAYS", "730")
            ),
            backtest_confidence_level=float(
                os.getenv("BACKTEST_CONFIDENCE_LEVEL", "0.95")
            ),
            # Strategy Thresholds
            min_win_rate=float(os.getenv("MIN_WIN_RATE", "0.55")),
            min_sharpe_ratio=float(os.getenv("MIN_SHARPE_RATIO", "0.8")),
            max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "15.0")),
            min_expectancy=float(os.getenv("MIN_EXPECTANCY", "0.02")),
            # Emergency Detection
            emergency_price_move_pct=float(
                os.getenv("EMERGENCY_PRICE_MOVE_PCT", "5.0")
            ),
            emergency_volume_multiplier=float(
                os.getenv("EMERGENCY_VOLUME_MULTIPLIER", "5.0")
            ),
            emergency_news_sentiment_spike=float(
                os.getenv("EMERGENCY_NEWS_SENTIMENT_SPIKE", "3.0")
            ),
            # RL Parameters
            rl_outcome_evaluation_days=int(
                os.getenv("RL_OUTCOME_EVALUATION_DAYS", "7")
            ),
            rl_success_threshold=float(
                os.getenv("RL_SUCCESS_THRESHOLD", "0.02")
            ),
            rl_failure_threshold=float(
                os.getenv("RL_FAILURE_THRESHOLD", "-0.02")
            ),
        )

    def validate(self) -> None:
        """Validate that required configuration is present."""
        missing = []
        if not self.deepseek_api_key:
            missing.append("DEEPSEEK_API_KEY")

        # Note: GEMINI_API_KEY is optional for MCP grounding
        # If not provided, MCP will use simulation mode

        if missing:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


# Global config instance
config = Config.from_env()

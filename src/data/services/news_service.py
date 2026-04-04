"""News service using Yahoo Finance + gemini-grounding MCP only.

NO NewsAPI - uses Yahoo Finance ticker data and gemini-grounding for context.
"""

from datetime import datetime, timedelta
from typing import Any

from src.data.clients.yfinance_client import YFinanceClient
from src.data.config import config
from src.data.models.news import NewsArticle


class NewsService:
    """Service for market updates using Yahoo Finance + gemini-grounding MCP.

    Uses Yahoo Finance for price movements and gemini-grounding MCP for context.
    NO NewsAPI dependency.
    """

    # Extended symbol mapping for various inputs
    SYMBOL_MAP: dict[str, str] = {
        # Precious Metals
        "GOLD": "GC=F",
        "SILVER": "SI=F",
        "PLATINUM": "PL=F",
        "PALLADIUM": "PA=F",
        # Energy
        "OIL": "CL=F",
        "BRENT": "BZ=F",
        "NATURAL_GAS": "NG=F",
        # Currency Pairs (Forex)
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "JPY=X",
        "USDCHF": "CHF=X",
        "AUDUSD": "AUDUSD=X",
        "USDCAD": "CAD=X",
        "NZDUSD": "NZDUSD=X",
        "EURGBP": "EURGBP=X",
        # Indices
        "SP500": "^GSPC",
        "NASDAQ": "^IXIC",
        "DOW": "^DJI",
        "VIX": "^VIX",
        # Crypto
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        # Commodities
        "COPPER": "HG=F",
        "WHEAT": "ZW=F",
        "CORN": "ZC=F",
        "SOYBEAN": "ZS=F",
        "COFFEE": "KC=F",
    }

    def __init__(self) -> None:
        """Initialize the news service with Yahoo Finance only."""
        self.yf_client = YFinanceClient()
        # No NewsAPI, no vector store needed

    def _get_symbol(self, input_str: str) -> str:
        """Get Yahoo Finance symbol from input string.

        Args:
            input_str: User input (GOLD, EURUSD, etc.)

        Returns:
            Yahoo Finance symbol
        """
        upper_input = input_str.upper().replace("/", "").replace("-", "")
        return self.SYMBOL_MAP.get(upper_input, input_str)

    def _generate_market_update(
        self, symbol: str, current: float, change_pct: float
    ) -> NewsArticle:
        """Generate a market update article from price data.

        Args:
            symbol: Symbol name
            current: Current price
            change_pct: Change percentage

        Returns:
            NewsArticle with market update
        """
        change_24h = current * (change_pct / 100) if change_pct else 0

        # Determine sentiment based on price movement
        if change_pct > 1:
            sentiment = "positive"
            sentiment_score = min(change_pct / 5, 1.0)  # Cap at 1.0
            title = f"{symbol} Rises {change_pct:+.2f}% on Strong Market Movement"
        elif change_pct > 0:
            sentiment = "neutral"
            sentiment_score = change_pct / 10
            title = f"{symbol} Edges Higher by {change_pct:+.2f}%"
        elif change_pct < -1:
            sentiment = "negative"
            sentiment_score = max(change_pct / 5, -1.0)  # Cap at -1.0
            title = f"{symbol} Falls {abs(change_pct):.2f}% Amid Market Pressure"
        else:
            sentiment = "neutral"
            sentiment_score = change_pct / 10
            title = f"{symbol} Holds Steady at ${current:,.2f}"

        # Generate content based on price action
        content = (
            f"Market Update for {symbol}:\n"
            f"Current Price: ${current:,.2f}\n"
            f"24h Change: ${change_24h:+.2f} ({change_pct:+.2f}%)\n"
            f"Data Source: Yahoo Finance"
        )

        return NewsArticle(
            id=f"market_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M')}",
            title=title,
            source="Yahoo Finance",
            date=datetime.now().strftime("%Y-%m-%d"),
            content=content,
            url=f"https://finance.yahoo.com/quote/{self._get_symbol(symbol)}",
            sentiment=sentiment,
            sentiment_score=sentiment_score,
            commodity=symbol,
            fetched_at=datetime.utcnow(),
        )

    def get_news_for_commodity(
        self,
        commodity: str,
        days: int = 7,
        limit: int = 20,
    ) -> list[NewsArticle]:
        """Get market updates for any symbol using Yahoo Finance.

        Args:
            commodity: Symbol (GOLD, EURUSD, SILVER, OIL, etc.)
            days: Number of days (for compatibility)
            limit: Maximum updates (for compatibility)

        Returns:
            List of NewsArticle objects with market data
        """
        try:
            # Fetch price data from Yahoo Finance (pass commodity key, not symbol)
            current, change_pct = self.yf_client.fetch_latest_price(commodity)

            # Generate market update article
            article = self._generate_market_update(commodity, current, change_pct)

            return [article]

        except Exception as e:
            # Return error article
            return [NewsArticle(
                id=f"error_{commodity}_{datetime.now().strftime('%Y%m%d_%H%M')}",
                title=f"Unable to fetch data for {commodity}",
                source="Error",
                date=datetime.now().strftime("%Y-%m-%d"),
                content=f"Error fetching data: {e}",
                sentiment="neutral",
                sentiment_score=0.0,
                commodity=commodity,
            )]

    def get_multi_symbol_updates(
        self, symbols: list[str]
    ) -> dict[str, list[NewsArticle]]:
        """Get market updates for multiple symbols.

        Args:
            symbols: List of symbols (GOLD, EURUSD, SILVER, etc.)

        Returns:
            Dictionary mapping symbol to list of updates
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_news_for_commodity(symbol)
        return results

    def search_relevant_news(
        self,
        query: str,
        commodity: str | None = None,
        top_k: int = 5,
    ) -> list[NewsArticle]:
        """Search for market data relevant to query.

        Uses Yahoo Finance to get current data for the queried symbol.

        Args:
            query: Search query (symbol name)
            commodity: Optional commodity filter
            top_k: Number of results (for compatibility)

        Returns:
            List of NewsArticle with market data
        """
        # Use query as symbol
        symbol = commodity or query.upper()
        return self.get_news_for_commodity(symbol, limit=top_k)

    def get_news_summary(self, commodity: str, max_articles: int = 5) -> str:
        """Generate a market summary for LLM context.

        Args:
            commodity: Symbol (GOLD, EURUSD, etc.)
            max_articles: Maximum articles (for compatibility)

        Returns:
            Market summary string
        """
        try:
            articles = self.get_news_for_commodity(commodity)
            if articles and articles[0].source != "Error":
                article = articles[0]
                return (
                    f"Market Update for {commodity}:\n"
                    f"{article.title}\n"
                    f"{article.content}"
                )
            return f"No market data available for {commodity}"
        except Exception as e:
            return f"Error getting market data for {commodity}: {e}"

    def get_supported_symbols(self) -> list[str]:
        """Get list of supported symbols.

        Returns:
            List of supported symbol names
        """
        return list(self.SYMBOL_MAP.keys())

    def init_vector_store(self) -> None:
        """No-op - no vector store needed for Yahoo Finance-only approach."""
        pass

    def fetch_and_embed_news(
        self,
        commodity: str,
        days_back: int = 7,
        page_size: int = 20,
        store_in_vector_db: bool = True,
    ) -> list[NewsArticle]:
        """Fetch market updates (Yahoo Finance only).

        Args:
            commodity: Symbol
            days_back: Not used (Yahoo Finance provides latest)
            page_size: Not used
            store_in_vector_db: Not used

        Returns:
            List with single market update article
        """
        return self.get_news_for_commodity(commodity)

    def get_enhanced_market_context(
        self, commodity: str, use_gemini: bool = True
    ) -> dict[str, Any]:
        """Get enhanced market context using Yahoo Finance + gemini-grounding MCP.

        Args:
            commodity: Symbol (GOLD, EURUSD, etc.)
            use_gemini: Whether to use gemini-grounding MCP for context

        Returns:
            Dictionary with market data and enhanced context
        """
        # Get base market data from Yahoo Finance
        articles = self.get_news_for_commodity(commodity)
        base_article = articles[0] if articles else None

        result = {
            "commodity": commodity,
            "yahoo_finance_data": base_article,
            "gemini_context": None,
        }

        # Enhance with gemini-grounding MCP if requested
        if use_gemini and base_article:
            try:
                gemini_context = self._get_gemini_context(commodity, base_article)
                result["gemini_context"] = gemini_context
            except Exception as e:
                result["gemini_error"] = str(e)

        return result

    def _get_gemini_context(
        self, commodity: str, article: NewsArticle
    ) -> dict[str, Any]:
        """Get additional context from gemini-grounding MCP.

        Args:
            commodity: Symbol name
            article: Base market article

        Returns:
            Gemini context dictionary
        """
        # This method would call the gemini-grounding MCP
        # For now, return placeholder structure
        return {
            "query": f"{commodity} market analysis latest",
            "context": f"Price: {article.content[:200]}...",
            "focus": "general",
            "note": "Call gemini-grounding MCP for real-time context",
        }

"""
data/mock_data.py — Fully implemented mock data for demo/dev mode (--mock flag).
No API keys required.
"""
from datetime import datetime, timedelta
import random
from data.macro_insight_text import WORLD_MACRO_INSIGHT_TEXT

# Seed per symbol for reproducible "random" data
_BASE_PRICES = {
    "GC=F": 2320.0,   # Gold USD/oz
    "SI=F": 27.5,     # Silver USD/oz
    "CL=F": 82.0,     # Crude Oil USD/bbl
    "NG=F": 2.15,     # Natural Gas USD/MMBtu
    "ZW=F": 560.0,    # Wheat USD/bu (cents)
    "HG=F": 4.35,     # Copper USD/lb
}

_CURRENCY = {
    "GC=F": "USD/oz",
    "SI=F": "USD/oz",
    "CL=F": "USD/bbl",
    "NG=F": "USD/MMBtu",
    "ZW=F": "USd/bu",
    "HG=F": "USD/lb",
}

_MOCK_NEWS = {
    "GC=F": [
        {
            "title": "Gold surges as Fed signals rate pause amid inflation concerns",
            "sentiment": "bullish",
            "source": "Reuters",
            "timestamp": "2026-04-03 14:22",
            "summary": "Gold prices climbed 1.2% after Fed officials hinted at holding rates steady, boosting the appeal of non-yielding assets.",
        },
        {
            "title": "Central banks continue record gold purchases in Q1 2026",
            "sentiment": "bullish",
            "source": "Bloomberg",
            "timestamp": "2026-04-02 09:10",
            "summary": "Global central banks bought 290 tonnes of gold in Q1, marking the fifth consecutive quarter of record purchases.",
        },
        {
            "title": "Dollar strengthens on strong jobs data, pressures gold",
            "sentiment": "bearish",
            "source": "MarketWatch",
            "timestamp": "2026-04-01 16:45",
            "summary": "A stronger-than-expected payrolls report pushed the DXY index higher, applying downward pressure on gold prices.",
        },
        {
            "title": "Gold ETF outflows signal short-term profit taking",
            "sentiment": "bearish",
            "source": "FT",
            "timestamp": "2026-03-31 11:30",
            "summary": "SPDR Gold Shares saw $340M in outflows this week as investors rotated into equities following tech earnings beats.",
        },
        {
            "title": "Geopolitical tensions in Middle East support safe-haven demand",
            "sentiment": "neutral",
            "source": "AP",
            "timestamp": "2026-03-30 08:00",
            "summary": "Ongoing uncertainty in the region keeps safe-haven demand intact, though analysts see limited near-term upside.",
        },
    ],
    "CL=F": [
        {
            "title": "OPEC+ maintains output cuts despite pressure from consumers",
            "sentiment": "bullish",
            "source": "Reuters",
            "timestamp": "2026-04-03 13:00",
            "summary": "The alliance extended its 2.2 million bpd voluntary cuts through Q2, tightening global supply outlook.",
        },
        {
            "title": "US crude inventories fall sharply, prices rally",
            "sentiment": "bullish",
            "source": "EIA",
            "timestamp": "2026-04-02 15:30",
            "summary": "EIA weekly report showed a drawdown of 4.8M barrels, beating analyst estimates of -1.2M barrels.",
        },
        {
            "title": "Recession fears dampen oil demand outlook for H2 2026",
            "sentiment": "bearish",
            "source": "IEA",
            "timestamp": "2026-04-01 10:00",
            "summary": "IEA cut its global oil demand growth forecast to 0.9 Mbpd from 1.3 Mbpd, citing slowing manufacturing activity.",
        },
        {
            "title": "Libya restores 300k bpd of production after outages",
            "sentiment": "bearish",
            "source": "Bloomberg",
            "timestamp": "2026-03-31 09:45",
            "summary": "Libyan NOC confirmed restoration of key field output, adding to global supply and capping price gains.",
        },
        {
            "title": "Shipping disruptions in Red Sea continue to affect WTI-Brent spread",
            "sentiment": "neutral",
            "source": "S&P Global",
            "timestamp": "2026-03-30 12:00",
            "summary": "Rerouting through the Cape of Good Hope adds 2 weeks to transit times, affecting regional pricing dynamics.",
        },
    ],
}

_MOCK_AI_INSIGHTS = {
    "Macro": WORLD_MACRO_INSIGHT_TEXT,
    "GC=F": (
        "**Chain-of-Thought Analysis — Gold (GC=F)**\n\n"
        "Step 1 — Macro context: The Fed's pause narrative is the dominant driver. "
        "Real yields (10Y TIPS) sit at +1.8%, historically a headwind, yet gold holds above $2,300 "
        "— indicating structural demand beyond rate sensitivity.\n\n"
        "Step 2 — Supply/demand: Central bank buying (290t in Q1) provides a persistent bid. "
        "ETF flows are mildly negative (-$340M), suggesting retail profit-taking, not structural selling.\n\n"
        "Step 3 — Technical: Price is consolidating in a $2,290–$2,360 range. "
        "RSI at 54 — neither overbought nor oversold. MACD shows a mild bullish crossover.\n\n"
        "**Conclusion:** Bias is **moderately bullish** near-term. A break above $2,360 opens $2,400. "
        "Key risk: stronger USD on hawkish Fed repricing."
    ),
    "SI=F": (
        "**Chain-of-Thought Analysis — Silver (SI=F)**\n\n"
        "Step 1 — Gold/Silver ratio at 84x, above the 5-year mean of 79x — silver appears undervalued relative to gold.\n\n"
        "Step 2 — Industrial demand: Solar panel installations hit record levels globally; silver's role in PV cells "
        "provides a structural demand tailwind not present in gold.\n\n"
        "Step 3 — Technical: Silver broke above the $27 resistance level on above-average volume. "
        "Next target: $28.50. Support at $26.20.\n\n"
        "**Conclusion:** **Bullish** with a catch-up trade thesis. Silver tends to outperform gold in the latter "
        "stages of a precious metals rally. Risk: industrial slowdown compressing the demand side."
    ),
    "CL=F": (
        "**Chain-of-Thought Analysis — Crude Oil (CL=F)**\n\n"
        "Step 1 — OPEC+ discipline remains intact. The group controls ~40% of global supply; "
        "voluntary cuts of 2.2 Mbpd represent a significant market intervention.\n\n"
        "Step 2 — Demand: IEA's downward revision is notable. China's manufacturing PMI fell to 49.1, "
        "contraction territory, which historically correlates with reduced oil import volumes.\n\n"
        "Step 3 — Technical: WTI oscillating around $82, the 200-day MA. Bollinger Bands are tightening, "
        "indicating a volatility expansion is imminent.\n\n"
        "**Conclusion:** **Neutral to slightly bullish**. Supply discipline offsets demand concerns near-term. "
        "A break above $85 would turn technical picture clearly bullish."
    ),
    "NG=F": (
        "**Chain-of-Thought Analysis — Natural Gas (NG=F)**\n\n"
        "Step 1 — Storage levels are 12% above the 5-year average, a bearish overhang that limits sustained rallies.\n\n"
        "Step 2 — Demand: LNG export capacity additions (Plaquemines LNG coming online) should absorb "
        "domestic supply over a 12-18 month horizon, improving the supply/demand balance.\n\n"
        "Step 3 — Seasonal: April-May is shoulder season (low heating, pre-summer cooling). "
        "Historically the weakest period for nat gas prices.\n\n"
        "**Conclusion:** **Bearish near-term, neutral medium-term**. Current prices around $2.15 may retest "
        "$1.90 support before recovering. Watch weather forecasts closely."
    ),
    "ZW=F": (
        "**Chain-of-Thought Analysis — Wheat (ZW=F)**\n\n"
        "Step 1 — Black Sea export corridor remains a geopolitical risk factor. "
        "Any disruption to Ukrainian exports (22% of global wheat trade) creates immediate price spikes.\n\n"
        "Step 2 — US crop conditions: USDA rates 58% of winter wheat as good/excellent, above last year's 54%. "
        "Domestic supply is favorable.\n\n"
        "Step 3 — Technical: Wheat tested 550 support three times — triple bottom pattern is constructive. "
        "A close above 575 would confirm a reversal.\n\n"
        "**Conclusion:** **Neutral with upside optionality**. Tight global stocks-to-use ratio (26%) provides "
        "a floor. Geopolitical risk premium can re-enter quickly."
    ),
    "HG=F": (
        "**Chain-of-Thought Analysis — Copper (HG=F)**\n\n"
        "Step 1 — China is the marginal buyer (55% of global demand). Stimulus measures announced in March "
        "targeting infrastructure spending are a positive catalyst.\n\n"
        "Step 2 — Supply: Chilean production disruptions at Escondida (-8% YoY) are tightening concentrate "
        "supply. TC/RCs at multi-decade lows confirm smelter squeeze.\n\n"
        "Step 3 — Energy transition: Copper is essential for EVs (83kg/vehicle), grid infrastructure, "
        "and renewables. Structural demand deficit expected by 2027.\n\n"
        "**Conclusion:** **Bullish medium-to-long term**. Near-term may consolidate at $4.35 "
        "before a move toward $4.70 if Chinese demand data confirms recovery."
    ),
}


def get_price_data(symbol: str, period_days: int = 30) -> dict:
    """Return realistic mock OHLCV data for the requested period."""
    random.seed(hash((symbol, int(period_days))) % 1_000_000)
    base = _BASE_PRICES.get(symbol, 100.0)

    today = datetime.today()
    days = max(2, int(period_days))
    dates = [(today - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d") for i in range(days)]

    opens, highs, lows, closes, volumes = [], [], [], [], []
    price = base
    for _ in dates:
        change_pct = random.uniform(-0.012, 0.012)
        open_ = round(price, 3)
        close = round(price * (1 + change_pct), 3)
        high = round(max(open_, close) * (1 + random.uniform(0, 0.005)), 3)
        low = round(min(open_, close) * (1 - random.uniform(0, 0.005)), 3)
        vol = int(random.uniform(80_000, 250_000))
        opens.append(open_)
        highs.append(high)
        lows.append(low)
        closes.append(close)
        volumes.append(vol)
        price = close

    return {
        "symbol": symbol,
        "currency": _CURRENCY.get(symbol, "USD"),
        "dates": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
    }


def get_news(symbol: str) -> list[dict]:
    """Return 5 mock news items for a given symbol."""
    # Fall back to generic gold news if symbol not explicitly mocked
    return _MOCK_NEWS.get(symbol, _MOCK_NEWS["GC=F"])


def get_ai_insight(symbol: str) -> str:
    """Return a mock LLM Chain-of-Thought insight for a given symbol."""
    return _MOCK_AI_INSIGHTS.get(
        symbol,
        f"**Mock AI Insight — {symbol}**\n\nNo specific mock insight available for this symbol. "
        "In production mode, the LLM will generate a real analysis based on current price data and news.",
    )


def get_macro_events() -> list[dict]:
    """
    Return geo-located macro events for the World Macro View map.

    Contract matches world-monitor NewsItem/Hotspot structure:
        title, lat, lon, severity ("high"|"medium"|"low"), category, country,
        country_iso3 (required for choropleth heat contribution), summary
    """
    return [
        {
            "title": "Iran Signals Potential Transit Friction in the Strait of Hormuz",
            "lat": 26.5, "lon": 56.2,
            "severity": "high",
            "category": "energy",
            "country": "Iran",
            "country_iso3": "IRN",
            "summary": "Tanker risk premiums rise as traders reassess disruption risk at a critical crude chokepoint.",
        },
        {
            "title": "Naval Escorts Expanded Near Hormuz After Drone Incident",
            "lat": 25.8, "lon": 54.9,
            "severity": "high",
            "category": "energy",
            "country": "Iran",
            "country_iso3": "IRN",
            "summary": "Security operations intensify around tanker lanes, lifting front-month oil volatility.",
        },
        {
            "title": "OPEC+ Emergency Meeting — Output Decision Pending",
            "lat": 24.7, "lon": 46.7,
            "severity": "high",
            "category": "energy",
            "country": "Saudi Arabia",
            "country_iso3": "SAU",
            "summary": "Alliance considering additional 500k bpd cut amid demand slowdown concerns.",
        },
        {
            "title": "Russia Reduces Gas Exports via Nord Stream Corridor",
            "lat": 55.7, "lon": 37.6,
            "severity": "high",
            "category": "energy",
            "country": "Russia",
            "country_iso3": "RUS",
            "summary": "Flow volumes down 35% week-on-week; European storage drawdown accelerating.",
        },
        {
            "title": "Black Sea Port Infrastructure Hit, Wheat Loadings Delayed",
            "lat": 46.5, "lon": 30.7,
            "severity": "high",
            "category": "agriculture",
            "country": "Ukraine",
            "country_iso3": "UKR",
            "summary": "Export scheduling uncertainty increases risk premium in global wheat contracts.",
        },
        {
            "title": "Russian Navy Activity Intensifies in Central Black Sea Corridor",
            "lat": 44.8, "lon": 37.6,
            "severity": "high",
            "category": "agriculture",
            "country": "Russia",
            "country_iso3": "RUS",
            "summary": "Commercial shippers face route adjustments, adding friction to grain logistics.",
        },
        {
            "title": "Ukraine Grain Corridor Extension Agreed for 60 Days",
            "lat": 50.4, "lon": 30.5,
            "severity": "medium",
            "category": "agriculture",
            "country": "Ukraine",
            "country_iso3": "UKR",
            "summary": "UN-brokered framework supports continued Black Sea wheat and corn exports.",
        },
        {
            "title": "Chile Copper Miners Strike — Escondida Output Halted",
            "lat": -23.7, "lon": -68.0,
            "severity": "high",
            "category": "metals",
            "country": "Chile",
            "country_iso3": "CHL",
            "summary": "Workers at world's largest copper mine vote to extend strike into third week.",
        },
        {
            "title": "Fed Chair Speech: Rate Path Remains Data-Dependent",
            "lat": 38.9, "lon": -77.0,
            "severity": "medium",
            "category": "market",
            "country": "USA",
            "country_iso3": "USA",
            "summary": "Powell reiterates restrictive stance; markets pricing in 60% chance of pause.",
        },
        {
            "title": "China Stimulus Package — Infrastructure Spending Approved",
            "lat": 39.9, "lon": 116.4,
            "severity": "medium",
            "category": "market",
            "country": "China",
            "country_iso3": "CHN",
            "summary": "CNY 1.5T infrastructure bond issuance supports copper and steel demand outlook.",
        },
        {
            "title": "Iran Oil Sanctions Tightening — EU Announcement Expected",
            "lat": 35.7, "lon": 51.4,
            "severity": "high",
            "category": "energy",
            "country": "Iran",
            "country_iso3": "IRN",
            "summary": "Additional sanctions could remove 800k bpd from global supply.",
        },
        {
            "title": "Red Sea Shipping Route Re-Risked After New Houthi Strike Claims",
            "lat": 15.9, "lon": 42.5,
            "severity": "high",
            "category": "energy",
            "country": "Yemen",
            "country_iso3": "YEM",
            "summary": "Shipowners increase rerouting rates, extending delivery times for fuels and grains.",
        },
        {
            "title": "Container and Tanker Transit Through Bab el-Mandeb Falls Again",
            "lat": 12.6, "lon": 43.4,
            "severity": "high",
            "category": "energy",
            "country": "Yemen",
            "country_iso3": "YEM",
            "summary": "Persistent Red Sea security concerns sustain freight and insurance surcharges.",
        },
        {
            "title": "Suez Canal Authority Reports Lower Throughput Versus Prior Quarter",
            "lat": 30.0, "lon": 32.5,
            "severity": "medium",
            "category": "energy",
            "country": "Egypt",
            "country_iso3": "EGY",
            "summary": "Reduced Red Sea flows support higher shipping costs and regional refined product spreads.",
        },
        {
            "title": "Australian Gold Output Hits 5-Year High",
            "lat": -25.3, "lon": 131.0,
            "severity": "low",
            "category": "metals",
            "country": "Australia",
            "country_iso3": "AUS",
            "summary": "Q1 production up 12% YoY; lower production costs support miner margins.",
        },
        {
            "title": "ECB Rate Decision: 25bp Hike Delivered",
            "lat": 50.1, "lon": 8.7,
            "severity": "medium",
            "category": "market",
            "country": "Germany",
            "country_iso3": "DEU",
            "summary": "Eurozone inflation remains above target; further hikes dependent on Q2 CPI print.",
        },
        {
            "title": "West Africa Drought — Wheat Crop Estimate Revised Down",
            "lat": 12.4, "lon": -1.5,
            "severity": "medium",
            "category": "agriculture",
            "country": "Burkina Faso",
            "country_iso3": "BFA",
            "summary": "USDA cuts regional wheat output by 8%; local food security concerns rise.",
        },
        {
            "title": "Argentina Corn and Wheat Belt Hit by Fresh Moisture Deficit",
            "lat": -34.6, "lon": -58.4,
            "severity": "medium",
            "category": "agriculture",
            "country": "Argentina",
            "country_iso3": "ARG",
            "summary": "Yield risk widens in key export provinces, supporting global feed grain prices.",
        },
        {
            "title": "US Gulf Refineries Increase Crude Runs Ahead of Summer Demand",
            "lat": 29.7, "lon": -95.3,
            "severity": "low",
            "category": "energy",
            "country": "USA",
            "country_iso3": "USA",
            "summary": "Higher throughput eases product tightness but keeps crude intake elevated.",
        },
        {
            "title": "India Raises Edible Oil Import Monitoring as Freight Costs Climb",
            "lat": 19.1, "lon": 72.9,
            "severity": "low",
            "category": "agriculture",
            "country": "India",
            "country_iso3": "IND",
            "summary": "Authorities flag transport-driven food inflation risks from prolonged Red Sea disruption.",
        },
    ]

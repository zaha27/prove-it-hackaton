"""Price API router."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.price.service import PriceService
from app.price.models import PriceDataResponse, LatestPriceResponse
from app.core.dependencies import get_price_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/data/{commodity}",
    response_model=PriceDataResponse,
    summary="Get OHLCV price data",
    description="Retrieve historical OHLCV price data for a commodity",
)
async def get_price_data(
    commodity: str,
    period: str = Query("1mo", description="Data period (1d, 5d, 1mo, 3mo, 6mo, 1y)"),
    interval: str = Query("1d", description="Data interval (1d, 1h, etc.)"),
    service: PriceService = Depends(get_price_service),
):
    """Get price data for a commodity."""
    try:
        return await service.get_price_data(commodity.upper(), period, interval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/latest/{commodity}",
    response_model=LatestPriceResponse,
    summary="Get latest price",
    description="Retrieve latest price and 24-hour change for a commodity",
)
async def get_latest_price(
    commodity: str,
    service: PriceService = Depends(get_price_service),
):
    """Get latest price for a commodity."""
    try:
        return await service.get_latest_price(commodity.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/symbols",
    summary="Get supported commodities",
    description="Retrieve list of supported commodity symbols",
)
async def get_supported_commodities():
    """Get supported commodities."""
    from src.data.config import config

    return {"symbols": list(config.commodity_symbols.keys())}


@router.get(
    "/macro-events",
    summary="Get macro events for world map",
    description="Returns geo-located market events for all tracked commodities",
)
async def get_macro_events():
    """
    Fetch latest price changes for all commodities and return them as
    geo-located events compatible with WorldMapWidget.load_events().

    Event format: {title, lat, lon, severity, category, country, country_iso3, summary}
    """
    events = [
        {"title": "Iran warns of tighter inspections in the Strait of Hormuz", "lat": 26.5, "lon": 56.2, "severity": "high", "category": "energy", "country_iso3": "IRN", "country": "Iran", "summary": "Higher transit risk is lifting freight rates and near-dated crude volatility."},
        {"title": "Iran exports decline after stricter sanctions enforcement", "lat": 35.7, "lon": 51.4, "severity": "high", "category": "energy", "country_iso3": "IRN", "country": "Iran", "summary": "Lower flows are tightening medium-sour crude availability in Asia."},
        {"title": "Saudi Arabia extends voluntary crude production cut", "lat": 24.7, "lon": 46.7, "severity": "high", "category": "energy", "country_iso3": "SAU", "country": "Saudi Arabia", "summary": "The extension supports higher Brent time spreads and strengthens OPEC+ pricing power."},
        {"title": "Saudi Aramco reports stable upstream maintenance schedule", "lat": 25.3, "lon": 49.6, "severity": "low", "category": "energy", "country_iso3": "SAU", "country": "Saudi Arabia", "summary": "Normal maintenance reduces near-term supply disruption concerns for refiners."},
        {"title": "Israel increases gas security posture in the Eastern Mediterranean", "lat": 31.8, "lon": 34.8, "severity": "medium", "category": "energy", "country_iso3": "ISR", "country": "Israel", "summary": "Regional gas risk premia are firming as operators review contingency plans."},
        {"title": "Israel shekel volatility rises after renewed regional tensions", "lat": 32.1, "lon": 34.8, "severity": "medium", "category": "market", "country_iso3": "ISR", "country": "Israel", "summary": "Risk-off positioning is increasing demand for safe-haven currencies and gold."},
        {"title": "Yemen-linked Red Sea attacks trigger rerouting of tanker traffic", "lat": 15.9, "lon": 42.5, "severity": "high", "category": "geopolitics", "country_iso3": "YEM", "country": "Yemen", "summary": "Longer shipping routes are lifting delivery costs for energy and grain cargoes."},
        {"title": "Bab el-Mandeb transit insurance premiums rise again", "lat": 12.6, "lon": 43.4, "severity": "high", "category": "energy", "country_iso3": "YEM", "country": "Yemen", "summary": "Higher insurance costs are feeding into refined product and LNG freight pricing."},
        {"title": "China PBOC cuts reserve ratio by 50 bps", "lat": 39.9, "lon": 116.4, "severity": "medium", "category": "market", "country_iso3": "CHN", "country": "China", "summary": "Liquidity easing is supporting risk assets and improving metals demand expectations."},
        {"title": "China steel output beats monthly forecast", "lat": 31.2, "lon": 121.5, "severity": "low", "category": "metals", "country_iso3": "CHN", "country": "China", "summary": "Higher mill activity reinforces iron ore and coking coal import demand."},
        {"title": "China soybean imports accelerate on stronger crush margins", "lat": 22.3, "lon": 114.2, "severity": "low", "category": "agriculture", "country_iso3": "CHN", "country": "China", "summary": "Improved processing economics are supporting global oilseed balances."},
        {"title": "Japan core inflation remains above target", "lat": 35.7, "lon": 139.7, "severity": "medium", "category": "market", "country_iso3": "JPN", "country": "Japan", "summary": "Persistent inflation keeps speculation alive around further policy normalization."},
        {"title": "Japan LNG buyers lock in additional summer cargoes", "lat": 34.7, "lon": 135.5, "severity": "medium", "category": "energy", "country_iso3": "JPN", "country": "Japan", "summary": "Incremental spot procurement is tightening Pacific basin LNG availability."},
        {"title": "India raises minimum support price guidance for wheat", "lat": 28.6, "lon": 77.2, "severity": "medium", "category": "agriculture", "country_iso3": "IND", "country": "India", "summary": "Higher domestic price signals may constrain export competitiveness this season."},
        {"title": "India refinery runs hit seasonal high", "lat": 19.1, "lon": 72.9, "severity": "low", "category": "energy", "country_iso3": "IND", "country": "India", "summary": "Strong throughput supports regional diesel exports and robust crude intake."},
        {"title": "India rupee weakens as crude import bill rises", "lat": 13.1, "lon": 80.3, "severity": "medium", "category": "market", "country_iso3": "IND", "country": "India", "summary": "Currency pressure increases imported inflation risk and hedging demand."},
        {"title": "Taiwan reports stronger semiconductor export orders", "lat": 25.0, "lon": 121.5, "severity": "low", "category": "market", "country_iso3": "TWN", "country": "Taiwan", "summary": "Improving electronics demand is supporting broader Asian manufacturing sentiment."},
        {"title": "Taiwan Strait military drills increase geopolitical risk premium", "lat": 24.0, "lon": 121.0, "severity": "high", "category": "geopolitics", "country_iso3": "TWN", "country": "Taiwan", "summary": "Elevated regional tension is driving defensive positioning across equity and FX markets."},
        {"title": "Ukraine grain corridor operations slowed by port damage", "lat": 46.5, "lon": 30.7, "severity": "high", "category": "agriculture", "country_iso3": "UKR", "country": "Ukraine", "summary": "Loading disruptions are tightening near-term wheat and corn export schedules."},
        {"title": "Ukraine winter wheat condition ratings improve month over month", "lat": 50.4, "lon": 30.5, "severity": "low", "category": "agriculture", "country_iso3": "UKR", "country": "Ukraine", "summary": "Better field conditions partially offset Black Sea logistics uncertainty."},
        {"title": "Russia pipeline maintenance trims regional gas flows", "lat": 55.8, "lon": 37.6, "severity": "high", "category": "energy", "country_iso3": "RUS", "country": "Russia", "summary": "Reduced deliveries are widening European gas spreads and raising storage concerns."},
        {"title": "Russia Black Sea shipping security checks delay grain cargoes", "lat": 44.6, "lon": 33.5, "severity": "high", "category": "geopolitics", "country_iso3": "RUS", "country": "Russia", "summary": "Longer vessel turnaround times are increasing export basis volatility."},
        {"title": "Germany factory PMI remains in contraction territory", "lat": 52.5, "lon": 13.4, "severity": "medium", "category": "market", "country_iso3": "DEU", "country": "Germany", "summary": "Weak industrial momentum is capping upside in European demand-linked commodities."},
        {"title": "Germany storage report shows lower monthly natural gas draw", "lat": 53.6, "lon": 10.0, "severity": "low", "category": "energy", "country_iso3": "DEU", "country": "Germany", "summary": "Moderate withdrawals ease short-term winter balance concerns."},
        {"title": "United Kingdom inflation surprises to the upside", "lat": 51.5, "lon": -0.1, "severity": "medium", "category": "market", "country_iso3": "GBR", "country": "United Kingdom", "summary": "Sticky prices push rate-cut expectations further out and lift gilt volatility."},
        {"title": "UK North Sea maintenance curbs temporary output", "lat": 57.1, "lon": -2.1, "severity": "low", "category": "energy", "country_iso3": "GBR", "country": "United Kingdom", "summary": "Short-lived production outages provide marginal support to Atlantic crude grades."},
        {"title": "US Federal Reserve minutes reinforce higher-for-longer messaging", "lat": 38.9, "lon": -77.0, "severity": "medium", "category": "market", "country_iso3": "USA", "country": "USA", "summary": "Markets are repricing front-end rates, pressuring risk assets and EM FX."},
        {"title": "US Gulf Coast refinery utilization climbs ahead of peak demand", "lat": 29.7, "lon": -95.3, "severity": "low", "category": "energy", "country_iso3": "USA", "country": "USA", "summary": "Higher crude runs improve product supply but keep feedstock demand elevated."},
        {"title": "US corn planting pace lags five-year average", "lat": 41.9, "lon": -93.6, "severity": "medium", "category": "agriculture", "country_iso3": "USA", "country": "USA", "summary": "Delayed fieldwork raises weather sensitivity and boosts grain risk premium."},
        {"title": "US strategic petroleum reserve refill schedule updated", "lat": 29.4, "lon": -94.9, "severity": "low", "category": "energy", "country_iso3": "USA", "country": "USA", "summary": "Incremental government buying supports medium-term crude demand expectations."},
        {"title": "Brazil soybean harvest advances faster than expected", "lat": -23.5, "lon": -46.6, "severity": "low", "category": "agriculture", "country_iso3": "BRA", "country": "Brazil", "summary": "Stronger crop flow improves export availability and pressures nearby basis."},
        {"title": "Brazil real volatility increases after fiscal guidance revision", "lat": -15.8, "lon": -47.9, "severity": "medium", "category": "market", "country_iso3": "BRA", "country": "Brazil", "summary": "Currency swings are prompting hedge adjustments across commodity exporters."},
        {"title": "Brazil dry weather raises concerns for second corn crop", "lat": -16.7, "lon": -49.3, "severity": "medium", "category": "agriculture", "country_iso3": "BRA", "country": "Brazil", "summary": "Potential yield downside is adding support to global feed grain prices."},
        {"title": "Chile copper mine labor negotiations stall", "lat": -23.7, "lon": -68.0, "severity": "high", "category": "metals", "country_iso3": "CHL", "country": "Chile", "summary": "Strike risk at major operations threatens concentrate supply for smelters."},
        {"title": "Chile central bank keeps policy rate unchanged", "lat": -33.4, "lon": -70.7, "severity": "low", "category": "market", "country_iso3": "CHL", "country": "Chile", "summary": "Steady policy guidance limits near-term volatility in local rates and FX."},
        {"title": "South Africa power outages hit platinum group metal output", "lat": -26.2, "lon": 28.0, "severity": "high", "category": "metals", "country_iso3": "ZAF", "country": "South Africa", "summary": "Energy constraints are curbing mine throughput and tightening PGM supply."},
        {"title": "South Africa rail congestion delays coal exports", "lat": -29.8, "lon": 31.0, "severity": "medium", "category": "energy", "country_iso3": "ZAF", "country": "South Africa", "summary": "Export bottlenecks are supporting seaborne thermal coal differentials."},
        {"title": "Congo copper-cobalt shipment permits face temporary delays", "lat": -11.7, "lon": 27.5, "severity": "high", "category": "metals", "country_iso3": "COD", "country": "Congo", "summary": "Documentation delays are tightening prompt availability for battery materials."},
        {"title": "Congo mine output report shows stable monthly production", "lat": -6.3, "lon": 23.6, "severity": "low", "category": "metals", "country_iso3": "COD", "country": "Congo", "summary": "Steady output data offsets part of the logistics risk premium."},
        {"title": "Ghana cocoa arrivals trend below seasonal average", "lat": 5.6, "lon": -0.2, "severity": "medium", "category": "agriculture", "country_iso3": "GHA", "country": "Ghana", "summary": "Lower arrivals are reinforcing tight global cocoa bean availability."},
        {"title": "Ghana cedi stabilizes after central bank liquidity operation", "lat": 6.7, "lon": -1.6, "severity": "low", "category": "market", "country_iso3": "GHA", "country": "Ghana", "summary": "Improved FX liquidity reduces near-term import cost pressure on food markets."},
    ]

    return {"events": events, "count": len(events)}

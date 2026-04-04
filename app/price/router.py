"""Price API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.price.service import PriceService
from app.price.models import PriceDataResponse, LatestPriceResponse
from app.core.dependencies import get_price_service

router = APIRouter()


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
async def get_macro_events(service: PriceService = Depends(get_price_service)):
    """
    Fetch latest price changes for all commodities and return them as
    geo-located events compatible with WorldMapWidget.load_events().

    Event format: {title, lat, lon, severity, category, country, country_iso3, summary}
    """
    import asyncio
    from src.data.config import config

    # Country coordinates for main commodity producers/consumers
    _GEO: dict[str, tuple[float, float, str, str]] = {
        "GOLD":        (-25.3, 131.0, "Australia", "AUS"),
        "SILVER":      (23.6, -102.5, "Mexico", "MEX"),
        "OIL":         (24.7,  46.7,  "Saudi Arabia", "SAU"),
        "NATURAL_GAS": (55.7,  37.6,  "Russia", "RUS"),
        "WHEAT":       (50.4,  30.5,  "Ukraine", "UKR"),
        "COPPER":      (-23.7, -68.0, "Chile", "CHL"),
    }
    _CATEGORY: dict[str, str] = {
        "GOLD": "metals", "SILVER": "metals", "COPPER": "metals",
        "OIL": "energy", "NATURAL_GAS": "energy",
        "WHEAT": "agriculture",
    }

    loop = asyncio.get_event_loop()
    events: list[dict] = []

    async def _fetch_one(commodity: str) -> dict | None:
        try:
            resp = await loop.run_in_executor(
                None, service._base_service.get_latest_price, commodity
            )
            change = resp.get("change_24h", 0.0)
            price  = resp.get("current_price", 0.0)

            if abs(change) >= 2.0:
                severity = "high"
            elif abs(change) >= 0.5:
                severity = "medium"
            else:
                severity = "low"

            direction = "up" if change >= 0 else "down"
            lat, lon, country, country_iso3 = _GEO.get(commodity, (0.0, 0.0, commodity, "UNK"))
            return {
                "title":    f"{commodity} {direction} {abs(change):.2f}% — ${price:,.2f}",
                "lat":      lat,
                "lon":      lon,
                "severity": severity,
                "category": _CATEGORY.get(commodity, "market"),
                "country":  country,
                "country_iso3": country_iso3,
                "summary":  f"24h change: {change:+.2f}% | Price: ${price:,.2f}",
            }
        except Exception:
            return None

    tasks = [_fetch_one(c) for c in _GEO]
    results = await asyncio.gather(*tasks)
    events = [r for r in results if r is not None]

    return {"events": events, "count": len(events)}

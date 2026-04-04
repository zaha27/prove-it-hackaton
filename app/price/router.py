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

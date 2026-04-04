"""Change API router."""

from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Optional

from app.change.service import ChangeService
from app.change.models import Change24hResponse, ChangeComparisonResponse
from app.core.dependencies import get_change_service

router = APIRouter()


@router.get(
    "/{commodity}",
    response_model=Change24hResponse,
    summary="Get 24-hour change",
    description="Retrieve 24-hour price change for a commodity",
)
async def get_24h_change(
    commodity: str = Path(..., description="Commodity symbol (e.g., GOLD, OIL)"),
    service: ChangeService = Depends(get_change_service),
):
    """Get 24-hour price change for a commodity."""
    try:
        return await service.get_24h_change(commodity.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/compare/{base_commodity}/{target_commodity}",
    response_model=ChangeComparisonResponse,
    summary="Compare 24-hour changes",
    description="Compare 24-hour price changes between two commodities",
)
async def compare_24h_change(
    base_commodity: str = Path(..., description="Base commodity symbol"),
    target_commodity: str = Path(..., description="Target commodity symbol"),
    service: ChangeService = Depends(get_change_service),
):
    """Compare 24-hour price changes between two commodities."""
    try:
        return await service.compare_24h_change(
            base_commodity.upper(), target_commodity.upper()
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

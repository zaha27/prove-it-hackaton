"""Macro API router."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_macro_service
from app.macro.models import MacroInsightResponse, MacroNewsItem
from app.macro.service import MacroService

router = APIRouter()


@router.get(
    "/news",
    response_model=List[MacroNewsItem],
    summary="Get global macro news",
    description="Retrieve general world macro news for economy, geopolitics and commodity markets",
)
async def get_macro_news(
    service: MacroService = Depends(get_macro_service),
):
    """Get world macro news."""
    try:
        return await service.get_macro_news()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/insight",
    response_model=MacroInsightResponse,
    summary="Get global macro insight",
    description="Retrieve a global macroeconomic overview for world commodity market context",
)
async def get_macro_insight(
    service: MacroService = Depends(get_macro_service),
):
    """Get world macro insight."""
    try:
        insight = await service.get_macro_insight()
        return MacroInsightResponse(insight=insight)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


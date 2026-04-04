"""Sentiment API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.sentiment.service import SentimentService
from app.sentiment.models import NewsResponse, SentimentSummary
from app.core.dependencies import get_sentiment_service

router = APIRouter()


@router.get(
    "/news/{commodity}",
    response_model=NewsResponse,
    summary="Get news articles",
    description="Retrieve news articles for a commodity with sentiment analysis",
)
async def get_news(
    commodity: str,
    days: int = Query(7, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(20, description="Maximum number of articles", ge=1, le=100),
    service: SentimentService = Depends(get_sentiment_service),
):
    """Get news articles for a commodity."""
    try:
        return await service.get_news(commodity.upper(), days, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/summary/{commodity}",
    response_model=SentimentSummary,
    summary="Get sentiment summary",
    description="Retrieve sentiment summary for a commodity",
)
async def get_sentiment_summary(
    commodity: str,
    days: int = Query(7, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(20, description="Maximum number of articles", ge=1, le=100),
    service: SentimentService = Depends(get_sentiment_service),
):
    """Get sentiment summary for a commodity."""
    try:
        return await service.get_sentiment_summary(commodity.upper(), days, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

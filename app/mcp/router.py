"""MCP API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any

from app.mcp.service import MCPService
from app.mcp.models import (
    MCPContextRequest,
    MCPContextResponse,
    MCPInsightRequest,
    MCPInsightResponse,
    ConsensusRequest,
    ConsensusResponse,
)
from app.core.dependencies import get_mcp_service

router = APIRouter()


@router.post(
    "/context",
    response_model=MCPContextResponse,
    summary="Get MCP context",
    description="Retrieve context using MCP (Gemini grounding when API key is configured)",
)
async def get_mcp_context(
    request: MCPContextRequest,
    service: MCPService = Depends(get_mcp_service),
):
    """Get context using MCP."""
    try:
        return await service.get_context(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/insight",
    response_model=MCPInsightResponse,
    summary="Get MCP-enhanced insight",
    description="Generate AI insight with optional MCP enhancement",
)
async def get_mcp_insight(
    request: MCPInsightRequest,
    service: MCPService = Depends(get_mcp_service),
):
    """Get AI insight with optional MCP enhancement."""
    try:
        return await service.get_insight(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/status",
    summary="Get MCP service status",
    description="Check if MCP/Gemini grounding service is available",
)
async def get_mcp_status():
    """Get MCP service status."""
    from src.data.config import config

    gemini_configured = bool(config.gemini_api_key)

    return {
        "service": "MCP/Gemini Grounding",
        "status": "available" if gemini_configured else "simulation_mode",
        "gemini_configured": gemini_configured,
        "description": (
            "MCP service with Gemini grounding is active."
            if gemini_configured
            else "MCP service running in simulation mode. Set GEMINI_API_KEY for real grounding."
        ),
        "capabilities": [
            "context_retrieval",
            "insight_enhancement",
            "grounded_information",
            "consensus_debate",
        ],
    }


@router.post(
    "/consensus/{commodity}",
    response_model=ConsensusResponse,
    summary="Get consensus trading recommendation",
    description="Run DeepSeek-Gemma4 debate loop to reach consensus on trading decision",
)
async def get_consensus_analysis(
    commodity: str,
    max_rounds: int = Query(5, description="Maximum debate rounds", ge=1, le=10),
    agreement_threshold: float = Query(0.8, description="Agreement threshold", ge=0.0, le=1.0),
    service: MCPService = Depends(get_mcp_service),
):
    """Get trading recommendation via DeepSeek-Gemma4 consensus debate.

    This endpoint runs a multi-round debate between DeepSeek and Gemma4 (with
    Gemini MCP web search) until they reach consensus on a trading decision.

    Returns full debate history and final recommendation.
    """
    try:
        request = ConsensusRequest(
            commodity=commodity.upper(),
            max_rounds=max_rounds,
            agreement_threshold=agreement_threshold,
        )
        return await service.get_consensus(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

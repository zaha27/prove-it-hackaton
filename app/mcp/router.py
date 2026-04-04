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
    summary="Get neuro-symbolic trading recommendation",
    description="XGBoost quantitative signal validated by DeepSeek Risk Manager",
)
async def get_consensus_analysis(
    commodity: str,
    request_body: ConsensusRequest = ConsensusRequest(),
    max_rounds: int = Query(3, description="Maximum rounds", ge=1, le=10),
    agreement_threshold: float = Query(0.8, description="Agreement threshold", ge=0.0, le=1.0),
    service: MCPService = Depends(get_mcp_service),
):
    """Get trading recommendation via XGBoost → DeepSeek neuro-symbolic pipeline.

    XGBoost computes the quantitative signal; DeepSeek validates it against macro news.
    Returns the full analysis including XGBoost input and DeepSeek's reality check.
    """
    try:
        # Always override commodity from the URL path (body may omit it)
        request = ConsensusRequest(
            commodity=commodity.upper(),
            max_rounds=request_body.max_rounds,
            agreement_threshold=request_body.agreement_threshold,
            risk_profile=request_body.risk_profile,
            risk_score=request_body.risk_score,
            investment_horizon=request_body.investment_horizon,
            market_familiarity=request_body.market_familiarity,
        )
        print(
            f"[consensus] commodity={request.commodity} "
            f"risk_profile={request.risk_profile} "
            f"risk_score={request.risk_score} "
            f"investment_horizon={request.investment_horizon} "
            f"market_familiarity={request.market_familiarity}"
        )
        return await service.get_consensus(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

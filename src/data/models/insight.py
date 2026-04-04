"""AI insight model definitions."""

from datetime import datetime

from pydantic import BaseModel, Field


class AIInsight(BaseModel):
    """AI-generated insight for a commodity."""

    commodity: str = Field(..., description="Commodity symbol")
    summary: str = Field(..., description="Executive summary of the analysis")
    key_factors: list[str] = Field(
        default_factory=list,
        description="Key factors affecting price (2-4 items)",
    )
    price_outlook: str = Field(
        default="", description="Price outlook with support/resistance levels"
    )
    recommendation: str = Field(
        default="", description="Trading recommendation"
    )
    sentiment: str = Field(
        default="neutral",
        description="Overall sentiment: bullish, bearish, neutral",
    )
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score (0-1)"
    )
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when insight was generated",
    )
    model: str = Field(
        default="deepseek-v3.2", description="LLM model used"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "commodity": "GOLD",
                "summary": "Bullish trend detected amid inflation concerns",
                "key_factors": [
                    "Inflation hedge demand rising",
                    "Central bank buying continues",
                    "Supply constraints in major mines",
                ],
                "price_outlook": "Resistance at $2050, support at $1980",
                "recommendation": "Accumulate on dips to $1990-2000 range",
                "sentiment": "bullish",
                "confidence": 0.82,
                "model": "deepseek-v3.2",
            }
        }

    def to_markdown(self) -> str:
        """Convert insight to markdown format for display."""
        factors_md = "\n".join(
            f"{i+1}. **{factor}**" for i, factor in enumerate(self.key_factors)
        )

        return f"""## {self.commodity} Price Analysis

**Current Trend:** {self.sentiment.upper()}

**Confidence:** {self.confidence:.0%}

### Key Factors:
{factors_md}

### Price Outlook:
{self.price_outlook}

### Recommendation:
{self.recommendation}

---
*Generated at {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')} using {self.model}*
"""

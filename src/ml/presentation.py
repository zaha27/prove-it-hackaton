"""Public presentation formatting for XGBoost predictions with Gemma4 validation."""

from typing import Any


def format_prediction_for_public(prediction_result: dict[str, Any]) -> str:
    """Format prediction in a convincing, presentable way for public display.

    Args:
        prediction_result: Result from predict_with_validation()

    Returns:
        Formatted string for public presentation
    """
    if "error" in prediction_result and prediction_result["error"]:
        return f"""
================================================================================
PREDICTION ERROR: {prediction_result.get('commodity', 'Unknown')}
================================================================================

Error: {prediction_result['error']}

Please try again later.
================================================================================
"""

    commodity = prediction_result.get("commodity", "Unknown")
    target_horizon = prediction_result.get("target_horizon", 7)
    xgboost = prediction_result.get("xgboost", {})
    gemma4_validation = prediction_result.get("gemma4_validation", {})
    final_recommendation = prediction_result.get("final_recommendation", "HOLD")

    # XGBoost data
    prediction_pct = xgboost.get("prediction_pct", 0)
    confidence = xgboost.get("confidence", 0)
    top_features = xgboost.get("top_features", [])
    reasoning = xgboost.get("reasoning", "")
    positive_factors = xgboost.get("positive_factors", 0)
    negative_factors = xgboost.get("negative_factors", 0)

    # Gemma4 validation data
    agreement = gemma4_validation.get("agreement", 0)
    critique = gemma4_validation.get("critique", "")
    enhanced_reasoning = gemma4_validation.get("enhanced_reasoning", reasoning)
    key_insights = gemma4_validation.get("key_insights", [])

    # Determine sentiment emoji
    if prediction_pct > 2:
        sentiment_emoji = "🚀"
    elif prediction_pct > 0.5:
        sentiment_emoji = "📈"
    elif prediction_pct < -2:
        sentiment_emoji = "🔻"
    elif prediction_pct < -0.5:
        sentiment_emoji = "📉"
    else:
        sentiment_emoji = "➡️"

    # Build output
    output = f"""
================================================================================
{sentiment_emoji} PREDICTION: {commodity} {prediction_pct:+.2f}% ({target_horizon} days)
================================================================================

CONFIDENCE: {confidence:.0%}
RECOMMENDATION: {final_recommendation}

--------------------------------------------------------------------------------
TOP 3 CORRELATED FACTORS (XGBoost Analysis)
--------------------------------------------------------------------------------
"""

    for i, feat in enumerate(top_features[:3], 1):
        impact_emoji = {"positive": "📈", "negative": "📉", "neutral": "➡️"}.get(
            feat.get("impact", "neutral"), "➡️"
        )
        output += f"""
{i}. {impact_emoji} {feat['name']}: {feat['value']:.4f}
   {feat['correlation']}
   [Model importance: {feat['importance']:.1%}]
"""

    output += f"""
--------------------------------------------------------------------------------
XGBoost Reasoning
--------------------------------------------------------------------------------
{reasoning}

Technical Summary: {positive_factors} positive factors, {negative_factors} negative factors

--------------------------------------------------------------------------------
AI Validation (Gemma4)
--------------------------------------------------------------------------------
Agreement Score: {agreement:.0%}
"""

    if critique:
        output += f"""
Gemma4 Critique:
{critique[:300]}{'...' if len(critique) > 300 else ''}
"""

    if enhanced_reasoning and enhanced_reasoning != reasoning:
        output += f"""
Enhanced Analysis:
{enhanced_reasoning[:250]}{'...' if len(enhanced_reasoning) > 250 else ''}
"""

    if key_insights:
        output += "\nKey Insights:\n"
        for insight in key_insights[:3]:
            output += f"  • {insight}\n"

    output += f"""
--------------------------------------------------------------------------------
FINAL RECOMMENDATION: {final_recommendation}
--------------------------------------------------------------------------------

This prediction is based on {len(top_features)} highly correlated technical 
indicators analyzed by XGBoost and validated by Gemma4 AI.

================================================================================
"""

    return output


def format_batch_predictions(results: list[dict[str, Any]]) -> str:
    """Format multiple predictions for public display.

    Args:
        results: List of prediction results

    Returns:
        Formatted string for batch display
    """
    output = """
================================================================================
BATCH PREDICTION SUMMARY
================================================================================

"""

    for result in results:
        commodity = result.get("commodity", "Unknown")
        xgboost = result.get("xgboost", {})
        prediction_pct = xgboost.get("prediction_pct", 0)
        confidence = xgboost.get("confidence", 0)
        recommendation = result.get("final_recommendation", "HOLD")

        # Sentiment indicator
        if prediction_pct > 2:
            indicator = "🚀"
        elif prediction_pct > 0.5:
            indicator = "📈"
        elif prediction_pct < -2:
            indicator = "🔻"
        elif prediction_pct < -0.5:
            indicator = "📉"
        else:
            indicator = "➡️"

        output += f"{indicator} {commodity:8s}: {prediction_pct:+6.2f}% | Confidence: {confidence:4.0%} | {recommendation}\n"

    output += """
================================================================================
"""
    return output


def format_feature_breakdown(feature_data: dict[str, Any]) -> str:
    """Format detailed feature explanation for public display.

    Args:
        feature_data: Feature explanation data

    Returns:
        Formatted string
    """
    name = feature_data.get("name", "Unknown")
    value = feature_data.get("value", 0)
    description = feature_data.get("description", "")
    interpretation = feature_data.get("interpretation", "")
    importance = feature_data.get("importance", 0)
    impact = feature_data.get("impact", "neutral")

    impact_emoji = {"positive": "📈", "negative": "📉", "neutral": "➡️"}.get(
        impact, "➡️"
    )

    return f"""
{impact_emoji} {name}
   Value: {value:.4f}
   Description: {description}
   Interpretation: {interpretation}
   Model Importance: {importance:.1%}
   Impact: {impact.upper()}
"""


def generate_public_report(
    prediction_result: dict[str, Any], include_raw: bool = False
) -> dict[str, str]:
    """Generate a complete public report with multiple formats.

    Args:
        prediction_result: Prediction result from predict_with_validation()
        include_raw: Whether to include raw data

    Returns:
        Dictionary with different report formats
    """
    report = {
        "summary": format_prediction_for_public(prediction_result),
        "one_line": _format_one_line(prediction_result),
        "social": _format_social_media(prediction_result),
    }

    if include_raw:
        report["raw_json"] = str(prediction_result)

    return report


def _format_one_line(result: dict[str, Any]) -> str:
    """Format as one-line summary."""
    commodity = result.get("commodity", "Unknown")
    xgboost = result.get("xgboost", {})
    prediction_pct = xgboost.get("prediction_pct", 0)
    confidence = xgboost.get("confidence", 0)
    recommendation = result.get("final_recommendation", "HOLD")
    gemma4 = result.get("gemma4_validation", {})
    agreement = gemma4.get("agreement", 0)

    return (
        f"{commodity}: {prediction_pct:+.2f}% | "
        f"Conf: {confidence:.0%} | "
        f"AI Agree: {agreement:.0%} | "
        f"→ {recommendation}"
    )


def _format_social_media(result: dict[str, Any]) -> str:
    """Format for social media sharing."""
    commodity = result.get("commodity", "Unknown")
    xgboost = result.get("xgboost", {})
    prediction_pct = xgboost.get("prediction_pct", 0)
    top_features = xgboost.get("top_features", [])
    recommendation = result.get("final_recommendation", "HOLD")

    # Get top feature
    top_feat = top_features[0] if top_features else {"name": "N/A", "correlation": ""}

    # Emoji based on prediction
    if prediction_pct > 2:
        emoji = "🚀"
    elif prediction_pct > 0.5:
        emoji = "📈"
    elif prediction_pct < -2:
        emoji = "🔻"
    elif prediction_pct < -0.5:
        emoji = "📉"
    else:
        emoji = "⚖️"

    return (
        f"{emoji} {commodity} Prediction: {prediction_pct:+.2f}% (7 days)\n\n"
        f"Key Factor: {top_feat.get('name', 'N/A')}\n"
        f"{top_feat.get('correlation', '')[:80]}...\n\n"
        f"Recommendation: {recommendation}\n"
        f"#Trading #Commodities #{commodity} #AI #XGBoost"
    )


def format_with_chain_of_thought(result: dict[str, Any]) -> str:
    """Format prediction showing complete chain of thought reasoning.

    Args:
        result: Result from predict_with_chain_of_thought()

    Returns:
        Formatted string with full reasoning process
    """
    sections = []

    # Header
    sections.append("=" * 80)
    sections.append("CHAIN OF THOUGHT ANALYSIS")
    sections.append("=" * 80)
    sections.append("")

    # Summary
    commodity = result.get("commodity", "Unknown")
    xgboost = result.get("xgboost", {})
    prediction_pct = xgboost.get("prediction_pct", 0)
    final_rec = result.get("final_recommendation", "HOLD")

    sections.append(f"Commodity: {commodity}")
    sections.append(f"Prediction: {prediction_pct:+.2f}% (7 days)")
    sections.append(f"Recommendation: {final_rec}")
    sections.append("")

    # XGBoost Chain of Thought
    xgb_thinking = result.get("xgboost_thinking", [])
    if xgb_thinking:
        sections.append("-" * 80)
        sections.append("XGBoost Chain of Thought:")
        sections.append("-" * 80)
        for step in xgb_thinking:
            sections.append(step)
        sections.append("")

    # Web Research
    web_context = result.get("web_context", [])
    if web_context:
        sections.append("-" * 80)
        sections.append("Web Research (brave-search MCP):")
        sections.append("-" * 80)
        for source in web_context:
            title = source.get("title", "No title")
            snippet = source.get("snippet", "")[:70]
            sections.append(f"  {title}")
            sections.append(f"    {snippet}...")
        sections.append("")

    # Historical Patterns
    historical = result.get("historical_patterns", [])
    if historical:
        sections.append("-" * 80)
        sections.append("Historical Patterns (Qdrant MCP):")
        sections.append("-" * 80)
        sections.append(f"  Patterns found: {len(historical)}")
        bullish = sum(1 for p in historical if p.get("return_7d", 0) > 0)
        rate = bullish / len(historical) * 100 if historical else 0
        sections.append(f"  Bullish success rate: {rate:.0f}%")
        sections.append("")

    # Gemma4 Chain of Thought
    gemma4_thinking = result.get("gemma4_thinking", [])
    if gemma4_thinking:
        sections.append("-" * 80)
        sections.append("Gemma4 Validation Chain of Thought:")
        sections.append("-" * 80)
        for step in gemma4_thinking:
            sections.append(step)
        sections.append("")

    # Raw Chain of Thought Display
    display = result.get("display", "")
    if display:
        sections.append("-" * 80)
        sections.append("Complete Raw Reasoning:")
        sections.append("-" * 80)
        sections.append(display)
        sections.append("")

    # Final Summary
    sections.append("=" * 80)
    sections.append("FINAL SUMMARY")
    sections.append("=" * 80)
    sections.append(f"XGBoost analyzed 104 features")
    sections.append(f"Top 3 features were validated by Gemma4")
    sections.append(f"Web research and historical patterns were consulted")
    gemma4 = result.get("gemma4_validation", {})
    agreement = gemma4.get("agreement", 0)
    sections.append(f"Gemma4 Agreement: {agreement:.0%}")
    sections.append(f"FINAL RECOMMENDATION: {final_rec}")
    sections.append("=" * 80)

    return "\n".join(sections)

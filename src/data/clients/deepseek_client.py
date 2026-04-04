"""DeepSeek API client for LLM-powered insights."""

import json
from typing import Any

from openai import OpenAI

from src.data.config import config
from src.data.models.insight import AIInsight


class DeepSeekClient:
    """Client for DeepSeek V3.2 API."""

    def __init__(self) -> None:
        """Initialize the DeepSeek client."""
        self.api_key = config.deepseek_api_key
        self.base_url = config.deepseek_base_url

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        ) if self.api_key else None

        self.model = "deepseek-chat"  # DeepSeek V3.2

    def _build_insight_prompt(
        self,
        commodity: str,
        price_data: dict[str, Any],
        news_summary: str,
    ) -> str:
        """Build the Chain-of-Thought prompt for insight generation.

        Args:
            commodity: Commodity symbol
            price_data: Dictionary with price information
            news_summary: Summary of recent news

        Returns:
            Formatted prompt string
        """
        current_price = price_data.get("current_price", 0)
        change_24h = price_data.get("change_24h", 0)
        price_trend = price_data.get("trend", "neutral")

        return f"""You are an expert commodity analyst. Analyze the following data for {commodity} and provide a structured insight.

## Price Data
- Current Price: ${current_price:,.2f}
- 24h Change: {change_24h:+.2f}%
- Trend: {price_trend}

## Recent News Summary
{news_summary}

## Task
Analyze the data using Chain-of-Thought reasoning:
1. Identify the key factors driving price movement
2. Assess market sentiment (bullish/bearish/neutral)
3. Determine support and resistance levels
4. Provide a trading recommendation

## Output Format
Return ONLY a valid JSON object with this exact structure:
{{
    "summary": "Brief executive summary (1-2 sentences)",
    "key_factors": ["Factor 1", "Factor 2", "Factor 3"],
    "price_outlook": "Technical analysis with support/resistance",
    "recommendation": "Clear trading action",
    "sentiment": "bullish|bearish|neutral",
    "confidence": 0.85
}}

Requirements:
- key_factors must have 2-4 items
- sentiment must be exactly: bullish, bearish, or neutral
- confidence must be between 0.0 and 1.0
- Be specific with price levels in recommendation"""

    def _parse_insight_response(self, response_text: str, commodity: str) -> AIInsight:
        """Parse the LLM response into an AIInsight object.

        Args:
            response_text: Raw response from LLM
            commodity: Commodity symbol

        Returns:
            AIInsight object
        """
        try:
            # Extract JSON from response (handle markdown code blocks)
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            data = json.loads(text)

            return AIInsight(
                commodity=commodity,
                summary=data.get("summary", "Analysis completed"),
                key_factors=data.get("key_factors", []),
                price_outlook=data.get("price_outlook", ""),
                recommendation=data.get("recommendation", ""),
                sentiment=data.get("sentiment", "neutral"),
                confidence=data.get("confidence", 0.5),
                model=self.model,
            )

        except json.JSONDecodeError as e:
            # Fallback if JSON parsing fails
            return AIInsight(
                commodity=commodity,
                summary="Analysis generated but parsing failed. Raw response available.",
                key_factors=["Data analyzed"],
                price_outlook="See raw data",
                recommendation="Review manually",
                sentiment="neutral",
                confidence=0.3,
                model=self.model,
            )

    def generate(
        self,
        prompt: str,
        system: str = "You are a helpful assistant.",
        temperature: float = 0.3,
        max_tokens: int = 1000,
    ) -> str:
        """Generate text using DeepSeek API.

        Args:
            prompt: The user prompt
            system: System message
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        if not self.client:
            raise ValueError("DeepSeek API key not configured")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise ValueError(f"DeepSeek generation failed: {e}") from e

    def generate_insight(
        self,
        commodity: str,
        price_data: dict[str, Any],
        news_summary: str,
    ) -> AIInsight:
        """Generate AI insight for a commodity.

        Args:
            commodity: Commodity symbol
            price_data: Dictionary with price information
            news_summary: Summary of recent news

        Returns:
            AIInsight object

        Raises:
            ValueError: If API key is not configured
        """
        if not self.client:
            raise ValueError("DeepSeek API key not configured")

        prompt = self._build_insight_prompt(commodity, price_data, news_summary)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst specializing in commodity markets. Provide structured, actionable insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower for more consistent output
                max_tokens=800,
            )

            response_text = response.choices[0].message.content or ""
            return self._parse_insight_response(response_text, commodity)

        except Exception as e:
            raise ValueError(f"Failed to generate insight for {commodity}: {e}") from e

    def generate_streaming_insight(
        self,
        commodity: str,
        price_data: dict[str, Any],
        news_summary: str,
    ):
        """Generate AI insight with streaming response.

        Args:
            commodity: Commodity symbol
            price_data: Dictionary with price information
            news_summary: Summary of recent news

        Yields:
            Chunks of the response text
        """
        if not self.client:
            raise ValueError("DeepSeek API key not configured")

        prompt = self._build_insight_prompt(commodity, price_data, news_summary)

        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst specializing in commodity markets."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=800,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            raise ValueError(f"Failed to stream insight for {commodity}: {e}") from e

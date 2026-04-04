"""Ollama client for local Gemma4 2B model."""

import json
import os
from typing import Any

import requests

from src.data.config import config


class OllamaClient:
    """Client for local Ollama Gemma4 2B model."""

    def __init__(self, base_url: str | None = None) -> None:
        """Initialize the Ollama client.

        Args:
            base_url: Ollama API base URL (defaults to config)
        """
        # Use provided URL, env var, or config default
        # For WSL connecting to Windows host: http://host.docker.internal:11434
        if base_url is None:
            base_url = os.getenv("OLLAMA_HOST", config.ollama_base_url)
        self.base_url = base_url.rstrip("/")
        self.model = config.ollama_model
        self.timeout = 120  # 2 minutes timeout for deep reasoning

    def _call_api(
        self, prompt: str, system: str | None = None, temperature: float = 0.3
    ) -> str:
        """Call Ollama API.

        Args:
            prompt: User prompt
            system: System message
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        url = f"{self.base_url}/api/generate"

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,
            },
        }

        if system:
            payload["system"] = system

        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                f"Is Ollama running? Run: ollama serve"
            ) from e
        except requests.exceptions.Timeout as e:
            raise TimeoutError(
                f"Ollama request timed out after {self.timeout}s"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}") from e

    def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text from Gemma4.

        Args:
            prompt: User prompt
            system: Optional system message

        Returns:
            Generated text
        """
        return self._call_api(prompt, system=system)

    def generate_with_grounding(
        self,
        prompt: str,
        system: str | None = None,
        search_query: str | None = None,
        gemini_mcp=None,
    ) -> dict[str, Any]:
        """Generate text with Gemini MCP web search grounding.

        Args:
            prompt: User prompt
            system: Optional system message
            search_query: Query for web search (defaults to prompt summary)
            gemini_mcp: Gemini grounding MCP tool

        Returns:
            Dict with 'response', 'sources', and 'grounding_used'
        """
        sources = []
        grounding_context = ""

        # Use Gemini MCP for web search if available
        if gemini_mcp and search_query:
            try:
                search_result = gemini_mcp.search_with_grounding(query=search_query)
                sources = search_result.get("sources", [])
                grounding_context = search_result.get("grounding", "")
            except Exception as e:
                grounding_context = f"[Web search failed: {e}]"

        # Enhance prompt with grounding context
        enhanced_prompt = prompt
        if grounding_context:
            enhanced_prompt = f"""{prompt}

## Web Search Results
{grounding_context}

Use the above web search results to inform your analysis."""

        # Generate response
        response = self._call_api(enhanced_prompt, system=system)

        return {
            "response": response,
            "sources": sources,
            "grounding_used": bool(grounding_context),
            "original_prompt": prompt,
        }

    def analyze_patterns(
        self, patterns: list[dict[str, Any]], question: str
    ) -> dict[str, Any]:
        """Analyze patterns and find commonalities.

        Args:
            patterns: List of pattern dictionaries
            question: Question to answer about patterns

        Returns:
            Analysis result with insights
        """
        system = """You are a pattern analysis expert. Analyze the given patterns and provide structured insights.
Respond in JSON format with keys: "findings" (list), "confidence" (0-1), "recommendations" (list)."""

        prompt = f"""Analyze these patterns:

{json.dumps(patterns[:20], indent=2)}

Question: {question}

Provide your analysis in JSON format."""

        response = self._call_api(prompt, system=system, temperature=0.2)

        # Try to parse JSON from response
        try:
            # Extract JSON if wrapped in markdown
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            return {
                "findings": [response],
                "confidence": 0.5,
                "recommendations": [],
            }

    def generate_hypothesis(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Generate testable hypothesis from observation.

        Args:
            observation: Observation data

        Returns:
            Hypothesis with test plan
        """
        system = """You are a research scientist. Generate testable hypotheses from observations.
Respond in JSON format with keys: "hypothesis" (string), "test_method" (string), "expected_outcome" (string)."""

        prompt = f"""Given this observation:

{json.dumps(observation, indent=2)}

Generate a testable hypothesis and describe how to test it.
Respond in JSON format."""

        response = self._call_api(prompt, system=system, temperature=0.4)

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            return {
                "hypothesis": response,
                "test_method": "Manual verification required",
                "expected_outcome": "Unknown",
            }

    def write_analysis_script(self, task_description: str, data_schema: dict[str, Any]) -> str:
        """Write Python script for data analysis.

        Args:
            task_description: What the script should do
            data_schema: Schema of available data

        Returns:
            Python script as string
        """
        system = """You are a Python data scientist. Write clean, efficient analysis scripts.
Use pandas, numpy, and sklearn. Include error handling and comments.
Only output the Python code, no markdown formatting."""

        prompt = f"""Write a Python script to: {task_description}

Available data schema:
{json.dumps(data_schema, indent=2)}

Requirements:
1. Use pandas for data manipulation
2. Include proper error handling
3. Save results to a JSON file
4. Print key findings to stdout
5. Use type hints where appropriate

Output only the Python code:"""

        response = self._call_api(prompt, system=system, temperature=0.2)

        # Clean up response
        code = response.strip()
        if code.startswith("```python"):
            code = code.split("```python")[1]
        if code.startswith("```"):
            code = code.split("```")[1]
        if code.endswith("```"):
            code = code.rsplit("```", 1)[0]

        return code.strip()

    def deep_reasoning(
        self, context: str, question: str, confidence_threshold: float = 0.7
    ) -> dict[str, Any]:
        """Perform deep reasoning on complex questions.

        Only use for low-confidence scenarios.

        Args:
            context: Background context
            question: Question to reason about
            confidence_threshold: Minimum confidence for direct answer

        Returns:
            Reasoning result with confidence
        """
        system = """You are a deep reasoning engine. Think step-by-step and provide evidence-backed conclusions.
Respond in JSON format with keys: "reasoning" (string), "conclusion" (string), "confidence" (0-1), "evidence" (list)."""

        prompt = f"""Context:
{context}

Question: {question}

Think through this step-by-step:
1. What do we know for certain?
2. What are the key uncertainties?
3. What patterns or correlations might exist?
4. What is the most likely conclusion?

Provide your reasoning in JSON format."""

        response = self._call_api(prompt, system=system, temperature=0.3)

        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response

            result = json.loads(json_str.strip())

            # Only return if confidence is sufficient
            if result.get("confidence", 0) < confidence_threshold:
                result["needs_more_research"] = True

            return result
        except json.JSONDecodeError:
            return {
                "reasoning": response,
                "conclusion": "Unable to parse structured response",
                "confidence": 0.3,
                "evidence": [],
                "needs_more_research": True,
            }

    def check_health(self) -> dict[str, Any]:
        """Check if Ollama is running and model is available.

        Returns:
            Health status dictionary
        """
        try:
            # Check if Ollama is running
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=5
            )
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check if our model is available
            model_available = any(
                self.model in name or name.startswith("gemma4")
                for name in model_names
            )

            return {
                "status": "healthy" if model_available else "model_missing",
                "available_models": model_names,
                "required_model": self.model,
                "model_available": model_available,
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "unavailable",
                "error": "Cannot connect to Ollama",
                "required_model": self.model,
                "model_available": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "required_model": self.model,
                "model_available": False,
            }

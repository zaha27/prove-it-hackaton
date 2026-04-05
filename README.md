# Commodity AI Analyzer

> **Institutional-grade, Neuro-Symbolic AI trading platform. Where Quantitative Mathematics meets Macroeconomic Reasoning.**

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-Frontend-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-Quant_Engine-orange.svg)
![DeepSeek](https://img.shields.io/badge/DeepSeek-Risk_Manager-blueviolet.svg)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-FF5252.svg)

## The Problem & The Solution

Traditional quantitative models (like pure Machine Learning or ARIMA) are mathematically precise but completely "blind" to the real world. They break down during geopolitical shocks or "Black Swan" events. Conversely, pure LLMs understand news but hallucinate numbers and lack statistical rigor.

**The Solution:** A **Neuro-Symbolic Architecture**. 
We combine the statistical power of **XGBoost** (The Quant) with the contextual and geopolitical reasoning of **DeepSeek LLM** (The Risk Manager). Every trade signal requires a *Consensus* between the two. If the math says "BUY" but the LLM detects a war breaking out in the news, the system overrides the trade to protect capital.

## Key Features (The "Wow" Factor)

* **Neuro-Symbolic Consensus Engine:** Evaluates 104 technical features via XGBoost and cross-references them against live Yahoo Finance news using DeepSeek.
* **Institutional Out-of-Sample Benchmark:** Prove it works! A rigorous backtesting engine using a strict 50/50 chronological split. Simulates realistic trading with fixed position sizing ($1,000/trade) and strict slippage/commission costs (0.1%).
* **"What-If" Stress Test Simulator (God Mode):** Input a hypothetical geopolitical shock (e.g., *"Fed unexpectedly raises rates +100 bps"*), and the LLM instantly recalculates the strategy's Alpha, ROI, and Risk/Reward parameters without touching the live database.
* **Episodic Memory via Qdrant:** The system learns from past mistakes. Predictions are vectorized and stored in Qdrant. Before making a new call, the AI retrieves similar past scenarios (RAG) to see if this pattern previously failed or succeeded.
* **World Macro View:** A live, geo-tagged Leaflet.js map tracking supply shocks, conflicts, and central bank decisions globally.
* **AI Alpha Strategy Report:** Automatically generates a Bloomberg-style institutional tear sheet with Entry, Stop Loss, Take Profit, and Risk Matrix, exportable to PDF.

---

## Architecture Stack

1. **Frontend:** `PyQt6` for a native, lightning-fast desktop experience. Charts are rendered using `QWebEngineView` integrating *Lightweight Charts (TradingView)* and *Plotly*.
2. **Backend Engine:** `FastAPI` serving as the brain coordinator.
3. **Machine Learning:** `XGBoost` for predicting 7-day forward returns based on complex momentum, volatility, and volume indicators.
4. **Agentic LLM:** `DeepSeek V3.2` API for unstructured text analysis, sentiment scoring, and reasoning.
5. **Vector Database:** `Qdrant` running in Docker to store historical price patterns and track prediction outcomes.
6. **Data Ingestion:** Live streams via `yfinance` (Yahoo Finance).

---

## Quick Start / Setup Guide

This project is optimized for `uv`, the lightning-fast Python package manager.

### 1. Prerequisites
* Python 3.12+
* Docker Desktop (for the Qdrant database)
* `uv` installed (`pip install uv`)

### 2. Environment Variables
Create a `.env` file in the `config/` directory (or project root) and add your API keys:
```env
DEEPSEEK_API_KEY="your_deepseek_api_key_here"
BACKEND_URL="http://localhost:8000"

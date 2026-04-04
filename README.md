# AI Commodity Price Intelligence Platform

> An AI-powered platform for traders to anticipate price fluctuations in energy and metals commodities.

## Overview

This hackathon project provides an intelligent solution for traders and companies who need to anticipate commodity price movements. The platform combines real-time data collection, machine learning predictions, and LLM-powered insights to deliver actionable intelligence.

## Problem

Traders and companies struggle to efficiently anticipate price fluctuations for:
- **Energy commodities** (oil, natural gas, electricity)
- **Metals** (gold, silver, copper, lithium)

## Solution

Our platform offers:

### 📊 Data Collection
- Real-time and historical commodity prices
- News feeds and geopolitical events
- Market indicators and trends

### 🤖 AI Capabilities
- **Time-series prediction** for accurate price forecasting
- **Sentiment analysis** on news and social media
- **LLM interpretation** for natural language insights ("Why did the price spike?")

### 📈 Dashboard
- Visual analytics and charts
- Predictions and confidence intervals
- Actionable insights

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Sources   │────▶│  Processing     │────▶│  AI Engine      │
│  - APIs         │     │  - Feature Eng. │     │  - LLM          │
│  - News Feeds   │     │  - Transform    │     │  - Predictions  │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                ┌─────────────────┐
                                                │  Dashboard      │
                                                │  - Visualize    │
                                                │  - Insights     │
                                                └─────────────────┘
```

## Team Structure

The project is organized into 3 development tracks:

| Developer | Focus Area | Exclusive Files |
|-----------|------------|-----------------|
| **Dev 1** | Backend - Data + AI Engine | `src/data/` |
| **Dev 2** | Frontend - PyQt UI | `src/ui/` |
| **Dev 3** | Charts + Final Wiring | `src/charts/` + `bridge.py` |

### Dev 1 - Backend Responsibilities
- Fetch prices from yfinance
- Fetch news (NewsAPI/GDELT)
- LLM API calls with Chain-of-Thought
- Return structured insights
- Expose: `get_price_data()`, `get_news()`, `get_ai_insight()`

### Dev 2 - Frontend Responsibilities
- QMainWindow with 3 panels
- Sidebar: commodity selector
- News panel + sentiment badge
- AI text panel (scroll, stream)
- qdarktheme + Bloomberg feel
- Expose: `set_chart_widget()`, `on_commodity_change`, `update_news()`, `update_insight()`

### Dev 3 - Charts & Integration Responsibilities
- Plotly candlestick + volume charts
- Technical indicators (RSI, MACD)
- QWebEngineView embed
- `bridge.py`: Connects UI ↔ Data ↔ Charts
- Final integration
- Expose: `ChartWidget`, `.load_data()`, `.set_indicator()`

## Tech Stack

- **Python**: 3.12+
- **Package Manager**: uv
- **Data**: yfinance, NewsAPI, GDELT
- **AI/ML**: Time-series models, sentiment analysis, LLM integration
- **Frontend**: PyQt6, qdarktheme
- **Charts**: Plotly, QWebEngineView

## Project Structure

```
prove-it-hackaton/
├── src/                      # Source code
│   ├── data/                 # Dev 1: Backend Data + AI Engine
│   │   └── mock_data.py      # Mock data for development (hour 1)
│   ├── ui/                   # Dev 2: PyQt Frontend
│   │   └── main_window.py    # Main window with 3 panels
│   └── charts/               # Dev 3: Graphics + Wiring
│       ├── chart_widget.py   # Plotly chart widget
│       └── bridge.py         # UI-Data-Chart integration
├── tests/                    # Test files
├── docs/                     # Documentation
├── config/                   # Configuration files
├── .qoder/                   # Qoder IDE configuration
│   ├── agents/               # Custom agents
│   └── skills/               # Custom skills
├── Proba.md                  # Project brief and requirements
├── README.md                 # This file
├── pyproject.toml            # UV project configuration
├── main.py                   # Application entry point
├── .python-version           # Python version specification
└── .gitignore                # Git ignore rules
```

## Getting Started

### Prerequisites

- Python 3.12+
- uv package manager

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd prove-it-hackaton

# Install dependencies with uv
uv sync

# Run the application
uv run python main.py
```

### Development Workflow

Each developer works in their designated folder:

1. **Dev 1** implements data fetching in `src/data/`
2. **Dev 2** builds the UI in `src/ui/`
3. **Dev 3** creates charts and integration in `src/charts/`

Mock data is available in `src/data/mock_data.py` for parallel development.

## Requirements Met

- ✅ AI component (required)
- ✅ Data flow pipeline: collection → processing → output
- ✅ Functional MVP
- ✅ Real use-case justified
- ✅ Git repository with source code

## Presentation Structure

1. **Problem** - The issue being solved
2. **Impact** - Why it matters
3. **Solution** - How the platform works
4. **Demo** - Live demonstration
5. **Architecture** - Technical design
6. **AI/LLM Role** - How AI contributes
7. **Scalability** - Future improvements

## Evaluation Criteria

| Category | Weight |
|----------|--------|
| Technical Component | 35% |
| Idea & Innovation | 30% |
| Presentation | 35% |

---

*Built for the Hackathon - demonstrating the intersection of AI and commodity trading intelligence.*

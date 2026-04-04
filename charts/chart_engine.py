"""
charts/chart_engine.py — Build Plotly candlestick charts and return HTML strings.
"""
import json
import logging

logger = logging.getLogger(__name__)

# Bloomberg-inspired dark theme colours
_BG = "#0D1117"
_GRID = "#1C2128"
_TEXT = "#CDD9E5"
_ACCENT = "#FFD700"
_GREEN = "#26a69a"
_RED = "#ef5350"


def build_candlestick(ohlcv: dict, indicator: str = "none") -> str:
    """
    Build a dark-themed Plotly candlestick + volume HTML string.

    Args:
        ohlcv: dict with keys dates, open, high, low, close, volume, symbol, currency.
        indicator: one of "none", "rsi", "macd", "bollinger".

    Returns:
        A self-contained HTML string that can be loaded into QWebEngineView.
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots

        dates = ohlcv["dates"]
        symbol = ohlcv.get("symbol", "")
        currency = ohlcv.get("currency", "USD")

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3],
        )

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=dates,
                open=ohlcv["open"],
                high=ohlcv["high"],
                low=ohlcv["low"],
                close=ohlcv["close"],
                name=symbol,
                increasing_line_color=_GREEN,
                decreasing_line_color=_RED,
                increasing_fillcolor=_GREEN,
                decreasing_fillcolor=_RED,
                hovertext=[
                    f"O: {o}  H: {h}  L: {l}  C: {c}"
                    for o, h, l, c in zip(
                        ohlcv["open"], ohlcv["high"], ohlcv["low"], ohlcv["close"]
                    )
                ],
            ),
            row=1,
            col=1,
        )

        # Volume bars
        colors = [
            _GREEN if c >= o else _RED
            for o, c in zip(ohlcv["open"], ohlcv["close"])
        ]
        fig.add_trace(
            go.Bar(
                x=dates,
                y=ohlcv["volume"],
                name="Volume",
                marker_color=colors,
                opacity=0.7,
            ),
            row=2,
            col=1,
        )

        # Optional indicators
        if indicator == "bollinger":
            _add_bollinger_traces(fig, ohlcv)

        layout = dict(
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            font=dict(color=_TEXT, family="Consolas, Courier New, monospace", size=12),
            title=dict(
                text=f"{symbol} — {currency}",
                font=dict(color=_ACCENT, size=16),
            ),
            xaxis=dict(
                rangeslider=dict(visible=False),
                gridcolor=_GRID,
                linecolor=_GRID,
                showgrid=True,
            ),
            xaxis2=dict(gridcolor=_GRID, linecolor=_GRID),
            yaxis=dict(gridcolor=_GRID, linecolor=_GRID, showgrid=True),
            yaxis2=dict(gridcolor=_GRID, linecolor=_GRID, showgrid=True),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor=_GRID,
                font=dict(color=_TEXT),
            ),
            margin=dict(l=50, r=20, t=50, b=40),
            hovermode="x unified",
        )
        fig.update_layout(**layout)

        return fig.to_html(
            full_html=True,
            include_plotlyjs="cdn",
            config={"displayModeBar": False},
        )

    except Exception as exc:
        logger.error("chart_engine error: %s", exc)
        return _error_html(str(exc))


def _add_bollinger_traces(fig, ohlcv: dict) -> None:
    """Add Bollinger Band traces to an existing figure."""
    try:
        import pandas as pd
        from charts.indicators import add_bollinger

        df = pd.DataFrame({"close": ohlcv["close"]}, index=ohlcv["dates"])
        df = add_bollinger(df)

        import plotly.graph_objects as go

        for col, color, name in [
            ("bb_upper", "#7986CB", "BB Upper"),
            ("bb_mid", _ACCENT, "BB Mid"),
            ("bb_lower", "#7986CB", "BB Lower"),
        ]:
            fig.add_trace(
                go.Scatter(
                    x=ohlcv["dates"],
                    y=df[col].tolist(),
                    name=name,
                    line=dict(color=color, width=1, dash="dot"),
                    opacity=0.7,
                ),
                row=1,
                col=1,
            )
    except Exception as exc:
        logger.warning("Failed to add Bollinger bands: %s", exc)


def _error_html(message: str) -> str:
    return f"""
    <html><body style="background:#0D1117;color:#ef5350;font-family:monospace;padding:40px;">
    <h2>Chart Error</h2><pre>{message}</pre>
    </body></html>
    """


PLACEHOLDER_HTML = f"""
<html>
<body style="background:{_BG};display:flex;align-items:center;justify-content:center;
             height:100vh;margin:0;">
  <div style="text-align:center;font-family:Consolas,monospace;color:{_TEXT};">
    <div style="font-size:48px;color:{_ACCENT};">◈</div>
    <div style="font-size:18px;margin-top:16px;">Select a commodity</div>
    <div style="font-size:13px;color:#555;margin-top:8px;">from the sidebar to load chart data</div>
  </div>
</body>
</html>
"""

"""
charts/chart_engine.py — Build Plotly candlestick charts and return HTML strings.
"""
import json
import logging

logger = logging.getLogger(__name__)

# Perplexity palette — near-black + baby blue (matches ui/styles/theme.py)
_BG     = "#080808"   # deepest bg
_PANEL  = "#0D0D0D"   # panel bg
_GRID   = "#1C1C1C"   # subtle grid
_TEXT   = "#F1F5F9"   # primary text
_MUTED  = "#6B7280"   # secondary text
_ACCENT = "#93C5FD"   # baby blue
_DIM    = "#374151"   # very muted
_GREEN  = "#4ADE80"   # bullish
_RED    = "#F87171"   # bearish


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

        _axis = dict(
            gridcolor=_GRID,
            linecolor=_GRID,
            tickfont=dict(color=_MUTED, size=11, family="SF Mono, Menlo, monospace"),
            showgrid=True,
            zeroline=False,
        )
        layout = dict(
            paper_bgcolor=_BG,
            plot_bgcolor=_PANEL,
            font=dict(color=_TEXT, family="SF Mono, Menlo, monospace", size=12),
            title=dict(
                text=f"<b>{symbol}</b>  <span style='color:{_MUTED};font-size:12px'>{currency}</span>",
                font=dict(color=_ACCENT, size=15, family="SF Mono, Menlo, monospace"),
                x=0.01,
                xanchor="left",
            ),
            xaxis=dict(rangeslider=dict(visible=False), **_axis),
            xaxis2=_axis.copy(),
            yaxis=_axis.copy(),
            yaxis2=_axis.copy(),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor=_GRID,
                font=dict(color=_MUTED, size=11),
            ),
            margin=dict(l=55, r=20, t=48, b=36),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="#111827",
                bordercolor=_GRID,
                font=dict(color=_TEXT, size=12, family="SF Mono, Menlo, monospace"),
            ),
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
            ("bb_upper", _PURPLE, "BB Upper"),
            ("bb_mid",   _ACCENT, "BB Mid"),
            ("bb_lower", _PURPLE, "BB Lower"),
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
    return f"""<!DOCTYPE html>
<html>
<body style="background:{_BG};color:{_RED};
             font-family:'SF Mono',Menlo,monospace;padding:40px;margin:0;">
  <div style="font-size:13px;font-weight:600;margin-bottom:12px;">Chart Error</div>
  <pre style="color:{_MUTED};font-size:12px;line-height:1.6;">{message}</pre>
</body></html>"""


PLACEHOLDER_HTML = f"""<!DOCTYPE html>
<html>
<body style="background:{_BG};margin:0;height:100vh;
             display:flex;align-items:center;justify-content:center;">
  <div style="text-align:center;font-family:-apple-system,'Segoe UI',Arial,sans-serif;">
    <div style="width:40px;height:40px;background:#111111;border:1px solid #1C1C1C;
                border-radius:8px;margin:0 auto 20px;display:flex;
                align-items:center;justify-content:center;">
      <span style="color:{_ACCENT};font-size:18px;font-weight:700;
                   font-family:'SF Mono',Menlo,monospace;">C</span>
    </div>
    <div style="font-size:14px;font-weight:500;color:{_TEXT};letter-spacing:0.3px;">
      Select a commodity
    </div>
    <div style="font-size:12px;color:{_MUTED};margin-top:6px;">
      Choose from the sidebar to load chart data
    </div>
  </div>
</body></html>"""

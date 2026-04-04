"""
charts/chart_engine.py — Build Plotly candlestick charts and return HTML strings.
"""
import logging
from datetime import datetime, date

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
        def _to_date(value):
            if isinstance(value, datetime):
                return value
            if isinstance(value, date):
                return datetime.combine(value, datetime.min.time())
            return pd.to_datetime(str(value))

        dates = [_to_date(v) for v in ohlcv["dates"]]
        opens = [float(v) for v in ohlcv["open"]]
        highs = [float(v) for v in ohlcv["high"]]
        lows = [float(v) for v in ohlcv["low"]]
        closes = [float(v) for v in ohlcv["close"]]
        volumes = [float(v) for v in ohlcv["volume"]]
        volume_colors = [_GREEN if c >= o else _RED for o, c in zip(opens, closes)]

        if indicator in {"rsi", "macd"}:
            fig = make_subplots(
                rows=3,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.60, 0.20, 0.20],
            )
            volume_row = 3
        else:
            fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.75, 0.25],
            )
            volume_row = 2

        fig.add_trace(
            go.Candlestick(
                x=dates,
                open=opens,
                high=highs,
                low=lows,
                close=closes,
                increasing_line_color=_GREEN,
                decreasing_line_color=_RED,
                showlegend=False,
                name="Price",
            ),
            row=1,
            col=1,
        )

        if indicator == "bollinger":
            close_s = pd.Series(closes)
            bb_mid = close_s.rolling(window=20).mean()
            bb_std = close_s.rolling(window=20).std()
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std
            fig.add_trace(go.Scatter(x=dates, y=bb_mid, mode="lines", line=dict(color=_ACCENT, width=1), name="BB Mid"), row=1, col=1)
            fig.add_trace(go.Scatter(x=dates, y=bb_upper, mode="lines", line=dict(color=_DIM, width=1), name="BB Upper"), row=1, col=1)
            fig.add_trace(go.Scatter(x=dates, y=bb_lower, mode="lines", line=dict(color=_DIM, width=1), name="BB Lower", fill="tonexty", fillcolor="rgba(147,197,253,0.08)"), row=1, col=1)
        elif indicator == "rsi":
            close_s = pd.Series(closes)
            delta = close_s.diff()
            gain = delta.clip(lower=0).rolling(window=14).mean()
            loss = (-delta.clip(upper=0)).rolling(window=14).mean()
            rs = gain / loss.replace(0, pd.NA)
            rsi = 100 - (100 / (1 + rs))
            fig.add_trace(go.Scatter(x=dates, y=rsi, mode="lines", line=dict(color=_ACCENT, width=1.5), name="RSI"), row=2, col=1)
            fig.add_hline(y=70, line=dict(color=_DIM, width=1, dash="dot"), row=2, col=1)
            fig.add_hline(y=30, line=dict(color=_DIM, width=1, dash="dot"), row=2, col=1)
            fig.update_yaxes(range=[0, 100], row=2, col=1)
        elif indicator == "macd":
            close_s = pd.Series(closes)
            ema_fast = close_s.ewm(span=12, adjust=False).mean()
            ema_slow = close_s.ewm(span=26, adjust=False).mean()
            macd = ema_fast - ema_slow
            signal = macd.ewm(span=9, adjust=False).mean()
            hist = macd - signal
            hist_colors = [_GREEN if v >= 0 else _RED for v in hist.fillna(0).tolist()]
            fig.add_trace(go.Bar(x=dates, y=hist, marker_color=hist_colors, name="MACD Hist"), row=2, col=1)
            fig.add_trace(go.Scatter(x=dates, y=macd, mode="lines", line=dict(color=_ACCENT, width=1.5), name="MACD"), row=2, col=1)
            fig.add_trace(go.Scatter(x=dates, y=signal, mode="lines", line=dict(color=_MUTED, width=1.2), name="Signal"), row=2, col=1)

        fig.add_trace(
            go.Bar(
                x=dates,
                y=volumes,
                marker_color=volume_colors,
                opacity=0.7,
                showlegend=False,
                name="Volume",
            ),
            row=volume_row,
            col=1,
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=_BG,
            plot_bgcolor=_PANEL,
            font=dict(color=_TEXT, size=11),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0.0),
        )
        fig.update_xaxes(showgrid=True, gridcolor=_GRID, zeroline=False)
        fig.update_yaxes(showgrid=True, gridcolor=_GRID, zeroline=False)

        return fig.to_html(
            full_html=True,
            include_plotlyjs="inline",
            config={"displayModeBar": False, "responsive": True},
        )

    except Exception as exc:
        logger.error("chart_engine error: %s", exc)
        return _error_html(str(exc))


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

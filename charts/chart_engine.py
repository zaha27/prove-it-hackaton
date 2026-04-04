"""
charts/chart_engine.py — Build Lightweight Charts candlestick charts and return HTML strings.
"""
import json
import logging
from datetime import datetime, date

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
    Build a dark-themed Lightweight Charts candlestick + volume HTML string.

    Args:
        ohlcv: dict with keys dates, open, high, low, close, volume, symbol, currency.
        indicator: one of "none", "rsi", "macd", "bollinger".

    Returns:
        A self-contained HTML string that can be loaded into QWebEngineView.
    """
    try:
        def _to_date_str(value) -> str:
            if isinstance(value, datetime):
                return value.date().isoformat()
            if isinstance(value, date):
                return value.isoformat()
            text = str(value)
            if len(text) >= 10:
                return text[:10]
            return text

        dates = ohlcv["dates"]
        opens = ohlcv["open"]
        highs = ohlcv["high"]
        lows = ohlcv["low"]
        closes = ohlcv["close"]
        volumes = ohlcv["volume"]

        price_data = [
            {
                "time": _to_date_str(t),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
            }
            for t, o, h, l, c in zip(dates, opens, highs, lows, closes)
        ]

        volume_data = [
            {
                "time": _to_date_str(t),
                "value": v,
                "color": _GREEN if c >= o else _RED,
            }
            for t, o, c, v in zip(dates, opens, closes, volumes)
        ]

        price_json = json.dumps(price_data, ensure_ascii=False)
        volume_json = json.dumps(volume_data, ensure_ascii=False)

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    html, body, #container {{
      width: 100vw;
      height: 100vh;
      position: absolute;
      top: 0;
      left: 0;
      margin: 0;
      background: {_PANEL};
      overflow: hidden;
    }}
  </style>
</head>
<body>
  <div id="container"></div>
  <script>
    const chart = LightweightCharts.createChart(document.getElementById('container'), {{
      layout: {{
        background: {{ color: '#0D0D0D' }},
        textColor: '#F1F5F9',
      }},
      grid: {{
        vertLines: {{ color: '#1C1C1C' }},
        horzLines: {{ color: '#1C1C1C' }},
      }},
      width: window.innerWidth,
      height: window.innerHeight,
    }});

    const candlestickSeries = chart.addCandlestickSeries({{
      upColor: '#4ADE80',
      downColor: '#F87171',
      wickUpColor: '#4ADE80',
      wickDownColor: '#F87171',
      borderVisible: false
    }});
    candlestickSeries.setData({price_json});

    const volumeSeries = chart.addHistogramSeries({{
      priceScaleId: '',
      priceFormat: {{ type: 'volume' }},
      scaleMargins: {{ top: 0.8, bottom: 0 }}
    }});
    volumeSeries.setData({volume_json});

    chart.timeScale().fitContent();

    window.addEventListener('resize', () => {{
      chart.applyOptions({{
        width: window.innerWidth,
        height: window.innerHeight
      }});
    }});
  </script>
</body>
</html>"""

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

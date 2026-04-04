"""
charts/chart_engine.py — Build Plotly candlestick charts and return HTML strings.
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
        def _to_iso_date(value):
            if isinstance(value, datetime):
                return value.strftime("%Y-%m-%d")
            if isinstance(value, date):
                return value.strftime("%Y-%m-%d")
            text = str(value)
            if "T" in text:
                text = text.split("T", 1)[0]
            if " " in text:
                text = text.split(" ", 1)[0]
            return text

        dates = ohlcv["dates"]
        opens = ohlcv["open"]
        highs = ohlcv["high"]
        lows = ohlcv["low"]
        closes = ohlcv["close"]
        volumes = ohlcv["volume"]

        candles = []
        volumes_data = []
        for d, o, h, l, c, v in zip(dates, opens, highs, lows, closes, volumes):
            time_value = _to_iso_date(d)
            open_value = float(o)
            close_value = float(c)
            candles.append(
                {
                    "time": time_value,
                    "open": open_value,
                    "high": float(h),
                    "low": float(l),
                    "close": close_value,
                }
            )
            volumes_data.append(
                {
                    "time": time_value,
                    "value": float(v),
                    "color": "rgba(74,222,128,0.5)" if close_value >= open_value else "rgba(248,113,113,0.5)",
                }
            )

        candles.sort(key=lambda item: item["time"])
        volumes_data.sort(key=lambda item: item["time"])

        candles_json = json.dumps(candles)
        volume_json = json.dumps(volumes_data)

        html_template = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body { margin: 0; padding: 0; background-color: #080808; overflow: hidden; }
#chart { width: 100vw; height: 100vh; }
</style>
</head>
<body>
  <div id="chart"></div>
  <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
  <script>
    const chart = LightweightCharts.createChart(document.getElementById('chart'), {
      layout: { background: { type: 'solid', color: '#0D0D0D' }, textColor: '#F1F5F9' },
      grid: { vertLines: { color: '#1C1C1C' }, horzLines: { color: '#1C1C1C' } },
      crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#1C1C1C' },
      timeScale: { borderColor: '#1C1C1C', timeVisible: true }
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#4ADE80',
      downColor: '#F87171',
      borderVisible: false,
      wickUpColor: '#4ADE80',
      wickDownColor: '#F87171'
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
      scaleMargins: { top: 0.75, bottom: 0 }
    });

    const candlesData = DATA_CANDLES;
    const volumeData = DATA_VOLUME;

    candleSeries.setData(candlesData);
    volumeSeries.setData(volumeData);
    chart.timeScale().fitContent();

    window.addEventListener('resize', function() {
      chart.resize(window.innerWidth, window.innerHeight);
    });
  </script>
</body>
</html>
"""
        return html_template.replace("DATA_CANDLES", candles_json).replace("DATA_VOLUME", volume_json)

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

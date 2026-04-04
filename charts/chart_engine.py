import json
import logging

logger = logging.getLogger(__name__)

_BG     = "#080808"
_PANEL  = "#0D0D0D"
_GRID   = "#1C1C1C"
_TEXT   = "#F1F5F9"
_MUTED  = "#6B7280"
_ACCENT = "#93C5FD"
_GREEN  = "#4ADE80"
_RED    = "#F87171"

_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { margin: 0; padding: 0; background-color: #080808; overflow: hidden; }
        #tvchart { width: 100vw; height: 100vh; position: absolute; top: 0; left: 0; }
    </style>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
</head>
<body>
    <div id="tvchart"></div>
    <script>
        try {
            const chartOptions = {
                layout: { 
                    textColor: '#F1F5F9', 
                    background: { type: 'solid', color: '#0D0D0D' } 
                },
                grid: { 
                    vertLines: { color: '#1C1C1C' }, 
                    horzLines: { color: '#1C1C1C' } 
                },
                crosshair: { 
                    mode: LightweightCharts.CrosshairMode.Normal 
                },
                rightPriceScale: { 
                    borderColor: '#1C1C1C' 
                },
                timeScale: { 
                    borderColor: '#1C1C1C', 
                    timeVisible: true 
                }
            };
            
            const chart = LightweightCharts.createChart(document.getElementById('tvchart'), chartOptions);

            // Candlesticks (Sintaxa corecta pentru v4+)
            const candlestickSeries = chart.addCandlestickSeries({
                upColor: '#4ADE80', 
                downColor: '#F87171', 
                borderVisible: false,
                wickUpColor: '#4ADE80', 
                wickDownColor: '#F87171'
            });
            candlestickSeries.setData(__CANDLES_DATA__);

            // Volume (Sintaxa corecta pentru v4+)
            const volumeSeries = chart.addHistogramSeries({
                priceFormat: { type: 'volume' },
                priceScaleId: '', // overlay pe chart
            });
            volumeSeries.priceScale().applyOptions({
                scaleMargins: { top: 0.8, bottom: 0 } // jos de tot
            });
            volumeSeries.setData(__VOLUMES_DATA__);

            chart.timeScale().fitContent();

            // Responsive
            window.addEventListener('resize', () => {
                chart.resize(window.innerWidth, window.innerHeight);
            });
            
        } catch (error) {
            console.error(error);
            document.body.innerHTML = '<div style="color:#F87171; padding:20px; font-family:monospace;">Chart Render Error: ' + error.message + '</div>';
        }
    </script>
</body>
</html>"""

def build_candlestick(ohlcv: dict, indicator: str = "none") -> str:
    """Returneaza codul HTML complet cu TradingView Lightweight Charts injectat cu date."""
    try:
        if not ohlcv or "dates" not in ohlcv or not ohlcv["dates"]:
            return _error_html("No valid data provided to chart engine.")

        candles = []
        volumes = []
        
        # Procesam listele in dict-urile asteptate de TradingView
        for i in range(len(ohlcv["dates"])):
            t = ohlcv["dates"][i]
            o = ohlcv["open"][i]
            h = ohlcv["high"][i]
            l = ohlcv["low"][i]
            c = ohlcv["close"][i]
            v = ohlcv["volume"][i]
            
            candles.append({"time": t, "open": o, "high": h, "low": l, "close": c})
            
            # Culoare verde transparent pentru up, rosu transparent pentru down
            vol_color = "rgba(74,222,128,0.4)" if c >= o else "rgba(248,113,113,0.4)"
            volumes.append({"time": t, "value": v, "color": vol_color})

        # Sortare obligatorie pentru TradingView (crapa daca nu sunt in ordine cronologica)
        candles.sort(key=lambda x: x["time"])
        volumes.sort(key=lambda x: x["time"])

        # Convertim in format JSON (string)
        candles_json = json.dumps(candles)
        volumes_json = json.dumps(volumes)

        # Injectam datele curat in template-ul HTML
        html = _HTML_TEMPLATE.replace("__CANDLES_DATA__", candles_json)
        html = html.replace("__VOLUMES_DATA__", volumes_json)

        return html

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
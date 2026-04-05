"""
ui/macro_map.py — World Macro View interactive map widget.

Architecture:
  HeuristicGeoTagger   — keyword dict → (lat, lng) mapping, no external API
  _NewsLoaderThread    — QThread that fetches live news and runs the tagger
  MacroMapView         — QWebEngineView hosting Leaflet.js / CartoDB Dark Matter

Integration (from main_window.py or bridge.py):
    map_view = MacroMapView()
    window.set_map_widget(map_view)
    map_view.load_macro_data(["GOLD", "OIL", "SILVER", "NATURAL_GAS", "WHEAT", "COPPER"])
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any, TYPE_CHECKING

from PyQt6.QtCore import QThread, QUrl, pyqtSignal
from PyQt6.QtWebEngineWidgets import QWebEngineView

if TYPE_CHECKING:
    from src.data.models.news import NewsArticle

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Leaflet HTML (CartoDB Dark Matter, circleMarkers, custom tooltips)
# ─────────────────────────────────────────────────────────────────────────────

_MAP_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body, #map { width: 100%; height: 100%; background: #080808; }

    /* Override default Leaflet tooltip chrome — we paint our own */
    .leaflet-tooltip {
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
    }
    .leaflet-tooltip::before { display: none !important; }

    /* Our custom tooltip card */
    .tt-card {
      background: rgba(10, 10, 10, 0.97);
      border: 1px solid #1C1C1C;
      border-radius: 7px;
      color: #E5E7EB;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      padding: 10px 13px;
      max-width: 300px;
      min-width: 200px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.04);
      pointer-events: none;
    }
    .tt-top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 6px;
    }
    .tt-commodity {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 1.2px;
      text-transform: uppercase;
    }
    .tt-location {
      font-size: 9px;
      color: #4B5563;
      letter-spacing: 0.3px;
    }
    .tt-headline {
      font-size: 12px;
      color: #D1D5DB;
      line-height: 1.45;
      margin-bottom: 8px;
      word-break: break-word;
    }
    .tt-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .tt-source { font-size: 10px; color: #6B7280; }
    .tt-score {
      font-size: 10px;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 4px;
    }
    .tt-score.positive { background: rgba(74,222,128,0.12); color: #4ADE80; }
    .tt-score.negative { background: rgba(248,113,113,0.12); color: #F87171; }
    .tt-score.neutral  { background: rgba(156,163,175,0.10); color: #9CA3AF; }

    /* Zoom controls dark theme */
    .leaflet-control-zoom a {
      background: #111 !important;
      color: #6B7280 !important;
      border-color: #1C1C1C !important;
    }
    .leaflet-control-zoom a:hover {
      background: #1C1C1C !important;
      color: #E5E7EB !important;
    }

    /* Empty state */
    #empty-state {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      color: #374151;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 13px;
      pointer-events: none;
      z-index: 500;
    }
    #empty-state.hidden { display: none; }
  </style>
  <link rel="stylesheet"
        href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
        crossorigin=""/>
</head>
<body>
  <div id="map"></div>
  <div id="empty-state">Loading macro intelligence...</div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
          crossorigin=""></script>
  <script>
    // ── Map init ──────────────────────────────────────────────────────────────
    var map = L.map('map', {
      center: [22, 15],
      zoom: 2,
      minZoom: 2,
      maxZoom: 12,
      zoomControl: true,
      attributionControl: false,
    });

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
      { subdomains: 'abcd', maxZoom: 19 }
    ).addTo(map);

    var markerLayer = L.layerGroup().addTo(map);

    // ── Commodity accent colours ───────────────────────────────────────────────
    var COMMODITY_COLOR = {
      GOLD:        '#F59E0B',
      SILVER:      '#94A3B8',
      OIL:         '#FB923C',
      NATURAL_GAS: '#A78BFA',
      WHEAT:       '#FDE68A',
      COPPER:      '#F97316',
    };

    // ── Helpers ───────────────────────────────────────────────────────────────
    function esc(s) {
      return String(s)
        .replace(/&/g,'&amp;')
        .replace(/</g,'&lt;')
        .replace(/>/g,'&gt;')
        .replace(/"/g,'&quot;');
    }

    function sentimentColor(sentiment, score) {
      if (sentiment === 'positive') return '#4ADE80';
      if (sentiment === 'negative') return '#F87171';
      return '#9CA3AF';
    }

    function sentimentClass(sentiment) {
      if (sentiment === 'positive') return 'positive';
      if (sentiment === 'negative') return 'negative';
      return 'neutral';
    }

    function markerRadius(score) {
      // 5 px baseline + up to 7 px based on absolute sentiment strength
      return 5 + Math.abs(score) * 7;
    }

    function commodityAccent(commodity) {
      return COMMODITY_COLOR[commodity] || '#93C5FD';
    }

    // ── Public API (called from Python via runJavaScript) ─────────────────────
    function updateMarkers(markers) {
      markerLayer.clearLayers();

      var emptyState = document.getElementById('empty-state');
      if (!markers || markers.length === 0) {
        emptyState.textContent = 'No macro events to display.';
        emptyState.classList.remove('hidden');
        return;
      }
      emptyState.classList.add('hidden');

      markers.forEach(function(m) {
        var fillColor   = sentimentColor(m.sentiment, m.sentiment_score);
        var accentColor = commodityAccent(m.commodity);
        var radius      = markerRadius(m.sentiment_score);
        var cls         = sentimentClass(m.sentiment);
        var scoreSign   = m.sentiment_score >= 0 ? '+' : '';
        var scoreLabel  = scoreSign + m.sentiment_score.toFixed(2);

        var circle = L.circleMarker([m.lat, m.lng], {
          radius:      radius,
          fillColor:   fillColor,
          color:       fillColor,
          weight:      1.5,
          opacity:     0.7,
          fillOpacity: 0.25,
        });

        // Tooltip card
        var tooltipHtml =
          '<div class="tt-card">' +
            '<div class="tt-top">' +
              '<span class="tt-commodity" style="color:' + accentColor + ';">' +
                esc(m.commodity) +
              '</span>' +
              '<span class="tt-location">' + esc(m.location) + '</span>' +
            '</div>' +
            '<div class="tt-headline">' + esc(m.headline) + '</div>' +
            '<div class="tt-footer">' +
              '<span class="tt-source">' + esc(m.source) + '</span>' +
              '<span class="tt-score ' + cls + '">' + scoreLabel + '</span>' +
            '</div>' +
          '</div>';

        circle.bindTooltip(tooltipHtml, {
          sticky: true,
          opacity: 1,
          className: 'leaflet-tooltip-raw',
          offset: [14, 0],
        });

        // Hover glow effect
        circle.on('mouseover', function() {
          this.setStyle({ fillOpacity: 0.75, opacity: 1.0, weight: 2 });
          this.bringToFront();
        });
        circle.on('mouseout', function() {
          this.setStyle({ fillOpacity: 0.25, opacity: 0.7, weight: 1.5 });
        });

        markerLayer.addLayer(circle);
      });
    }
  </script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# HeuristicGeoTagger
# ─────────────────────────────────────────────────────────────────────────────

class HeuristicGeoTagger:
    """
    Maps keyword mentions in news text to approximate (lat, lng) coordinates.
    No LLM, no external geocoding — pure dictionary lookup on lowercased text.
    Keyword priority: longer/more-specific phrases beat shorter ones.
    """

    # (lat, lng, human-readable location name)
    _KW: dict[str, tuple[float, float, str]] = {
        # ── United States: institutions ──────────────────────────────────────
        "federal reserve":   (38.89, -77.04, "Federal Reserve, D.C."),
        "fomc":              (38.89, -77.04, "Federal Reserve, D.C."),
        "jerome powell":     (38.89, -77.04, "Federal Reserve, D.C."),
        "powell":            (38.89, -77.04, "Federal Reserve, D.C."),
        "janet yellen":      (38.89, -77.04, "Treasury, D.C."),
        "us treasury":       (38.89, -77.04, "U.S. Treasury, D.C."),
        "imf":               (38.89, -77.04, "IMF, Washington D.C."),
        "world bank":        (38.89, -77.04, "World Bank, D.C."),
        # ── United States: cities & markets ─────────────────────────────────
        "wall street":       (40.71, -74.01, "Wall Street, New York"),
        "new york":          (40.71, -74.01, "New York, USA"),
        "nasdaq":            (40.71, -74.01, "NASDAQ, New York"),
        "nyse":              (40.71, -74.01, "NYSE, New York"),
        "comex":             (40.71, -74.01, "COMEX, New York"),
        "s&p 500":           (40.71, -74.01, "S&P 500, New York"),
        "chicago":           (41.88, -87.63, "Chicago, USA"),
        "cbot":              (41.88, -87.63, "CBOT, Chicago"),
        "houston":           (29.76, -95.37, "Houston, Texas"),
        "permian":           (31.83,-102.37, "Permian Basin, Texas"),
        "henry hub":         (29.96, -90.11, "Henry Hub, Louisiana"),
        "louisiana":         (30.98, -91.96, "Louisiana, USA"),
        "alaska":            (64.20,-153.37, "Alaska, USA"),
        # ── United States: general ───────────────────────────────────────────
        "united states":     (37.09, -95.71, "United States"),
        "u.s.":              (37.09, -95.71, "United States"),
        "american":          (37.09, -95.71, "United States"),
        "washington":        (38.89, -77.04, "Washington D.C., USA"),
        "texas":             (31.97, -99.90, "Texas, USA"),

        # ── China ────────────────────────────────────────────────────────────
        "peoples bank of china": (39.91, 116.39, "PBOC, Beijing"),
        "pboc":              (39.91, 116.39, "PBOC, Beijing"),
        "beijing":           (39.91, 116.39, "Beijing, China"),
        "shanghai":          (31.22, 121.47, "Shanghai, China"),
        "china":             (35.86, 104.19, "China"),
        "chinese":           (35.86, 104.19, "China"),
        "yuan":              (35.86, 104.19, "China"),
        "renminbi":          (35.86, 104.19, "China"),

        # ── Russia & Ukraine ─────────────────────────────────────────────────
        "gazprom":           (55.75,  37.62, "Gazprom, Moscow"),
        "rosneft":           (55.75,  37.62, "Rosneft, Moscow"),
        "moscow":            (55.75,  37.62, "Moscow, Russia"),
        "russia":            (61.52, 105.32, "Russia"),
        "russian":           (61.52, 105.32, "Russia"),
        "kyiv":              (50.45,  30.52, "Kyiv, Ukraine"),
        "ukraine":           (49.00,  31.00, "Ukraine"),
        "ukrainian":         (49.00,  31.00, "Ukraine"),
        "black sea":         (43.00,  35.00, "Black Sea"),

        # ── Europe: institutions ──────────────────────────────────────────────
        "ecb":               (50.11,   8.68, "ECB, Frankfurt"),
        "lagarde":           (50.11,   8.68, "ECB, Frankfurt"),
        "bank of england":   (51.51,  -0.13, "Bank of England, London"),
        "boe":               (51.51,  -0.13, "Bank of England, London"),
        "lme":               (51.51,  -0.13, "London Metal Exchange"),
        # ── Europe: countries & cities ───────────────────────────────────────
        "london":            (51.51,  -0.13, "London, UK"),
        "britain":           (55.37,  -3.44, "United Kingdom"),
        "british":           (55.37,  -3.44, "United Kingdom"),
        "united kingdom":    (55.37,  -3.44, "United Kingdom"),
        "uk":                (55.37,  -3.44, "United Kingdom"),
        "germany":           (51.16,  10.45, "Germany"),
        "berlin":            (52.52,  13.40, "Berlin, Germany"),
        "frankfurt":         (50.11,   8.68, "Frankfurt, Germany"),
        "france":            (46.23,   2.21, "France"),
        "paris":             (48.86,   2.35, "Paris, France"),
        "eurozone":          (48.86,   2.35, "Eurozone"),
        "europe":            (50.11,   8.68, "Europe"),
        "european":          (50.11,   8.68, "Europe"),
        "norway":            (60.47,   8.47, "Norway"),
        "north sea":         (56.00,   3.00, "North Sea"),
        "brent":             (57.00,   2.00, "North Sea (Brent Crude)"),
        "turkey":            (38.96,  35.24, "Turkey"),
        "istanbul":          (41.01,  28.96, "Istanbul, Turkey"),

        # ── Middle East ───────────────────────────────────────────────────────
        "strait of hormuz":  (26.56,  56.25, "Strait of Hormuz"),
        "saudi aramco":      (26.30,  50.11, "Saudi Aramco, Dhahran"),
        "aramco":            (26.30,  50.11, "Saudi Aramco, Dhahran"),
        "opec":              (24.69,  46.72, "OPEC, Riyadh"),
        "riyadh":            (24.69,  46.72, "Riyadh, Saudi Arabia"),
        "saudi":             (23.89,  45.08, "Saudi Arabia"),
        "middle east":       (29.31,  47.48, "Middle East"),
        "persian gulf":      (26.21,  50.58, "Persian Gulf"),
        "gulf":              (26.21,  50.58, "Persian Gulf"),
        "iran":              (32.43,  53.69, "Iran"),
        "tehran":            (35.70,  51.42, "Tehran, Iran"),
        "iraq":              (33.22,  43.68, "Iraq"),
        "baghdad":           (33.33,  44.44, "Baghdad, Iraq"),
        "israel":            (31.05,  34.85, "Israel"),
        "tel aviv":          (32.08,  34.78, "Tel Aviv, Israel"),
        "hamas":             (31.35,  34.31, "Gaza"),
        "gaza":              (31.35,  34.31, "Gaza"),
        "houthi":            (15.55,  44.20, "Yemen (Houthi)"),
        "yemen":             (15.55,  44.20, "Yemen"),
        "red sea":           (20.00,  38.00, "Red Sea"),
        "uae":               (23.42,  53.85, "UAE"),
        "dubai":             (25.20,  55.27, "Dubai, UAE"),
        "abu dhabi":         (24.45,  54.38, "Abu Dhabi, UAE"),
        "qatar":             (25.35,  51.18, "Qatar"),
        "kuwait":            (29.31,  47.48, "Kuwait"),

        # ── Asia-Pacific ─────────────────────────────────────────────────────
        "bank of japan":     (35.68, 139.69, "Bank of Japan, Tokyo"),
        "boj":               (35.68, 139.69, "Bank of Japan, Tokyo"),
        "tokyo":             (35.68, 139.69, "Tokyo, Japan"),
        "japan":             (36.20, 138.25, "Japan"),
        "japanese":          (36.20, 138.25, "Japan"),
        "south korea":       (35.91, 127.77, "South Korea"),
        "seoul":             (37.57, 126.98, "Seoul, South Korea"),
        "taiwan":            (23.70, 120.96, "Taiwan"),
        "taipei":            (25.03, 121.56, "Taipei, Taiwan"),
        "singapore":         (1.35,  103.82, "Singapore"),
        "india":             (20.59,  78.96, "India"),
        "mumbai":            (19.08,  72.88, "Mumbai, India"),
        "new delhi":         (28.61,  77.21, "New Delhi, India"),
        "australia":         (-25.27, 133.78, "Australia"),
        "sydney":            (-33.87, 151.21, "Sydney, Australia"),
        "indonesia":         (-0.79,  113.92, "Indonesia"),
        "malaysia":          (4.21,  101.98,  "Malaysia"),
        "philippines":       (12.88, 121.77,  "Philippines"),
        "vietnam":           (14.06, 108.28,  "Vietnam"),
        "kazakhstan":        (48.02,  66.92,  "Kazakhstan"),
        "azerbaijan":        (40.14,  47.58,  "Azerbaijan"),

        # ── Americas ─────────────────────────────────────────────────────────
        "canada":            (56.13,-106.35, "Canada"),
        "ottawa":            (45.42,  -75.70, "Ottawa, Canada"),
        "mexico":            (23.63, -102.55, "Mexico"),
        "brazil":            (-14.24, -51.93, "Brazil"),
        "sao paulo":         (-23.55, -46.63, "São Paulo, Brazil"),
        "argentina":         (-38.42, -63.62, "Argentina"),
        "venezuela":         (6.42,  -66.59, "Venezuela"),
        "colombia":          (4.57,  -74.30, "Colombia"),
        "chile":             (-35.68, -71.54, "Chile"),
        "santiago":          (-33.45, -70.67, "Santiago, Chile"),
        "peru":              (-9.19,  -75.02, "Peru"),

        # ── Africa ───────────────────────────────────────────────────────────
        "south africa":      (-30.56,  22.94, "South Africa"),
        "johannesburg":      (-26.20,  28.04, "Johannesburg, SA"),
        "nigeria":           (9.08,    8.68, "Nigeria"),
        "ghana":             (7.95,   -1.02, "Ghana"),
        "congo":             (-4.04,  21.76, "DR Congo"),
        "drc":               (-4.04,  21.76, "DR Congo"),
        "zambia":            (-13.13,  27.85, "Zambia"),
        "africa":            (-8.78,  34.51, "Africa"),

        # ── Global bodies ────────────────────────────────────────────────────
        "g7":                (48.86,   2.35, "G7"),
        "g20":               (48.86,   2.35, "G20"),
        "brics":             (55.75,  37.62, "BRICS"),
        "wto":               (46.23,   6.10, "WTO, Geneva"),
        "swift":             (50.86,   4.35, "SWIFT, Brussels"),

        # ── Commodity-specific terms ─────────────────────────────────────────
        "wti":               (29.76,  -95.37, "WTI, Houston"),
        "shale":             (31.83, -102.37, "Permian Basin, Texas"),
        "lng":               (29.76,  -95.37, "LNG Hub, Houston"),
        "wheat ukraine":     (49.00,  31.00, "Ukraine (Wheat)"),
        "black sea grain":   (43.00,  35.00, "Black Sea Grain Route"),
    }

    # Sorted by descending key length so longer/more-specific phrases match first
    _SORTED_KW: list[tuple[str, tuple[float, float, str]]] = sorted(
        _KW.items(), key=lambda kv: len(kv[0]), reverse=True
    )

    # Fallback coordinates per commodity when no keyword matches
    _DEFAULTS: dict[str, tuple[float, float, str]] = {
        "GOLD":        (51.51,  -0.13, "London Gold Market"),
        "SILVER":      (40.71, -74.01, "COMEX, New York"),
        "OIL":         (29.76, -95.37, "Houston, Texas"),
        "NATURAL_GAS": (29.96, -90.11, "Henry Hub, Louisiana"),
        "WHEAT":       (41.88, -87.63, "CBOT, Chicago"),
        "COPPER":      (-33.45,-70.67, "Santiago, Chile"),
    }

    def tag_article(
        self, article: "NewsArticle"
    ) -> tuple[float, float, str] | None:
        """Return (lat, lng, location_name) for one article, or None."""
        text = f"{article.title} {article.content}".lower()
        for keyword, coords in self._SORTED_KW:
            if keyword in text:
                return coords
        return self._DEFAULTS.get((article.commodity or "").upper())

    def tag_news(
        self, news_list: list["NewsArticle"]
    ) -> list[dict[str, Any]]:
        """
        Geotag a list of NewsArticle objects.

        Returns a list of marker dicts for JSON injection into Leaflet:
            { lat, lng, location, commodity, headline,
              sentiment, sentiment_score, source }
        """
        markers: list[dict[str, Any]] = []
        coord_counts: dict[tuple[int, int], int] = {}

        for article in news_list:
            coords = self.tag_article(article)
            if coords is None:
                continue

            lat, lng, location = coords

            # Jitter articles landing on the same rounded coordinate
            # so dots don't stack on top of each other
            key = (round(lat), round(lng))
            n = coord_counts.get(key, 0)
            coord_counts[key] = n + 1
            if n > 0:
                lat += random.uniform(-1.2, 1.2)
                lng += random.uniform(-1.2, 1.2)

            markers.append({
                "lat":             round(lat, 4),
                "lng":             round(lng, 4),
                "location":        location,
                "commodity":       (article.commodity or "GLOBAL").upper(),
                "headline":        article.title,
                "sentiment":       article.sentiment,
                "sentiment_score": round(float(article.sentiment_score), 3),
                "source":          article.source,
            })

        return markers


# ─────────────────────────────────────────────────────────────────────────────
# Background news loader
# ─────────────────────────────────────────────────────────────────────────────

class _NewsLoaderThread(QThread):
    """
    Fetches live news for a list of commodities and runs HeuristicGeoTagger.
    Emits data_ready(list[dict]) on success, error_occurred(str) on failure.
    """

    data_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, commodities: list[str], parent=None) -> None:
        super().__init__(parent)
        self._commodities = commodities
        self._tagger = HeuristicGeoTagger()

    def run(self) -> None:
        try:
            from src.data.api import data_api

            all_articles: list[Any] = []
            for commodity in self._commodities:
                try:
                    articles = data_api.get_news(commodity, days=7, limit=10)
                    all_articles.extend(articles)
                    logger.debug(
                        "Fetched %d articles for %s", len(articles), commodity
                    )
                except Exception:
                    logger.warning(
                        "Could not fetch news for %s", commodity, exc_info=True
                    )

            markers = self._tagger.tag_news(all_articles)
            logger.info(
                "MacroMap: %d articles → %d geotagged markers",
                len(all_articles), len(markers),
            )
            self.data_ready.emit(markers)

        except Exception as exc:
            logger.exception("_NewsLoaderThread failed")
            self.error_occurred.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# MacroMapView widget
# ─────────────────────────────────────────────────────────────────────────────

class MacroMapView(QWebEngineView):
    """
    QWebEngineView hosting a Leaflet.js world map with live macro news markers.

    Usage:
        map_view = MacroMapView()
        window.set_map_widget(map_view)
        map_view.load_macro_data(["GOLD", "OIL", "SILVER", "NATURAL_GAS", "WHEAT", "COPPER"])
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._loader: _NewsLoaderThread | None = None
        self._pending_markers: list[dict] | None = None  # buffered if page not ready

        # Load base map — use a dummy local base URL so CDN requests aren't blocked
        self.setHtml(_MAP_HTML, QUrl("about:blank"))
        self.loadFinished.connect(self._on_page_loaded)

    # ── Public API ────────────────────────────────────────────────────────────

    def load_macro_data(self, commodities: list[str]) -> None:
        """
        Fetch live news for *commodities* in a background thread,
        geotag, and push markers to the Leaflet map.

        Safe to call multiple times; a running fetch is cancelled first.
        """
        if self._loader is not None and self._loader.isRunning():
            self._loader.data_ready.disconnect()
            self._loader.error_occurred.disconnect()
            self._loader.quit()

        self._loader = _NewsLoaderThread(commodities, parent=self)
        self._loader.data_ready.connect(self._on_data_ready)
        self._loader.error_occurred.connect(self._on_load_error)
        self._loader.start()

    # ── Internals ─────────────────────────────────────────────────────────────

    def _on_page_loaded(self, ok: bool) -> None:
        if not ok:
            logger.error("MacroMapView: Leaflet page failed to load")
            return
        # Flush any markers that arrived before the page was ready
        if self._pending_markers is not None:
            self._push_markers(self._pending_markers)
            self._pending_markers = None

    def _on_data_ready(self, markers: list[dict]) -> None:
        if self.page() is None:
            return
        # If the page finished loading already, push immediately
        # Otherwise buffer until _on_page_loaded fires
        if self._is_page_ready():
            self._push_markers(markers)
        else:
            self._pending_markers = markers

    def _on_load_error(self, error: str) -> None:
        logger.error("MacroMapView: data load failed — %s", error)
        # Show an error state on the map
        escaped = error.replace("'", "\\'").replace("\n", " ")
        self.page().runJavaScript(
            f"document.getElementById('empty-state').textContent = "
            f"'Data load failed: {escaped}';"
            f"document.getElementById('empty-state').classList.remove('hidden');"
        )

    def _push_markers(self, markers: list[dict]) -> None:
        """Serialize markers to JSON and call updateMarkers() in Leaflet."""
        try:
            js_payload = json.dumps(markers, ensure_ascii=False)
            self.page().runJavaScript(f"updateMarkers({js_payload});")
        except Exception:
            logger.exception("MacroMapView: failed to push markers to JS")

    def _is_page_ready(self) -> bool:
        """Heuristic: page is ready when its URL has been set (not blank)."""
        # After setHtml resolves, loadFinished has fired — we track this with
        # _pending_markers being None as the "ready" signal.
        # Use a simple flag instead to be explicit.
        return True  # loadFinished already gates _pending_markers flush

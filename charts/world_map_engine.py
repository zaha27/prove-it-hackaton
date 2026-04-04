"""
charts/world_map_engine.py — Plotly world map HTML for the Macro View tab.

Adapted from world-monitor (github.com/cn620/world-monitor) data structure.
Their NewsItem/Hotspot types (lat, lon, threat level) map directly to our
scatter_geo markers.

Event dict contract (matches world-monitor NewsItem + our mock_data format):
    {
        "title":      str,
        "lat":        float,
        "lon":        float,
        "severity":   "high" | "medium" | "low",   # maps to world-monitor ThreatLevel
        "category":   str,                          # e.g. "conflict", "energy", "market"
        "country":    str,
        "summary":    str,
    }
"""
import logging

logger = logging.getLogger(__name__)

# Palette — same as theme.py
_BG     = "#080808"
_PANEL  = "#0D0D0D"
_GRID   = "#1C1C1C"
_TEXT   = "#F1F5F9"
_MUTED  = "#6B7280"
_BLUE   = "#93C5FD"
_GREEN  = "#4ADE80"
_YELLOW = "#FCD34D"
_RED    = "#F87171"

_SEVERITY_COLOR = {
    "high":   _RED,
    "medium": _YELLOW,
    "low":    _BLUE,
}

# Commodity-producing regions highlighted on the choropleth
# iso_alpha_3 → intensity 0–1  (used for the base layer)
_COMMODITY_EXPOSURE = {
    "SAU": 1.0,   # Saudi Arabia — crude oil
    "RUS": 0.9,   # Russia — oil / gas / wheat
    "USA": 0.7,   # USA — crude / nat gas / wheat
    "CHN": 0.6,   # China — copper demand
    "AUS": 0.6,   # Australia — copper / gold
    "ZAF": 0.5,   # South Africa — gold
    "CHL": 0.5,   # Chile — copper
    "IRN": 0.8,   # Iran — crude / geopolitical
    "UKR": 0.7,   # Ukraine — wheat
    "ARE": 0.6,   # UAE — oil
    "NOR": 0.5,   # Norway — oil / gas
    "CAN": 0.4,   # Canada — oil sands
    "BRA": 0.4,   # Brazil — iron ore / soy
    "PER": 0.4,   # Peru — copper / gold
    "GHA": 0.3,   # Ghana — gold
}


def build_world_map(events: list[dict] | None = None) -> str:
    """
    Build a dark-themed Plotly world map and return a self-contained HTML string.

    Args:
        events: list of event dicts (see module docstring for contract).
                Pass None to show only the commodity exposure layer.

    Returns:
        HTML string ready for QWebEngineView.setHtml()
    """
    try:
        import plotly.graph_objects as go

        fig = go.Figure()

        # ── Layer 1: commodity exposure choropleth ───────────────────────────
        countries  = list(_COMMODITY_EXPOSURE.keys())
        intensities = list(_COMMODITY_EXPOSURE.values())

        fig.add_trace(go.Choropleth(
            locations=countries,
            z=intensities,
            locationmode="ISO-3",
            colorscale=[
                [0.0, "#0D0D0D"],
                [0.3, "#0D2340"],
                [0.7, "#0F3560"],
                [1.0, "#1E3A5F"],
            ],
            showscale=False,
            marker_line_color="#1C1C1C",
            marker_line_width=0.5,
            hovertemplate="<b>%{location}</b><extra></extra>",
            name="Commodity Exposure",
        ))

        # ── Layer 2: geo-located events ──────────────────────────────────────
        if events:
            for severity, color in _SEVERITY_COLOR.items():
                subset = [e for e in events if e.get("severity", "low") == severity]
                if not subset:
                    continue

                fig.add_trace(go.Scattergeo(
                    lat=[e["lat"] for e in subset],
                    lon=[e["lon"] for e in subset],
                    mode="markers",
                    marker=dict(
                        size=9,
                        color=color,
                        opacity=0.85,
                        symbol="circle",
                        line=dict(width=1, color=_BG),
                    ),
                    text=[
                        f"<b>{e.get('title','')}</b><br>"
                        f"{e.get('country','')} — {e.get('category','')}<br>"
                        f"<i>{e.get('summary','')[:80]}…</i>"
                        for e in subset
                    ],
                    hovertemplate="%{text}<extra></extra>",
                    name=severity.capitalize(),
                    showlegend=True,
                ))

        # ── Layout ───────────────────────────────────────────────────────────
        fig.update_layout(
            paper_bgcolor=_BG,
            plot_bgcolor=_BG,
            margin=dict(l=0, r=0, t=0, b=0),
            geo=dict(
                showframe=False,
                showcoastlines=True,
                coastlinecolor=_GRID,
                showland=True,
                landcolor="#111111",
                showocean=True,
                oceancolor=_PANEL,
                showlakes=False,
                showcountries=True,
                countrycolor=_GRID,
                bgcolor=_BG,
                projection_type="natural earth",
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(color=_MUTED, size=11),
                x=0.01,
                y=0.05,
                bordercolor=_GRID,
                borderwidth=1,
            ),
            hoverlabel=dict(
                bgcolor="#141414",
                bordercolor=_GRID,
                font=dict(color=_TEXT, size=12),
            ),
        )

        return fig.to_html(
            full_html=True,
            include_plotlyjs="cdn",
            config={"displayModeBar": False, "scrollZoom": True},
        )

    except Exception as exc:
        logger.error("world_map_engine error: %s", exc)
        return _error_html(str(exc))


def _error_html(msg: str) -> str:
    return (
        f'<html><body style="background:{_BG};color:{_RED};'
        f'font-family:monospace;padding:32px;">'
        f'<pre>{msg}</pre></body></html>'
    )


PLACEHOLDER_HTML = f"""<!DOCTYPE html>
<html>
<body style="background:{_BG};margin:0;height:100vh;
             display:flex;align-items:center;justify-content:center;">
  <div style="text-align:center;font-family:-apple-system,Arial,sans-serif;">
    <div style="font-size:14px;font-weight:500;color:{_TEXT};">
      World Macro View
    </div>
    <div style="font-size:12px;color:{_MUTED};margin-top:6px;">
      Loading map data...
    </div>
  </div>
</body></html>"""

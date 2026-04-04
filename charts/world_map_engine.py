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
        "country_iso3": str,                        # ISO-3 (e.g. IRN, UKR, RUS)
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
# Weighted risk contribution per event severity.
_SEVERITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}
_DEFAULT_HEAT_MAX = 1


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

        # ── Layer 1: dynamic country heat from event severity ────────────────
        country_scores: dict[str, int] = {}
        country_event_counts: dict[str, int] = {}
        country_names: dict[str, str] = {}

        for event in (events or []):
            iso3 = str(event.get("country_iso3", "")).strip().upper()
            # Intentionally skip events without ISO-3 so the choropleth only maps valid countries.
            if not iso3:
                continue
            sev = str(event.get("severity", "low")).strip().lower()
            country_scores[iso3] = country_scores.get(iso3, 0) + _SEVERITY_WEIGHTS.get(sev, 1)
            country_event_counts[iso3] = country_event_counts.get(iso3, 0) + 1
            if iso3 not in country_names:
                country_names[iso3] = str(event.get("country", iso3))

        countries = list(country_scores.keys())
        heat_scores = [country_scores[c] for c in countries]
        event_counts = [country_event_counts.get(c, 0) for c in countries]
        country_labels = [country_names.get(c, c) for c in countries]

        fig.add_trace(go.Choropleth(
            locations=countries,
            z=heat_scores,
            customdata=list(zip(country_labels, event_counts)),
            locationmode="ISO-3",
            colorscale=[
                [0.0, "#0D0D0D"],
                [0.25, "#2A1216"],
                [0.50, "#5A131A"],
                [0.75, "#8C1823"],
                [1.0, "#DC2626"],
            ],
            zmin=0,
            zmax=max(heat_scores, default=_DEFAULT_HEAT_MAX),
            showscale=False,
            marker_line_color="#1C1C1C",
            marker_line_width=0.5,
            hovertemplate=(
                "<b>%{customdata[0]}</b> (%{location})<br>"
                "Risk heat score: %{z}<br>"
                "Tracked events: %{customdata[1]}<extra></extra>"
            ),
            name="Country Risk Heat",
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

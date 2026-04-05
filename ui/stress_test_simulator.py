"""
ui/stress_test_simulator.py — What-If Stress Test Simulator.

Lets the user type a hypothetical macro / geopolitical scenario and see how
the AI's current outlook for a commodity would shift, all without touching
the live database.

Architecture:
    Input panel (native Qt) → _StressWorker (QThread) → DeepSeek direct call
                           → results rendered in QWebEngineView (HTML + SVG)
"""
import json
import logging
import math
import os
import random
import re
from datetime import datetime, timedelta
from html import escape

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QWidget, QSplitter, QFrame,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Prompt constants
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a Senior Macro Strategist and Quantitative Risk Analyst at a top-tier hedge fund.

You will be given:
1. The CURRENT market state and AI consensus verdict for a commodity.
2. A HYPOTHETICAL scenario typed by the analyst (e.g. "China imposes naval blockade on Taiwan").

Your job: run a STRESS TEST. Reason through how this hypothetical event would \
shift supply/demand, safe-haven flows, risk sentiment, and the 7-day outlook \
for the commodity.

RESPOND ONLY WITH VALID JSON — no markdown fences, no text outside the JSON:
{
  "simulated_verdict": "STRONG BUY|BUY|HOLD|SELL|STRONG SELL",
  "simulated_confidence": <float 0.0–1.0>,
  "simulated_roi_7d": <float, e.g. 4.2 means +4.2%, -1.8 means -1.8%>,
  "alpha_rating": "A++|A+|A|B+|B|C",
  "volatility_multiplier": <float ≥ 1.0, how much volatility increases vs baseline>,
  "risks": ["<concise risk 1>", "<concise risk 2>", "<concise risk 3>"],
  "opportunities": ["<opportunity 1>", "<opportunity 2>", "<opportunity 3>"],
  "reasoning": "<2-3 punchy sentences explaining the stress-test impact>"
}"""

_USER_PROMPT_TEMPLATE = """\
COMMODITY: {commodity}
CURRENT PRICE: ${current_price:,.3f}
CURRENT VERDICT: {current_verdict}  (Confidence: {current_confidence:.0%})
CURRENT 7D ROI ESTIMATE: {current_roi:+.2f}%
TOP XGBOOST DRIVERS: {top_features}
RECENT NEWS HEADLINES: {news_headlines}

HYPOTHETICAL SCENARIO (stress test this):
\"{scenario}\"

Perform the stress test now."""

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _alpha_color(rating: str) -> str:
    return {
        "A++": "#00FF87", "A+": "#4ADE80", "A": "#86EFAC",
        "B+": "#FCD34D", "B": "#FBBF24", "C": "#F87171",
    }.get(rating, "#9CA3AF")


def _verdict_color(verdict: str) -> str:
    v = verdict.upper()
    if "STRONG BUY"  in v: return "#00FF87"
    if "BUY"         in v: return "#4ADE80"
    if "STRONG SELL" in v: return "#F87171"
    if "SELL"        in v: return "#EF4444"
    return "#FCD34D"


def _svg_sparkline(values: list[float], color: str, width: int = 320, height: int = 60) -> str:
    if len(values) < 2:
        return ""
    W, H, PAD = width, height, 6
    lo, hi = min(values), max(values)
    spread = (hi - lo) or 1.0

    def pt(i, v):
        x = PAD + i / (len(values) - 1) * (W - 2 * PAD)
        y = (H - PAD) - (v - lo) / spread * (H - 2 * PAD)
        return x, y

    pts_line = [f"{pt(i, v)[0]:.1f},{pt(i, v)[1]:.1f}" for i, v in enumerate(values)]
    pts_fill = (
        [f"{pt(0, values[0])[0]:.1f},{H - PAD}"]
        + pts_line
        + [f"{pt(len(values)-1, values[-1])[0]:.1f},{H - PAD}"]
    )
    lx, ly = pt(len(values) - 1, values[-1])

    gid = f"g{abs(hash(color)) % 9999}"
    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"'
        f' style="width:{W}px;height:{H}px;display:block;">'
        f"<defs><linearGradient id='{gid}' x1='0' y1='0' x2='0' y2='1'>"
        f"<stop offset='0%' stop-color='{color}' stop-opacity='0.22'/>"
        f"<stop offset='100%' stop-color='{color}' stop-opacity='0'/>"
        f"</linearGradient></defs>"
        f"<polygon points='{' '.join(pts_fill)}' fill='url(#{gid})'/>"
        f"<polyline points='{' '.join(pts_line)}' fill='none'"
        f" stroke='{color}' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'/>"
        f"<circle cx='{lx:.1f}' cy='{ly:.1f}' r='3.5' fill='{color}'/>"
        f"</svg>"
    )


def _build_equity_curves(
    base_roi: float,
    sim_roi: float,
    vol_multiplier: float,
) -> tuple[list[float], list[float]]:
    """Return (baseline_curve, stress_curve) each 8 values from $10,000."""
    rng = random.Random(42)
    base, stress = [10_000.0], [10_000.0]
    for _ in range(7):
        b_step = (base_roi / 100) / 7 + rng.uniform(-0.0008, 0.0008)
        s_step = (sim_roi / 100) / 7 + rng.uniform(
            -0.0008 * vol_multiplier, 0.0008 * vol_multiplier
        )
        base.append(round(base[-1] * (1 + b_step), 2))
        stress.append(round(stress[-1] * (1 + s_step), 2))
    return base, stress


def _parse_deepseek_json(raw: str) -> dict:
    """Extract the JSON object from the LLM response; raise ValueError on failure."""
    # Strip markdown fences if present
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    # Find first { ... } block
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in LLM response")
    return json.loads(m.group())


# ─────────────────────────────────────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────────────────────────────────────

class _StressWorker(QThread):
    """Calls DeepSeek in a background thread; emits result or error."""

    finished = pyqtSignal(dict)   # parsed stress result
    failed   = pyqtSignal(str)    # error message

    def __init__(
        self,
        scenario: str,
        symbol: str,
        price_data: dict,
        consensus_result: dict,
        news: list[dict],
        parent=None,
    ):
        super().__init__(parent)
        self._scenario        = scenario
        self._symbol          = symbol
        self._price_data      = price_data
        self._consensus_result = consensus_result
        self._news            = news

    def run(self) -> None:
        try:
            result = self._call_deepseek()
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("StressWorker failed")
            self.failed.emit(str(exc))

    # ── private ──────────────────────────────────────────────────────────────

    def _call_deepseek(self) -> dict:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY not set. Add it to your .env file and restart."
            )

        closes = self._price_data.get("close") or []
        current_price = closes[-1] if closes else 0.0

        current_verdict = str(
            self._consensus_result.get("final_recommendation", "HOLD")
        ).upper()
        current_confidence = _f(self._consensus_result.get("confidence", 0.5))

        xgb = self._consensus_result.get("xgboost_input") or {}
        current_roi = _f(xgb.get("predicted_return", 0.0))
        if current_roi == 0.0:
            # Heuristic fallback
            highs = self._price_data.get("high") or []
            lows  = self._price_data.get("low")  or []
            n = min(len(highs), len(lows), 14)
            atr = sum(highs[i] - lows[i] for i in range(-n, 0)) / n if n > 0 else current_price * 0.02
            direction = 1.0 if "BUY" in current_verdict else (-1.0 if "SELL" in current_verdict else 0.0)
            current_roi = direction * current_confidence * (atr / current_price) * 1.5 * 100

        features = xgb.get("top_features") or []
        top_feat_str = ", ".join(
            f.get("name", "?") for f in features[:5] if isinstance(f, dict)
        ) or "N/A"

        headlines = "; ".join(
            n.get("title", "") for n in (self._news or [])[:4]
        ) or "No recent news."

        user_prompt = _USER_PROMPT_TEMPLATE.format(
            commodity=self._symbol,
            current_price=current_price,
            current_verdict=current_verdict,
            current_confidence=current_confidence,
            current_roi=current_roi,
            top_features=top_feat_str,
            news_headlines=headlines,
            scenario=self._scenario,
        )

        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system",  "content": _SYSTEM_PROMPT},
                {"role": "user",    "content": user_prompt},
            ],
            max_tokens=600,
            temperature=0.4,
        )
        raw = response.choices[0].message.content or ""
        logger.debug("DeepSeek stress raw: %s", raw)

        result = _parse_deepseek_json(raw)

        # Inject originals so the UI can diff them
        result["_original_verdict"]    = current_verdict
        result["_original_confidence"] = current_confidence
        result["_original_roi"]        = current_roi
        result["_scenario"]            = self._scenario
        return result


# ─────────────────────────────────────────────────────────────────────────────
# HTML builders
# ─────────────────────────────────────────────────────────────────────────────

_LOADING_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  html,body { background:#080808; height:100%; display:flex;
              align-items:center; justify-content:center; }
  .wrap { text-align:center; font-family:-apple-system,sans-serif; }
  .title { font-size:15px; font-weight:600; color:#E5E7EB; margin-bottom:28px; }
  .bars { display:flex; gap:6px; justify-content:center; align-items:flex-end;
          height:40px; margin-bottom:28px; }
  .bar { width:6px; border-radius:3px; animation:bounce 1.1s ease-in-out infinite; }
  .bar:nth-child(1){ background:#4ADE80; animation-delay:0s;    height:14px; }
  .bar:nth-child(2){ background:#86EFAC; animation-delay:0.15s; height:24px; }
  .bar:nth-child(3){ background:#FCD34D; animation-delay:0.3s;  height:36px; }
  .bar:nth-child(4){ background:#86EFAC; animation-delay:0.45s; height:24px; }
  .bar:nth-child(5){ background:#4ADE80; animation-delay:0.6s;  height:14px; }
  @keyframes bounce {
    0%,100% { transform:scaleY(1);   opacity:.7; }
    50%      { transform:scaleY(2.2);opacity:1;  }
  }
  .sub { font-size:11px; color:#374151; letter-spacing:0.3px; }
</style>
</head><body>
<div class="wrap">
  <div class="title">Running Stress Test Simulation...</div>
  <div class="bars">
    <div class="bar"></div><div class="bar"></div><div class="bar"></div>
    <div class="bar"></div><div class="bar"></div>
  </div>
  <div class="sub">DeepSeek Macro Strategist is analysing the scenario</div>
</div>
</body></html>"""


_IDLE_HTML = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  html,body { background:#080808; height:100%; display:flex;
              align-items:center; justify-content:center; }
  .wrap { text-align:center; font-family:-apple-system,sans-serif; }
  .icon { font-size:32px; margin-bottom:16px; color:#1C1C1C; }
  .msg  { font-size:13px; color:#374151; line-height:1.6; max-width:300px; }
</style>
</head><body>
<div class="wrap">
  <div class="icon">&#9650;</div>
  <div class="msg">Enter a hypothetical scenario on the left<br>and click <b>Run Stress Test</b> to see<br>how the AI outlook changes.</div>
</div>
</body></html>"""


_RESULTS_CSS = """
* { box-sizing:border-box; margin:0; padding:0; }
html,body {
  background:#080808; color:#E5E7EB;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  font-size:13px; line-height:1.5;
}
.wrap { padding:18px 20px 32px; }

/* scenario badge */
.scenario-box {
  background:#111111; border:1px solid #1C1C1C; border-radius:6px;
  padding:10px 14px; margin-bottom:16px; font-size:12px; color:#9CA3AF;
}
.scenario-box b { color:#E5E7EB; }

/* before / after grid */
.ba-grid {
  display:grid; grid-template-columns:1fr auto 1fr;
  gap:10px; align-items:center; margin-bottom:16px;
}
.ba-card {
  background:#0D0D0D; border:1px solid #1C1C1C; border-radius:8px; padding:14px 16px;
}
.ba-label {
  font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase;
  color:#374151; margin-bottom:8px;
}
.ba-verdict {
  font-size:18px; font-weight:800; font-family:'SF Mono','Menlo',monospace;
  margin-bottom:4px;
}
.ba-conf { font-size:12px; color:#6B7280; }
.ba-roi  { font-size:13px; font-weight:600; font-family:monospace; margin-top:4px; }

/* confidence bar */
.conf-track { height:4px; background:#1C1C1C; border-radius:2px; margin-top:6px; overflow:hidden; }
.conf-fill  { height:100%; border-radius:2px; }

/* arrow */
.arrow { text-align:center; font-size:22px; color:#262626; }

/* change delta */
.delta {
  text-align:center; font-size:11px; font-family:monospace;
  color:#9CA3AF; margin-bottom:16px;
}
.delta .up   { color:#4ADE80; font-weight:700; }
.delta .down { color:#F87171; font-weight:700; }
.delta .neut { color:#FCD34D; font-weight:700; }

/* impact panels */
.impact-grid {
  display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:16px;
}
.impact-panel {
  background:#0D0D0D; border:1px solid #1C1C1C; border-radius:8px; overflow:hidden;
}
.impact-ph {
  padding:8px 14px; background:#111111; border-bottom:1px solid #1C1C1C;
  font-size:10px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase;
}
.impact-body { padding:12px 14px; }
.impact-item {
  display:flex; align-items:flex-start; gap:8px; padding:4px 0;
  border-bottom:1px solid #111111; font-size:12px; color:#D1D5DB;
}
.impact-item:last-child { border-bottom:none; }
.dot { flex:0 0 6px; width:6px; height:6px; border-radius:50%; margin-top:5px; }

/* chart section */
.chart-panel {
  background:#0D0D0D; border:1px solid #1C1C1C; border-radius:8px; overflow:hidden;
  margin-bottom:16px;
}
.chart-ph {
  padding:8px 14px; background:#111111; border-bottom:1px solid #1C1C1C;
  font-size:10px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase;
  color:#9CA3AF;
}
.chart-body { padding:14px 14px 8px; display:flex; gap:20px; align-items:flex-start; }
.chart-col  { flex:1; }
.chart-sub  { font-size:10px; color:#374151; margin-bottom:6px; text-transform:uppercase;
              letter-spacing:0.8px; }
.chart-dates{
  display:flex; justify-content:space-between; font-size:9px; color:#1C1C1C;
  font-family:monospace; padding:4px 0 0;
}

/* reasoning */
.reasoning {
  background:#0D0D0D; border:1px solid #1C1C1C; border-radius:8px; padding:14px 16px;
}
.reasoning-label {
  font-size:10px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase;
  color:#6B7280; margin-bottom:8px;
}
.reasoning-text { font-size:12px; color:#9CA3AF; line-height:1.7; }

/* scrollbar */
::-webkit-scrollbar { width:4px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:#1C1C1C; border-radius:2px; }
"""


def _build_results_html(result: dict) -> str:
    # ── parse fields ─────────────────────────────────────────────────────────
    orig_verdict    = str(result.get("_original_verdict",    "HOLD")).upper()
    orig_confidence = _f(result.get("_original_confidence", 0.5))
    orig_roi        = _f(result.get("_original_roi",         0.0))
    scenario        = escape(str(result.get("_scenario", "")))

    sim_verdict    = str(result.get("simulated_verdict",    "HOLD")).upper()
    sim_confidence = _f(result.get("simulated_confidence", 0.5))
    sim_roi        = _f(result.get("simulated_roi_7d",      0.0))
    alpha          = str(result.get("alpha_rating",          "B"))
    vol_mult       = max(1.0, _f(result.get("volatility_multiplier", 1.2)))
    risks          = result.get("risks",         []) or []
    opps           = result.get("opportunities", []) or []
    reasoning      = escape(str(result.get("reasoning", ""))).replace("\n", "<br>")

    # ── colours ──────────────────────────────────────────────────────────────
    orig_col = _verdict_color(orig_verdict)
    sim_col  = _verdict_color(sim_verdict)
    a_col    = _alpha_color(alpha)

    conf_change = sim_confidence - orig_confidence
    roi_change  = sim_roi - orig_roi

    def _sign_span(val: float, fmt: str = "+.2f") -> str:
        cls = "up" if val > 0.005 else ("down" if val < -0.005 else "neut")
        return f'<span class="{cls}">{val:{fmt}}</span>'

    conf_delta_html = _sign_span(conf_change, "+.0%")
    roi_delta_html  = _sign_span(roi_change,  "+.2f")

    # ── confidence bar widths ────────────────────────────────────────────────
    orig_bar_w = int(min(100, orig_confidence * 100))
    sim_bar_w  = int(min(100, sim_confidence  * 100))

    # ── ROI sign/colour ──────────────────────────────────────────────────────
    roi_sign   = "+" if orig_roi >= 0 else ""
    s_roi_sign = "+" if sim_roi  >= 0 else ""
    orig_roi_col = "#4ADE80" if orig_roi >= 0 else "#F87171"
    sim_roi_col  = "#4ADE80" if sim_roi  >= 0 else "#F87171"

    # ── equity curves ────────────────────────────────────────────────────────
    base_curve, stress_curve = _build_equity_curves(orig_roi, sim_roi, vol_mult)
    base_svg   = _svg_sparkline(base_curve,   orig_col, width=280, height=56)
    stress_svg = _svg_sparkline(stress_curve, sim_col,  width=280, height=56)

    today = datetime.today()
    date_labels = " ".join(
        f"<span>{(today + timedelta(days=i)).strftime('%b %d')}</span>"
        for i in [0, 2, 4, 7]
    )

    # ── risks / opportunities ────────────────────────────────────────────────
    def _bullet_items(items: list, color: str) -> str:
        html = ""
        for item in items[:4]:
            txt = escape(str(item))
            html += (
                f'<div class="impact-item">'
                f'<div class="dot" style="background:{color};"></div>'
                f'<span>{txt}</span></div>'
            )
        return html or f'<div style="color:#374151;font-size:11px;">None identified</div>'

    risks_html = _bullet_items(risks, "#F87171")
    opps_html  = _bullet_items(opps, "#4ADE80")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>{_RESULTS_CSS}</style>
</head><body>
<div class="wrap">

  <!-- scenario recap -->
  <div class="scenario-box">
    <b>Hypothetical Scenario:</b>&nbsp; {scenario}
  </div>

  <!-- before / after -->
  <div class="ba-grid">
    <div class="ba-card" style="border-color:{orig_col}22;">
      <div class="ba-label">Original Outlook</div>
      <div class="ba-verdict" style="color:{orig_col};">{orig_verdict}</div>
      <div class="ba-conf">Confidence: {orig_confidence:.0%}</div>
      <div class="conf-track">
        <div class="conf-fill" style="width:{orig_bar_w}%;background:{orig_col};"></div>
      </div>
      <div class="ba-roi" style="color:{orig_roi_col};">{roi_sign}{orig_roi:.2f}% ROI (7d)</div>
    </div>

    <div class="arrow">&#8594;</div>

    <div class="ba-card" style="border-color:{sim_col}44;box-shadow:0 0 14px {sim_col}18;">
      <div class="ba-label">
        Simulated Outcome &nbsp;
        <span style="color:{a_col};font-size:11px;">{alpha}</span>
      </div>
      <div class="ba-verdict" style="color:{sim_col};text-shadow:0 0 12px {sim_col}60;">
        {sim_verdict}
      </div>
      <div class="ba-conf">Confidence: {sim_confidence:.0%}</div>
      <div class="conf-track">
        <div class="conf-fill" style="width:{sim_bar_w}%;background:{sim_col};"></div>
      </div>
      <div class="ba-roi" style="color:{sim_roi_col};">{s_roi_sign}{sim_roi:.2f}% ROI (7d)</div>
    </div>
  </div>

  <!-- delta summary -->
  <div class="delta">
    Confidence {conf_delta_html} &nbsp;|&nbsp;
    ROI estimate {roi_delta_html}% &nbsp;|&nbsp;
    Volatility <span class="{'up' if vol_mult > 1.2 else 'neut'}">{vol_mult:.1f}×</span> baseline
  </div>

  <!-- impact: risks + opportunities -->
  <div class="impact-grid">
    <div class="impact-panel">
      <div class="impact-ph" style="color:#F87171;">Top Risks Created</div>
      <div class="impact-body">{risks_html}</div>
    </div>
    <div class="impact-panel">
      <div class="impact-ph" style="color:#4ADE80;">Top Opportunities Created</div>
      <div class="impact-body">{opps_html}</div>
    </div>
  </div>

  <!-- equity curves -->
  <div class="chart-panel">
    <div class="chart-ph">Simulated Equity Curve — $10,000 seed · 7-day projection</div>
    <div class="chart-body">
      <div class="chart-col">
        <div class="chart-sub">Baseline</div>
        {base_svg}
        <div class="chart-dates">{date_labels}</div>
      </div>
      <div class="chart-col">
        <div class="chart-sub">Under Stress Scenario</div>
        {stress_svg}
        <div class="chart-dates">{date_labels}</div>
      </div>
    </div>
  </div>

  <!-- reasoning -->
  <div class="reasoning">
    <div class="reasoning-label">Strategist Reasoning</div>
    <div class="reasoning-text">{reasoning or '<span style="color:#374151;">No reasoning provided.</span>'}</div>
  </div>

</div>
</body></html>"""


def _build_error_html(message: str) -> str:
    msg = escape(message).replace("\n", "<br>")
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
  *{{box-sizing:border-box;margin:0;padding:0;}}
  html,body{{background:#080808;height:100%;display:flex;
             align-items:center;justify-content:center;font-family:sans-serif;}}
  .box{{background:#0D0D0D;border:1px solid #F87171;border-radius:8px;
        padding:24px 28px;max-width:480px;}}
  h3{{color:#F87171;font-size:14px;margin-bottom:10px;}}
  p{{font-size:12px;color:#9CA3AF;line-height:1.7;}}
</style>
</head><body>
<div class="box">
  <h3>Stress Test Failed</h3>
  <p>{msg}</p>
</div>
</body></html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Dialog
# ─────────────────────────────────────────────────────────────────────────────

_EXAMPLE_SCENARIOS = [
    "Fed unexpectedly raises rates +100 bps",
    "China imposes naval blockade on Taiwan Strait",
    "OPEC+ announces emergency 2M bbl/day cut",
    "Major US bank collapses, contagion fears spread",
    "Russia-Ukraine ceasefire signed, sanctions lifted",
]


class StressTestDialog(QDialog):
    """
    What-If Stress Test Simulator dialog.

    Usage:
        dlg = StressTestDialog(symbol, price_data, consensus_result, news, parent=self)
        dlg.exec()
    """

    def __init__(
        self,
        symbol: str,
        price_data: dict,
        consensus_result: dict,
        news: list[dict] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._symbol           = symbol
        self._price_data       = price_data or {}
        self._consensus_result = consensus_result or {}
        self._news             = news or []
        self._worker: _StressWorker | None = None

        self.setWindowTitle(f"What-If Stress Test — {symbol}")
        self.setModal(True)
        self.resize(1160, 740)
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background:#080808;")

        self._init_ui()

    # ── construction ─────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background:#1C1C1C; }")

        splitter.addWidget(self._build_input_panel())

        self._web = QWebEngineView()
        self._web.setHtml(_IDLE_HTML)
        splitter.addWidget(self._web)

        splitter.setSizes([380, 780])
        root.addWidget(splitter, stretch=1)

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(46)
        bar.setStyleSheet(
            "background:#0D0D0D; border-bottom:1px solid #1C1C1C;"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(20, 0, 16, 0)

        title = QLabel(f"What-If Stress Test Simulator  ·  {self._symbol}")
        title.setStyleSheet(
            "color:#F1F5F9; font-size:14px; font-weight:700; letter-spacing:-0.2px;"
        )
        row.addWidget(title)
        row.addStretch()

        badge = QLabel("SANDBOX — no real data is modified")
        badge.setStyleSheet(
            "color:#374151; background:#111111; border:1px solid #1C1C1C;"
            "border-radius:4px; font-size:10px; font-weight:600;"
            "letter-spacing:0.5px; padding:3px 10px;"
        )
        row.addWidget(badge)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet(
            "QPushButton{background:#111111;color:#6B7280;border:1px solid #1C1C1C;"
            "border-radius:5px;font-size:13px;}"
            "QPushButton:hover{background:#1C1C1C;color:#E5E7EB;}"
        )
        btn_close.clicked.connect(self.close)
        row.addWidget(btn_close)
        return bar

    def _build_input_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background:#080808;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 14, 18)
        layout.setSpacing(12)

        # ── label ────────────────────────────────────────────────────────────
        lbl = QLabel("Hypothetical Scenario")
        lbl.setStyleSheet(
            "color:#9CA3AF; font-size:11px; font-weight:600; letter-spacing:0.5px;"
        )
        layout.addWidget(lbl)

        # ── text input ───────────────────────────────────────────────────────
        self._scenario_edit = QTextEdit()
        self._scenario_edit.setPlaceholderText(
            "Describe a macro or geopolitical event...\n\n"
            'e.g. "The Federal Reserve unexpectedly raises rates\n'
            'by 100 basis points in an emergency meeting."\n\n'
            'or "China imposes a naval blockade on the Taiwan Strait,\n'
            'disrupting global semiconductor supply chains."'
        )
        self._scenario_edit.setFont(QFont("Menlo", 12))
        self._scenario_edit.setStyleSheet(
            "QTextEdit {"
            "  background:#0D0D0D; color:#E5E7EB;"
            "  border:1px solid #1C1C1C; border-radius:6px;"
            "  padding:12px; font-size:12px; line-height:1.6;"
            "  selection-background-color:#262626;"
            "}"
            "QTextEdit:focus { border-color:#262626; }"
        )
        layout.addWidget(self._scenario_edit, stretch=1)

        # ── quick-fill chips ─────────────────────────────────────────────────
        chips_lbl = QLabel("Quick examples")
        chips_lbl.setStyleSheet("color:#374151; font-size:10px; letter-spacing:0.3px;")
        layout.addWidget(chips_lbl)

        chips_wrap = QWidget()
        chips_layout = QVBoxLayout(chips_wrap)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(4)

        for scenario in _EXAMPLE_SCENARIOS:
            chip = QPushButton(scenario)
            chip.setStyleSheet(
                "QPushButton {"
                "  background:#0D0D0D; color:#6B7280;"
                "  border:1px solid #1C1C1C; border-radius:4px;"
                "  font-size:11px; padding:5px 10px;"
                "  text-align:left;"
                "}"
                "QPushButton:hover { background:#111111; color:#D1D5DB; border-color:#262626; }"
            )
            chip.clicked.connect(
                lambda _, s=scenario: self._scenario_edit.setPlainText(s)
            )
            chips_layout.addWidget(chip)

        layout.addWidget(chips_wrap)

        # ── separator ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#1C1C1C;")
        layout.addWidget(sep)

        # ── run button ───────────────────────────────────────────────────────
        self._run_btn = QPushButton("Run Stress Test Simulation")
        self._run_btn.setFixedHeight(40)
        self._run_btn.setStyleSheet(
            "QPushButton {"
            "  background:#0D0D0D; color:#4ADE80;"
            "  border:1px solid #14532D; border-radius:6px;"
            "  font-size:13px; font-weight:700; letter-spacing:0.2px;"
            "}"
            "QPushButton:hover {"
            "  background:#14532D; border-color:#4ADE80;"
            "  box-shadow:0 0 12px rgba(74,222,128,0.25);"
            "}"
            "QPushButton:pressed { background:#16A34A; color:#F0FDF4; }"
            "QPushButton:disabled { background:#0D0D0D; color:#1C1C1C;"
            "                       border-color:#111111; }"
        )
        self._run_btn.clicked.connect(self._on_run)
        layout.addWidget(self._run_btn)

        return panel

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_run(self) -> None:
        scenario = self._scenario_edit.toPlainText().strip()
        if not scenario:
            self._scenario_edit.setFocus()
            return

        # Cancel any previous worker
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(200)

        self._run_btn.setEnabled(False)
        self._run_btn.setText("Running...")
        self._web.setHtml(_LOADING_HTML)

        self._worker = _StressWorker(
            scenario=scenario,
            symbol=self._symbol,
            price_data=self._price_data,
            consensus_result=self._consensus_result,
            news=self._news,
            parent=self,
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_finished(self, result: dict) -> None:
        self._web.setHtml(_build_results_html(result))
        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run Stress Test Simulation")

    def _on_failed(self, message: str) -> None:
        self._web.setHtml(_build_error_html(message))
        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run Stress Test Simulation")

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(300)
        super().closeEvent(event)

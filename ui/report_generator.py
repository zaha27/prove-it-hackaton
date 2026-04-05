"""
ui/report_generator.py — AI Alpha Strategy Report Dialog.

Bloomberg Terminal aesthetic: deep navy background, neon accents.
Opens as a large modal; renders a QWebEngineView with full HTML report.

Usage:
    from ui.report_generator import AIStrategyReportDialog
    dlg = AIStrategyReportDialog(symbol, price_data, consensus_result, parent=self)
    dlg.exec()
"""
import math
import logging
import random
from datetime import datetime, timedelta
from html import escape

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QWidget,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Pure helper functions
# ─────────────────────────────────────────────────────────────────────────────

def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _alpha_rating(conf: float) -> tuple[str, str]:
    """(rating_str, hex_color) keyed on confidence."""
    if conf >= 0.85: return "A++", "#00FF87"
    if conf >= 0.75: return "A+",  "#4ADE80"
    if conf >= 0.65: return "A",   "#86EFAC"
    if conf >= 0.55: return "B+",  "#FCD34D"
    if conf >= 0.45: return "B",   "#FBBF24"
    return "C", "#F87171"


def _risk_label(atr_pct: float) -> tuple[str, str]:
    """(label, hex_color) from ATR as fraction of price."""
    if atr_pct < 0.015: return "LOW",    "#4ADE80"
    if atr_pct < 0.035: return "MEDIUM", "#FCD34D"
    return "HIGH", "#EF4444"


def _svg_sparkline(values: list[float], color: str = "#00FF87") -> str:
    """Return an inline SVG sparkline with gradient fill under the curve."""
    if len(values) < 2:
        return ""
    W, H, PAD = 440, 88, 8
    lo, hi = min(values), max(values)
    spread = (hi - lo) or 1.0

    def pt(i: int, v: float) -> tuple[float, float]:
        x = PAD + i / (len(values) - 1) * (W - 2 * PAD)
        y = (H - PAD) - (v - lo) / spread * (H - 2 * PAD)
        return x, y

    line_pts = [f"{pt(i, v)[0]:.1f},{pt(i, v)[1]:.1f}" for i, v in enumerate(values)]
    fill_pts = (
        [f"{pt(0, values[0])[0]:.1f},{H - PAD}"]
        + line_pts
        + [f"{pt(len(values) - 1, values[-1])[0]:.1f},{H - PAD}"]
    )
    lx, ly = pt(len(values) - 1, values[-1])

    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"'
        f' style="width:100%;height:{H}px;display:block;">'
        f"<defs><linearGradient id='sg' x1='0' y1='0' x2='0' y2='1'>"
        f"<stop offset='0%' stop-color='{color}' stop-opacity='0.28'/>"
        f"<stop offset='100%' stop-color='{color}' stop-opacity='0'/>"
        f"</linearGradient></defs>"
        f"<polygon points='{' '.join(fill_pts)}' fill='url(#sg)'/>"
        f"<polyline points='{' '.join(line_pts)}' fill='none'"
        f" stroke='{color}' stroke-width='2.2' stroke-linejoin='round' stroke-linecap='round'/>"
        f"<circle cx='{lx:.1f}' cy='{ly:.1f}' r='4.5' fill='{color}'"
        f" filter='drop-shadow(0 0 6px {color})'/>"
        f"</svg>"
    )


def _compute_metrics(price_data: dict, consensus_result: dict) -> dict:
    """Derive all numeric metrics needed to populate the report."""
    closes = price_data.get("close") or []
    highs  = price_data.get("high")  or []
    lows   = price_data.get("low")   or []

    last_price = closes[-1] if closes else 0.0
    n = min(len(highs), len(lows), 14)
    atr = sum(highs[i] - lows[i] for i in range(-n, 0)) / n if n > 0 else last_price * 0.02
    atr_pct = atr / last_price if last_price else 0.02

    confidence     = _f(consensus_result.get("confidence", 0.5))
    recommendation = str(consensus_result.get("final_recommendation", "HOLD")).upper()
    direction      = 1.0 if "BUY" in recommendation else (-1.0 if "SELL" in recommendation else 0.0)

    xgb              = consensus_result.get("xgboost_input") or {}
    predicted_return = _f(xgb.get("predicted_return"))
    if predicted_return == 0.0:
        # Heuristic: confidence × direction × 1.5× ATR% over 7 days
        predicted_return = direction * confidence * atr_pct * 1.5 * 100

    # Annualised volatility from daily returns
    if len(closes) >= 10:
        rets = [(closes[i] - closes[i - 1]) / closes[i - 1]
                for i in range(1, len(closes)) if closes[i - 1] != 0]
        if rets:
            mean_r    = sum(rets) / len(rets)
            vol_daily = math.sqrt(sum((r - mean_r) ** 2 for r in rets) / len(rets))
            vol_ann   = vol_daily * math.sqrt(252)
        else:
            vol_ann = atr_pct * math.sqrt(252)
    else:
        vol_ann = atr_pct * math.sqrt(252)

    ann_ret = predicted_return / 100 * (252 / 7)
    sharpe  = (ann_ret - 0.02) / vol_ann if vol_ann > 0 else 0.0

    entry       = last_price
    stop_loss   = entry - 1.5 * atr
    take_profit = entry + 2.5 * atr
    risk_reward = (take_profit - entry) / (entry - stop_loss) if (entry - stop_loss) > 0 else 0.0

    investment      = 10_000.0
    proj_value      = investment * (1 + predicted_return / 100)
    pnl             = proj_value - investment

    # 7-day equity curve (deterministic noise seed from confidence)
    rng = random.Random(int(abs(confidence) * 9999))
    eq_vals = [investment]
    for _ in range(7):
        step = (predicted_return / 100) / 7 + rng.uniform(-0.0008, 0.0008)
        eq_vals.append(round(eq_vals[-1] * (1 + step), 2))
    eq_dates = [
        (datetime.today() + timedelta(days=i)).strftime("%b %d")
        for i in range(8)
    ]

    alpha_str, alpha_color = _alpha_rating(confidence)
    risk_str,  risk_color  = _risk_label(atr_pct)

    return dict(
        last_price=last_price, atr=atr, atr_pct=atr_pct,
        confidence=confidence, predicted_return=predicted_return,
        vol_ann=vol_ann, sharpe=sharpe,
        entry=entry, stop_loss=stop_loss, take_profit=take_profit,
        risk_reward=risk_reward,
        investment=investment, proj_value=proj_value, pnl=pnl,
        alpha_str=alpha_str, alpha_color=alpha_color,
        risk_str=risk_str, risk_color=risk_color,
        recommendation=recommendation,
        top_features=(xgb.get("top_features") or []),
        eq_dates=eq_dates, eq_vals=eq_vals,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HTML report builder
# ─────────────────────────────────────────────────────────────────────────────

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  background: #050A14;
  color: #CBD5E1;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 13px;
  line-height: 1.5;
}

.wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 22px 26px 44px;
}

/* ── Header ─────────────────────────────────────── */
.hdr {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 22px 28px;
  background: linear-gradient(135deg, #06101F 0%, #0D1D35 55%, #06101F 100%);
  border: 1px solid #112240;
  border-radius: 10px;
  margin-bottom: 18px;
  position: relative;
  overflow: hidden;
}
.hdr::before {
  content: '';
  position: absolute;
  top: -60px; right: -60px;
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(59,158,255,0.06) 0%, transparent 70%);
  pointer-events: none;
}
.hdr-brand {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #1E6EBE;
  margin-bottom: 5px;
}
.hdr-title {
  font-size: 24px;
  font-weight: 800;
  color: #F1F5F9;
  letter-spacing: -0.4px;
}
.hdr-title span { color: #3B9EFF; }
.hdr-sub {
  font-size: 11px;
  color: #334155;
  margin-top: 5px;
  letter-spacing: 0.4px;
}
.hdr-right { text-align: right; }
.hdr-symbol {
  font-size: 32px;
  font-weight: 900;
  color: #3B9EFF;
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  letter-spacing: -0.5px;
  text-shadow: 0 0 20px rgba(59,158,255,0.4);
}
.hdr-ts {
  font-size: 11px;
  color: #334155;
  font-family: 'SF Mono', 'Menlo', monospace;
  margin-top: 5px;
}
.hdr-badge {
  display: inline-block;
  margin-top: 10px;
  padding: 5px 18px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1.2px;
}

/* ── Metric Cards ────────────────────────────────── */
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.mc {
  background: #06101F;
  border-radius: 8px;
  padding: 16px 18px 14px;
  border: 1px solid #0F2040;
  transition: box-shadow 0.2s;
}
.mc-lbl {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.6px;
  text-transform: uppercase;
  color: #334155;
  margin-bottom: 7px;
}
.mc-val {
  font-size: 30px;
  font-weight: 800;
  font-family: 'SF Mono', 'Menlo', monospace;
  line-height: 1;
}
.mc-sub {
  font-size: 11px;
  color: #334155;
  margin-top: 6px;
}

/* ── Panels ──────────────────────────────────────── */
.row2 {
  display: grid;
  grid-template-columns: 310px 1fr;
  gap: 12px;
  margin-bottom: 16px;
}
.panel {
  background: #06101F;
  border: 1px solid #0F2040;
  border-radius: 8px;
  overflow: hidden;
}
.ph {
  padding: 9px 16px;
  background: #0A1628;
  border-bottom: 1px solid #0F2040;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.pb { padding: 14px 16px; }

/* ── Trade Levels ────────────────────────────────── */
.tlevel {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 13px;
  border-radius: 6px;
  margin-bottom: 8px;
}
.tl-lbl {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.4px;
  text-transform: uppercase;
}
.tl-val {
  font-size: 17px;
  font-weight: 700;
  font-family: 'SF Mono', 'Menlo', monospace;
}
.tl-entry { background: rgba(59,158,255,0.07); border: 1px solid rgba(59,158,255,0.18); }
.tl-stop  { background: rgba(239,68,68,0.07);  border: 1px solid rgba(239,68,68,0.18); }
.tl-tp    { background: rgba(0,255,135,0.07);  border: 1px solid rgba(0,255,135,0.18); }
.rr-row {
  display: flex;
  justify-content: space-between;
  padding: 7px 12px 0;
  font-size: 11px;
  color: #334155;
  border-top: 1px solid #0F2040;
  margin-top: 6px;
}
.rr-val { font-weight: 700; font-family: monospace; color: #FCD34D; }

/* ── Intelligence cols ───────────────────────────── */
.intel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  height: 100%;
}
.feat-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  border-bottom: 1px solid #0A1628;
}
.feat-row:last-child { border-bottom: none; }
.fn {
  flex: 0 0 118px;
  font-size: 11px;
  color: #94A3B8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.ft { flex: 1; height: 5px; background: #0A1628; border-radius: 3px; overflow: hidden; }
.fb { height: 100%; border-radius: 3px; }
.fp { flex: 0 0 38px; text-align: right; font-size: 11px; font-family: monospace; }

.ds-text {
  font-size: 12px;
  line-height: 1.7;
  color: #94A3B8;
  max-height: 240px;
  overflow-y: auto;
}
.ds-text::-webkit-scrollbar { width: 4px; }
.ds-text::-webkit-scrollbar-track { background: transparent; }
.ds-text::-webkit-scrollbar-thumb { background: #1E3A5F; border-radius: 2px; }

/* ── Portfolio Simulator ─────────────────────────── */
.pf-row {
  display: grid;
  grid-template-columns: 260px 1fr;
}
.pf-stats { padding: 20px 20px 16px; display: flex; flex-direction: column; justify-content: center; gap: 12px; }
.pf-lbl { font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase; color: #334155; margin-bottom: 3px; }
.pf-amt { font-size: 22px; font-weight: 800; font-family: 'SF Mono', 'Menlo', monospace; }
.pf-pnl { font-size: 13px; font-weight: 600; font-family: monospace; margin-top: 4px; }
.pf-hor { font-size: 11px; color: #334155; margin-top: 3px; }
.pf-arrow { font-size: 28px; color: #0F2040; text-align: center; line-height: 1; }

.chart-area { padding: 16px 14px 6px; }
.chart-dates {
  display: flex;
  justify-content: space-between;
  padding: 4px 8px 0;
  font-size: 10px;
  color: #1E3A5F;
  font-family: monospace;
}

/* ── Footer ──────────────────────────────────────── */
.footer {
  margin-top: 20px;
  padding: 14px 16px;
  border-top: 1px solid #0A1628;
  font-size: 10px;
  color: #1A2E47;
  text-align: center;
  line-height: 1.7;
}

/* ── Scanline CRT overlay ────────────────────────── */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,0,0,0.025) 2px,
    rgba(0,0,0,0.025) 4px
  );
  pointer-events: none;
  z-index: 9999;
}
"""


def _build_report_html(symbol: str, m: dict, consensus_result: dict) -> str:
    ts  = datetime.now().strftime("%Y-%m-%d  %H:%M:%S  UTC")
    rec = m["recommendation"]

    roi_sign  = "+" if m["predicted_return"] >= 0 else ""
    roi_color = "#4ADE80" if m["predicted_return"] >= 0 else "#F87171"
    pnl_sign  = "+" if m["pnl"] >= 0 else ""
    curve_col = "#00FF87" if m["pnl"] >= 0 else "#F87171"
    sharpe_col = "#4ADE80" if m["sharpe"] > 1 else ("#FCD34D" if m["sharpe"] > 0 else "#F87171")

    # Recommendation badge colours
    if "BUY" in rec:
        rec_col, rec_bg = "#00FF87", "rgba(0,255,135,0.10)"
    elif "SELL" in rec:
        rec_col, rec_bg = "#EF4444", "rgba(239,68,68,0.10)"
    else:
        rec_col, rec_bg = "#FCD34D", "rgba(252,211,77,0.10)"

    # ── Feature rows
    feat_html = ""
    for feat in (m["top_features"] or [])[:9]:
        if not isinstance(feat, dict):
            continue
        name   = escape(str(feat.get("name", "")))
        imp    = _f(feat.get("importance", 0))
        impact = str(feat.get("impact", "neutral")).lower()
        fc     = "#4ADE80" if impact == "positive" else "#F87171" if impact == "negative" else "#94A3B8"
        bw     = min(100, int(imp * 280))
        feat_html += (
            f'<div class="feat-row">'
            f'<span class="fn">{name}</span>'
            f'<div class="ft"><div class="fb" style="width:{bw}%;background:{fc};"></div></div>'
            f'<span class="fp" style="color:{fc};">{imp:.1%}</span>'
            f"</div>"
        )
    if not feat_html:
        feat_html = '<div style="color:#334155;font-size:12px;padding:8px 0;">No feature data available</div>'

    # ── DeepSeek reasoning
    reasoning_raw = str(consensus_result.get("final_reasoning", "") or "").strip()
    reasoning_html = escape(reasoning_raw).replace("\n", "<br>") if reasoning_raw else (
        '<span style="color:#334155;">No geopolitical analysis available</span>'
    )

    # ── SVG sparkline
    svg = _svg_sparkline(m["eq_vals"], curve_col)

    # ── Equity curve date labels (first, 3 midpoints, last)
    ed = m["eq_dates"]
    date_labels = f"""
      <span>{ed[0]}</span><span>{ed[2]}</span>
      <span>{ed[4]}</span><span>{ed[6]}</span><span>{ed[7]}</span>
    """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">

  <!-- ═══ HEADER ═══════════════════════════════════════════════════════════ -->
  <div class="hdr">
    <div>
      <div class="hdr-brand">Neuro-Symbolic Intelligence Platform &nbsp;·&nbsp; Institutional Grade</div>
      <div class="hdr-title">AI Alpha <span>Strategy Report</span></div>
      <div class="hdr-sub">XGBoost Quantitative Signal &nbsp;×&nbsp; DeepSeek Macro Validator</div>
    </div>
    <div class="hdr-right">
      <div class="hdr-symbol">{escape(symbol)}</div>
      <div class="hdr-ts">{ts}</div>
      <div class="hdr-badge"
           style="color:{rec_col};background:{rec_bg};border:1px solid {rec_col}44;">
        {rec}
      </div>
    </div>
  </div>

  <!-- ═══ METRIC CARDS ═════════════════════════════════════════════════════ -->
  <div class="metrics">
    <div class="mc"
         style="box-shadow:0 0 22px {m['alpha_color']}20;border-color:{m['alpha_color']}30;">
      <div class="mc-lbl">Alpha Rating</div>
      <div class="mc-val" style="color:{m['alpha_color']};text-shadow:0 0 16px {m['alpha_color']}60;">
        {m['alpha_str']}
      </div>
      <div class="mc-sub">Confidence: {m['confidence']:.0%}</div>
    </div>

    <div class="mc"
         style="box-shadow:0 0 22px {roi_color}20;border-color:{roi_color}30;">
      <div class="mc-lbl">Projected ROI (7d)</div>
      <div class="mc-val" style="color:{roi_color};text-shadow:0 0 16px {roi_color}60;">
        {roi_sign}{m['predicted_return']:.2f}%
      </div>
      <div class="mc-sub">7-day forward return</div>
    </div>

    <div class="mc"
         style="box-shadow:0 0 22px {m['risk_color']}20;border-color:{m['risk_color']}30;">
      <div class="mc-lbl">Risk Level</div>
      <div class="mc-val" style="color:{m['risk_color']};font-size:22px;text-shadow:0 0 16px {m['risk_color']}60;">
        {m['risk_str']}
      </div>
      <div class="mc-sub">ATR/Price: {m['atr_pct']:.2%}</div>
    </div>

    <div class="mc"
         style="box-shadow:0 0 22px {sharpe_col}20;border-color:{sharpe_col}30;">
      <div class="mc-lbl">Sharpe Ratio</div>
      <div class="mc-val" style="color:{sharpe_col};text-shadow:0 0 16px {sharpe_col}60;">
        {m['sharpe']:.2f}
      </div>
      <div class="mc-sub">Ann. vol: {m['vol_ann']:.1%}</div>
    </div>
  </div>

  <!-- ═══ TRADE SETUP + INTELLIGENCE SYNTHESIS ════════════════════════════ -->
  <div class="row2">

    <!-- Trade Setup -->
    <div class="panel">
      <div class="ph" style="color:#3B9EFF;">Trade Setup</div>
      <div class="pb">
        <div class="tlevel tl-entry">
          <span class="tl-lbl" style="color:#3B9EFF;">Entry</span>
          <span class="tl-val" style="color:#3B9EFF;">${m['entry']:,.3f}</span>
        </div>
        <div class="tlevel tl-stop">
          <span class="tl-lbl" style="color:#EF4444;">Stop Loss &#9660;</span>
          <span class="tl-val" style="color:#EF4444;">${m['stop_loss']:,.3f}</span>
        </div>
        <div class="tlevel tl-tp">
          <span class="tl-lbl" style="color:#00FF87;">Take Profit &#9650;</span>
          <span class="tl-val" style="color:#00FF87;">${m['take_profit']:,.3f}</span>
        </div>
        <div class="rr-row">
          <span>Risk / Reward</span>
          <span class="rr-val">1&nbsp;:&nbsp;{m['risk_reward']:.2f}</span>
        </div>
        <div class="rr-row" style="border-top:none; margin-top:4px;">
          <span>ATR (14-bar)</span>
          <span class="rr-val">{m['atr']:,.3f}</span>
        </div>
      </div>
    </div>

    <!-- Intelligence Synthesis -->
    <div class="intel">
      <div class="panel">
        <div class="ph" style="color:#93C5FD;">XGBoost Technical Drivers</div>
        <div class="pb">{feat_html}</div>
      </div>
      <div class="panel">
        <div class="ph" style="color:#4ADE80;">DeepSeek Geopolitical Analysis</div>
        <div class="pb">
          <div class="ds-text">{reasoning_html}</div>
        </div>
      </div>
    </div>

  </div>

  <!-- ═══ PORTFOLIO SIMULATOR ══════════════════════════════════════════════ -->
  <div class="panel">
    <div class="ph" style="color:#CBD5E1;">
      Portfolio Simulator
      <span style="font-weight:400;color:#334155;letter-spacing:0.5px;">
        &nbsp; — 7-day projection · seed capital $10,000
      </span>
    </div>
    <div class="pf-row">
      <div class="pf-stats">
        <div>
          <div class="pf-lbl">Investment</div>
          <div class="pf-amt" style="color:#CBD5E1;">${m['investment']:,.2f}</div>
        </div>
        <div class="pf-arrow">&#8594;</div>
        <div>
          <div class="pf-lbl">Projected Outcome</div>
          <div class="pf-amt" style="color:{curve_col};text-shadow:0 0 12px {curve_col}50;">
            ${m['proj_value']:,.2f}
          </div>
          <div class="pf-pnl" style="color:{curve_col};">
            {pnl_sign}${m['pnl']:,.2f} &nbsp;({roi_sign}{m['predicted_return']:.2f}%)
          </div>
          <div class="pf-hor">Horizon: 7 trading days</div>
        </div>
      </div>
      <div>
        <div class="chart-area">{svg}</div>
        <div class="chart-dates">{date_labels}</div>
      </div>
    </div>
  </div>

  <!-- ═══ FOOTER ════════════════════════════════════════════════════════════ -->
  <div class="footer">
    This report is generated by an autonomous AI system combining XGBoost quantitative signals
    with DeepSeek large language model macro analysis. It does not constitute financial advice.
    Past performance is not indicative of future results. Always perform independent due diligence
    before making investment decisions.
    &nbsp;·&nbsp; Generated: {ts} &nbsp;·&nbsp; Signal confidence: {m['confidence']:.0%}
  </div>

</div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Dialog
# ─────────────────────────────────────────────────────────────────────────────

class AIStrategyReportDialog(QDialog):
    """
    Full-screen institutional strategy report dialog.

    Usage:
        dlg = AIStrategyReportDialog("GOLD", price_data, consensus_result, parent=self)
        dlg.exec()

    Args:
        symbol:           Commodity ticker (e.g. "GOLD").
        price_data:       Dict with keys close/high/low/open/dates (from backend_client).
        consensus_result: Dict returned by the neuro-symbolic consensus pipeline.
    """

    def __init__(
        self,
        symbol: str,
        price_data: dict,
        consensus_result: dict,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._symbol           = symbol
        self._price_data       = price_data or {}
        self._consensus_result = consensus_result or {}
        self._metrics          = _compute_metrics(self._price_data, self._consensus_result)

        self.setWindowTitle(f"AI Alpha Strategy Report — {symbol}")
        self.setModal(True)
        self.resize(1240, 880)
        self.setMinimumSize(960, 720)
        self.setStyleSheet("background: #050A14;")

        self._init_ui()

    # ── Construction ──────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._web = QWebEngineView()
        self._web.setHtml(
            _build_report_html(self._symbol, self._metrics, self._consensus_result)
        )
        root.addWidget(self._web, stretch=1)
        root.addWidget(self._build_action_bar())

    def _build_action_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet(
            "background: #06101F;"
            "border-top: 1px solid #0F2040;"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(24, 0, 24, 0)
        row.setSpacing(10)

        meta = QLabel(
            f"\u00a0\u00a0{self._symbol}"
            f"\u00a0\u00b7\u00a0{datetime.now().strftime('%Y-%m-%d %H:%M')}"
            f"\u00a0\u00b7\u00a0AI Alpha Strategy Report"
            f"\u00a0\u00b7\u00a0Confidence: {self._metrics['confidence']:.0%}"
        )
        meta.setStyleSheet(
            "color: #1E3A5F; font-size: 11px;"
            "font-family: 'SF Mono', 'Menlo', monospace;"
        )
        row.addWidget(meta)
        row.addStretch()

        btn_pdf = self._make_btn("Export to PDF", "#3B9EFF", "#0D1B30", "#1E3A5F", w=138)
        btn_pdf.clicked.connect(self._export_pdf)
        row.addWidget(btn_pdf)

        btn_close = self._make_btn("Close", "#6B7280", "#111111", "#1C1C1C", w=80)
        btn_close.clicked.connect(self.close)
        row.addWidget(btn_close)

        return bar

    @staticmethod
    def _make_btn(
        text: str, color: str, bg: str, bg_hover: str, w: int = 100
    ) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        btn.setFixedWidth(w)
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background:{bg}; color:{color};"
            f"  border:1px solid {color}44; border-radius:6px;"
            f"  font-size:12px; font-weight:600;"
            f"}}"
            f"QPushButton:hover {{ background:{bg_hover}; border-color:{color}; }}"
            f"QPushButton:pressed {{ background:{color}; color:#050A14; }}"
        )
        return btn

    # ── Export ────────────────────────────────────────────────────────────────

    def _export_pdf(self) -> None:
        default = (
            f"StrategyReport_{self._symbol}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Strategy Report as PDF", default, "PDF Files (*.pdf)"
        )
        if not path:
            return

        try:
            from PyQt6.QtPrintSupport import QPrinter

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)

            def _on_done(ok: bool) -> None:
                from PyQt6.QtWidgets import QMessageBox
                if ok:
                    QMessageBox.information(
                        self, "Export Complete",
                        f"Strategy report exported to:\n{path}"
                    )
                else:
                    QMessageBox.warning(
                        self, "Export Failed",
                        "PDF generation failed. Try printing to PDF via your OS."
                    )

            self._web.page().print(printer, _on_done)

        except Exception as exc:
            logger.exception("PDF export failed")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Export Error", f"Could not export PDF:\n{exc}")

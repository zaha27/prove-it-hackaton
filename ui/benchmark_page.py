"""
ui/benchmark_page.py — System Benchmark page for AI Trading Platform.

Architecture:
  BenchmarkResult     — dataclass carrying all output metrics + equity curves
  BenchmarkEngine     — pulls Qdrant patterns, runs XGBoost, computes stats
  _BenchmarkWorker    — QThread wrapper so the UI never freezes
  _StatCard           — reusable metric card widget
  BenchmarkPage       — top-level QWidget; integrate via window.set_benchmark_widget()
                        or add directly to a QTabWidget / QStackedWidget
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Callable

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)

_COMMODITIES = ["GOLD", "OIL", "SILVER", "NATURAL_GAS", "WHEAT", "COPPER"]

# ─────────────────────────────────────────────────────────────────────────────
# Plotly HTML shell — data injected later via runJavaScript("renderChart(...)")
# ─────────────────────────────────────────────────────────────────────────────

_CHART_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    html, body, #chart { width:100%; height:100%; background:#0D0D0D; }
    #placeholder {
      position:absolute; top:50%; left:50%;
      transform:translate(-50%,-50%);
      color:#374151; font-family:-apple-system,sans-serif; font-size:13px;
      pointer-events:none;
    }
  </style>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js" charset="utf-8"></script>
</head>
<body>
  <div id="chart"></div>
  <div id="placeholder">Run a benchmark to see the equity curve</div>

  <script>
    function renderChart(dates, aiEquity, bhEquity, commodity) {
      document.getElementById('placeholder').style.display = 'none';

      var traceAI = {
        x: dates, y: aiEquity,
        type: 'scatter', mode: 'lines',
        name: 'AI Strategy',
        line: { color: '#93C5FD', width: 2.5 },
        fill: 'tozeroy',
        fillcolor: 'rgba(147,197,253,0.04)',
        hovertemplate: '<b>AI</b>  $%{y:.2f}<extra></extra>',
      };
      var traceBH = {
        x: dates, y: bhEquity,
        type: 'scatter', mode: 'lines',
        name: 'Buy & Hold',
        line: { color: '#6B7280', width: 1.5, dash: 'dot' },
        hovertemplate: '<b>B&H</b>  $%{y:.2f}<extra></extra>',
      };

      var layout = {
        paper_bgcolor: '#0D0D0D',
        plot_bgcolor:  '#0D0D0D',
        font: { color:'#9CA3AF', family:"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif", size:11 },
        title: {
          text: commodity + '  —  AI Strategy vs Buy & Hold  (test set, $10,000 start)',
          font: { color:'#F1F5F9', size:13, weight:600 },
          x: 0.02, xanchor:'left',
        },
        xaxis: {
          gridcolor:'#111111', linecolor:'#1C1C1C',
          tickformat:'%b %Y', tickangle:-30,
          showgrid: true,
        },
        yaxis: {
          gridcolor:'#111111', linecolor:'#1C1C1C',
          tickprefix:'$', tickformat:',.0f',
          title:{ text:'Portfolio value (start $10,000 · fixed $1,000/trade)', font:{size:10,color:'#4B5563'} },
          showgrid: true,
        },
        legend: {
          bgcolor:'rgba(13,13,13,0.8)',
          bordercolor:'#1C1C1C', borderwidth:1,
          x:0.02, y:0.98, xanchor:'left', yanchor:'top',
          font:{ size:11 },
        },
        margin: { l:58, r:18, t:44, b:48 },
        hovermode: 'x unified',
        hoverlabel: {
          bgcolor:'#111111', bordercolor:'#1C1C1C',
          font:{ color:'#E5E7EB', size:12 },
        },
      };

      Plotly.newPlot('chart', [traceAI, traceBH], layout, {
        displayModeBar: false,
        responsive: true,
      });
    }
  </script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BenchmarkResult:
    commodity:             str
    total_trades:          int
    correct_trades:        int
    directional_accuracy:  float          # %
    ai_roi:                float          # %  (ai final equity − 100)
    bh_roi:                float          # %  (buy-and-hold final equity − 100)
    alpha:                 float          # ai_roi − bh_roi
    dates:                 list[str]      = field(default_factory=list)
    ai_equity:             list[float]    = field(default_factory=list)
    bh_equity:             list[float]    = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# BenchmarkEngine
# ─────────────────────────────────────────────────────────────────────────────

class BenchmarkEngine:
    """
    Pulls all historical patterns from Qdrant, splits 50/50 chronologically,
    and evaluates XGBoost directional accuracy on the held-out second half.
    """

    _BATCH  = 500
    _QDRANT_TIMEOUT = 60

    def __init__(self) -> None:
        from qdrant_client import QdrantClient
        from src.data.config import config
        from src.data.vector_schema import PRICE_PATTERNS_COLLECTION

        self._qdrant    = QdrantClient(url=config.qdrant_url, timeout=self._QDRANT_TIMEOUT)
        self._collection = PRICE_PATTERNS_COLLECTION.name

    # ── Qdrant helpers ────────────────────────────────────────────────────────

    def _fetch_patterns(self, commodity: str) -> list[dict]:
        """Scroll through the entire collection and return all payloads."""
        payloads: list[dict] = []
        offset = None

        while True:
            points, next_offset = self._qdrant.scroll(
                collection_name=self._collection,
                scroll_filter={
                    "must": [{"key": "commodity", "match": {"value": commodity}}]
                },
                limit=self._BATCH,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                if p.payload:
                    payloads.append(p.payload)
            if next_offset is None or not points:
                break
            offset = next_offset

        return payloads

    # ── Simulation constants ──────────────────────────────────────────────────
    #
    # These three parameters prevent the "exploding ROI" problem:
    #
    #   STARTING_CAPITAL  — dollar value of the paper portfolio
    #   MAX_POSITION_PCT  — fraction of current equity risked per trade
    #                       (10% sizing means a −5% actual return costs $50
    #                        on a $10,000 book, not $500)
    #   TRADING_COST_PCT  — one-way broker commission + slippage (0.1%).
    #                       Applied on the position size for every trade
    #                       regardless of win/loss.
    #
    STARTING_CAPITAL = 10_000.0
    FIXED_POSITION   = 1_000.0     # fixed $1,000 per trade — never changes
    TRADING_COST_PCT = 0.001       # 0.1% commission + slippage per trade

    # ── Main entry point ──────────────────────────────────────────────────────

    def run(
        self,
        commodity: str,
        progress_cb: Callable[[int, int], None],
        log_cb: Callable[[str], None],
    ) -> BenchmarkResult:

        log_cb(f"[INIT] Querying Qdrant for {commodity} patterns...")
        raw = self._fetch_patterns(commodity)
        log_cb(f"[DATA] {len(raw)} raw patterns retrieved")

        # Keep only points that have engineered features + a 7d actual return
        valid: list[dict] = []
        for p in raw:
            features = p.get("features") or {}
            actual   = p.get("return_7d", p.get("next_7d_return"))
            date     = p.get("date", "")
            if features and actual is not None and date:
                valid.append({
                    "date":     date,
                    "features": features,
                    "actual":   float(actual),
                })

        if len(valid) < 20:
            raise ValueError(
                f"Only {len(valid)} usable patterns for {commodity} "
                f"(need ≥20 with engineered features). "
                f"Run the enhanced ingestor first."
            )

        # ── Strict chronological split (no look-ahead) ────────────────────────
        # Sort by date ascending so train is always earlier than test.
        # The split index is the exact midpoint — no overlap, no shuffle.
        valid.sort(key=lambda x: x["date"])

        split = len(valid) // 2
        train = valid[:split]   # noqa: F841 — kept for logging context
        test  = valid[split:]

        log_cb(f"[SPLIT] Train : {train[0]['date']} → {train[-1]['date']}  ({len(train)} pts)")
        log_cb(f"[SPLIT] Test  : {test[0]['date']}  → {test[-1]['date']}   ({len(test)} pts)")
        log_cb(f"[SIM]   Starting capital : ${self.STARTING_CAPITAL:,.0f}")
        log_cb(f"[SIM]   Position size    : ${self.FIXED_POSITION:,.0f} fixed per trade (no compounding)")
        log_cb(f"[SIM]   Trading cost     : {self.TRADING_COST_PCT:.2%} per trade")
        log_cb("")

        # Load (or train) the XGBoost model
        from src.ml.xgboost_trainer import XGBoostTrainer
        trainer = XGBoostTrainer()
        try:
            trainer.load_model(commodity)
            log_cb(f"[MODEL] Loaded xgboost_{commodity}.pkl")
        except FileNotFoundError:
            log_cb("[MODEL] No saved model — training on demand...")
            trainer.train_model(commodity)
        log_cb("")

        # ── Evaluation loop ───────────────────────────────────────────────────
        #
        # Equity accounting rules
        # ───────────────────────
        # • position_size  = current_equity × MAX_POSITION_PCT
        #   (never more than 10% of the book on a single 7-day bet)
        #
        # • dollar_pnl     = position_size × (gross_return / 100)
        #   where gross_return = +actual  (long,  model said UP)
        #                      = −actual  (short, model said DOWN)
        #
        # • trading_cost   = position_size × TRADING_COST_PCT
        #   (always subtracted; simulates round-trip commission / slippage)
        #
        # • new_equity     = old_equity + dollar_pnl − trading_cost
        #   floored at $1 so the account can never go fully bankrupt
        #
        # Buy & Hold accounting
        # ─────────────────────
        # The Qdrant patterns are daily-sampled with 7-day forward returns.
        # Chaining raw 7-day returns day-by-day creates artificial leverage
        # (365 compounded 7-day windows >> one 7-day return over the year).
        # Fix: convert each stored 7-day return to its daily equivalent before
        # chaining, so the B&H equity curve reflects the true 1× buy-and-hold:
        #   daily_r = (1 + r7d/100)^(1/7) − 1

        correct   = 0
        ai_equity = [self.STARTING_CAPITAL]
        bh_equity = [self.STARTING_CAPITAL]
        dates     = [test[0]["date"]]
        evaluated = 0

        for i, point in enumerate(test):
            progress_cb(i + 1, len(test))

            try:
                pred = trainer.predict(commodity, point["features"])
            except Exception as exc:
                log_cb(f"  [{point['date']}] SKIP — prediction error: {exc}")
                continue

            # Clamp to a realistic range (-50% … +50%) to discard
            # corrupted Qdrant payloads and prevent complex-number math.
            actual     = max(-50.0, min(50.0, float(point["actual"])))
            pred_up    = pred > 0
            actual_up  = actual > 0
            is_correct = pred_up == actual_up
            evaluated += 1
            if is_correct:
                correct += 1

            # ── AI equity (fixed dollar position — no compounding) ────────
            # FIXED_POSITION never changes regardless of current equity.
            # Profits accumulate in the account but are never reinvested
            # into the bet size, keeping the equity curve linear.
            gross_pct    = actual if pred_up else -actual    # % on the position
            dollar_pnl   = self.FIXED_POSITION * (gross_pct / 100.0)
            trading_cost = self.FIXED_POSITION * self.TRADING_COST_PCT
            net_pnl      = dollar_pnl - trading_cost

            new_equity = max(1.0, ai_equity[-1] + net_pnl)
            ai_equity.append(new_equity)

            # ── B&H equity (de-overlapped daily chaining) ─────────────────
            # Convert 7-day % return → approximate daily % return.
            # base is clamped > 0 so ** (1/7) always returns a real float,
            # never a complex number (which happens when base < 0).
            base    = max(1e-4, 1.0 + actual / 100.0)
            daily_r = base ** (1.0 / 7.0) - 1.0
            bh_equity.append(bh_equity[-1] * (1.0 + daily_r))

            dates.append(point["date"])

            # log row
            pred_lbl   = f"UP  ({pred:+.2f}%)" if pred_up  else f"DOWN({pred:+.2f}%)"
            actual_lbl = f"UP  ({actual:+.2f}%)" if actual_up else f"DOWN({actual:+.2f}%)"
            tag        = "✓" if is_correct else "✗"
            log_cb(
                f"  [{point['date']}]  Pred:{pred_lbl}  "
                f"Act:{actual_lbl}  {tag}  "
                f"PnL:${net_pnl:+.2f}  Eq:${new_equity:,.0f}"
            )

        if evaluated == 0:
            raise ValueError("No predictions could be made — check model and features.")

        da     = correct / evaluated * 100
        ai_roi = (ai_equity[-1] / self.STARTING_CAPITAL - 1.0) * 100.0
        bh_roi = (bh_equity[-1] / self.STARTING_CAPITAL - 1.0) * 100.0
        alpha  = ai_roi - bh_roi

        log_cb("")
        log_cb("─" * 58)
        log_cb(f"  Directional Accuracy : {da:.1f}%")
        log_cb(f"  AI Final Equity      : ${ai_equity[-1]:>10,.2f}")
        log_cb(f"  B&H Final Equity     : ${bh_equity[-1]:>10,.2f}")
        log_cb(f"  AI Strategy ROI      : {ai_roi:+.2f}%")
        log_cb(f"  Buy & Hold ROI       : {bh_roi:+.2f}%")
        log_cb(f"  Alpha (AI − B&H)     : {alpha:+.2f}%")
        log_cb(f"  Trades evaluated     : {evaluated}")
        log_cb("─" * 58)

        return BenchmarkResult(
            commodity=commodity,
            total_trades=evaluated,
            correct_trades=correct,
            directional_accuracy=da,
            ai_roi=ai_roi,
            bh_roi=bh_roi,
            alpha=alpha,
            dates=dates,
            ai_equity=ai_equity,
            bh_equity=bh_equity,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Background worker
# ─────────────────────────────────────────────────────────────────────────────

class _BenchmarkWorker(QThread):
    progress  = pyqtSignal(int, int)        # (done, total)
    log_line  = pyqtSignal(str)
    finished  = pyqtSignal(object)          # BenchmarkResult
    failed    = pyqtSignal(str)

    def __init__(self, commodity: str, parent=None) -> None:
        super().__init__(parent)
        self._commodity = commodity

    def run(self) -> None:
        try:
            engine = BenchmarkEngine()
            result = engine.run(
                self._commodity,
                progress_cb=lambda done, total: self.progress.emit(done, total),
                log_cb=lambda msg: self.log_line.emit(msg),
            )
            self.finished.emit(result)
        except Exception as exc:
            logger.exception("BenchmarkWorker failed")
            self.failed.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Stat card widget
# ─────────────────────────────────────────────────────────────────────────────

class _StatCard(QFrame):
    """Single metric card: large value + label + optional delta colour."""

    def __init__(self, title: str, placeholder: str = "—", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setStyleSheet("""
            QFrame#statCard {
                background: #111111;
                border: 1px solid #1C1C1C;
                border-radius: 8px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(86)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(4)

        self._value_label = QLabel(placeholder)
        self._value_label.setFont(QFont("-apple-system", 24, QFont.Weight.Bold))
        self._value_label.setStyleSheet("color:#F1F5F9; background:transparent;")
        layout.addWidget(self._value_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color:#6B7280; font-size:11px; font-weight:500;"
            "letter-spacing:0.4px; background:transparent;"
        )
        layout.addWidget(title_label)

    def set_value(self, text: str, color: str = "#F1F5F9") -> None:
        self._value_label.setText(text)
        self._value_label.setStyleSheet(f"color:{color}; background:transparent;")


# ─────────────────────────────────────────────────────────────────────────────
# BenchmarkPage
# ─────────────────────────────────────────────────────────────────────────────

class BenchmarkPage(QWidget):
    """
    Full-page benchmark widget. Drop into any layout:

        page = BenchmarkPage()
        tab_widget.addTab(page, "System Benchmark")
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet("background:#080808;")
        self._worker: _BenchmarkWorker | None = None
        self._page_loaded = False
        self._pending_result: BenchmarkResult | None = None
        self._init_ui()

    # ── Construction ──────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_top_bar())
        root.addWidget(self._build_progress_row())
        root.addWidget(self._build_stats_row())

        # Lower half: chart (left) + log (right)
        lower = QHBoxLayout()
        lower.setContentsMargins(16, 0, 16, 16)
        lower.setSpacing(12)
        lower.addWidget(self._build_chart(), stretch=3)
        lower.addWidget(self._build_log(),   stretch=1)
        root.addLayout(lower, stretch=1)

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet("background:#080808; border-bottom:1px solid #1C1C1C;")
        row = QHBoxLayout(bar)
        row.setContentsMargins(22, 0, 22, 0)

        title = QLabel("System Benchmark")
        title.setStyleSheet(
            "color:#F1F5F9; font-size:15px; font-weight:700; letter-spacing:0.2px;"
        )
        row.addWidget(title)
        row.addStretch()

        sub = QLabel("50/50 chronological split  ·  XGBoost directional accuracy")
        sub.setStyleSheet("color:#374151; font-size:11px;")
        row.addWidget(sub)
        return bar

    def _build_top_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background:#080808; border-bottom:1px solid #111111;")
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(10)

        row.addWidget(QLabel(
            "<span style='color:#6B7280;font-size:11px;'>Commodity</span>"
        ))

        self._combo = QComboBox()
        self._combo.addItems(_COMMODITIES)
        self._combo.setFixedHeight(28)
        self._combo.setFixedWidth(150)
        self._combo.setStyleSheet("""
            QComboBox {
                background:#111111; color:#F1F5F9;
                border:1px solid #1C1C1C; border-radius:5px;
                font-size:12px; padding:0 10px;
            }
            QComboBox::drop-down { border:none; width:18px; }
            QComboBox QAbstractItemView {
                background:#111111; color:#F1F5F9;
                border:1px solid #1C1C1C;
                selection-background-color:#1E3A5F;
            }
        """)
        row.addWidget(self._combo)

        self._run_btn = QPushButton("Run System Benchmark")
        self._run_btn.setFixedHeight(28)
        self._run_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._run_btn.setStyleSheet("""
            QPushButton {
                background:#1E3A5F; color:#93C5FD;
                border:1px solid #2563EB; border-radius:5px;
                font-size:12px; font-weight:600; padding:0 18px;
            }
            QPushButton:hover  { background:#2563EB; color:#FFFFFF; }
            QPushButton:pressed { background:#1D4ED8; }
            QPushButton:disabled { background:#111111; color:#374151; border-color:#1C1C1C; }
        """)
        self._run_btn.clicked.connect(self._on_run)
        row.addWidget(self._run_btn)

        row.addStretch()

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color:#374151; font-size:11px;")
        row.addWidget(self._status_label)
        return bar

    def _build_progress_row(self) -> QWidget:
        container = QWidget()
        container.setFixedHeight(6)
        container.setStyleSheet("background:#080808;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(3)
        self._progress.setStyleSheet("""
            QProgressBar {
                background:#111111; border:none; border-radius:1px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1E3A5F, stop:1 #93C5FD
                );
                border-radius:1px;
            }
        """)
        self._progress.hide()
        layout.addWidget(self._progress)
        return container

    def _build_stats_row(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background:#080808;")
        container.setFixedHeight(110)
        row = QHBoxLayout(container)
        row.setContentsMargins(16, 12, 16, 12)
        row.setSpacing(12)

        self._card_da      = _StatCard("Directional Accuracy")
        self._card_roi     = _StatCard("AI Strategy ROI")
        self._card_alpha   = _StatCard("Alpha  (AI − B&H)")
        self._card_trades  = _StatCard("Trades Evaluated")

        for card in (self._card_da, self._card_roi, self._card_alpha, self._card_trades):
            row.addWidget(card)
        return container

    def _build_chart(self) -> QWebEngineView:
        self._chart = QWebEngineView()
        self._chart.setMinimumHeight(260)
        self._chart.setStyleSheet("background:#0D0D0D; border:none;")
        self._chart.loadFinished.connect(self._on_chart_loaded)
        self._chart.setHtml(_CHART_HTML, QUrl("about:blank"))
        return self._chart

    def _build_log(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet("background:#0D0D0D;")
        vbox = QVBoxLayout(wrapper)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(32)
        header.setStyleSheet("background:#080808; border:1px solid #1C1C1C; border-radius:6px 6px 0 0;")
        hrow = QHBoxLayout(header)
        hrow.setContentsMargins(12, 0, 12, 0)
        lbl = QLabel("Simulation Log")
        lbl.setStyleSheet("color:#6B7280; font-size:10px; font-weight:600; letter-spacing:0.5px;")
        hrow.addWidget(lbl)
        hrow.addStretch()
        self._clear_btn = QPushButton("clear")
        self._clear_btn.setFixedHeight(18)
        self._clear_btn.setStyleSheet(
            "QPushButton { background:transparent; color:#374151; border:none; font-size:10px; }"
            "QPushButton:hover { color:#6B7280; }"
        )
        hrow.addWidget(self._clear_btn)
        vbox.addWidget(header)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setStyleSheet("""
            QTextEdit {
                background:#0A0A0A;
                color:#4ADE80;
                border:1px solid #1C1C1C;
                border-top:none;
                border-radius:0 0 6px 6px;
                padding:10px 12px;
                font-size:11px;
                selection-background-color:#1E3A5F;
            }
            QScrollBar:vertical {
                background:#0A0A0A; width:6px; border:none;
            }
            QScrollBar::handle:vertical {
                background:#1C1C1C; border-radius:3px; min-height:20px;
            }
        """)
        mono = QFont("Menlo")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(10)
        self._log_edit.setFont(mono)
        self._clear_btn.clicked.connect(self._log_edit.clear)
        vbox.addWidget(self._log_edit, stretch=1)
        return wrapper

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_run(self) -> None:
        if self._worker and self._worker.isRunning():
            return

        commodity = self._combo.currentText()
        self._log_edit.clear()
        self._reset_cards()
        self._set_running(True)
        self._status_label.setText(f"Benchmarking {commodity}...")

        self._worker = _BenchmarkWorker(commodity, parent=self)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        pct = int(done / total * 100) if total else 0
        self._progress.setValue(pct)
        self._status_label.setText(f"Evaluating {done}/{total}...")

    def _append_log(self, msg: str) -> None:
        self._log_edit.append(msg)
        sb = self._log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_finished(self, result: BenchmarkResult) -> None:
        self._set_running(False)
        self._status_label.setText(
            f"Done  ·  {result.total_trades} trades  ·  "
            f"{result.directional_accuracy:.1f}% accuracy"
        )
        self._update_cards(result)
        self._render_chart(result)

    def _on_failed(self, error: str) -> None:
        self._set_running(False)
        self._status_label.setText("Benchmark failed")
        self._append_log(f"\n[ERROR] {error}")

    def _on_chart_loaded(self, ok: bool) -> None:
        self._page_loaded = ok
        if ok and self._pending_result is not None:
            self._render_chart(self._pending_result)
            self._pending_result = None

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _set_running(self, running: bool) -> None:
        self._run_btn.setEnabled(not running)
        self._combo.setEnabled(not running)
        if running:
            self._progress.setValue(0)
            self._progress.show()
        else:
            self._progress.hide()

    def _reset_cards(self) -> None:
        for card in (self._card_da, self._card_roi, self._card_alpha, self._card_trades):
            card.set_value("—")

    def _update_cards(self, r: BenchmarkResult) -> None:
        # Directional Accuracy
        da_color = (
            "#4ADE80" if r.directional_accuracy >= 55
            else "#FCD34D" if r.directional_accuracy >= 45
            else "#F87171"
        )
        self._card_da.set_value(f"{r.directional_accuracy:.1f}%", da_color)

        # AI ROI
        roi_color = "#4ADE80" if r.ai_roi >= 0 else "#F87171"
        self._card_roi.set_value(f"{r.ai_roi:+.2f}%", roi_color)

        # Alpha
        alpha_color = "#4ADE80" if r.alpha >= 0 else "#F87171"
        self._card_alpha.set_value(f"{r.alpha:+.2f}%", alpha_color)

        # Trades
        self._card_trades.set_value(str(r.total_trades), "#F1F5F9")

    def _render_chart(self, result: BenchmarkResult) -> None:
        if not self._page_loaded:
            self._pending_result = result
            return

        dates_js     = json.dumps(result.dates)
        ai_equity_js = json.dumps([round(v, 4) for v in result.ai_equity])
        bh_equity_js = json.dumps([round(v, 4) for v in result.bh_equity])
        commodity_js = json.dumps(result.commodity)

        self._chart.page().runJavaScript(
            f"renderChart({dates_js}, {ai_equity_js}, {bh_equity_js}, {commodity_js});"
        )

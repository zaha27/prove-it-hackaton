"""
ui/panel_ai.py — AI insight panel, clean Perplexity style, no emoji.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout, QComboBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class PanelAI(QWidget):
    """
    LLM Chain-of-Thought analysis panel.
    Call set_loading(True) before fetch, update_insight(text) when done.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:#0D0D0D;")
        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_loading)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_tag_bar())
        layout.addWidget(self._build_text_area(), stretch=1)
        self._recommendation_label = QLabel("")
        self._recommendation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._recommendation_label)
        self.set_recommendation("HOLD")

    def _build_header(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(40)
        bar.setStyleSheet("background:#080808; border-bottom:1px solid #1C1C1C;")
        row = QHBoxLayout(bar)
        row.setContentsMargins(18, 0, 18, 0)

        title = QLabel("AI Insight")
        title.setStyleSheet(
            "color:#9CA3AF; font-size:12px; font-weight:500; letter-spacing:0.3px;"
        )
        row.addWidget(title)
        row.addStretch()

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color:#374151; font-size:11px;")
        row.addWidget(self._status_label)

        # Tiny status indicator square (replaces pulsing dot)
        self._indicator = QLabel("")
        self._indicator.setFixedSize(6, 6)
        self._indicator.setStyleSheet(
            "background:#1C1C1C; border-radius:3px; margin-left:6px;"
        )
        row.addWidget(self._indicator)
        return bar

    def _build_tag_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(30)
        bar.setStyleSheet("background:#0D0D0D; border-bottom:1px solid #111111;")
        row = QHBoxLayout(bar)
        row.setContentsMargins(18, 0, 18, 0)
        row.setSpacing(6)

        for text, fg, bg in [
            ("XGBoost Quant",     "#93C5FD", "rgba(147,197,253,0.08)"),
            ("DeepSeek Validator","#4ADE80", "rgba(74,222,128,0.07)"),
        ]:
            tag = QLabel(text)
            tag.setStyleSheet(
                f"color:{fg}; background:{bg}; border-radius:4px;"
                "font-size:10px; font-weight:500; padding:1px 8px;"
            )
            row.addWidget(tag)

        row.addStretch()

        # Risk profile label
        risk_label = QLabel("Risk:")
        risk_label.setStyleSheet("color:#6B7280; font-size:10px; font-weight:500;")
        row.addWidget(risk_label)

        # Risk selector
        self._risk_combo = QComboBox()
        self._risk_combo.addItems(["Conservative", "Balanced", "Aggressive"])
        self._risk_combo.setCurrentIndex(1)  # Balanced default
        self._risk_combo.setFixedHeight(20)
        self._risk_combo.setStyleSheet(
            "QComboBox {"
            "  background:#111111; color:#F1F5F9; border:1px solid #1C1C1C;"
            "  border-radius:4px; font-size:10px; padding:0 8px; min-width:88px;"
            "}"
            "QComboBox::drop-down { border:none; width:16px; }"
            "QComboBox::down-arrow { width:8px; height:8px; }"
            "QComboBox QAbstractItemView {"
            "  background:#111111; color:#F1F5F9; border:1px solid #1C1C1C;"
            "  selection-background-color:#1E3A5F; outline:none;"
            "}"
        )
        row.addWidget(self._risk_combo)
        return bar

    def _build_text_area(self) -> QTextEdit:
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        font = QFont("Menlo", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text_edit.setFont(font)
        self._text_edit.setStyleSheet(
            "QTextEdit {"
            "  background:#0D0D0D;"
            "  color:#E5E7EB;"
            "  border:none;"
            "  padding:20px 22px;"
            "  selection-background-color:#1E3A5F;"
            "}"
        )
        return self._text_edit

    # Public contract ──────────────────────────────────────────────────────────

    def get_risk_profile(self) -> str:
        """Return the currently selected risk profile: Conservative, Balanced, or Aggressive."""
        return self._risk_combo.currentText()

    def update_insight(self, insight_text: str) -> None:
        """Called by Backend/Bridge with the LLM response (plain text or markdown)."""
        self.set_text(insight_text)

    def set_recommendation(self, decision: str):
        normalized = (decision or "").strip().upper()
        self._recommendation_label.setText(
            f"<b>AI suggests from your investment profile to:</b> {normalized}"
        )

        base_style = "font-size: 14px; padding: 10px; border-top: 1px solid #333;"
        if normalized == "BUY":
            color = "#00E676"
        elif normalized == "SELL":
            color = "#FF1744"
        else:
            color = "#FFEA00"

        self._recommendation_label.setStyleSheet(f"color: {color}; {base_style}")

    def update_consensus(self, consensus_result: dict) -> None:
        """Display XGBoost + DeepSeek neuro-symbolic analysis result.

        Args:
            consensus_result: Dict with debate rounds and final recommendation
        """
        lines = []

        # Header with source attribution
        commodity = consensus_result.get("commodity", "Unknown")
        consensus_reached = consensus_result.get("consensus_reached", False)
        rounds = consensus_result.get("rounds_conducted", 0)

        lines.append(f"# AI Consensus Analysis — {commodity}")
        lines.append("")

        # Source attribution badge
        lines.append("> **Powered by:** XGBoost Quant + DeepSeek Validator")
        lines.append("")

        # Consensus status
        if consensus_reached:
            lines.append("✓ **Consensus Reached**")
        else:
            lines.append("⚠ **No Consensus** (max rounds reached)")
        lines.append(f"*Debate rounds: {rounds}*")
        lines.append("")

        # Final recommendation
        recommendation = consensus_result.get("final_recommendation", "HOLD")
        self.set_recommendation(recommendation)
        confidence = consensus_result.get("confidence", 0.5)
        direction = consensus_result.get("direction", "hold")
        risk_level = consensus_result.get("risk_level", "medium")

        lines.append(f"## Final Recommendation: **{recommendation}**")
        lines.append(f"- **Confidence:** {confidence:.0%}")
        lines.append(f"- **Direction:** {direction.upper()}")
        lines.append(f"- **Risk Level:** {risk_level.upper()}")
        lines.append("")

        # Final reasoning
        final_reasoning = consensus_result.get("final_reasoning", "")
        if final_reasoning:
            lines.append("### Reasoning")
            lines.append(final_reasoning)
            lines.append("")

        # XGBoost input summary
        xgboost = consensus_result.get("xgboost_input", {})
        if xgboost:
            prediction = xgboost.get("prediction_pct", 0)
            xgb_confidence = xgboost.get("confidence", 0)
            lines.append("### XGBoost Technical Analysis")
            lines.append(f"- Prediction: {prediction:+.2f}%")
            lines.append(f"- Confidence: {xgb_confidence:.0%}")
            lines.append("")

        # Yahoo news summary
        news_summary = consensus_result.get("yahoo_news_summary", "")
        if news_summary:
            lines.append("### News Sentiment")
            lines.append(news_summary[:500])  # Truncate if too long
            lines.append("")

        # Debate history (collapsible sections)
        debate_history = consensus_result.get("debate_history", [])
        if debate_history:
            lines.append("---")
            lines.append("## Debate History")
            lines.append("")

            for i, round_data in enumerate(debate_history, 1):
                lines.append(f"### Round {i}")

                # XGBoost Quant position
                quant_pos = round_data.get("gemma4_position", {})
                quant_dir = quant_pos.get("direction", "unknown")
                quant_conf = quant_pos.get("confidence", 0)

                lines.append(f"**XGBoost Quant:** {quant_dir.upper()} ({quant_conf}% confidence)")

                # Quant argument
                quant_arg = round_data.get("gemma4_argument", "")
                if quant_arg:
                    lines.append(f"> {quant_arg[:200]}...")

                # Sources
                sources = round_data.get("gemma4_sources", [])
                if sources:
                    lines.append(f"*Sources: {', '.join(sources[:3])}*")

                lines.append("")

                # DeepSeek position
                deepseek_pos = round_data.get("deepseek_position", {})
                deepseek_dir = deepseek_pos.get("direction", "unknown")
                deepseek_conf = deepseek_pos.get("confidence", 0)

                lines.append(f"**DeepSeek:** {deepseek_dir.upper()} ({deepseek_conf}% confidence)")

                # DeepSeek critique
                critique = round_data.get("deepseek_critique", "")
                if critique:
                    lines.append(f"> {critique[:200]}...")

                # Agreement score
                agreement = round_data.get("agreement_score", 0)
                lines.append(f"*Agreement: {agreement:.0%}*")
                lines.append("")

        self.set_text("\n".join(lines))

    def set_text(self, text: str) -> None:
        self._timer.stop()
        self._status_label.setText("")
        self._indicator.setStyleSheet(
            "background:#4ADE80; border-radius:3px; margin-left:6px;"
        )
        self._text_edit.setMarkdown(text)

    def set_loading(self, loading: bool) -> None:
        if loading:
            self._text_edit.clear()
            self._dot_count = 0
            self._indicator.setStyleSheet(
                "background:#93C5FD; border-radius:3px; margin-left:6px;"
            )
            self._timer.start(400)
        else:
            self._timer.stop()
            self._status_label.setText("")
            self._indicator.setStyleSheet(
                "background:#1C1C1C; border-radius:3px; margin-left:6px;"
            )

    def _tick_loading(self) -> None:
        self._dot_count = (self._dot_count + 1) % 4
        suffix = "." * self._dot_count
        self._status_label.setText(f"Analyzing{suffix}")
        # Pulse: bright -> dim -> bright
        bright = self._dot_count % 2 == 0
        color = "#93C5FD" if bright else "#1E3A5F"
        self._indicator.setStyleSheet(
            f"background:{color}; border-radius:3px; margin-left:6px;"
        )

    def show_loading_animation(self, symbol: str) -> None:
        """Show a cool animated loading state for multi-agent consensus.

        Args:
            symbol: The commodity symbol being analyzed
        """
        self._timer.stop()
        self._text_edit.clear()

        # Build animated HTML content
        html = f"""
        <div style="padding: 40px 20px; text-align: center; color: #E5E7EB;">
            <h2 style="color: #93C5FD; margin-bottom: 30px;">Analyzing {symbol}</h2>

            <div style="margin: 30px 0;">
                <div style="display: inline-block; animation: pulse 1.5s infinite;">
                    <span style="font-size: 14px; color: #93C5FD; font-family: Menlo, monospace;">XGBoost</span>
                </div>
                <div style="display: inline-block; margin: 0 20px; animation: bounce 1s infinite;">
                    <span style="font-size: 32px; color: #6B7280;">&#8594;</span>
                </div>
                <div style="display: inline-block; animation: pulse 1.5s infinite 0.5s;">
                    <span style="font-size: 14px; color: #4ADE80; font-family: Menlo, monospace;">DeepSeek</span>
                </div>
            </div>

            <div style="margin-top: 30px; font-family: Menlo, monospace; font-size: 13px;">
                <p style="color: #6B7280; margin: 8px 0;">
                    <span style="color: #93C5FD;">&#9679;</span> XGBoost Quant — Computing technical signal...
                </p>
                <p style="color: #6B7280; margin: 8px 0;">
                    <span style="color: #4ADE80;">&#9679;</span> DeepSeek Validator — Running macro reality check...
                </p>
            </div>

            <div style="margin-top: 40px; color: #374151; font-size: 12px;">
                Neuro-Symbolic Pipeline<br/>
                <span style="color: #6B7280;">Quant signal validated against macro context</span>
            </div>
        </div>

        <style>
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; transform: scale(1); }}
                50% {{ opacity: 0.5; transform: scale(0.95); }}
            }}
            @keyframes bounce {{
                0%, 100% {{ transform: translateX(0); }}
                50% {{ transform: translateX(10px); }}
            }}
        </style>
        """
        self._text_edit.setHtml(html)

        # Start pulsing indicator
        self._indicator.setStyleSheet(
            "background:#93C5FD; border-radius:3px; margin-left:6px;"
        )
        self._dot_count = 0
        self._timer.start(400)

"""
ui/panel_ai.py — AI insight panel, clean Perplexity style, no emoji.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import logging

logger = logging.getLogger(__name__)


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
            ("XGBoost Quant",      "#93C5FD", "rgba(147,197,253,0.08)"),
            ("DeepSeek Validator","#4ADE80", "rgba(74,222,128,0.07)"),
        ]:
            tag = QLabel(text)
            tag.setStyleSheet(
                f"color:{fg}; background:{bg}; border-radius:4px;"
                "font-size:10px; font-weight:500; padding:1px 8px;"
            )
            row.addWidget(tag)

        row.addStretch()
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

    def update_insight(self, insight_text: str) -> None:
        """Called by Backend/Bridge with the LLM response (plain text or markdown)."""
        logger.info(f"PanelAI: updating insight with text (length: {len(insight_text)})")
        self.set_text(insight_text)

    def set_recommendation(self, decision: str):
        normalized = (decision or "HOLD").strip().upper()
        self._recommendation_label.setText(
            f"<b>AI suggests from your investment profile to:</b> {normalized}"
        )

        base_style = "font-size: 14px; padding: 10px; border-top: 1px solid #333;"
        if "BUY" in normalized:
            color = "#00E676"
        elif "SELL" in normalized:
            color = "#FF1744"
        else:
            color = "#FFEA00"

        self._recommendation_label.setStyleSheet(f"color: {color}; {base_style}")

    def update_consensus(self, consensus_result: dict) -> None:
        """Display XGBoost + DeepSeek neuro-symbolic analysis result with clean, professional HTML."""
        import logging
        logger = logging.getLogger(__name__)
        
        self._timer.stop()
        self._status_label.setText("")
        
        # 1. Safety net: If it's not a dict, show raw data
        if not isinstance(consensus_result, dict):
            error_html = f"""
            <div style="color: #F87171; font-family: sans-serif; padding: 20px;">
                <h3>Data Format Error</h3>
                <p>Expected a dictionary from the backend, but received:</p>
                <pre style="background: #111111; padding: 10px; border-radius: 4px; color: #D1D5DB; white-space: pre-wrap;">{str(consensus_result)}</pre>
            </div>
            """
            self._text_edit.setHtml(error_html)
            self._indicator.setStyleSheet("background:#F87171; border-radius:3px; margin-left:6px;")
            return

        try:
            # 2. Safe data extraction (with fallbacks)
            commodity = str(consensus_result.get("commodity", "Unknown"))
            consensus_reached = bool(consensus_result.get("consensus_reached", False))
            rounds = int(consensus_result.get("rounds_conducted", 0))
            recommendation = str(consensus_result.get("final_recommendation", "HOLD"))
            
            # Handle confidence safely
            conf_raw = consensus_result.get("confidence", 0.5)
            try:
                confidence = float(conf_raw)
            except (ValueError, TypeError):
                confidence = 0.5
                
            self.set_recommendation(recommendation)
            
            # Prepare HTML Design (No emojis)
            status_color = "#4ADE80" if consensus_reached else "#FCD34D"
            status_text = "Consensus Reached" if consensus_reached else "No Consensus (Max rounds hit)"
            
            html_parts = []
            html_parts.append(f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #E5E7EB;">
                <h2 style="color: #F1F5F9; margin-bottom: 5px; font-weight: 600;">AI Consensus Analysis — {commodity}</h2>
                <p style="color: #9CA3AF; font-size: 12px; margin-top: 0;">Powered by XGBoost Quant + DeepSeek Validator</p>
                
                <div style="background-color: #1A1A1A; padding: 12px; border-radius: 6px; border-left: 4px solid {status_color}; margin-bottom: 20px;">
                    <b style="color: {status_color}; font-size: 14px;">{status_text}</b>
                    <span style="color: #6B7280; font-size: 12px; margin-left: 10px;">(After {rounds} debate rounds)</span><br>
                    <b style="color: #F1F5F9; font-size: 15px; display: block; margin-top: 8px;">Confidence: {confidence:.0%}</b>
                </div>
            """)

            # --- XGBoost Feature Importance ---
            xgboost = consensus_result.get("xgboost_input", {})
            if isinstance(xgboost, dict) and "top_features" in xgboost:
                top_features = xgboost.get("top_features", [])
                if isinstance(top_features, list) and top_features:
                    html_parts.append("""
                    <h3 style="color: #93C5FD; border-bottom: 1px solid #262626; padding-bottom: 5px; font-weight: 500;">XGBoost Core Drivers</h3>
                    <table width="100%" cellspacing="0" cellpadding="6" style="margin-bottom: 25px; border-collapse: collapse;">
                    """)
                    
                    for feat in top_features:
                        if not isinstance(feat, dict): continue
                        
                        name = str(feat.get("name", "Unknown"))
                        
                        try:
                            importance = float(feat.get("importance", 0))
                        except (ValueError, TypeError):
                            importance = 0.0
                            
                        impact = str(feat.get("impact", "neutral")).lower()
                        
                        bar_color = "#4ADE80" if impact == "positive" else "#F87171" if impact == "negative" else "#9CA3AF"
                        width_pct = min(100, int(importance * 200)) # Scale for visibility
                        
                        html_parts.append(f"""
                        <tr>
                            <td width="40%" style="color: #D1D5DB; font-size: 13px; border-bottom: 1px solid #1A1A1A;">{name}</td>
                            <td width="45%" style="border-bottom: 1px solid #1A1A1A;">
                                <div style="background-color: #1C1C1C; width: 100%; height: 6px; border-radius: 3px; overflow: hidden;">
                                    <div style="background-color: {bar_color}; width: {width_pct}%; height: 100%; border-radius: 3px;"></div>
                                </div>
                            </td>
                            <td width="15%" style="color: #9CA3AF; font-size: 12px; text-align: right; border-bottom: 1px solid #1A1A1A;">{importance:.1%}</td>
                        </tr>
                        """)
                    html_parts.append("</table>")

            # --- DeepSeek Reasoning ---
            final_reasoning = consensus_result.get("final_reasoning", "")
            if final_reasoning:
                # Escape HTML chars to prevent breaking rendering
                safe_reasoning = str(final_reasoning).replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
                html_parts.append(f"""
                <h3 style="color: #4ADE80; border-bottom: 1px solid #262626; padding-bottom: 5px; font-weight: 500;">DeepSeek Risk Manager Verdict</h3>
                <div style="color: #E5E7EB; font-size: 13px; line-height: 1.6; background: rgba(74, 222, 128, 0.05); padding: 12px; border-radius: 6px; border: 1px solid rgba(74, 222, 128, 0.1);">
                    {safe_reasoning}
                </div>
                """)

            # --- Debate History ---
            debate_history = consensus_result.get("debate_history", [])
            if isinstance(debate_history, list) and debate_history:
                html_parts.append("""
                <h3 style="color: #9CA3AF; border-bottom: 1px solid #262626; padding-bottom: 5px; margin-top: 30px; font-weight: 500;">Internal Debate Log</h3>
                """)
                for i, round_data in enumerate(debate_history, 1):
                    if not isinstance(round_data, dict): continue
                    
                    quant_pos = round_data.get("gemma4_position", {})
                    ds_pos = round_data.get("deepseek_position", {})
                    
                    quant_dir = str(quant_pos.get('direction', 'UNK')).upper() if isinstance(quant_pos, dict) else "UNK"
                    ds_dir = str(ds_pos.get('direction', 'UNK')).upper() if isinstance(ds_pos, dict) else "UNK"
                    
                    quant_arg = str(round_data.get('gemma4_argument', '')).replace("<", "&lt;")[:150]
                    ds_critique = str(round_data.get('deepseek_critique', '')).replace("<", "&lt;")[:150]
                    
                    try:
                        agr_score = float(round_data.get('agreement_score', 0))
                    except (ValueError, TypeError):
                        agr_score = 0.0
                    
                    html_parts.append(f"""
                    <div style="margin-bottom: 15px; border-left: 2px solid #374151; padding-left: 12px; background: rgba(255,255,255,0.02); padding: 10px; border-radius: 0 6px 6px 0;">
                        <div style="font-size: 11px; color: #9CA3AF; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px;"><b>Round {i}</b> &nbsp;|&nbsp; Agreement: {agr_score:.0%}</div>
                        <div style="color: #93C5FD; font-size: 12px; margin-bottom: 4px;"><b>Quant:</b> {quant_dir} <span style="color:#6B7280;"><i>({quant_arg}...)</i></span></div>
                        <div style="color: #4ADE80; font-size: 12px;"><b>Risk Mgr:</b> {ds_dir} <span style="color:#6B7280;"><i>({ds_critique}...)</i></span></div>
                    </div>
                    """)

            # Fallback if nothing was rendered
            if len(html_parts) == 1:
                 html_parts.append(f"""
                 <div style="padding: 20px; background: #1A1A1A; border-radius: 6px; color: #D1D5DB;">
                    <p><b>Raw Data Dump:</b></p>
                    <pre style="white-space: pre-wrap; font-size: 11px; color: #9CA3AF;">{str(consensus_result)}</pre>
                 </div>
                 """)

            html_parts.append("</div>")

            # Combine and set HTML
            final_html = "".join(html_parts)
            self._text_edit.setHtml(final_html)
            self._indicator.setStyleSheet("background:#4ADE80; border-radius:3px; margin-left:6px;")

        except Exception as e:
            logger.exception("Failed to render consensus HTML")
            error_html = f"""
            <div style="color: #F87171; font-family: sans-serif; padding: 20px;">
                <h3>Rendering Error</h3>
                <p>Failed to parse the AI analysis:</p>
                <pre style="background: #111111; padding: 10px; border-radius: 4px; color: #D1D5DB;">{str(e)}</pre>
            </div>
            """
            self._text_edit.setHtml(error_html)
            self._indicator.setStyleSheet("background:#F87171; border-radius:3px; margin-left:6px;")
            
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
        <div style="padding: 40px 20px; text-align: center; color: #E5E7EB; font-family: -apple-system, sans-serif;">
            <h2 style="color: #93C5FD; margin-bottom: 30px; font-weight: 500;">Analyzing {symbol}</h2>

            <div style="margin: 30px 0;">
                <div style="display: inline-block; animation: pulse 1.5s infinite;">
                    <span style="font-size: 14px; color: #93C5FD; font-family: Menlo, monospace; font-weight: bold;">XGBoost</span>
                </div>
                <div style="display: inline-block; margin: 0 20px; animation: bounce 1s infinite;">
                    <span style="font-size: 32px; color: #6B7280;">&#8594;</span>
                </div>
                <div style="display: inline-block; animation: pulse 1.5s infinite 0.5s;">
                    <span style="font-size: 14px; color: #4ADE80; font-family: Menlo, monospace; font-weight: bold;">DeepSeek</span>
                </div>
            </div>

            <div style="margin-top: 30px; font-family: Menlo, monospace; font-size: 13px; text-align: left; display: inline-block;">
                <p style="color: #9CA3AF; margin: 10px 0;">
                    <span style="color: #93C5FD;">&#9679;</span> XGBoost Quant — Computing technical signal...
                </p>
                <p style="color: #9CA3AF; margin: 10px 0;">
                    <span style="color: #4ADE80;">&#9679;</span> DeepSeek Validator — Running macro reality check...
                </p>
            </div>

            <div style="margin-top: 50px; color: #4B5563; font-size: 12px; border-top: 1px solid #1C1C1C; padding-top: 20px; max-width: 80%; margin-left: auto; margin-right: auto;">
                <b>Neuro-Symbolic Pipeline</b><br/>
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
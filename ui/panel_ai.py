"""
ui/panel_ai.py — AI insight panel, clean Perplexity style, no emoji.
# TODO: Dev1 — add streaming token display when using real Anthropic API
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout
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
            ("Chain-of-Thought", "#93C5FD", "rgba(147,197,253,0.08)"),
            ("claude-sonnet",    "#6B7280", "rgba(107,114,128,0.06)"),
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
        self.set_text(insight_text)

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

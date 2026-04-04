"""
ui/panel_ai.py — AI insight panel with loading animation.
# TODO: Dev1 — add streaming token display when using real Anthropic API
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class PanelAI(QWidget):
    """
    Panel that displays the LLM Chain-of-Thought analysis.

    Usage:
        panel.set_loading(True)   # show "Analyzing..." animation
        panel.set_text(insight)   # display the result
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dot_count = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick_loading)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header_bar = QWidget()
        header_bar.setFixedHeight(32)
        header_bar.setStyleSheet(
            "background:#161b22;border-bottom:1px solid #30363d;"
        )
        hbox = QHBoxLayout(header_bar)
        hbox.setContentsMargins(8, 0, 8, 0)
        title = QLabel("⚡ AI INSIGHT")
        title.setStyleSheet(
            "color:#FFD700;font-size:11px;font-weight:bold;letter-spacing:2px;"
        )
        hbox.addWidget(title)
        hbox.addStretch()
        self._loading_label = QLabel("")
        self._loading_label.setStyleSheet("color:#8b949e;font-size:12px;")
        hbox.addWidget(self._loading_label)
        layout.addWidget(header_bar)

        # Text area
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        font = QFont("Menlo", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._text_edit.setFont(font)
        self._text_edit.setStyleSheet(
            "QTextEdit{background:#0d1117;color:#cdd9e5;border:none;padding:12px;}"
        )
        layout.addWidget(self._text_edit, stretch=1)

    def update_insight(self, insight_text: str) -> None:
        """
        Public contract method — called by Backend/Bridge with the LLM response.

        Args:
            insight_text: plain text or markdown string from the AI engine.
        """
        self.set_text(insight_text)

    def set_text(self, text: str) -> None:
        """Display the AI analysis text. Stops any loading animation."""
        self._timer.stop()
        self._loading_label.setText("")
        self._text_edit.setMarkdown(text)

    def set_loading(self, loading: bool) -> None:
        """Show or hide the 'Analyzing...' animation."""
        if loading:
            self._text_edit.setPlaceholderText("Waiting for AI analysis...")
            self._text_edit.clear()
            self._dot_count = 0
            self._timer.start(400)
        else:
            self._timer.stop()
            self._loading_label.setText("")

    def _tick_loading(self) -> None:
        self._dot_count = (self._dot_count + 1) % 4
        self._loading_label.setText("Analyzing" + "." * self._dot_count)

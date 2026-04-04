"""
ui/styles/theme.py — Perplexity-style: near-black + baby blue, zero emoji.

Palette:
  #080808  deepest bg         #93C5FD  baby blue (accent)
  #0D0D0D  panel bg           #BFDBFE  baby blue light (hover)
  #141414  card surface       #1E3A5F  baby blue dim (badge bg)
  #1C1C1C  hover / border     #4ADE80  bullish green
  #F1F5F9  text primary       #F87171  bearish red
  #6B7280  text muted         #9CA3AF  text secondary
"""
import logging

logger = logging.getLogger(__name__)

_SANS = '"-apple-system", "Segoe UI", "Helvetica Neue", Arial, sans-serif'
_MONO = '"SF Mono", "Menlo", "Courier New", monospace'

_QSS = f"""
QMainWindow, QDialog {{
    background: #080808;
    font-family: {_SANS};
    font-size: 13px;
}}
QWidget {{
    background: transparent;
    color: #F1F5F9;
    font-family: {_SANS};
    font-size: 13px;
}}

/* Splitter */
QSplitter::handle {{
    background: #1C1C1C;
}}

/* Scrollbar */
QScrollBar:vertical {{
    background: transparent;
    width: 5px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #2A2A2A;
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: #374151;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

/* List widget */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    padding: 9px 16px;
    color: #6B7280;
    border-radius: 6px;
    margin: 1px 6px;
    font-size: 13px;
    font-weight: 400;
}}
QListWidget::item:hover {{
    background: #111111;
    color: #D1D5DB;
}}
QListWidget::item:selected {{
    background: #111111;
    color: #93C5FD;
    border-left: 2px solid #93C5FD;
    padding-left: 14px;
    font-weight: 500;
}}

/* Buttons */
QPushButton {{
    background: #111111;
    color: #6B7280;
    border: 1px solid #1C1C1C;
    border-radius: 6px;
    padding: 6px 16px;
    font-family: {_SANS};
    font-size: 12px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: #1C1C1C;
    color: #D1D5DB;
    border-color: #374151;
}}
QPushButton:pressed, QPushButton:checked {{
    background: #1E3A5F;
    border-color: #93C5FD;
    color: #93C5FD;
    font-weight: 600;
}}

/* TextEdit */
QTextEdit {{
    background: #0D0D0D;
    color: #F1F5F9;
    border: none;
    font-family: {_MONO};
    font-size: 13px;
    padding: 20px;
    selection-background-color: #1E3A5F;
}}

/* ComboBox */
QComboBox {{
    background: #111111;
    color: #6B7280;
    border: 1px solid #1C1C1C;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
}}
QComboBox:hover {{
    border-color: #374151;
    color: #D1D5DB;
}}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 4px solid #6B7280;
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: #111111;
    color: #D1D5DB;
    border: 1px solid #1C1C1C;
    selection-background-color: #1E3A5F;
    outline: none;
    padding: 4px;
}}

/* Status bar */
QStatusBar {{
    background: #080808;
    color: #374151;
    border-top: 1px solid #111111;
    font-family: {_MONO};
    font-size: 11px;
    padding: 0 12px;
}}

/* Label fallback */
QLabel {{
    background: transparent;
    color: #F1F5F9;
}}

/* Tooltip */
QToolTip {{
    background: #141414;
    color: #F1F5F9;
    border: 1px solid #1C1C1C;
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 12px;
}}
"""


def apply_theme(app) -> None:
    """Apply near-black + baby blue Perplexity theme."""
    try:
        import qdarktheme
        qdarktheme.setup_theme("dark", custom_colors={"primary": "#93C5FD"})
    except Exception as exc:
        logger.warning("qdarktheme skipped: %s", exc)
    app.setStyleSheet(_QSS)

"""
ui/styles/theme.py — Apply qdarktheme and custom Bloomberg-style QSS.
"""
import logging

logger = logging.getLogger(__name__)

_EXTRA_QSS = """
QMainWindow, QWidget {
    font-family: "Menlo", "SF Mono", "Courier New", monospace;
}
QListWidget {
    border: 1px solid #30363d;
    border-radius: 4px;
    background: #161b22;
}
QListWidget::item {
    padding: 8px 12px;
    color: #cdd9e5;
}
QListWidget::item:selected {
    background: #FFD700;
    color: #000000;
    font-weight: bold;
}
QListWidget::item:hover {
    background: #21262d;
}
QPushButton {
    background: #21262d;
    color: #cdd9e5;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 6px 14px;
}
QPushButton:hover {
    background: #30363d;
    border-color: #FFD700;
}
QPushButton:pressed {
    background: #FFD700;
    color: #000;
}
QTextEdit {
    background: #161b22;
    color: #cdd9e5;
    border: 1px solid #30363d;
    font-family: "Menlo", "SF Mono", "Courier New", monospace;
    font-size: 13px;
}
QStatusBar {
    background: #161b22;
    color: #cdd9e5;
    border-top: 1px solid #30363d;
    font-family: "Menlo", "SF Mono", "Courier New", monospace;
}
QScrollBar:vertical {
    background: #161b22;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 4px;
}
QSplitter::handle {
    background: #30363d;
}
QLabel {
    color: #cdd9e5;
}
"""


def apply_theme(app) -> None:
    """Apply qdarktheme + custom QSS to the QApplication instance."""
    try:
        import qdarktheme
        qdarktheme.setup_theme("dark")
        logger.info("qdarktheme applied")
    except ImportError:
        logger.warning("qdarktheme not installed — falling back to default Qt style")
    except Exception as exc:
        logger.warning("qdarktheme setup failed: %s", exc)

    app.setStyleSheet(app.styleSheet() + _EXTRA_QSS)

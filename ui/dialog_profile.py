"""
ui/dialog_profile.py — Robo-Advisor investor profile dialog.

Revolut/Fintech dark style. Opens on first launch (no user.json) or
when user clicks "My Investor Profile" in the header.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QWidget, QFrame,
)
from PyQt6.QtCore import Qt


_DARK = "#0D0D0D"
_SURFACE = "#111111"
_BORDER = "#1C1C1C"
_TEXT = "#F1F5F9"
_MUTED = "#6B7280"
_ACCENT = "#93C5FD"
_GREEN = "#4ADE80"


def _slider_style() -> str:
    return (
        "QSlider::groove:horizontal {"
        f"  height:4px; background:{_BORDER}; border-radius:2px;"
        "}"
        "QSlider::handle:horizontal {"
        f"  background:{_ACCENT}; border:none;"
        "  width:16px; height:16px; margin:-6px 0; border-radius:8px;"
        "}"
        "QSlider::sub-page:horizontal {"
        f"  background:{_ACCENT}; border-radius:2px;"
        "}"
    )


class _QuestionRow(QWidget):
    """One question with a slider and live value display."""

    def __init__(self, question: str, lo_label: str, hi_label: str, initial: int = 3):
        super().__init__()
        self.setStyleSheet(f"background:{_DARK};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        # Question text
        q_label = QLabel(question)
        q_label.setStyleSheet(
            f"color:{_TEXT}; font-size:13px; font-weight:500; background:{_DARK};"
        )
        outer.addWidget(q_label)

        # Slider + value pill
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        lo = QLabel(lo_label)
        lo.setStyleSheet(f"color:{_MUTED}; font-size:10px; background:{_DARK};")
        row.addWidget(lo)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(1, 5)
        self._slider.setValue(initial)
        self._slider.setStyleSheet(_slider_style())
        row.addWidget(self._slider, stretch=1)

        hi = QLabel(hi_label)
        hi.setStyleSheet(f"color:{_MUTED}; font-size:10px; background:{_DARK};")
        row.addWidget(hi)

        # Current value badge
        self._val_label = QLabel(str(initial))
        self._val_label.setFixedSize(28, 22)
        self._val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._val_label.setStyleSheet(
            f"color:{_ACCENT}; background:#1E3A5F; border-radius:4px;"
            "font-size:11px; font-weight:700;"
        )
        row.addWidget(self._val_label)

        outer.addLayout(row)

        self._slider.valueChanged.connect(lambda v: self._val_label.setText(str(v)))

    def value(self) -> int:
        return self._slider.value()

    def set_value(self, v: int) -> None:
        self._slider.setValue(v)


class ProfileDialog(QDialog):
    """
    Investor profile questionnaire — Revolut dark style.
    Call .exec() to show modally. If rejected/closed without saving,
    caller should keep existing profile values.
    """

    def __init__(self, profile: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("My Investor Profile")
        self.setFixedWidth(480)
        self.setModal(True)
        self.setStyleSheet(
            f"QDialog {{ background:{_DARK}; }}"
            f"QWidget {{ background:{_DARK}; }}"
        )

        self._saved = False
        self._build_ui(profile)

    def _build_ui(self, profile: dict) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Investor Profile")
        title.setStyleSheet(
            f"color:{_TEXT}; font-size:18px; font-weight:700; letter-spacing:0.2px;"
        )
        header_row.addWidget(title)
        header_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            f"QPushButton {{ background:{_SURFACE}; color:{_MUTED}; border:1px solid {_BORDER};"
            "  border-radius:14px; font-size:12px; font-weight:600; }}"
            f"QPushButton:hover {{ background:{_BORDER}; color:{_TEXT}; }}"
        )
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)
        root.addLayout(header_row)

        # Subtitle
        sub = QLabel("Your answers personalise the AI trading recommendations.")
        sub.setStyleSheet(f"color:{_MUTED}; font-size:11px; margin-top:4px;")
        root.addWidget(sub)

        root.addSpacing(24)

        # ── Divider ─────────────────────────────────────────────────────────────
        root.addWidget(self._divider())
        root.addSpacing(20)

        # ── Questions ───────────────────────────────────────────────────────────
        self._q_risk = _QuestionRow(
            "1.  What is your risk tolerance?",
            "Low — preserve capital",
            "High — maximize gains",
            initial=int(profile.get("risk_score", 3)),
        )
        root.addWidget(self._q_risk)
        root.addSpacing(20)

        self._q_horizon = _QuestionRow(
            "2.  What is your investment horizon?",
            "Days (scalping)",
            "Years (HODL)",
            initial=int(profile.get("investment_horizon", 3)),
        )
        root.addWidget(self._q_horizon)
        root.addSpacing(20)

        self._q_familiarity = _QuestionRow(
            "3.  Experience with commodity markets?",
            "Novice",
            "Pro",
            initial=int(profile.get("market_familiarity", 3)),
        )
        root.addWidget(self._q_familiarity)

        root.addSpacing(28)
        root.addWidget(self._divider())
        root.addSpacing(20)

        # ── Save button ─────────────────────────────────────────────────────────
        save_btn = QPushButton("Save Profile")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(
            f"QPushButton {{ background:{_ACCENT}; color:#0D0D0D; border:none;"
            "  border-radius:8px; font-size:13px; font-weight:700; letter-spacing:0.3px; }}"
            f"QPushButton:hover {{ background:#BAD7FF; }}"
            "QPushButton:pressed { background:#6BA5E7; }"
        )
        save_btn.clicked.connect(self._on_save)
        root.addWidget(save_btn)

        # Profile note
        note = QLabel("Changes take effect on the next analysis refresh.")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"color:{_MUTED}; font-size:10px; margin-top:8px;")
        root.addWidget(note)

    def _divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color:{_BORDER};")
        return line

    def _on_save(self) -> None:
        from data.user_manager import UserManager
        profile = {
            "risk_score": self._q_risk.value(),
            "investment_horizon": self._q_horizon.value(),
            "market_familiarity": self._q_familiarity.value(),
            "preferred_strategy": _score_to_strategy(self._q_risk.value()),
        }
        UserManager.save_profile(profile)
        self._saved = True
        self.accept()

    def was_saved(self) -> bool:
        return self._saved


def _score_to_strategy(risk_score: int) -> str:
    if risk_score <= 2:
        return "Conservative"
    elif risk_score == 3:
        return "Balanced"
    else:
        return "Aggressive"

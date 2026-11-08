"""
Office-Grade Executive UI Components for Bahata Kiln System.
Provides clean, accessible, emoji-free UI primitives matching professional desktop ERP standards.
"""
from typing import Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from app.ui.theme_manager import theme_mgr


class PageHeader(QFrame):
    """
    Standard corporate page header.
    Features:
    - High-contrast, semantic typography (primary heading + muted descriptor).
    - Optional status badge / live indicator.
    - Optional action button with callback.
    - Zero gradients, zero emojis, zero inline style overrides.
    """
    def __init__(
        self,
        title: str,
        subtitle: Optional[str] = None,
        badge_text: Optional[str] = None,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setObjectName("officePageHeader")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 12)
        layout.setSpacing(12)

        # Title & Subtitle block
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageHeaderTitle")
        self.title_label.setProperty("role", "heading-1")
        title_row.addWidget(self.title_label)

        if badge_text:
            self.badge_label = QLabel(badge_text)
            self.badge_label.setObjectName("pageHeaderBadge")
            self.badge_label.setProperty("role", "badge")
            title_row.addWidget(self.badge_label)

        title_row.addStretch()
        text_layout.addLayout(title_row)

        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setObjectName("pageHeaderSubtitle")
            self.subtitle_label.setProperty("role", "subtext")
            text_layout.addWidget(self.subtitle_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        if action_text and action_callback:
            self.action_btn = QPushButton(action_text)
            self.action_btn.setObjectName("pageHeaderActionBtn")
            self.action_btn.setProperty("variant", "secondary")
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.clicked.connect(action_callback)
            layout.addWidget(self.action_btn)


class MetricCard(QFrame):
    """
    Executive KPI summary card matching BAHTA ERP Stitch Design.
    Features:
    - Tabular monospace metric counter.
    - Icon badge + category header.
    - Status trend pill badge.
    - Semantic caption.
    - Bottom accent indicator bar.
    - Theme-reactive (supports light/dark automatically).
    """
    def __init__(
        self,
        title: str,
        initial_value: str = "0",
        caption: Optional[str] = None,
        accent_color: str = "#2563EB",
        badge_text: Optional[str] = None,
        badge_bg: str = "#DCFCE7",
        badge_fg: str = "#15803D",
        icon_symbol: str = "👥",
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.accent_color = accent_color
        self.setObjectName("officeMetricCard")
        self.setProperty("role", "metric-card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Top row: Title + Icon Badge
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setObjectName("metricTitle")
        self.title_lbl.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.6px;"
        )
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()

        self.icon_badge = QLabel(icon_symbol)
        self.icon_badge.setFixedSize(30, 30)
        self.icon_badge.setAlignment(Qt.AlignCenter)
        self.icon_badge.setStyleSheet(
            f"background-color: {accent_color}18; color: {accent_color}; "
            "border-radius: 6px; font-size: 13px; font-weight: bold;"
        )
        top_row.addWidget(self.icon_badge)
        layout.addLayout(top_row)

        # Middle row: Large Tabular Metric Value + Trend Badge
        val_row = QHBoxLayout()
        val_row.setContentsMargins(0, 2, 0, 0)
        val_row.setSpacing(10)

        self.val_lbl = QLabel(initial_value)
        self.val_lbl.setObjectName("metricValue")
        font = QFont("JetBrains Mono", 24, QFont.ExtraBold)
        font.setStyleHint(QFont.Monospace)
        self.val_lbl.setFont(font)
        self.val_lbl.setStyleSheet(f"color: {accent_color}; font-size: 26px; font-weight: 800;")
        val_row.addWidget(self.val_lbl)

        if badge_text:
            self.badge_lbl = QLabel(badge_text)
            self.badge_lbl.setStyleSheet(
                f"background-color: {badge_bg}; color: {badge_fg}; font-size: 10.5px; "
                "font-weight: 700; border-radius: 4px; padding: 2px 6px;"
            )
            val_row.addWidget(self.badge_lbl)
        else:
            self.badge_lbl = None

        val_row.addStretch()
        layout.addLayout(val_row)

        # Caption
        if caption:
            self.caption_lbl = QLabel(caption)
            self.caption_lbl.setObjectName("metricCaption")
            self.caption_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
            layout.addWidget(self.caption_lbl)

        # Bottom accent bar
        layout.addSpacing(4)
        self.bar = QFrame()
        self.bar.setFixedHeight(3)
        self.bar.setStyleSheet(f"background-color: {accent_color}; border-radius: 1.5px;")
        layout.addWidget(self.bar)

        self._apply_theme()
        theme_mgr.theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        is_dark = theme_mgr.is_dark_mode()
        title_col = "#E2E8F0" if is_dark else "#64748B"
        caption_col = "#E2E8F0" if is_dark else "#64748B"
        card_bg = "#1E293B" if is_dark else "#FFFFFF"
        card_border = "#334155" if is_dark else "#E2E8F0"

        self.setStyleSheet(
            f"QFrame#officeMetricCard {{ background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 8px; }}"
        )
        self.title_lbl.setStyleSheet(
            f"font-size: 11px; font-weight: 700; color: {title_col}; letter-spacing: 0.6px; border: none; background: transparent;"
        )
        if hasattr(self, "caption_lbl") and self.caption_lbl:
            self.caption_lbl.setStyleSheet(
                f"font-size: 11px; color: {caption_col}; font-weight: 500; border: none; background: transparent;"
            )

    def set_value(self, new_val: str, badge_text: Optional[str] = None):
        self.val_lbl.setText(str(new_val))
        if badge_text and hasattr(self, "badge_lbl") and self.badge_lbl:
            self.badge_lbl.setText(badge_text)


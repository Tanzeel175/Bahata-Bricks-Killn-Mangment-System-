"""
Theme Manager for Bahata Bricks Kiln Management System.
Provides dynamic Light and Dark mode theming, OS dark-mode detection,
and persistent theme preferences.
"""
import os
import json
import logging
import tempfile
from typing import Optional
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QPalette, QColor, QTextCharFormat, QFont, QGuiApplication
from PySide6.QtWidgets import QApplication, QCalendarWidget, QDateEdit
from app.config import USER_PREFS_FILE

logger = logging.getLogger(__name__)

# Modern SVG Assets for UI Controls
_RESOURCES_DIR = Path(__file__).parent / "resources"
_RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

_CHECK_SVG = _RESOURCES_DIR / "check.svg"
if not _CHECK_SVG.exists():
    _CHECK_SVG.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="20 6 9 17 4 12"></polyline>'
        '</svg>',
        encoding="utf-8"
    )

_CHEVRON_DARK_SVG = _RESOURCES_DIR / "chevron_down_dark.svg"
if not _CHEVRON_DARK_SVG.exists():
    _CHEVRON_DARK_SVG.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#475569" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="6 9 12 15 18 9"></polyline>'
        '</svg>',
        encoding="utf-8"
    )

_CHEVRON_LIGHT_SVG = _RESOURCES_DIR / "chevron_down_light.svg"
if not _CHEVRON_LIGHT_SVG.exists():
    _CHEVRON_LIGHT_SVG.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="6 9 12 15 18 9"></polyline>'
        '</svg>',
        encoding="utf-8"
    )

_CHECK_SVG_PATH = _CHECK_SVG.as_posix()
_CHEVRON_DARK_PATH = _CHEVRON_DARK_SVG.as_posix()
_CHEVRON_LIGHT_PATH = _CHEVRON_LIGHT_SVG.as_posix()

# ==============================================================================
# LIGHT THEME STYLESHEET
# ==============================================================================
LIGHT_THEME_QSS = """
/* Global Window & Base */
QWidget {
    font-family: "Segoe UI", "Inter", "Ubuntu", -apple-system, sans-serif;
    font-size: 13px;
    color: #0F172A;
}

QMainWindow, QDialog {
    background-color: #F8FAFC;
    color: #0F172A;
}

QWidget#MainContainer, QFrame#MainContainer {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    color: #0F172A;
}

/* Card / Section Panels */
QFrame.card-panel, QWidget.card-panel, QFrame[class="card-panel"], QWidget[class="card-panel"],
QFrame#cardPanel, QFrame#form_card, QFrame#meta_card, QFrame#items_card, QFrame#hist_card,
QFrame#filterCard, QFrame#tableCard, QFrame#grid_card, QFrame#recent_panel, QFrame#kpi_frame,
QFrame#criteriaCard, QFrame#tabsFrame, QFrame#shortcutsCard, QFrame#distributionCard, QFrame#auditCard {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    color: #0F172A;
}

QFrame#formCardHeader {
    background-color: #F8FAFC;
    border-bottom: 1px solid #E2E8F0;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

QFrame#omitCard {
    background-color: #FEF9C3;
    border: 1.5px solid #FDE047;
    border-radius: 8px;
}

QLineEdit#totalStockValue {
    background-color: #EFF6FF;
    color: #1E40AF;
}

/* Labels */
QLabel {
    background-color: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
    color: #0F172A;
}

QLabel.heading-primary, QLabel[class="heading-primary"], QLabel#headingPrimary, QLabel#viewTitle {
    font-size: 20px;
    font-weight: 800;
    color: #0F172A;
}

QLabel.heading-secondary, QLabel[class="heading-secondary"], QLabel#headingSecondary {
    font-size: 15px;
    font-weight: 700;
    color: #334155;
}

QLabel.subtext, QLabel[class="subtext"], QLabel#subtext, QLabel#viewSubtitle {
    font-size: 12px;
    color: #64748B;
}

QLabel.form-field-label, QLabel[class="form-field-label"] {
    font-size: 11.5px;
    font-weight: 700;
    color: #334155;
}

/* Office UI Primitives - Light Theme */
QFrame#officeMetricCard, QFrame[role="metric-card"] {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
}
QFrame#officeMetricCard:hover, QFrame[role="metric-card"]:hover {
    border-color: #CBD5E1;
}
QLabel[role="heading-1"], QLabel#pageHeaderTitle {
    font-size: 20px;
    font-weight: 700;
    color: #0F172A;
    letter-spacing: -0.02em;
}
QLabel[role="heading-2"] {
    font-size: 15px;
    font-weight: 600;
    color: #1E293B;
}
QLabel[role="subtext"], QLabel#pageHeaderSubtitle {
    font-size: 12px;
    color: #64748B;
}
QLabel[role="caption"], QLabel#metricTitle {
    font-size: 11px;
    font-weight: 600;
    color: #64748B;
    letter-spacing: 0.05em;
}
QLabel[role="metric-val"], QLabel#metricValue {
    font-size: 24px;
    font-weight: 700;
    color: #0F172A;
}
QLabel[role="badge"], QLabel#pageHeaderBadge {
    background-color: #F1F5F9;
    color: #334155;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid #E2E8F0;
    border-radius: 4px;
    padding: 2px 8px;
}

/* Group Boxes */
QGroupBox {
    font-weight: 700;
    font-size: 13px;
    color: #1D4ED8;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 20px;
    padding-bottom: 12px;
    padding-left: 10px;
    padding-right: 10px;
    background-color: #FFFFFF;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 2px 8px;
    background-color: #FFFFFF;
    color: #1D4ED8;
    border-radius: 4px;
}

/* Scroll Area */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: #F1F5F9;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar:horizontal {
    border: none;
    background: #F1F5F9;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 4px;
    min-width: 20px;
}

QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

/* Inputs & Combo Boxes */
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QDateEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
    color: #0F172A;
    min-height: 26px;
    selection-background-color: #3B82F6;
    selection-color: #FFFFFF;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 28px 5px 10px;
    font-size: 13px;
    color: #0F172A;
    min-height: 26px;
    selection-background-color: #3B82F6;
    selection-color: #FFFFFF;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #2563EB;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QDateEdit:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border: 1px solid #E2E8F0;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 0px;
}

QComboBox::down-arrow {
    image: url("__CHEVRON_DARK_PATH__");
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    selection-background-color: #EFF6FF;
    selection-color: #1D4ED8;
    outline: 0px;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 5px 10px;
    background-color: #FFFFFF;
    color: #0F172A;
    border: none;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
    font-weight: 600;
}

/* Push Buttons */
QPushButton {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 600;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
    color: #0F172A;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

QPushButton:disabled {
    background-color: #F8FAFC;
    color: #CBD5E1;
    border-color: #E2E8F0;
}

/* Primary Action Buttons */
QPushButton.btn-primary, QPushButton[class="btn-primary"] {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #1D4ED8;
    font-weight: 700;
}

QPushButton.btn-primary:hover, QPushButton[class="btn-primary"]:hover {
    background-color: #1D4ED8;
    border-color: #1E40AF;
}

QPushButton.btn-primary:pressed, QPushButton[class="btn-primary"]:pressed {
    background-color: #1E40AF;
}

/* Danger Buttons */
QPushButton.btn-danger, QPushButton[class="btn-danger"] {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
    font-weight: 700;
}

QPushButton.btn-danger:hover, QPushButton[class="btn-danger"]:hover {
    background-color: #B91C1C;
}

/* Success Buttons */
QPushButton.btn-success, QPushButton[class="btn-success"] {
    background-color: #16A34A;
    color: #FFFFFF;
    border: 1px solid #15803D;
    font-weight: 700;
}

QPushButton.btn-success:hover, QPushButton[class="btn-success"]:hover {
    background-color: #15803D;
}

/* Secondary Buttons */
QPushButton.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #F1F5F9;
    color: #334155;
    border: 1px solid #CBD5E1;
    font-weight: 600;
}

QPushButton.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #E2E8F0;
    border-color: #94A3B8;
    color: #0F172A;
}

/* Table Widget */
QTableWidget, QTableView {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    font-size: 13px;
    color: #0F172A;
    selection-background-color: #E2E8F0;
    selection-color: #0F172A;
    outline: none;
}

QTableWidget::item, QTableView::item {
    padding: 6px 10px;
    border-bottom: 1px solid #F1F5F9;
    color: #0F172A;
}

QTableWidget::item:alternate, QTableView::item:alternate {
    background-color: #F8FAFC;
}

QTableWidget::item:hover, QTableView::item:hover {
    background-color: #F1F5F9;
    color: #0F172A;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #E2E8F0;
    color: #0F172A;
    font-weight: 600;
}

QTableWidget::item:selected:hover, QTableView::item:selected:hover {
    background-color: #CBD5E1;
    color: #0F172A;
}

QHeaderView::section {
    background-color: #F1F5F9;
    color: #1E293B;
    padding: 6px 10px;
    font-weight: 700;
    font-size: 12px;
    min-height: 38px;
    height: 38px;
    border: none;
    border-bottom: 2px solid #CBD5E1;
    border-right: 1px solid #E2E8F0;
}

/* Checkboxes */
QCheckBox {
    font-size: 13px;
    color: #0F172A;
    spacing: 8px;
    background-color: transparent;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid #94A3B8;
    background-color: #FFFFFF;
}

QCheckBox::indicator:hover {
    border-color: #2563EB;
    background-color: #F8FAFC;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #1D4ED8;
    image: url("__CHECK_SVG_PATH__");
}

QCheckBox::indicator:disabled {
    border-color: #CBD5E1;
    background-color: #E2E8F0;
}

QCheckBox:disabled {
    color: #94A3B8;
}

/* Status Bar */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    color: #334155;
    font-size: 12px;
}

/* Tab Widget */
QTabWidget::pane {
    border: none;
    background-color: #F5F7FB;
    top: 0px;
}

QTabBar::tab {
    background-color: transparent;
    color: #64748B;
    border: none;
    padding: 10px 16px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #2563EB;
    border-bottom: 2px solid #2563EB;
}

QTabBar::tab:hover:!selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
}

/* Menu Bar & Menus */
QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E1E8F0;
    padding: 3px 8px;
    color: #0F172A;
}

QMenuBar::item {
    color: #0F172A;
    background-color: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #DCE5EF;
    padding: 5px;
    color: #0F172A;
}

QMenu::item {
    color: #0F172A;
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
}

/* Sidebar navigation */
QFrame#premiumSidebar {
    background-color: #0A1128;
    border-right: 1px solid #1E293B;
}

QFrame#premiumSidebar QLabel#sidebarBrand {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QFrame#premiumSidebar QLabel#sidebarCompany {
    color: #94A3B8;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.8px;
}

QFrame#premiumSidebar QLabel#sidebarSection {
    color: #64748B;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    margin: 12px 6px 4px;
}

QFrame#premiumSidebar QPushButton#sidebarItem,
QFrame#premiumSidebar QPushButton#sidebarActive,
QFrame#premiumSidebar QPushButton#sidebarLogout {
    background: transparent;
    color: #CBD5E1;
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 8px 12px;
    font-size: 12.5px;
    font-weight: 600;
}

QFrame#premiumSidebar QPushButton#sidebarItem:hover {
    background: #1B2F4F;
    color: #FFFFFF;
}

QFrame#premiumSidebar QPushButton#sidebarActive {
    background: #2563EB;
    color: #FFFFFF;
    font-weight: 700;
}

QFrame#premiumSidebar QPushButton#sidebarLogout {
    background: transparent;
    color: #FCA5A5;
    margin-top: 6px;
}

QFrame#premiumSidebar QPushButton#sidebarLogout:hover {
    background: rgba(225, 29, 72, 0.2);
    color: #FFFFFF;
}
"""

# ==============================================================================
# DARK THEME STYLESHEET
# ==============================================================================
DARK_THEME_QSS = """
/* Global Window & Base */
QWidget {
    font-family: "Segoe UI", "Inter", "Ubuntu", -apple-system, sans-serif;
    font-size: 13px;
    color: #F8FAFC;
}

QMainWindow, QDialog {
    background-color: #0F172A;
    color: #F8FAFC;
}

QWidget#MainContainer, QFrame#MainContainer {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 12px;
    color: #F8FAFC;
}

/* Card / Section Panels */
QFrame.card-panel, QWidget.card-panel, QFrame[class="card-panel"], QWidget[class="card-panel"],
QFrame#cardPanel, QFrame#form_card, QFrame#meta_card, QFrame#items_card, QFrame#hist_card,
QFrame#filterCard, QFrame#tableCard, QFrame#grid_card, QFrame#recent_panel, QFrame#kpi_frame,
QFrame#criteriaCard, QFrame#tabsFrame, QFrame#shortcutsCard, QFrame#distributionCard, QFrame#auditCard {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 10px;
    color: #F8FAFC;
}

QFrame#formCardHeader {
    background-color: #0F172A;
    border-bottom: 1px solid #334155;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}

QFrame#omitCard {
    background-color: rgba(161, 98, 7, 0.18);
    border: 1.5px solid #CA8A04;
    border-radius: 8px;
}

QLineEdit#totalStockValue {
    background-color: rgba(37, 99, 235, 0.2);
    color: #93C5FD;
}

/* Labels */
QLabel {
    background-color: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
    color: #FFFFFF;
}

QLabel.heading-primary, QLabel[class="heading-primary"], QLabel#headingPrimary, QLabel#viewTitle {
    font-size: 20px;
    font-weight: 800;
    color: #FFFFFF;
}

QLabel.heading-secondary, QLabel[class="heading-secondary"], QLabel#headingSecondary {
    font-size: 15px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel.subtext, QLabel[class="subtext"], QLabel#subtext, QLabel#viewSubtitle {
    font-size: 12px;
    color: #E2E8F0;
}

QLabel.form-field-label, QLabel[class="form-field-label"] {
    font-size: 11.5px;
    font-weight: 700;
    color: #FFFFFF;
}

/* Office UI Primitives - Dark Theme */
QFrame#officeMetricCard, QFrame[role="metric-card"] {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
}
QFrame#officeMetricCard:hover, QFrame[role="metric-card"]:hover {
    border-color: #475569;
}
QLabel[role="heading-1"], QLabel#pageHeaderTitle {
    font-size: 20px;
    font-weight: 700;
    color: #FFFFFF;
    letter-spacing: -0.02em;
}
QLabel[role="heading-2"] {
    font-size: 15px;
    font-weight: 600;
    color: #FFFFFF;
}
QLabel[role="subtext"], QLabel#pageHeaderSubtitle {
    font-size: 12px;
    color: #E2E8F0;
}
QLabel[role="caption"], QLabel#metricTitle {
    font-size: 11px;
    font-weight: 600;
    color: #E2E8F0;
    letter-spacing: 0.05em;
}
QLabel[role="metric-val"], QLabel#metricValue {
    font-size: 24px;
    font-weight: 700;
    color: #FFFFFF;
}
QLabel[role="badge"], QLabel#pageHeaderBadge {
    background-color: #1E293B;
    color: #E2E8F0;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid #334155;
    border-radius: 4px;
    padding: 2px 8px;
}

/* Group Boxes */
QGroupBox {
    font-weight: 700;
    font-size: 13px;
    color: #38BDF8;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 20px;
    padding-bottom: 12px;
    padding-left: 10px;
    padding-right: 10px;
    background-color: #1E293B;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 2px 8px;
    background-color: #1E293B;
    color: #38BDF8;
    border-radius: 4px;
}

/* Scroll Area */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    border: none;
    background: #0F172A;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar:horizontal {
    border: none;
    background: #0F172A;
    height: 8px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 4px;
    min-width: 20px;
}

QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
    width: 0px;
}

/* Inputs & Combo Boxes */
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit, QDateEdit {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 13px;
    color: #F8FAFC;
    min-height: 26px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QComboBox {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 5px 28px 5px 10px;
    font-size: 13px;
    color: #F8FAFC;
    min-height: 26px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}

QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus, QDateEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #38BDF8;
    background-color: #0F172A;
}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled, QDateEdit:disabled {
    background-color: #162032;
    color: #64748B;
    border: 1px solid #1E293B;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 0px;
}

QComboBox::down-arrow {
    image: url("__CHEVRON_LIGHT_PATH__");
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    border: 1px solid #334155;
    border-radius: 6px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
    outline: 0px;
    padding: 4px;
}

QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 5px 10px;
    background-color: #1E293B;
    color: #F8FAFC;
    border: none;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #334155;
    color: #F8FAFC;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: 600;
}

/* Push Buttons */
QPushButton {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 600;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #243248;
}

QPushButton:disabled {
    background-color: #162032;
    color: #475569;
    border-color: #1E293B;
}

/* Primary Action Buttons */
QPushButton.btn-primary, QPushButton[class="btn-primary"] {
    background-color: #2563EB;
    color: #FFFFFF;
    border: 1px solid #38BDF8;
    font-weight: 700;
}

QPushButton.btn-primary:hover, QPushButton[class="btn-primary"]:hover {
    background-color: #1D4ED8;
    border-color: #60A5FA;
}

QPushButton.btn-primary:pressed, QPushButton[class="btn-primary"]:pressed {
    background-color: #1E40AF;
}

/* Danger Buttons */
QPushButton.btn-danger, QPushButton[class="btn-danger"] {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #EF4444;
    font-weight: 700;
}

QPushButton.btn-danger:hover, QPushButton[class="btn-danger"]:hover {
    background-color: #B91C1C;
}

/* Success Buttons */
QPushButton.btn-success, QPushButton[class="btn-success"] {
    background-color: #16A34A;
    color: #FFFFFF;
    border: 1px solid #22C55E;
    font-weight: 700;
}

QPushButton.btn-success:hover, QPushButton[class="btn-success"]:hover {
    background-color: #15803D;
}

/* Dark Theme Secondary Buttons */
QPushButton.btn-secondary, QPushButton[class="btn-secondary"] {
    background-color: #1E293B;
    color: #E2E8F0;
    border: 1px solid #334155;
    font-weight: 600;
}

QPushButton.btn-secondary:hover, QPushButton[class="btn-secondary"]:hover {
    background-color: #334155;
    border-color: #64748B;
    color: #FFFFFF;
}

/* Table Widget */
QTableWidget, QTableView {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #243248;
    font-size: 13px;
    color: #F8FAFC;
    selection-background-color: #1D4ED8;
    selection-color: #FFFFFF;
    outline: none;
}

QTableWidget::item, QTableView::item {
    padding: 6px 10px;
    border-bottom: 1px solid #243248;
    color: #F8FAFC;
}

QTableWidget::item:alternate, QTableView::item:alternate {
    background-color: #172337;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #1D4ED8;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #0F172A;
    color: #FFFFFF;
    padding: 6px 10px;
    font-weight: 700;
    font-size: 12px;
    min-height: 38px;
    height: 38px;
    border: none;
    border-bottom: 2px solid #334155;
    border-right: 1px solid #243248;
}

/* Checkboxes */
QCheckBox {
    font-size: 13px;
    color: #F8FAFC;
    spacing: 8px;
    background-color: transparent;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1.5px solid #64748B;
    background-color: #1E293B;
}

QCheckBox::indicator:hover {
    border-color: #38BDF8;
    background-color: #334155;
}

QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #38BDF8;
    image: url("__CHECK_SVG_PATH__");
}

QCheckBox::indicator:disabled {
    border-color: #334155;
    background-color: #0F172A;
}

QCheckBox:disabled {
    color: #64748B;
}

/* Status Bar */
QStatusBar {
    background-color: #0F172A;
    border-top: 1px solid #1E293B;
    color: #94A3B8;
    font-size: 12px;
}

/* Tab Widget */
QTabWidget::pane {
    border: none;
    background-color: #0F172A;
    top: 0px;
}

QTabBar::tab {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    padding: 10px 16px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #1E293B;
    color: #38BDF8;
    border-bottom: 2px solid #38BDF8;
}

QTabBar::tab:hover:!selected {
    background-color: #162032;
    color: #F8FAFC;
}

/* Menu Bar & Menus */
QMenuBar {
    background-color: #0F172A;
    border-bottom: 1px solid #1E293B;
    padding: 3px 8px;
    color: #F8FAFC;
}

QMenuBar::item {
    color: #F8FAFC;
    background-color: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #1E293B;
    color: #38BDF8;
}

QMenu {
    background-color: #1E293B;
    border: 1px solid #334155;
    padding: 5px;
    color: #F8FAFC;
}

QMenu::item {
    color: #F8FAFC;
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #2563EB;
    color: #FFFFFF;
}

/* Sidebar navigation */
QFrame#premiumSidebar {
    background-color: #070D1F;
    border-right: 1px solid #1E293B;
}

QFrame#premiumSidebar QLabel#sidebarBrand {
    color: #FFFFFF;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QFrame#premiumSidebar QLabel#sidebarCompany {
    color: #94A3B8;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.8px;
}

QFrame#premiumSidebar QLabel#sidebarSection {
    color: #64748B;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
    margin: 12px 6px 4px;
}

QFrame#premiumSidebar QPushButton#sidebarItem,
QFrame#premiumSidebar QPushButton#sidebarActive,
QFrame#premiumSidebar QPushButton#sidebarLogout {
    background: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 8px 12px;
    font-size: 12.5px;
    font-weight: 600;
}

QFrame#premiumSidebar QPushButton#sidebarItem:hover {
    background: #111E38;
    color: #F8FAFC;
}

QFrame#premiumSidebar QPushButton#sidebarActive {
    background: #2563EB;
    color: #FFFFFF;
    font-weight: 700;
}

QFrame#premiumSidebar QPushButton#sidebarLogout {
    background: transparent;
    color: #FCA5A5;
    margin-top: 6px;
}

QFrame#premiumSidebar QPushButton#sidebarLogout:hover {
    background: rgba(225, 29, 72, 0.25);
    color: #FFFFFF;
}
"""


# ==============================================================================
# CALENDAR STYLESHEETS
# ==============================================================================
def get_calendar_qss(is_dark: bool = False) -> str:
    if is_dark:
        return """
        QCalendarWidget {
            background-color: #1E293B;
            border: 1.5px solid #334155;
            border-radius: 8px;
        }
        QCalendarWidget QWidget {
            background-color: #1E293B;
            color: #F8FAFC;
        }
        QCalendarWidget QWidget#qt_calendar_navigationbar {
            background: #0F172A;
            border-bottom: 1px solid #334155;
            min-height: 42px;
            border-top-left-radius: 7px;
            border-top-right-radius: 7px;
        }
        QCalendarWidget QToolButton {
            color: #FFFFFF;
            background-color: transparent;
            font-size: 13px;
            font-weight: 700;
            border-radius: 4px;
            padding: 4px 8px;
            margin: 2px 3px;
            border: none;
        }
        QCalendarWidget QToolButton:hover {
            background-color: rgba(255, 255, 255, 0.15);
        }
        QCalendarWidget QSpinBox {
            color: #FFFFFF;
            background-color: rgba(255, 255, 255, 0.15);
            selection-background-color: #2563EB;
            selection-color: #FFFFFF;
            font-size: 13px;
            font-weight: 700;
            border-radius: 4px;
            padding: 2px 4px;
            border: none;
            min-width: 60px;
        }
        QCalendarWidget QMenu {
            background-color: #1E293B;
            color: #F8FAFC;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px;
            font-size: 12px;
        }
        QCalendarWidget QMenu::item:selected {
            background-color: #2563EB;
            color: #FFFFFF;
        }
        QCalendarWidget QTableView {
            background-color: #1E293B;
            alternate-background-color: #172337;
            selection-background-color: #2563EB;
            selection-color: #FFFFFF;
            color: #F8FAFC;
            font-size: 12px;
            font-weight: 600;
            border: none;
            gridline-color: transparent;
            outline: none;
        }
        QCalendarWidget QTableView::item:hover {
            background-color: #334155;
            color: #38BDF8;
            border-radius: 4px;
        }
        QCalendarWidget QTableView::item:selected {
            background-color: #2563EB;
            color: #FFFFFF;
            border-radius: 4px;
            font-weight: bold;
        }
        QCalendarWidget QHeaderView {
            background-color: #0F172A;
            border: none;
        }
        QCalendarWidget QHeaderView::section {
            background-color: #0F172A;
            color: #94A3B8;
            font-weight: 700;
            font-size: 11px;
            padding: 6px 0px;
            border: none;
            border-bottom: 1px solid #334155;
        }
        """
    return """
    QCalendarWidget {
        background-color: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 8px;
    }
    QCalendarWidget QWidget {
        background-color: #FFFFFF;
        color: #0F172A;
    }
    QCalendarWidget QWidget#qt_calendar_navigationbar {
        background: #1E3A8A;
        border-bottom: 1px solid #1D4ED8;
        min-height: 42px;
        border-top-left-radius: 7px;
        border-top-right-radius: 7px;
    }
    QCalendarWidget QToolButton {
        color: #FFFFFF;
        background-color: transparent;
        font-size: 13px;
        font-weight: 700;
        border-radius: 4px;
        padding: 4px 8px;
        margin: 2px 3px;
        border: none;
    }
    QCalendarWidget QToolButton:hover {
        background-color: rgba(255, 255, 255, 0.22);
    }
    QCalendarWidget QSpinBox {
        color: #FFFFFF;
        background-color: rgba(255, 255, 255, 0.2);
        selection-background-color: #2563EB;
        selection-color: #FFFFFF;
        font-size: 13px;
        font-weight: 700;
        border-radius: 4px;
        padding: 2px 4px;
        border: none;
        min-width: 60px;
    }
    QCalendarWidget QMenu {
        background-color: #FFFFFF;
        color: #0F172A;
        border: 1px solid #CBD5E1;
        border-radius: 6px;
        padding: 4px;
        font-size: 12px;
    }
    QCalendarWidget QMenu::item:selected {
        background-color: #EFF6FF;
        color: #1D4ED8;
    }
    QCalendarWidget QTableView {
        background-color: #FFFFFF;
        alternate-background-color: #F8FAFC;
        selection-background-color: #2563EB;
        selection-color: #FFFFFF;
        color: #0F172A;
        font-size: 12px;
        font-weight: 600;
        border: none;
        gridline-color: transparent;
        outline: none;
    }
    QCalendarWidget QTableView::item:hover {
        background-color: #DBEAFE;
        color: #1E3A8A;
        border-radius: 4px;
    }
    QCalendarWidget QTableView::item:selected {
        background-color: #2563EB;
        color: #FFFFFF;
        border-radius: 4px;
        font-weight: bold;
    }
    QCalendarWidget QHeaderView {
        background-color: #F1F5F9;
        border: none;
    }
    QCalendarWidget QHeaderView::section {
        background-color: #F1F5F9;
        color: #475569;
        font-weight: 700;
        font-size: 11px;
        padding: 6px 0px;
        border: none;
        border-bottom: 1px solid #E2E8F0;
    }
    """

# Resolve dynamic SVG asset paths in stylesheets
LIGHT_THEME_QSS = (
    LIGHT_THEME_QSS
    .replace("__CHECK_SVG_PATH__", _CHECK_SVG_PATH)
    .replace("__CHEVRON_DARK_PATH__", _CHEVRON_DARK_PATH)
)
DARK_THEME_QSS = (
    DARK_THEME_QSS
    .replace("__CHECK_SVG_PATH__", _CHECK_SVG_PATH)
    .replace("__CHEVRON_LIGHT_PATH__", _CHEVRON_LIGHT_PATH)
)


# ==============================================================================
# THEME MANAGER CORE CLASS
# ==============================================================================
class ThemeManager(QObject):
    """
    Central manager for theme selection (light, dark, system).
    Emits theme_changed(str) when theme transitions.
    """
    theme_changed = Signal(str)  # "dark" or "light"

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, parent=None):
        if hasattr(self, "_initialized") and self._initialized:
            return
        super().__init__(parent)
        self._initialized = True
        self._cached_pref: Optional[str] = None
        self._current_active = "light"

    @classmethod
    def instance(cls) -> "ThemeManager":
        if not cls._instance:
            cls._instance = ThemeManager()
        return cls._instance

    @staticmethod
    def is_system_dark() -> bool:
        """Detect whether the host OS is configured in Dark Mode."""
        # 1. Native Qt 6.5+ style hints detection (fastest, 0 overhead, no subprocess)
        try:
            hints = QGuiApplication.styleHints()
            if hasattr(hints, "colorScheme"):
                return hints.colorScheme() == Qt.ColorScheme.Dark
        except Exception:
            pass

        # 2. Linux GNOME / Freedesktop detection fallback
        if os.name != "nt":
            try:
                import subprocess
                res = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True, text=True, timeout=0.5
                )
                if "prefer-dark" in res.stdout.lower() or "dark" in res.stdout.lower():
                    return True
            except Exception:
                pass
        else:
            # 3. Windows registry check
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return val == 0
            except Exception:
                pass

        # 4. Fallback: Check active Qt palette brightness
        app = QApplication.instance()
        if app:
            return app.palette().color(QPalette.Window).lightness() < 128
        return False

    def get_theme_preference(self) -> str:
        """Returns saved preference: 'dark', 'light', or 'system'."""
        if self._cached_pref is not None:
            return self._cached_pref
        try:
            if USER_PREFS_FILE.exists():
                with open(USER_PREFS_FILE, "r", encoding="utf-8") as f:
                    prefs = json.load(f)
                    self._cached_pref = prefs.get("theme", "system")
                    return self._cached_pref
        except Exception:
            pass
        self._cached_pref = "system"
        return self._cached_pref

    def set_theme_preference(self, theme: str) -> None:
        """Saves preference ('dark', 'light', 'system') and applies it immediately."""
        if theme not in ("dark", "light", "system"):
            theme = "system"

        if self._cached_pref == theme and self._current_active:
            # Already active and loaded, avoid redundant work
            return

        self._cached_pref = theme
        # Apply theme first for instantaneous visual feedback
        self.apply_theme()

        # Persist preference to disk asynchronously without blocking the UI
        try:
            prefs = {}
            if USER_PREFS_FILE.exists():
                try:
                    with open(USER_PREFS_FILE, "r", encoding="utf-8") as f:
                        prefs = json.load(f)
                except Exception:
                    prefs = {}
            prefs["theme"] = theme
            USER_PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(USER_PREFS_FILE, "w", encoding="utf-8") as f:
                json.dump(prefs, f)
        except Exception as e:
            logger.warning(f"Could not persist theme preference: {e}")

    def get_active_theme(self) -> str:
        """Returns effective active theme: 'dark' or 'light'."""
        pref = self.get_theme_preference()
        if pref == "system":
            return "dark" if self.is_system_dark() else "light"
        return pref

    def is_dark_mode(self) -> bool:
        """Returns True if dark mode is currently active."""
        return self.get_active_theme() == "dark"

    def toggle_theme(self) -> str:
        """Toggles between light and dark modes."""
        new_theme = "light" if self.is_dark_mode() else "dark"
        self.set_theme_preference(new_theme)
        return new_theme

    def apply_theme(self) -> None:
        """Applies stylesheet and palette to QApplication instance smoothly."""
        app = QApplication.instance()
        if not app:
            return

        active_theme = self.get_active_theme()
        self._current_active = active_theme

        # Freeze updates on top-level windows AND inactive tabs to prevent layout thrashing
        top_levels = app.topLevelWidgets()
        for w in top_levels:
            w.setUpdatesEnabled(False)
            try:
                for tw in w.findChildren(QTabWidget):
                    curr = tw.currentWidget()
                    for i in range(tw.count()):
                        page = tw.widget(i)
                        if page != curr:
                            page.setUpdatesEnabled(False)
            except Exception:
                pass

        try:
            # 1. Apply QPalette to prevent OS palette mismatch
            palette = QPalette()
            if active_theme == "dark":
                palette.setColor(QPalette.Window, QColor("#0F172A"))
                palette.setColor(QPalette.WindowText, QColor("#F8FAFC"))
                palette.setColor(QPalette.Base, QColor("#1E293B"))
                palette.setColor(QPalette.AlternateBase, QColor("#162032"))
                palette.setColor(QPalette.ToolTipBase, QColor("#1E293B"))
                palette.setColor(QPalette.ToolTipText, QColor("#F8FAFC"))
                palette.setColor(QPalette.Text, QColor("#F8FAFC"))
                palette.setColor(QPalette.Button, QColor("#1E293B"))
                palette.setColor(QPalette.ButtonText, QColor("#F8FAFC"))
                palette.setColor(QPalette.BrightText, QColor("#EF4444"))
                palette.setColor(QPalette.Highlight, QColor("#2563EB"))
                palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
                palette.setColor(QPalette.PlaceholderText, QColor("#94A3B8"))
            else:
                palette.setColor(QPalette.Window, QColor("#F5F7FB"))
                palette.setColor(QPalette.WindowText, QColor("#0F172A"))
                palette.setColor(QPalette.Base, QColor("#FFFFFF"))
                palette.setColor(QPalette.AlternateBase, QColor("#F8FAFC"))
                palette.setColor(QPalette.ToolTipBase, QColor("#0F172A"))
                palette.setColor(QPalette.ToolTipText, QColor("#FFFFFF"))
                palette.setColor(QPalette.Text, QColor("#0F172A"))
                palette.setColor(QPalette.Button, QColor("#FFFFFF"))
                palette.setColor(QPalette.ButtonText, QColor("#0F172A"))
                palette.setColor(QPalette.BrightText, QColor("#DC2626"))
                palette.setColor(QPalette.Highlight, QColor("#2563EB"))
                palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
                palette.setColor(QPalette.PlaceholderText, QColor("#64748B"))

            app.setPalette(palette)

            # 2. Apply Stylesheet to QApplication instance and top-level windows
            qss = DARK_THEME_QSS if active_theme == "dark" else LIGHT_THEME_QSS
            app.setStyleSheet(qss)
            for w in top_levels:
                w.setStyleSheet(qss)

            # 3. Emit theme changed notification
            self.theme_changed.emit(active_theme)
        finally:
            for w in top_levels:
                try:
                    for tw in w.findChildren(QTabWidget):
                        for i in range(tw.count()):
                            tw.widget(i).setUpdatesEnabled(True)
                except Exception:
                    pass
                w.setUpdatesEnabled(True)
                w.update()

        logger.info(f"Theme switched to: {active_theme} (pref: {self.get_theme_preference()})")


# Singleton helper instance
theme_mgr = ThemeManager.instance()


def configure_date_edit(date_edit: QDateEdit, min_width: int = 125, min_height: int = 28) -> None:
    """Configures a QDateEdit with theme-aware calendar styling."""
    date_edit.setCalendarPopup(True)
    date_edit.setDisplayFormat("yyyy-MM-dd")
    if min_width:
        date_edit.setMinimumWidth(min_width)
    if min_height:
        date_edit.setMinimumHeight(min_height)

    cal = date_edit.calendarWidget()
    if cal:
        is_dark = theme_mgr.is_dark_mode()
        cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        cal.setMinimumSize(290, 240)
        cal.setStyleSheet(get_calendar_qss(is_dark=is_dark))

        sunday_fmt = QTextCharFormat()
        sunday_fmt.setForeground(QColor("#EF4444" if is_dark else "#DC2626"))
        sunday_fmt.setFontWeight(QFont.Weight.Bold)
        cal.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, sunday_fmt)

        weekday_fmt = QTextCharFormat()
        weekday_fmt.setForeground(QColor("#F8FAFC" if is_dark else "#0F172A"))
        weekday_fmt.setFontWeight(QFont.Weight.DemiBold)
        for day in [
            Qt.DayOfWeek.Monday, Qt.DayOfWeek.Tuesday, Qt.DayOfWeek.Wednesday,
            Qt.DayOfWeek.Thursday, Qt.DayOfWeek.Friday, Qt.DayOfWeek.Saturday
        ]:
            cal.setWeekdayTextFormat(day, weekday_fmt)

"""
Modern Light ERP Theme QSS Stylesheet for PySide6
"""

LIGHT_THEME_QSS = """
/* Global Window Background */
QMainWindow, QDialog, QWidget#MainContainer {
    background-color: #F8F9FA;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
    color: #1E293B;
}

/* Card / Section Panels */
QFrame.card-panel, QWidget.card-panel {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

QLabel {
    background-color: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}

QLabel.heading-primary {
    font-size: 20px;
    font-weight: 700;
    color: #0F172A;
}

QLabel.heading-secondary {
    font-size: 15px;
    font-weight: 600;
    color: #334155;
}

QLabel.subtext {
    font-size: 12px;
    color: #64748B;
}

/* Group Boxes */
QGroupBox {
    font-weight: 700;
    font-size: 13px;
    color: #1A73E8;
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
    color: #1A73E8;
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

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Inputs & Combo Boxes */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
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

QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
    border: 2px solid #1A73E8;
    background-color: #FFFFFF;
}

QLineEdit:disabled, QComboBox:disabled, QTextEdit:disabled {
    background-color: #F1F5F9;
    color: #94A3B8;
    border: 1px solid #E2E8F0;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 0px;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
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
QPushButton.btn-primary {
    background-color: #1A73E8;
    color: #FFFFFF;
    border: 1px solid #1557B0;
}

QPushButton.btn-primary:hover {
    background-color: #1557B0;
    border-color: #0D47A1;
}

QPushButton.btn-primary:pressed {
    background-color: #0D47A1;
}

/* Danger Buttons */
QPushButton.btn-danger {
    background-color: #DC2626;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
}

QPushButton.btn-danger:hover {
    background-color: #B91C1C;
}

/* Success Buttons */
QPushButton.btn-success {
    background-color: #16A34A;
    color: #FFFFFF;
    border: 1px solid #15803D;
}

QPushButton.btn-success:hover {
    background-color: #15803D;
}

/* Table Widget */
QTableWidget, QTableView {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    gridline-color: #F1F5F9;
    font-size: 13px;
    color: #1E293B;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A8A;
    outline: none;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #F1F5F9;
}

QTableWidget::item:alternate {
    background-color: #F8FAFC;
}

QTableWidget::item:selected {
    background-color: #DBEAFE;
    color: #1E3A8A;
}

QHeaderView::section {
    background-color: #F1F5F9;
    color: #334155;
    padding: 6px 12px;
    font-weight: 700;
    font-size: 12px;
    min-height: 28px;
    height: 32px;
    border: none;
    border-bottom: 2px solid #CBD5E1;
    border-right: 1px solid #E2E8F0;
}

/* Checkboxes */
QCheckBox {
    font-size: 13px;
    color: #334155;
    spacing: 6px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #CBD5E1;
    background-color: #FFFFFF;
}

QCheckBox::indicator:checked {
    background-color: #1A73E8;
    border-color: #1557B0;
}

/* Status Bar */
QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    color: #64748B;
    font-size: 12px;
}

/* Tab Widget */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    background-color: #FFFFFF;
    border-radius: 6px;
    top: -1px;
}

QTabBar::tab {
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #E2E8F0;
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #1A73E8;
    border-bottom-color: #FFFFFF;
}

QTabBar::tab:hover:!selected {
    background-color: #E2E8F0;
}

/* ToolBar */
QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    spacing: 6px;
    padding: 4px;
}
"""

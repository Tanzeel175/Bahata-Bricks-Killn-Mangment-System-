import csv
from datetime import date
from typing import Dict, Any, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QPushButton, QFrame, QScrollArea, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QFileDialog, QRadioButton,
    QButtonGroup, QListView, QAbstractItemView, QMenu, QLayout
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont

from app.ui.components.toast import ToastNotification
from app.services.register_service import RegisterService
from app.services.ledger_service import LedgerService
from app.ui.views.ledger_report_window import LedgerReportWindow, TabularSummaryReportWindow
from app.ui.styles import configure_date_edit
from app.ui.theme_manager import theme_mgr


class NonWheelComboBox(QComboBox):
    """
    QComboBox that does NOT consume the mouse wheel unless its popup menu is open.
    This prevents hijacking the parent window/container scrolling!
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxVisibleItems(14)
        v = self.view()
        if v:
            v.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            v.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            v.setAutoFillBackground(True)

    def showPopup(self):
        v = self.view()
        if v:
            v.setAutoFillBackground(True)
            p = v.parentWidget()
            if p:
                p.setAutoFillBackground(True)
        super().showPopup()

    def wheelEvent(self, event):
        # Only change selection via mouse wheel if the drop-down popup is actively visible
        if self.view() and self.view().isVisible():
            super().wheelEvent(event)
        else:
            # Let the mouse wheel event propagate to parent scroll area
            event.ignore()


class CentralRegistersView(QWidget):
    """
    Central Registers & Khatas Hub (مرکزی رجسٹر اور کھاتہ جات).
    Redesigned for optimal ergonomics on general laptops (1366x768, 1280x720, 1080p).
    Features:
    - Ultra-compact, non-merging header & segmented tab switcher.
    - Responsive 2-row filter card with generous spacing and zero overlap.
    - Low-profile, high-impact KPI stat badges.
    - Full-height data table with smooth mouse wheel scrolling.
    - Seamless outer scroll area so small screens never clip content.
    """

    close_requested = Signal()

    MODE_CUSTOMER = "CUSTOMER"
    MODE_LABOUR = "LABOUR"
    MODE_SALES = "SALES"
    MODE_WORK = "WORK"
    MODE_CASHBOOK = "CASHBOOK"
    MODE_OTHER = "OTHER"

    def __init__(self, default_mode=None, parent=None):
        super().__init__(parent)
        self.current_mode = default_mode or self.MODE_CUSTOMER
        self.current_rows: List[Dict[str, Any]] = []
        self.current_kpis: Dict[str, Any] = {}
        self._init_ui()
        self._load_initial_data()
        theme_mgr.theme_changed.connect(self._on_theme_changed)

    def _init_ui(self):
        # Root Layout: Contains the outer scroll area to guarantee 100% laptop compatibility
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Main Outer Scroll Area
        self.main_scroll = QScrollArea()
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setFrameShape(QFrame.NoFrame)
        self.main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        # Inner Container
        self.inner_container = QWidget()
        self.inner_container.setObjectName("registersInnerContainer")
        self.inner_container.setStyleSheet("#registersInnerContainer { background-color: transparent; }")
        self.content_layout = QVBoxLayout(self.inner_container)
        self.content_layout.setContentsMargins(12, 10, 12, 10)
        self.content_layout.setSpacing(8)

        # 2. Compact Top Bar: Title + Segmented Register Switcher + Refresh
        top_bar = QFrame()
        top_bar.setStyleSheet(
            "QFrame#topBar { background-color: #0F172A; "
            "border: 1px solid #1E293B; border-radius: 8px; padding: 6px 12px; }"
        )
        top_bar.setObjectName("topBar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)
        t_label = QLabel("Central Registers & Khatas (مرکزی رجسٹر اور کھاتہ جات)")
        t_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFFFFF;")
        sub_label = QLabel("Customer, Labour, Sales, Production, and Cashbook Records")
        sub_label.setStyleSheet("font-size: 10.5px; color: #BFDBFE; font-weight: 500;")
        title_layout.addWidget(t_label)
        title_layout.addWidget(sub_label)
        top_layout.addLayout(title_layout)

        top_layout.addStretch()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: #FFFFFF; border: 1px solid #60A5FA; "
            "border-radius: 5px; padding: 5px 12px; font-weight: 700; font-size: 11.5px; } "
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_refresh.clicked.connect(self.refresh_view)
        top_layout.addWidget(self.btn_refresh)

        self.content_layout.addWidget(top_bar)

        # 3. Modern Segmented Tab Switcher (Horizontal Pill Strip)
        tabs_frame = QFrame()
        tabs_frame.setObjectName("tabsFrame")
        tabs_frame.setProperty("class", "card-panel")
        tabs_layout = QHBoxLayout(tabs_frame)
        tabs_layout.setContentsMargins(4, 4, 4, 4)
        tabs_layout.setSpacing(4)

        self.btn_tab_customer = self._create_nav_pill("Customers (گاہک)", self.MODE_CUSTOMER)
        self.btn_tab_labour = self._create_nav_pill("Labour (لیبر کھاتہ)", self.MODE_LABOUR)
        self.btn_tab_sales = self._create_nav_pill("Sales (سیلز)", self.MODE_SALES)
        self.btn_tab_work = self._create_nav_pill("Daily Work (پیداوار)", self.MODE_WORK)
        self.btn_tab_cash = self._create_nav_pill("Cashbook (آمدن و اخراجات)", self.MODE_CASHBOOK)
        self.btn_tab_other = self._create_nav_pill("Other Accounts (دیگر)", self.MODE_OTHER)

        tabs_layout.addWidget(self.btn_tab_customer)
        tabs_layout.addWidget(self.btn_tab_labour)
        tabs_layout.addWidget(self.btn_tab_sales)
        tabs_layout.addWidget(self.btn_tab_work)
        tabs_layout.addWidget(self.btn_tab_cash)
        tabs_layout.addWidget(self.btn_tab_other)

        self.content_layout.addWidget(tabs_frame)

        # 4. Ergonomic Criteria & Filter Card (2 Spacious, Clean Rows)
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_card.setProperty("class", "card-panel")
        f_vbox = QVBoxLayout(filter_card)
        f_vbox.setContentsMargins(6, 6, 6, 6)
        f_vbox.setSpacing(6)

        # Filter Row 1: Mode Switch + Category + Account + Search
        r1_layout = QHBoxLayout()
        r1_layout.setSpacing(10)

        # Radio mode buttons
        self.radio_group = QButtonGroup(self)
        self.rb_summary = QRadioButton("Group Summary")
        self.rb_summary.setStyleSheet("font-weight: 700; font-size: 11.5px;")
        self.rb_summary.setChecked(True)
        self.rb_summary.toggled.connect(self._on_sub_mode_changed)

        self.rb_individual = QRadioButton("Individual Khata")
        self.rb_individual.setStyleSheet("font-weight: 700; font-size: 11.5px;")
        self.rb_individual.toggled.connect(self._on_sub_mode_changed)

        self.radio_group.addButton(self.rb_summary)
        self.radio_group.addButton(self.rb_individual)

        self.radio_box = QWidget()
        rb_layout = QHBoxLayout(self.radio_box)
        rb_layout.setContentsMargins(0, 0, 0, 0)
        rb_layout.setSpacing(8)
        rb_layout.addWidget(self.rb_summary)
        rb_layout.addWidget(self.rb_individual)
        r1_layout.addWidget(self.radio_box)

        # Category
        self.lbl_category = QLabel("Category:")
        self.lbl_category.setStyleSheet("font-weight: 700; font-size: 11px;")
        self.cmb_category = NonWheelComboBox()
        self.cmb_category.setStyleSheet(self._input_style())
        self.cmb_category.setMinimumWidth(130)
        self.cmb_category.currentTextChanged.connect(self._on_category_changed)
        r1_layout.addWidget(self.lbl_category)
        r1_layout.addWidget(self.cmb_category)

        # Account Picker
        self.lbl_account = QLabel("Account:")
        self.lbl_account.setStyleSheet("font-weight: 700; font-size: 11px;")
        self.cmb_account = NonWheelComboBox()
        self.cmb_account.setStyleSheet(self._input_style())
        self.cmb_account.setMinimumWidth(160)
        self.cmb_account.currentIndexChanged.connect(self._on_account_changed)
        r1_layout.addWidget(self.lbl_account)
        r1_layout.addWidget(self.cmb_account)

        r1_layout.addStretch()

        self.btn_apply = QPushButton("Load Register Data")
        self.btn_apply.setCursor(Qt.PointingHandCursor)
        self.btn_apply.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 11.5px; "
            "border-radius: 5px; padding: 5px 14px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_apply.clicked.connect(self.load_register_data)
        r1_layout.addWidget(self.btn_apply)

        self.btn_top_print = QPushButton("View / Print A4 Report")
        self.btn_top_print.setCursor(Qt.PointingHandCursor)
        self.btn_top_print.setStyleSheet(
            "QPushButton { background-color: #16A34A; color: #FFFFFF; font-weight: 700; font-size: 11.5px; "
            "border-radius: 5px; padding: 5px 14px; border: 1px solid #15803D; } "
            "QPushButton:hover { background-color: #15803D; }"
        )
        self.btn_top_print.clicked.connect(self._on_print_report)
        r1_layout.addWidget(self.btn_top_print)

        f_vbox.addLayout(r1_layout)

        # Filter Row 2: Date Range + Quick Presets + Search Filter + Fit Columns
        r2_layout = QHBoxLayout()
        r2_layout.setSpacing(8)

        # Unified Date & Preset Sub-Container (mathematically guarantees zero overlap)
        date_filter_box = QWidget()
        df_layout = QHBoxLayout(date_filter_box)
        df_layout.setSizeConstraint(QLayout.SetMinimumSize)
        df_layout.setContentsMargins(0, 0, 0, 0)
        df_layout.setSpacing(6)

        is_d = theme_mgr.is_dark_mode()
        lbl_col = "#FFFFFF" if is_d else "#475569"

        self.lbl_from = QLabel("From:")
        self.lbl_from.setStyleSheet(f"font-weight: 700; font-size: 11px; color: {lbl_col};")
        self.dt_from = QDateEdit()
        configure_date_edit(self.dt_from, min_width=110, min_height=26)
        self.dt_from.setFixedWidth(125)
        self.dt_from.setStyleSheet(self._date_input_style())
        today = QDate.currentDate()
        self.dt_from.setDate(QDate(today.year(), today.month(), 1))

        self.lbl_to = QLabel("To:")
        self.lbl_to.setStyleSheet(f"font-weight: 700; font-size: 11px; color: {lbl_col};")
        self.dt_to = QDateEdit()
        configure_date_edit(self.dt_to, min_width=110, min_height=26)
        self.dt_to.setFixedWidth(125)
        self.dt_to.setDate(today)
        self.dt_to.setStyleSheet(self._date_input_style())

        self.lbl_preset = QLabel("Preset:")
        self.lbl_preset.setStyleSheet(f"font-weight: 700; font-size: 11px; color: {lbl_col};")

        self.cmb_preset = NonWheelComboBox()
        self.cmb_preset.addItems(["This Month", "Last 30 Days", "Full Year", "Custom Range"])
        self.cmb_preset.setStyleSheet(self._input_style())
        self.cmb_preset.setFixedWidth(135)
        self.cmb_preset.currentIndexChanged.connect(self._on_preset_changed)

        df_layout.addWidget(self.lbl_from)
        df_layout.addWidget(self.dt_from)
        df_layout.addSpacing(4)
        df_layout.addWidget(self.lbl_to)
        df_layout.addWidget(self.dt_to)
        df_layout.addSpacing(8)
        df_layout.addWidget(self.lbl_preset)
        df_layout.addWidget(self.cmb_preset)

        date_filter_box.setMinimumWidth(df_layout.sizeHint().width())
        r2_layout.addWidget(date_filter_box)

        # Sync manual date changes to mark preset as 'Custom Range'
        self.dt_from.dateChanged.connect(self._on_date_manually_changed)
        self.dt_to.dateChanged.connect(self._on_date_manually_changed)

        r2_layout.addStretch()

        # Search Bar
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search in table...")
        self.txt_search.setStyleSheet("min-width: 130px; max-width: 220px; font-size: 11.5px;")
        self.txt_search.textChanged.connect(self._apply_client_filter)
        r2_layout.addWidget(self.txt_search)

        self.btn_fit_cols = QPushButton("Fit Columns")
        self.btn_fit_cols.setCursor(Qt.PointingHandCursor)
        self.btn_fit_cols.setToolTip("Auto-fit columns to page width (کالمز کو صفحہ کے سائز پر فٹ کریں)")
        self.btn_fit_cols.setProperty("class", "btn-secondary")
        self.btn_fit_cols.clicked.connect(self._on_user_fit_columns)
        r2_layout.addWidget(self.btn_fit_cols)

        f_vbox.addLayout(r2_layout)
        self.content_layout.addWidget(filter_card)

        # 5. Low-Profile KPI Metric Ribbon (4 Compact Stat Pills)
        kpi_ribbon = QFrame()
        kpi_ribbon.setObjectName("kpiRibbon")
        kpi_ribbon.setProperty("class", "card-panel")
        kpi_layout = QHBoxLayout(kpi_ribbon)
        kpi_layout.setContentsMargins(4, 2, 4, 2)
        kpi_layout.setSpacing(8)

        self.kpi_card_1 = self._create_kpi_pill("Total", "—", "#2563EB", "#EFF6FF")
        self.kpi_card_2 = self._create_kpi_pill("Inflow / Credit", "—", "#16A34A", "#F0FDF4")
        self.kpi_card_3 = self._create_kpi_pill("Outflow / Debit", "—", "#DC2626", "#FEF2F2")
        self.kpi_card_4 = self._create_kpi_pill("Net Balance", "—", "#D97706", "#FFFBEB")

        kpi_layout.addWidget(self.kpi_card_1)
        kpi_layout.addWidget(self.kpi_card_2)
        kpi_layout.addWidget(self.kpi_card_3)
        kpi_layout.addWidget(self.kpi_card_4)

        self.content_layout.addWidget(kpi_ribbon)

        # 6. Main High-Performance Data Table
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setWordWrap(False)
        self.table.setMinimumHeight(320)  # Guarantees generous table view even inside small laptop viewports
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setStyleSheet("QTableWidget { font-size: 11.5px; } QTableWidget::item { padding: 4px 6px; }")
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._on_table_double_clicked)
        header = self.table.horizontalHeader()
        header.setContextMenuPolicy(Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_header_context_menu)
        header.sectionResized.connect(self._on_section_resized)
        self.content_layout.addWidget(self.table, stretch=1)

        # 7. Action Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.lbl_status = QLabel("Ready.")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 600;")
        action_bar.addWidget(self.lbl_status)
        action_bar.addStretch()

        btn_print = QPushButton("Print A4 Report")
        btn_print.setCursor(Qt.PointingHandCursor)
        btn_print.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 11.5px; "
            "border-radius: 5px; padding: 6px 14px; border: 1px solid #0369A1; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        btn_print.clicked.connect(self._on_print_report)
        action_bar.addWidget(btn_print)

        btn_export = QPushButton("Export CSV")
        btn_export.setCursor(Qt.PointingHandCursor)
        btn_export.setStyleSheet(
            "QPushButton { background-color: #059669; color: #FFFFFF; font-weight: 700; font-size: 11.5px; "
            "border-radius: 5px; padding: 6px 14px; border: 1px solid #047857; } "
            "QPushButton:hover { background-color: #047857; }"
        )
        btn_export.clicked.connect(self._on_export_csv)
        action_bar.addWidget(btn_export)

        self.btn_quick_pay = QPushButton("Quick Payment")
        self.btn_quick_pay.setCursor(Qt.PointingHandCursor)
        self._apply_quick_pay_style()
        self.btn_quick_pay.clicked.connect(self._on_quick_payment)
        action_bar.addWidget(self.btn_quick_pay)

        self.content_layout.addLayout(action_bar)

        # Set inner container into scroll area
        self.main_scroll.setWidget(self.inner_container)
        root_layout.addWidget(self.main_scroll)

    def _create_nav_pill(self, text: str, mode_key: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(30)
        btn.setProperty("mode_key", mode_key)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.clicked.connect(lambda: self.switch_mode(mode_key))
        return btn

    def _create_kpi_pill(self, title: str, val: str, accent_color: str, bg_color: str) -> QFrame:
        card = QFrame()
        card._accent = accent_color
        card._bg = bg_color
        self._apply_kpi_pill_style(card)
        l = QVBoxLayout(card)
        l.setContentsMargins(4, 2, 4, 2)
        l.setSpacing(1)

        t = QLabel(title + ":")
        t.setObjectName("lbl_title")
        t.setStyleSheet("font-size: 10px; font-weight: 700; text-transform: uppercase;")

        v = QLabel(val)
        v.setObjectName("lbl_val")
        v.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {accent_color};")

        l.addWidget(t)
        l.addWidget(v)
        return card

    def _apply_kpi_pill_style(self, card: QFrame):
        is_dark = theme_mgr.is_dark_mode()
        bg = "#1E293B" if is_dark else getattr(card, "_bg", "#FFFFFF")
        border = "#334155" if is_dark else "#CBD5E1"
        card.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: 1px solid {border}; border-left: 3px solid {card._accent}; "
            f"border-radius: 5px; padding: 4px 8px; }}"
        )

    def _apply_quick_pay_style(self):
        if not hasattr(self, "btn_quick_pay") or not self.btn_quick_pay:
            return
        is_dark = theme_mgr.is_dark_mode()
        if is_dark:
            self.btn_quick_pay.setStyleSheet(
                "QPushButton { background-color: #1E293B; color: #38BDF8; font-weight: 700; font-size: 11.5px; "
                "border: 1px solid #334155; border-radius: 5px; padding: 6px 12px; } "
                "QPushButton:hover { background-color: #334155; border-color: #38BDF8; color: #FFFFFF; }"
            )
        else:
            self.btn_quick_pay.setStyleSheet(
                "QPushButton { background-color: #F1F5F9; color: #0284C7; font-weight: 700; font-size: 11.5px; "
                "border: 1px solid #BAE6FD; border-radius: 5px; padding: 6px 12px; } "
                "QPushButton:hover { background-color: #E0F2FE; }"
            )

    def _on_theme_changed(self, _theme: str):
        is_dark = theme_mgr.is_dark_mode()
        lbl_col = "#FFFFFF" if is_dark else "#475569"
        status_col = "#E2E8F0" if is_dark else "#64748B"

        for lbl in (getattr(self, "lbl_from", None), getattr(self, "lbl_to", None), getattr(self, "lbl_preset", None)):
            if lbl:
                lbl.setStyleSheet(f"font-weight: 700; font-size: 11px; color: {lbl_col};")

        if hasattr(self, "lbl_status") and self.lbl_status:
            self.lbl_status.setStyleSheet(f"font-size: 11px; color: {status_col}; font-weight: 600;")

        self._apply_quick_pay_style()

        for card in (
            getattr(self, "kpi_card_1", None),
            getattr(self, "kpi_card_2", None),
            getattr(self, "kpi_card_3", None),
            getattr(self, "kpi_card_4", None),
        ):
            if card:
                self._apply_kpi_pill_style(card)
        self._update_tab_buttons_style()
        for cmb in (
            getattr(self, "cmb_category", None),
            getattr(self, "cmb_account", None),
            getattr(self, "cmb_preset", None),
        ):
            if cmb:
                cmb.setStyleSheet(self._input_style())
        for dt in (
            getattr(self, "dt_from", None),
            getattr(self, "dt_to", None),
        ):
            if dt:
                dt.setStyleSheet(self._date_input_style())

    def _update_tab_buttons_style(self):
        """Update styling of tab pill buttons based on current theme without reloading data."""
        is_dark = theme_mgr.is_dark_mode()
        current_mode = getattr(self, "current_mode", self.MODE_CUSTOMER)
        for btn in (
            getattr(self, "btn_tab_customer", None),
            getattr(self, "btn_tab_labour", None),
            getattr(self, "btn_tab_sales", None),
            getattr(self, "btn_tab_work", None),
            getattr(self, "btn_tab_cash", None),
            getattr(self, "btn_tab_other", None),
        ):
            if not btn:
                continue
            is_active = (btn.property("mode_key") == current_mode)
            if is_active:
                btn.setStyleSheet(
                    "QPushButton { background-color: #1E3A8A; "
                    "color: #FFFFFF; font-weight: 800; font-size: 11.5px; border-radius: 5px; border: 1px solid #2563EB; padding: 4px 8px; }"
                )
            else:
                inact_bg = "#1E293B" if is_dark else "#F8FAFC"
                inact_color = "#94A3B8" if is_dark else "#334155"
                inact_border = "#334155" if is_dark else "#E2E8F0"
                inact_hover = "#334155" if is_dark else "#F1F5F9"
                btn.setStyleSheet(
                    f"QPushButton {{ background-color: {inact_bg}; color: {inact_color}; font-weight: 600; font-size: 11.5px; "
                    f"border: 1px solid {inact_border}; border-radius: 5px; padding: 4px 8px; }} "
                    f"QPushButton:hover {{ background-color: {inact_hover}; border-color: #0284C7; }}"
                )

    def _update_kpi(self, card: QFrame, title: str, val: str, accent_color: str = None):
        card.findChild(QLabel, "lbl_title").setText(title + ":")
        val_lbl = card.findChild(QLabel, "lbl_val")
        val_lbl.setText(val)
        if accent_color:
            val_lbl.setStyleSheet(f"font-size: 13px; font-weight: 800; color: {accent_color};")

    def switch_mode(self, mode_key: str):
        self.current_mode = mode_key
        # Update pill button active styles
        self._update_tab_buttons_style()

        self._user_resized_columns = False
        if hasattr(self, "inner_container") and hasattr(self, "main_scroll"):
            vw = self.main_scroll.viewport().width()
            if vw > 100:
                self.inner_container.setFixedWidth(vw)
        self._configure_filters_for_mode()
        self.load_register_data()

    def _configure_filters_for_mode(self):
        """Show/hide appropriate dropdowns based on the selected register mode."""
        self.cmb_category.blockSignals(True)
        self.cmb_category.clear()

        is_submode_applicable = self.current_mode in (self.MODE_CUSTOMER, self.MODE_LABOUR)
        self.radio_box.setVisible(is_submode_applicable)

        if self.current_mode == self.MODE_CUSTOMER:
            self.lbl_category.setVisible(False)
            self.cmb_category.setVisible(False)
            self._load_accounts("Customer")
            self.lbl_account.setVisible(self.rb_individual.isChecked())
            self.cmb_account.setVisible(self.rb_individual.isChecked())

        elif self.current_mode == self.MODE_LABOUR:
            self.lbl_category.setVisible(True)
            self.cmb_category.setVisible(True)
            self.lbl_category.setText("Labour:")
            cats = ["All Labour"] + RegisterService.get_labour_categories()
            self.cmb_category.addItems(cats)

            is_ind = self.rb_individual.isChecked()
            self.lbl_account.setVisible(is_ind)
            self.cmb_account.setVisible(is_ind)
            if is_ind:
                self._load_accounts(self.cmb_category.currentText())

        elif self.current_mode == self.MODE_SALES:
            self.lbl_category.setVisible(True)
            self.lbl_category.setText("Transport:")
            modes = ["All Modes", "Rehra (ریڑھا)", "Tractor Trolley (ٹریکٹر ٹرالی)", "Truck (ٹرک)", "Customer Own Transport", "Other"]
            self.cmb_category.addItems(modes)

            self.lbl_account.setVisible(True)
            self.lbl_account.setText("Customer:")
            self._load_accounts("Customer", include_all=True)

        elif self.current_mode == self.MODE_WORK:
            self.lbl_category.setVisible(True)
            self.lbl_category.setText("Work Type:")
            cats = ["All Labour"] + RegisterService.get_labour_categories()
            self.cmb_category.addItems(cats)

            self.lbl_account.setVisible(True)
            self.lbl_account.setText("Worker:")
            self._load_accounts("All Labour", include_all=True)

        elif self.current_mode == self.MODE_CASHBOOK:
            self.lbl_category.setVisible(True)
            self.lbl_category.setText("Type:")
            self.cmb_category.addItems(["Both (Amdan & Akrajat)", "RECEIPT (Amdan Only)", "PAYMENT (Akrajat Only)"])

            self.lbl_account.setVisible(True)
            self.lbl_account.setText("Method:")
            self.cmb_account.blockSignals(True)
            self.cmb_account.clear()
            self.cmb_account.addItems(["All Methods", "Cash", "Bank", "Cheque", "Online"])
            self.cmb_account.blockSignals(False)

        elif self.current_mode == self.MODE_OTHER:
            self.lbl_category.setVisible(True)
            self.lbl_category.setText("Category:")
            self.cmb_category.addItems(RegisterService.get_other_categories())

            self.lbl_account.setVisible(True)
            self.lbl_account.setText("Account:")
            curr_cat = self.cmb_category.currentText()
            self._load_accounts(curr_cat, include_all=True)

        self.cmb_category.blockSignals(False)

    def _load_accounts(self, category_name: str, include_all: bool = False):
        self.cmb_account.blockSignals(True)
        self.cmb_account.clear()

        if include_all:
            self.cmb_account.addItem("All Accounts", userData="All")

        if category_name in ("All Labour", "All Modes", "Both (Amdan & Akrajat)"):
            workers = []
            for c in RegisterService.get_labour_categories():
                workers.extend(LedgerService.get_workers_by_category(c))
        else:
            workers = LedgerService.get_workers_by_category(category_name)

        for w in workers:
            name = f"{w['WorkerID']} — {w['EnglishName']}"
            if w.get('UrduName'):
                name += f" ({w['UrduName']})"
            self.cmb_account.addItem(name, userData=w['WorkerID'])

        if not workers and not include_all:
            self.cmb_account.addItem("No accounts found", userData=None)

        self.cmb_account.blockSignals(False)

    def _on_sub_mode_changed(self):
        is_ind = self.rb_individual.isChecked()
        self.lbl_account.setVisible(is_ind)
        self.cmb_account.setVisible(is_ind)
        if is_ind:
            cat = self.cmb_category.currentText() if self.current_mode == self.MODE_LABOUR else "Customer"
            self._load_accounts(cat)
        self.load_register_data()

    def _on_category_changed(self, text: str):
        if self.current_mode in (self.MODE_LABOUR, self.MODE_WORK, self.MODE_OTHER):
            include_all = (self.current_mode != self.MODE_LABOUR) or self.rb_summary.isChecked()
            self._load_accounts(text, include_all=include_all)
        self.load_register_data()

    def _on_account_changed(self):
        if self.current_mode in (self.MODE_CUSTOMER, self.MODE_LABOUR) and self.rb_individual.isChecked():
            self.load_register_data()

    def _on_preset_changed(self, index: int):
        if index == 0:
            self._preset_this_month()
        elif index == 1:
            self._preset_last_30()
        elif index == 2:
            self._preset_full_year()

    def _on_date_manually_changed(self):
        if hasattr(self, "cmb_preset"):
            self.cmb_preset.blockSignals(True)
            self.cmb_preset.setCurrentIndex(3)  # Custom Range
            self.cmb_preset.blockSignals(False)

    def _preset_this_month(self):
        today = QDate.currentDate()
        self.dt_from.blockSignals(True)
        self.dt_to.blockSignals(True)
        self.dt_from.setDate(QDate(today.year(), today.month(), 1))
        self.dt_to.setDate(today)
        self.dt_from.blockSignals(False)
        self.dt_to.blockSignals(False)
        if hasattr(self, "cmb_preset"):
            self.cmb_preset.blockSignals(True)
            self.cmb_preset.setCurrentIndex(0)
            self.cmb_preset.blockSignals(False)
        self.load_register_data()

    def _preset_last_30(self):
        today = QDate.currentDate()
        self.dt_from.blockSignals(True)
        self.dt_to.blockSignals(True)
        self.dt_from.setDate(today.addDays(-30))
        self.dt_to.setDate(today)
        self.dt_from.blockSignals(False)
        self.dt_to.blockSignals(False)
        if hasattr(self, "cmb_preset"):
            self.cmb_preset.blockSignals(True)
            self.cmb_preset.setCurrentIndex(1)
            self.cmb_preset.blockSignals(False)
        self.load_register_data()

    def _preset_full_year(self):
        today = QDate.currentDate()
        self.dt_from.blockSignals(True)
        self.dt_to.blockSignals(True)
        self.dt_from.setDate(QDate(today.year(), 1, 1))
        self.dt_to.setDate(today)
        self.dt_from.blockSignals(False)
        self.dt_to.blockSignals(False)
        if hasattr(self, "cmb_preset"):
            self.cmb_preset.blockSignals(True)
            self.cmb_preset.setCurrentIndex(2)
            self.cmb_preset.blockSignals(False)
        self.load_register_data()

    def _load_initial_data(self):
        self.switch_mode(self.MODE_CUSTOMER)

    def refresh_view(self):
        self.load_register_data()

    def load_register_data(self):
        f_date = self.dt_from.date().toPython()
        t_date = self.dt_to.date().toPython()
        search = self.txt_search.text().strip()

        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)

        try:
            if self.current_mode == self.MODE_CUSTOMER:
                if self.rb_individual.isChecked():
                    self._load_individual_ledger_mode(f_date, t_date)
                else:
                    self._load_customers_summary(f_date, t_date, search)

            elif self.current_mode == self.MODE_LABOUR:
                if self.rb_individual.isChecked():
                    self._load_individual_ledger_mode(f_date, t_date)
                else:
                    cat = self.cmb_category.currentText()
                    self._load_labour_summary(cat, f_date, t_date, search)

            elif self.current_mode == self.MODE_SALES:
                cust_id = self.cmb_account.currentData()
                t_mode = self.cmb_category.currentText()
                if t_mode == "All Modes":
                    t_mode = None
                self._load_sales_register(f_date, t_date, cust_id, t_mode, search)

            elif self.current_mode == self.MODE_WORK:
                cat = self.cmb_category.currentText()
                w_id = self.cmb_account.currentData()
                self._load_work_register(f_date, t_date, cat, w_id, search)

            elif self.current_mode == self.MODE_CASHBOOK:
                t_type = self.cmb_category.currentText()
                if "RECEIPT" in t_type:
                    raw_type = "RECEIPT"
                elif "PAYMENT" in t_type:
                    raw_type = "PAYMENT"
                else:
                    raw_type = "All"
                method = self.cmb_account.currentText()
                self._load_cashbook_register(f_date, t_date, raw_type, method, search)

            elif self.current_mode == self.MODE_OTHER:
                cat = self.cmb_category.currentText()
                self._load_other_summary(cat, f_date, t_date, search)

        except Exception as e:
            self.lbl_status.setText(f"Error loading register: {e}")
            ToastNotification.show_error(self, "Load Error", f"Failed to load register data: {e}")
        finally:
            self.table.setSortingEnabled(True)

    # -------------------------------------------------------------------------
    # DATA LOADERS FOR EACH REGISTER
    # -------------------------------------------------------------------------
    def _load_customers_summary(self, f_date, t_date, search):
        data = RegisterService.get_customers_summary_report(f_date, t_date, search)
        self.current_rows = data["rows"]
        k = data["kpis"]

        self._update_kpi(self.kpi_card_1, "Customers", f"{k.get('total_customers', 0):,}")
        self._update_kpi(self.kpi_card_2, "Sales (Debit)", f"Rs. {k.get('total_sales', 0):,.2f}", "#2563EB")
        self._update_kpi(self.kpi_card_3, "Receipts (Credit)", f"Rs. {k.get('total_receipts', 0):,.2f}", "#16A34A")
        self._update_kpi(self.kpi_card_4, "Net Baqi", f"Rs. {k.get('total_baqi', 0):,.2f}", "#DC2626")

        cols = [
            "Customer ID", "Customer Name", "Phone", "Opening Bal",
            "Period Sales", "Period Receipts", "Invoices", "Net Balance", "Status"
        ]
        self._setup_table(cols, stretch_col=1, col_widths={
            0: 95, 2: 100, 3: 100, 4: 100, 5: 100, 6: 70, 7: 110, 8: 95
        })

        self.table.setRowCount(len(self.current_rows))
        for r_idx, r in enumerate(self.current_rows):
            name = r["EnglishName"]
            if r["UrduName"]:
                name += f" ({r['UrduName']})"

            self._set_item(r_idx, 0, r["CustomerID"], bold=True)
            self._set_item(r_idx, 1, name)
            self._set_item(r_idx, 2, r["Mobile"] or "—")
            self._set_currency(r_idx, 3, r["OpeningBalance"])
            self._set_currency(r_idx, 4, r["PeriodSales"], color="#2563EB")
            self._set_currency(r_idx, 5, r["PeriodReceipts"], color="#16A34A")
            self._set_item(r_idx, 6, str(r["InvoicesCount"]), align=Qt.AlignCenter)
            self._set_currency(r_idx, 7, r["ClosingBalance"], color="#DC2626" if r["ClosingBalance"] < 0 else "#16A34A")
            self._set_status_badge(r_idx, 8, r["Status"])

        self.lbl_status.setText(f"Showing {len(self.current_rows)} Customer accounts ({f_date} to {t_date})")

    def _load_labour_summary(self, category_name, f_date, t_date, search):
        data = RegisterService.get_labour_summary_report(f_date, t_date, category_name, search)
        self.current_rows = data["rows"]
        k = data["kpis"]

        self._update_kpi(self.kpi_card_1, "Labourers", f"{k.get('total_workers', 0):,}")
        self._update_kpi(self.kpi_card_2, "Production Qty", f"{k.get('total_production_qty', 0):,.0f} Pcs", "#2563EB")
        self._update_kpi(self.kpi_card_3, "Earned Wages", f"Rs. {k.get('total_wages_earned', 0):,.2f}", "#16A34A")
        self._update_kpi(self.kpi_card_4, "Payable to Labour", f"Rs. {k.get('total_payable', 0):,.2f}", "#DC2626")

        cols = [
            "Worker ID", "Labour Name", "Category", "Opening Bal",
            "Production Qty", "Earned Wages", "Advances Paid", "Closing Balance", "Status"
        ]
        self._setup_table(cols, stretch_col=1, col_widths={
            0: 85, 2: 95, 3: 100, 4: 95, 5: 105, 6: 105, 7: 110, 8: 95
        })

        self.table.setRowCount(len(self.current_rows))
        for r_idx, r in enumerate(self.current_rows):
            name = r["EnglishName"]
            if r["UrduName"]:
                name += f" ({r['UrduName']})"

            self._set_item(r_idx, 0, r["WorkerID"], bold=True)
            self._set_item(r_idx, 1, name)
            self._set_item(r_idx, 2, r["CategoryName"])
            self._set_currency(r_idx, 3, r["OpeningBalance"])
            self._set_item(r_idx, 4, f"{r['ProductionQty']:,.0f}", align=Qt.AlignRight)
            self._set_currency(r_idx, 5, r["EarnedWages"], color="#16A34A")
            self._set_currency(r_idx, 6, r["PaymentsPaid"], color="#DC2626")
            self._set_currency(r_idx, 7, r["ClosingBalance"], color="#DC2626" if r["ClosingBalance"] > 0 else "#16A34A")
            self._set_status_badge(r_idx, 8, r["Status"])

        self.lbl_status.setText(f"Showing {len(self.current_rows)} Labourers ({category_name} • {f_date} to {t_date})")

    def _load_individual_ledger_mode(self, f_date, t_date):
        wid = self.cmb_account.currentData()
        if not wid or wid == "All":
            self.lbl_status.setText("Please select an individual account above.")
            return

        data = LedgerService.calculate_worker_ledger(wid, f_date, t_date)
        if not data:
            self.lbl_status.setText("Account not found.")
            return

        txns = data.get("transactions", [])
        self.current_rows = txns

        self._update_kpi(self.kpi_card_1, "Opening Bal", f"Rs. {data['opening_balance']:,.2f}")
        self._update_kpi(self.kpi_card_2, "Period Credit", f"Rs. {data['total_credit']:,.2f}", "#16A34A")
        self._update_kpi(self.kpi_card_3, "Period Debit", f"Rs. {data['total_debit']:,.2f}", "#DC2626")
        self._update_kpi(self.kpi_card_4, "Closing Balance", f"Rs. {data['closing_balance']:,.2f}", "#2563EB")

        cols = ["Date", "Ref #", "Transaction Description", "Credit (Rs.)", "Debit (Rs.)", "Running Balance"]
        self._setup_table(cols, stretch_col=2, col_widths={
            0: 95, 1: 90, 3: 110, 4: 110, 5: 120
        })

        self.table.setRowCount(len(txns))
        for r_idx, t in enumerate(txns):
            self._set_item(r_idx, 0, t["date_str"])
            self._set_item(r_idx, 1, t["ref"], bold=True)
            self._set_item(r_idx, 2, t["description"])
            self._set_currency(r_idx, 3, t["credit"], color="#16A34A")
            self._set_currency(r_idx, 4, t["debit"], color="#DC2626")
            self._set_currency(r_idx, 5, t["running_balance"])

        self.lbl_status.setText(f"Loaded {len(txns)} transactions for {data['worker']['english_name']} ({wid})")

    def _load_sales_register(self, f_date, t_date, cust_id, t_mode, search):
        data = RegisterService.get_sales_register(f_date, t_date, cust_id, None, t_mode, search)
        self.current_rows = data["rows"]
        k = data["kpis"]

        self._update_kpi(self.kpi_card_1, "Total Invoices", f"{k.get('total_invoices', 0):,}")
        self._update_kpi(self.kpi_card_2, "Bricks Sold", f"{k.get('total_bricks_sold', 0):,.0f} Pcs", "#2563EB")
        self._update_kpi(self.kpi_card_3, "Total Sale Value", f"Rs. {k.get('total_sale_amount', 0):,.2f}", "#16A34A")
        self._update_kpi(self.kpi_card_4, "Avg Rate / 1000", f"Rs. {k.get('avg_rate_per_k', 0):,.2f}", "#D97706")

        cols = ["Invoice #", "Date", "Customer Name", "Transport", "Vehicle #", "Driver", "Products / Description", "Bricks Qty", "Total Amount"]
        self._setup_table(cols, stretch_cols=[2, 6], col_widths={
            0: 95,   # Invoice #
            1: 90,   # Date
            3: 110,  # Transport
            4: 100,  # Vehicle #
            5: 95,   # Driver
            7: 90,   # Qty
            8: 105   # Total Amount
        })

        self.table.setRowCount(len(self.current_rows))
        for r_idx, r in enumerate(self.current_rows):
            self._set_item(r_idx, 0, r["InvoiceNo"], bold=True)
            self._set_item(r_idx, 1, r["SaleDate"])
            self._set_item(r_idx, 2, r["CustomerName"])
            self._set_item(r_idx, 3, r["TransportMode"])
            self._set_item(r_idx, 4, r["VehicleNumber"])
            self._set_item(r_idx, 5, r["DriverName"])
            self._set_item(r_idx, 6, r["ItemsSummary"])
            self._set_item(r_idx, 7, f"{r['TotalBricks']:,.0f}", align=Qt.AlignRight)
            self._set_currency(r_idx, 8, r["TotalAmount"], color="#16A34A")

        self.lbl_status.setText(f"Showing {len(self.current_rows)} Sales Invoices ({f_date} to {t_date})")

    def _load_work_register(self, f_date, t_date, category_name, worker_id, search):
        data = RegisterService.get_production_register(f_date, t_date, category_name, worker_id, None, search)
        self.current_rows = data["rows"]
        k = data["kpis"]

        self._update_kpi(self.kpi_card_1, "Daily Entries", f"{k.get('total_entries', 0):,}")
        self._update_kpi(self.kpi_card_2, "Production Qty", f"{k.get('total_production_qty', 0):,.0f} Pcs", "#2563EB")
        self._update_kpi(self.kpi_card_3, "Labour Cost", f"Rs. {k.get('total_wages_earned', 0):,.2f}", "#DC2626")
        self._update_kpi(self.kpi_card_4, "Avg Wage / 1000", f"Rs. {k.get('avg_wage_rate', 0):,.2f}", "#D97706")

        cols = ["Date", "Worker ID", "Labourer Name", "Category", "Product", "Quantity", "Rate / 1000", "Total Wage (Rs.)", "Remarks"]
        self._setup_table(cols, stretch_cols=[2, 8], col_widths={
            0: 90,   # Date
            1: 85,   # Worker ID
            3: 95,   # Category
            4: 100,  # Product
            5: 90,   # Quantity
            6: 85,   # Rate
            7: 105   # Total Wage
        })

        self.table.setRowCount(len(self.current_rows))
        for r_idx, r in enumerate(self.current_rows):
            self._set_item(r_idx, 0, r["EntryDate"])
            self._set_item(r_idx, 1, r["WorkerID"], bold=True)
            self._set_item(r_idx, 2, r["WorkerName"])
            self._set_item(r_idx, 3, r["CategoryName"])
            self._set_item(r_idx, 4, r["ProductName"])
            self._set_item(r_idx, 5, f"{r['Quantity']:,.0f}", align=Qt.AlignRight)
            self._set_currency(r_idx, 6, r["RatePer1000"])
            self._set_currency(r_idx, 7, r["TotalWage"], color="#16A34A")
            self._set_item(r_idx, 8, r["Remarks"])

        self.lbl_status.setText(f"Showing {len(self.current_rows)} daily production records ({f_date} to {t_date})")

    def _load_cashbook_register(self, f_date, t_date, txn_type, payment_method, search):
        data = RegisterService.get_cashbook_register(f_date, t_date, txn_type, None, payment_method, search)
        self.current_rows = data["rows"]
        k = data["kpis"]

        self._update_kpi(self.kpi_card_1, "Opening Cash", f"Rs. {k.get('opening_cash', 0):,.2f}")
        self._update_kpi(self.kpi_card_2, "Total Amdan", f"Rs. {k.get('total_amdan', 0):,.2f}", "#16A34A")
        self._update_kpi(self.kpi_card_3, "Total Akrajat", f"Rs. {k.get('total_akrajat', 0):,.2f}", "#DC2626")
        self._update_kpi(self.kpi_card_4, "Closing Cash", f"Rs. {k.get('closing_cash', 0):,.2f}", "#2563EB")

        cols = ["Txn #", "Date", "Type", "Account Name", "Category", "Method", "Amdan (Rs.)", "Akrajat (Rs.)", "Balance (Rs.)", "Description"]
        self._setup_table(cols, stretch_cols=[3, 9], col_widths={
            0: 75,   # Txn #
            1: 80,   # Date
            2: 70,   # Type
            3: 155,  # Account Name
            4: 85,   # Category
            5: 70,   # Method
            6: 90,   # Amdan
            7: 90,   # Akrajat
            8: 95,   # Balance
            9: 165   # Description
        })

        self.table.setRowCount(len(self.current_rows))
        for r_idx, r in enumerate(self.current_rows):
            is_amdan = (r["TransactionType"] == "RECEIPT")
            self._set_item(r_idx, 0, r["TransactionNo"], bold=True)
            self._set_item(r_idx, 1, r["TransactionDate"])
            self._set_status_badge(r_idx, 2, "AMDAN" if is_amdan else "AKRAJAT")
            self._set_item(r_idx, 3, r["AccountName"])
            self._set_item(r_idx, 4, r["CategoryName"])
            self._set_item(r_idx, 5, r["PaymentMethod"])
            self._set_currency(r_idx, 6, r["Amdan"], color="#16A34A")
            self._set_currency(r_idx, 7, r["Akrajat"], color="#DC2626")
            self._set_currency(r_idx, 8, r["RunningCash"])
            self._set_item(r_idx, 9, r["Description"])

        self.lbl_status.setText(f"Showing {len(self.current_rows)} Cashbook transactions ({f_date} to {t_date})")

    def _load_other_summary(self, category_name, f_date, t_date, search):
        data = RegisterService.get_general_accounts_summary(category_name, f_date, t_date, search)
        self.current_rows = data["rows"]
        k = data["kpis"]

        self._update_kpi(self.kpi_card_1, "Accounts", f"{k.get('total_accounts', 0):,}")
        self._update_kpi(self.kpi_card_2, "Period Credit", f"Rs. {k.get('total_credit', 0):,.2f}", "#16A34A")
        self._update_kpi(self.kpi_card_3, "Period Debit", f"Rs. {k.get('total_debit', 0):,.2f}", "#DC2626")
        self._update_kpi(self.kpi_card_4, "Net Balance", f"Rs. {k.get('net_balance', 0):,.2f}", "#2563EB")

        cols = ["Account ID", "Account Name", "Category", "Phone", "Opening Bal", "Period Credit", "Period Debit", "Closing Balance", "Status"]
        self._setup_table(cols, stretch_col=1, col_widths={
            0: 90, 2: 95, 3: 100, 4: 100, 5: 105, 6: 105, 7: 110, 8: 95
        })

        self.table.setRowCount(len(self.current_rows))
        for r_idx, r in enumerate(self.current_rows):
            name = r["EnglishName"]
            if r["UrduName"]:
                name += f" ({r['UrduName']})"

            self._set_item(r_idx, 0, r["AccountID"], bold=True)
            self._set_item(r_idx, 1, name)
            self._set_item(r_idx, 2, r["CategoryName"])
            self._set_item(r_idx, 3, r["Mobile"] or "—")
            self._set_currency(r_idx, 4, r["OpeningBalance"])
            self._set_currency(r_idx, 5, r["PeriodCredit"], color="#16A34A")
            self._set_currency(r_idx, 6, r["PeriodDebit"], color="#DC2626")
            self._set_currency(r_idx, 7, r["ClosingBalance"])
            self._set_status_badge(r_idx, 8, r["Status"])

        self.lbl_status.setText(f"Showing {len(self.current_rows)} accounts for {category_name} ({f_date} to {t_date})")

    # -------------------------------------------------------------------------
    # TABLE HELPERS
    # -------------------------------------------------------------------------
    def _setup_table(
        self,
        col_names: List[str],
        stretch_col: Optional[int] = None,
        stretch_cols: Optional[List[int]] = None,
        col_widths: Optional[Dict[int, int]] = None
    ):
        self.table.setColumnCount(len(col_names))
        self.table.setHorizontalHeaderLabels(col_names)
        header = self.table.horizontalHeader()

        # Set all columns to interactive resize mode so user can drag any header to increase/decrease size
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setMinimumSectionSize(35)  # Allows user to shrink unnecessary columns very small
        header.setStretchLastSection(False)

        weights = {}
        if col_widths:
            weights = dict(col_widths)
        else:
            weights = {i: 100 for i in range(len(col_names))}

        if stretch_cols:
            for sc in stretch_cols:
                weights[sc] = max(weights.get(sc, 100), 160)
        elif stretch_col is not None:
            weights[stretch_col] = max(weights.get(stretch_col, 100), 160)

        for i in range(len(col_names)):
            if i not in weights:
                weights[i] = 100

        self._current_col_weights = weights
        self.fit_columns_to_page()

    def fit_columns_to_page(self):
        """Fit all visible columns to the table viewport width without horizontal scroll, keeping them 100% interactive."""
        col_count = self.table.columnCount()
        if col_count == 0:
            return

        visible_cols = [c for c in range(col_count) if not self.table.isColumnHidden(c)]
        if not visible_cols:
            return

        viewport_w = self.table.viewport().width()
        if viewport_w < 300:
            viewport_w = max(self.table.width() - 25, 850)

        weights = getattr(self, "_current_col_weights", None)
        if not weights or len(weights) != col_count:
            weights = {c: self.table.columnWidth(c) if self.table.columnWidth(c) > 0 else 100 for c in range(col_count)}

        total_weight = sum(weights.get(c, 100) for c in visible_cols)
        if total_weight <= 0:
            total_weight = len(visible_cols) * 100

        self._is_programmatic_resize = True
        try:
            allocated = 0
            for i, c in enumerate(visible_cols):
                if i == len(visible_cols) - 1:
                    rem = max(viewport_w - allocated, 40)
                    self.table.setColumnWidth(c, rem)
                else:
                    w = max(int(viewport_w * (weights.get(c, 100) / total_weight)), 35)
                    self.table.setColumnWidth(c, w)
                    allocated += w
        finally:
            self._is_programmatic_resize = False

    def _on_section_resized(self, logicalIndex, oldSize, newSize):
        if not getattr(self, "_is_programmatic_resize", False):
            self._user_resized_columns = True

    def _show_header_context_menu(self, pos):
        col = self.table.horizontalHeader().logicalIndexAt(pos)
        menu = QMenu(self)

        act_fit = menu.addAction("Auto-Fit Columns to Page (سائز صفحہ کے مطابق کریں)")
        act_fit.triggered.connect(self._on_user_fit_columns)

        if 0 <= col < self.table.columnCount():
            col_name = self.table.horizontalHeaderItem(col).text() if self.table.horizontalHeaderItem(col) else f"Column {col+1}"
            act_hide = menu.addAction(f"Hide Column '{col_name}' (یہ کالم چھپائیں)")
            act_hide.triggered.connect(lambda _, c=col: self._hide_column(c))

        hidden_cols = [c for c in range(self.table.columnCount()) if self.table.isColumnHidden(c)]
        if hidden_cols:
            act_show_all = menu.addAction("Show All Hidden Columns (تمام کالم دکھائیں)")
            act_show_all.triggered.connect(self._show_all_columns)

        menu.exec(self.table.horizontalHeader().mapToGlobal(pos))

    def _hide_column(self, col: int):
        self.table.setColumnHidden(col, True)
        self.fit_columns_to_page()

    def _show_all_columns(self):
        for c in range(self.table.columnCount()):
            self.table.setColumnHidden(c, False)
        self.fit_columns_to_page()

    def _on_user_fit_columns(self):
        self._user_resized_columns = False
        self.fit_columns_to_page()
        self.lbl_status.setText("Columns adjusted to fit window width.")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "inner_container") and hasattr(self, "main_scroll"):
            vw = self.main_scroll.viewport().width()
            if vw > 100:
                self.inner_container.setFixedWidth(vw)
        if not getattr(self, "_user_resized_columns", False):
            if hasattr(self, "table") and self.table.columnCount() > 0:
                self.fit_columns_to_page()

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "inner_container") and hasattr(self, "main_scroll"):
            vw = self.main_scroll.viewport().width()
            if vw > 100:
                self.inner_container.setFixedWidth(vw)
        self.fit_columns_to_page()

    def _set_item(self, row: int, col: int, text: str, align=Qt.AlignLeft, bold=False):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(align | Qt.AlignVCenter)
        item.setToolTip(str(text))
        if bold:
            item.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.table.setItem(row, col, item)

    def _set_currency(self, row: int, col: int, val: float, color: str = None):
        if not val or val == 0:
            text = "0.00"
            c = "#64748B"
        elif val < 0:
            text = f"-Rs. {abs(val):,.2f}"
            c = color or "#DC2626"
        else:
            text = f"Rs. {val:,.2f}"
            c = color or "#15803D"

        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        item.setForeground(Qt.GlobalColor.black)
        item.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.table.setItem(row, col, item)

    def _set_status_badge(self, row: int, col: int, status: str):
        item = QTableWidgetItem(str(status))
        item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        item.setFont(QFont("Segoe UI", 9, QFont.Bold))

        if status in ("RECEIVABLE", "AKRAJAT"):
            item.setBackground(Qt.GlobalColor.red)
        elif status in ("PAYABLE", "ADVANCE", "AMDAN", "CREDIT"):
            item.setBackground(Qt.GlobalColor.green)
        self.table.setItem(row, col, item)

    def _apply_client_filter(self, text: str):
        search = text.lower().strip()
        for r in range(self.table.rowCount()):
            match = False
            if not search:
                match = True
            else:
                for c in range(self.table.columnCount()):
                    it = self.table.item(r, c)
                    if it and search in it.text().lower():
                        match = True
                        break
            self.table.setRowHidden(r, not match)

    def _on_table_double_clicked(self, index):
        r = index.row()
        if self.current_mode in (self.MODE_CUSTOMER, self.MODE_LABOUR, self.MODE_OTHER):
            it = self.table.item(r, 0)
            if it:
                acc_id = it.text().strip()
                f_date = self.dt_from.date().toPython()
                t_date = self.dt_to.date().toPython()
                data = LedgerService.calculate_worker_ledger(acc_id, f_date, t_date)
                if data:
                    dlg = LedgerReportWindow(data, from_date=f_date, to_date=t_date, parent=self)
                    dlg.exec()
                    return

    # -------------------------------------------------------------------------
    # REPORTING & ACTIONS
    # -------------------------------------------------------------------------
    def _on_print_report(self):
        f_date = self.dt_from.date().toPython()
        t_date = self.dt_to.date().toPython()

        # Check if individual account mode is active
        if (self.current_mode in (self.MODE_CUSTOMER, self.MODE_LABOUR) and self.rb_individual.isChecked()) or \
           (self.current_mode == self.MODE_OTHER and self.cmb_account.isVisible() and self.cmb_account.currentData() not in (None, "All")):
            wid = self.cmb_account.currentData()
            if wid and wid != "All":
                data = LedgerService.calculate_worker_ledger(wid, f_date, t_date)
                if data:
                    dlg = LedgerReportWindow(data, from_date=f_date, to_date=t_date, parent=self)
                    dlg.exec()
                    return

        cols = []
        for c in range(self.table.columnCount()):
            header = self.table.horizontalHeaderItem(c).text() if self.table.horizontalHeaderItem(c) else f"Col {c}"
            cols.append({
                "header": header,
                "key": f"_col_{c}",
                "align": "right" if ("Rs." in header or "Qty" in header or "Bal" in header) else "left"
            })

        report_rows = []
        for r in range(self.table.rowCount()):
            if self.table.isRowHidden(r):
                continue
            row_dict = {}
            for c in range(self.table.columnCount()):
                it = self.table.item(r, c)
                row_dict[f"_col_{c}"] = it.text() if it else ""
            report_rows.append(row_dict)

        title_map = {
            self.MODE_CUSTOMER: "All Customers Balance & Sales Summary Report",
            self.MODE_LABOUR: f"Labour Summary Report ({self.cmb_category.currentText()})",
            self.MODE_SALES: "Brick Sales Invoicing Register Report",
            self.MODE_WORK: f"Daily Work & Production Register ({self.cmb_category.currentText()})",
            self.MODE_CASHBOOK: "Amdan & Akrajat (Cashbook) Register Report",
            self.MODE_OTHER: f"{self.cmb_category.currentText()} Accounts Khata Statement"
        }

        kpis = [
            (self.kpi_card_1.findChild(QLabel, "lbl_title").text().rstrip(":"), self.kpi_card_1.findChild(QLabel, "lbl_val").text(), "#2563EB"),
            (self.kpi_card_2.findChild(QLabel, "lbl_title").text().rstrip(":"), self.kpi_card_2.findChild(QLabel, "lbl_val").text(), "#16A34A"),
            (self.kpi_card_3.findChild(QLabel, "lbl_title").text().rstrip(":"), self.kpi_card_3.findChild(QLabel, "lbl_val").text(), "#DC2626"),
            (self.kpi_card_4.findChild(QLabel, "lbl_title").text().rstrip(":"), self.kpi_card_4.findChild(QLabel, "lbl_val").text(), "#D97706"),
        ]

        title = title_map.get(self.current_mode, "Central Register Report")
        dlg = TabularSummaryReportWindow(
            title=title,
            subtitle="Central Registers & Khatas Hub",
            columns=cols,
            rows=report_rows,
            kpi_items=kpis,
            from_date=f_date,
            to_date=t_date,
            parent=self
        )
        dlg.exec()

    def _on_export_csv(self):
        default_name = f"{self.current_mode.lower()}_register_{date.today().strftime('%Y%m%d')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Register to CSV", default_name, "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = [self.table.horizontalHeaderItem(c).text() for c in range(self.table.columnCount())]
                writer.writerow(headers)

                for r in range(self.table.rowCount()):
                    if self.table.isRowHidden(r):
                        continue
                    row_data = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(self.table.columnCount())]
                    writer.writerow(row_data)

            ToastNotification.show_success(self, "Export Successful", f"Register successfully exported to:\n{file_path}")
        except Exception as e:
            ToastNotification.show_error(self, "Export Failed", f"Could not write CSV: {e}")

    def _on_quick_payment(self):
        wid = None
        wname = ""
        sel_row = self.table.currentRow()
        if sel_row >= 0:
            it_id = self.table.item(sel_row, 0)
            it_name = self.table.item(sel_row, 1)
            if it_id and it_id.text().strip():
                wid = it_id.text().strip()
            if it_name and it_name.text().strip():
                wname = it_name.text().strip()

        if not wid and self.cmb_account.isVisible():
            cand_id = self.cmb_account.currentData()
            if cand_id and cand_id != "All":
                wid = cand_id
                wname = self.cmb_account.currentText()

        dlg = RecordPaymentDialog(worker_id=wid or "", worker_name=wname or "", parent=self)
        dlg.payment_saved.connect(self.load_register_data)
        dlg.exec()

    # -------------------------------------------------------------------------
    # STYLING
    # -------------------------------------------------------------------------
    def _input_style(self) -> str:
        is_dark = theme_mgr.is_dark_mode()
        bg = "#1E293B" if is_dark else "#FFFFFF"
        fg = "#F8FAFC" if is_dark else "#0F172A"
        border = "#334155" if is_dark else "#CBD5E1"
        sel_bg = "#2563EB" if is_dark else "#EFF6FF"
        sel_fg = "#FFFFFF" if is_dark else "#1D4ED8"
        hover_bg = "#334155" if is_dark else "#F1F5F9"
        return (
            f"QComboBox {{ background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            f"border-radius: 5px; padding: 3px 8px; font-size: 11px; font-weight: 600; min-height: 24px; }} "
            f"QComboBox:focus {{ border: 2px solid #2563EB; }} "
            f"QComboBox QAbstractItemView {{ "
            f"background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            f"selection-background-color: {sel_bg}; selection-color: {sel_fg}; outline: none; padding: 2px; }} "
            f"QComboBox QAbstractItemView::item {{ min-height: 26px; padding: 4px 8px; background-color: {bg}; color: {fg}; }} "
            f"QComboBox QAbstractItemView::item:hover {{ background-color: {hover_bg}; }} "
            f"QComboBox QAbstractItemView::item:selected {{ background-color: {sel_bg}; color: {sel_fg}; font-weight: 600; }}"
        )

    def _date_input_style(self) -> str:
        is_dark = theme_mgr.is_dark_mode()
        bg = "#1E293B" if is_dark else "#FFFFFF"
        fg = "#F8FAFC" if is_dark else "#0F172A"
        border = "#334155" if is_dark else "#CBD5E1"
        return (
            f"QDateEdit {{ background-color: {bg}; color: {fg}; border: 1px solid {border}; "
            f"border-radius: 5px; padding: 3px 6px; font-size: 11.5px; font-weight: 600; min-height: 26px; }} "
            f"QDateEdit:focus {{ border: 2px solid #2563EB; }}"
        )

    def _preset_btn_style(self) -> str:
        return (
            "QPushButton { background-color: #F1F5F9; color: #475569; font-weight: 600; font-size: 10.5px; "
            "border: 1px solid #CBD5E1; border-radius: 4px; padding: 3px 8px; } "
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }"
        )

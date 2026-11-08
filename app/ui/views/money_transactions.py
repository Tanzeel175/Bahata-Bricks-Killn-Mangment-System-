import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QScrollArea, QMessageBox, QGroupBox, QCheckBox, QDialog, QRadioButton, QButtonGroup,
    QSizePolicy
)
from PySide6.QtCore import Qt, QDate, Signal, QTimer, QByteArray, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

from app.services.money_transaction_service import MoneyTransactionService
from app.services.ledger_service import LedgerService
from app.ui.components.formatted_inputs import CurrencyEdit
from app.ui.components.toast import ToastNotification
from app.ui.views.voucher_window import VoucherWindow
from app.security.session import current_session
from app.ui.styles import configure_date_edit
from app.ui.theme_manager import theme_mgr

logger = logging.getLogger(__name__)

_SVG_PRINT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="6 9 6 2 18 2 18 9"></polyline>
  <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
  <rect x="6" y="14" width="12" height="8"></rect>
</svg>"""

_SVG_EDIT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
</svg>"""

_SVG_DELETE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <polyline points="3 6 5 6 21 6"></polyline>
  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
  <line x1="10" y1="11" x2="10" y2="17"></line>
  <line x1="14" y1="11" x2="14" y2="17"></line>
</svg>"""


def _create_svg_icon(svg_text: str, size: int = 14) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return QIcon(pix)


class CashbookReportFilterDialog(QDialog):
    """Filter dialog for generating full A4 Cashbook / Amdan / Akrajat report."""

    def __init__(self, parent=None, default_type: str = "ALL"):
        super().__init__(parent)
        self.setWindowTitle("Cashbook Report Options (کیش بک رپورٹ فلٹرز)")
        self.setFixedWidth(460)
        self.selected_from_date = None
        self.selected_to_date = None
        self.selected_type = "ALL"  # "ALL", "RECEIPT", "PAYMENT"
        self._init_ui(default_type)

    def _init_ui(self, default_type: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        # Header banner
        hdr_frame = QFrame()
        is_dark = theme_mgr.is_dark_mode()
        hdr_bg = "#1E293B" if is_dark else "#EFF6FF"
        hdr_border = "#334155" if is_dark else "#BFDBFE"
        hdr_frame.setStyleSheet(f"background-color: {hdr_bg}; border: 1px solid {hdr_border}; border-radius: 6px; padding: 10px;")
        h_layout = QVBoxLayout(hdr_frame)
        h_layout.setContentsMargins(4, 2, 4, 2)
        h_layout.setSpacing(2)

        title = QLabel("Cashbook & Financial Statement Report")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #1E3A8A; border: none;")
        subtitle = QLabel("Choose date range and whether to view Amdan (آمدن), Akrajat (اخراجات), or Full Cashbook.")
        subtitle.setStyleSheet("font-size: 11.5px; color: #475569; border: none;")
        h_layout.addWidget(title)
        h_layout.addWidget(subtitle)
        layout.addWidget(hdr_frame)

        # 1. Transaction Type Selection Group
        type_group = QGroupBox("Select Report Type (رپورٹ کی قسم)")
        type_layout = QVBoxLayout(type_group)
        type_layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)

        self.rb_all = QRadioButton("Full Cashbook (آمدن اور اخراجات دونوں)")
        self.rb_amdan = QRadioButton("Amdan Only / Receipts (صرف آمدن کی تفصیل)")
        self.rb_akrajat = QRadioButton("Akrajat Only / Payments (صرف اخراجات کی تفصیل)")

        self.btn_group.addButton(self.rb_all, 0)
        self.btn_group.addButton(self.rb_amdan, 1)
        self.btn_group.addButton(self.rb_akrajat, 2)

        type_layout.addWidget(self.rb_all)
        type_layout.addWidget(self.rb_amdan)
        type_layout.addWidget(self.rb_akrajat)

        if default_type == "RECEIPT":
            self.rb_amdan.setChecked(True)
        elif default_type == "PAYMENT":
            self.rb_akrajat.setChecked(True)
        else:
            self.rb_all.setChecked(True)

        layout.addWidget(type_group)

        # 2. Date Range Selection Group
        date_group = QGroupBox("Select Date Range (تاریخ کی حد)")
        date_layout = QVBoxLayout(date_group)
        date_layout.setSpacing(10)

        d_grid = QGridLayout()
        d_grid.setSpacing(8)

        lbl_from = QLabel("From Date (شروع تاریخ):")
        lbl_from.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569;")
        self.dt_from = QDateEdit()
        configure_date_edit(self.dt_from)

        lbl_to = QLabel("To Date (آخری تاریخ):")
        lbl_to.setStyleSheet("font-weight: 600; font-size: 12px; color: #475569;")
        self.dt_to = QDateEdit()
        configure_date_edit(self.dt_to)

        today = date.today()
        # Default from 1st of month to today
        self.dt_from.setDate(QDate(today.year, today.month, 1))
        self.dt_to.setDate(QDate(today.year, today.month, today.day))

        d_grid.addWidget(lbl_from, 0, 0)
        d_grid.addWidget(self.dt_from, 0, 1)
        d_grid.addWidget(lbl_to, 1, 0)
        d_grid.addWidget(self.dt_to, 1, 1)
        date_layout.addLayout(d_grid)

        # Quick Preset Buttons
        presets_layout = QHBoxLayout()
        presets_layout.setSpacing(6)

        def make_preset_btn(text, slot):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton { background-color: #F1F5F9; color: #334155; font-size: 11px; font-weight: 600; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; }
                QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }
            """)
            btn.clicked.connect(slot)
            return btn

        presets_layout.addWidget(make_preset_btn("Today", self._set_today))
        presets_layout.addWidget(make_preset_btn("This Month", self._set_this_month))
        presets_layout.addWidget(make_preset_btn("Last 30 Days", self._set_last_30_days))
        presets_layout.addWidget(make_preset_btn("This Year", self._set_this_year))
        date_layout.addLayout(presets_layout)

        layout.addWidget(date_group)

        # Action Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setMinimumHeight(34)
        self.btn_cancel.setStyleSheet("""
            QPushButton { background-color: #E2E8F0; color: #475569; font-weight: 700; border-radius: 5px; padding: 0 16px; border: none; }
            QPushButton:hover { background-color: #CBD5E1; color: #0F172A; }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        self.btn_generate = QPushButton("Generate A4 Report")
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.setMinimumHeight(34)
        self.btn_generate.setStyleSheet("""
            QPushButton { background-color: #16A34A; color: #FFFFFF; font-weight: 700; border-radius: 5px; padding: 0 20px; border: 1px solid #15803D; }
            QPushButton:hover { background-color: #15803D; }
        """)
        self.btn_generate.clicked.connect(self._on_generate)
        btn_row.addWidget(self.btn_generate)

        layout.addLayout(btn_row)

    def _set_today(self):
        t = date.today()
        self.dt_from.setDate(QDate(t.year, t.month, t.day))
        self.dt_to.setDate(QDate(t.year, t.month, t.day))

    def _set_this_month(self):
        t = date.today()
        self.dt_from.setDate(QDate(t.year, t.month, 1))
        self.dt_to.setDate(QDate(t.year, t.month, t.day))

    def _set_last_30_days(self):
        from datetime import timedelta
        t = date.today()
        past = t - timedelta(days=30)
        self.dt_from.setDate(QDate(past.year, past.month, past.day))
        self.dt_to.setDate(QDate(t.year, t.month, t.day))

    def _set_this_year(self):
        t = date.today()
        self.dt_from.setDate(QDate(t.year, 1, 1))
        self.dt_to.setDate(QDate(t.year, t.month, t.day))

    def _on_generate(self):
        q_from = self.dt_from.date()
        q_to = self.dt_to.date()
        f_date = date(q_from.year(), q_from.month(), q_from.day())
        t_date = date(q_to.year(), q_to.month(), q_to.day())

        if f_date > t_date:
            QMessageBox.warning(self, "Invalid Date Range", "From Date cannot be later than To Date.")
            return

        self.selected_from_date = f_date
        self.selected_to_date = t_date

        if self.rb_amdan.isChecked():
            self.selected_type = "RECEIPT"
        elif self.rb_akrajat.isChecked():
            self.selected_type = "PAYMENT"
        else:
            self.selected_type = "ALL"

        self.accept()


class MoneyTransactionsView(QWidget):
    """
    Unified Cash Transaction / Amdan & Akrajat Management Workspace.
    Smooth Scrollable Vertical Layout:
    - Top: Real-Time Cash KPI Cards (Cash in Hand, Total Amdan, Total Akrajat, Bank Net)
    - Upper Section: Full-Width Transaction Entry Form with High-Contrast Segmented Mode Selector
    - Lower Section: Full-Width Amdan & Akrajat Register (History, Multi-Filters & Vouchers)
    """

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_txn_id: Optional[int] = None
        self.is_edit_mode: bool = False
        self.current_txn_type: str = "RECEIPT"  # "RECEIPT" or "PAYMENT"
        self._ignore_signals: bool = False

        self._init_ui()
        self.refresh_all_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. OUTER SCROLL AREA ENCLOSING ENTIRE WORKSPACE (Guarantees zero horizontal panning)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background-color: #F1F5F9; width: 10px; margin: 0px; border-radius: 5px; } "
            "QScrollBar::handle:vertical { background-color: #CBD5E1; min-height: 30px; border-radius: 5px; } "
            "QScrollBar::handle:vertical:hover { background-color: #94A3B8; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } "
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
        )

        container = QWidget()
        container.setObjectName("cashbookContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 10)
        container_layout.setSpacing(14)

        # 2. TOP TITLE HEADER (Inside container so it wraps cleanly without forcing min-width)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 2)
        top_bar.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        self.lbl_main_title = QLabel("Cash Transactions & Cashbook")
        self.lbl_main_title.setStyleSheet("font-size: 19px; font-weight: 800; border: none; background: transparent;")

        # Heading Urdu Badge (Main Section Identifier)
        self.lbl_urdu_badge = QLabel("نقد لین دین اور روزنامچہ")
        self.lbl_urdu_badge.setStyleSheet(
            "border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 700;"
        )
        title_row.addWidget(self.lbl_main_title)
        title_row.addWidget(self.lbl_urdu_badge)
        title_row.addStretch()
        title_box.addLayout(title_row)

        self.lbl_sub_desc = QLabel("Unified financial movement & auto-reconciled double-entry ledger")
        self.lbl_sub_desc.setStyleSheet("font-size: 11.5px; border: none; background: transparent;")
        title_box.addWidget(self.lbl_sub_desc)

        top_bar.addLayout(title_box)
        top_bar.addStretch()

        # Top Right Actions: Refresh, A4 Cashbook Journal, Cash Flow Summary
        self.btn_refresh_all = QPushButton("↻  Refresh")
        self.btn_refresh_all.setMinimumHeight(32)
        self.btn_refresh_all.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_all.clicked.connect(self.refresh_all_data)
        top_bar.addWidget(self.btn_refresh_all)

        self.btn_open_a4_top = QPushButton("🖨  A4 Journal")
        self.btn_open_a4_top.setMinimumHeight(32)
        self.btn_open_a4_top.setCursor(Qt.PointingHandCursor)
        self.btn_open_a4_top.clicked.connect(self._open_a4_report)
        top_bar.addWidget(self.btn_open_a4_top)

        self.btn_summary_top = QPushButton("📊  Summary")
        self.btn_summary_top.setMinimumHeight(32)
        self.btn_summary_top.setCursor(Qt.PointingHandCursor)
        self.btn_summary_top.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: #FFFFFF; font-weight: 700; font-size: 11.5px; "
            "border-radius: 6px; padding: 0 14px; border: none; } "
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_summary_top.clicked.connect(self._open_a4_report)
        top_bar.addWidget(self.btn_summary_top)

        container_layout.addLayout(top_bar)

        # 3. REAL-TIME CASH SUMMARY KPI CARDS (4-Column Flexible Row)
        kpi_layout = QHBoxLayout()
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(10)

        self.card_cash = self._create_kpi_card(
            category="LIQUIDITY POOL",
            title="Cash in Hand",
            val="Rs. 0.00",
            badge_text="● Safe Reserve",
            accent_color="#15803D",
            badge_bg="#DCFCE7",
            badge_fg="#15803D",
            icon_text="💵",
            card_type="cash"
        )
        self.card_amdan = self._create_kpi_card(
            category="TODAY'S INFLOW",
            title="Total Receipts",
            val="Rs. 0.00",
            badge_text="14 Receipts",
            accent_color="#1D4ED8",
            badge_bg="#EFF6FF",
            badge_fg="#1D4ED8",
            icon_text="↓",
            card_type="amdan"
        )
        self.card_akrajat = self._create_kpi_card(
            category="TODAY'S OUTFLOW",
            title="Total Payments",
            val="Rs. 0.00",
            badge_text="7 Disbursements",
            accent_color="#B45309",
            badge_bg="#FEF3C7",
            badge_fg="#B45309",
            icon_text="↑",
            card_type="akrajat"
        )
        self.card_bank = self._create_kpi_card(
            category="CLEARING ACCOUNTS",
            title="Bank Clearance",
            val="Rs. 0.00",
            badge_text="HBL Settled",
            accent_color="#4338CA",
            badge_bg="#EEF2FF",
            badge_fg="#4338CA",
            icon_text="🏛",
            card_type="bank"
        )

        kpi_layout.addWidget(self.card_cash)
        kpi_layout.addWidget(self.card_amdan)
        kpi_layout.addWidget(self.card_akrajat)
        kpi_layout.addWidget(self.card_bank)
        container_layout.addLayout(kpi_layout)

        # Connect to theme changes
        theme_mgr.theme_changed.connect(self._on_theme_changed)

        # =========================================================================
        # 4. UPPER SECTION: TRANSACTION ENTRY FORM CARD
        # =========================================================================
        is_dark = theme_mgr.is_dark_mode()
        self.form_card = QFrame()
        self.form_card.setObjectName("entry_form_card")
        init_card_bg = "#1E293B" if is_dark else "#FFFFFF"
        init_border = "#334155" if is_dark else "#E2E8F0"
        self.form_card.setStyleSheet(
            f"#entry_form_card {{ background-color: {init_card_bg}; border: 1px solid {init_border}; border-radius: 12px; }}"
        )

        form_main_layout = QVBoxLayout(self.form_card)
        form_main_layout.setContentsMargins(20, 16, 20, 18)
        form_main_layout.setSpacing(12)

        # Header strip: Left Accent Bar + Title & Subtitle | Right Mode Selector
        form_header = QHBoxLayout()
        form_header.setContentsMargins(0, 0, 0, 2)
        form_header.setSpacing(10)

        self.form_accent_bar = QFrame()
        self.form_accent_bar.setFixedSize(4, 22)
        self.form_accent_bar.setStyleSheet("background-color: #2563EB; border-radius: 2px;")
        form_header.addWidget(self.form_accent_bar)

        f_title_box = QVBoxLayout()
        f_title_box.setSpacing(2)
        self.lbl_form_mode = QLabel("New Receipt Voucher (Amdan)")
        mode_col = "#FFFFFF" if is_dark else "#0F172A"
        sub_col = "#E2E8F0" if is_dark else "#64748B"
        self.lbl_form_mode.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {mode_col}; border: none; background: transparent;")
        self.lbl_form_sub = QLabel("Record counterparty receipts or customer advances")
        self.lbl_form_sub.setStyleSheet(f"font-size: 11.5px; color: {sub_col}; border: none; background: transparent;")
        f_title_box.addWidget(self.lbl_form_mode)
        f_title_box.addWidget(self.lbl_form_sub)
        form_header.addLayout(f_title_box)

        form_header.addStretch()

        # HIGH-CONTRAST SEGMENTED TOGGLE BUTTONS FOR AMDAN VS AKRAJAT (Headings in Urdu)
        mode_box = QHBoxLayout()
        mode_box.setSpacing(6)

        self.btn_type_amdan = QPushButton("↓  Receipt (آمدن)")
        self.btn_type_amdan.setFixedHeight(34)
        self.btn_type_amdan.setCursor(Qt.PointingHandCursor)
        self.btn_type_amdan.clicked.connect(lambda: self._set_transaction_type("RECEIPT"))
        mode_box.addWidget(self.btn_type_amdan)

        self.btn_type_akrajat = QPushButton("↑  Payment (اخراجات)")
        self.btn_type_akrajat.setFixedHeight(34)
        self.btn_type_akrajat.setCursor(Qt.PointingHandCursor)
        self.btn_type_akrajat.clicked.connect(lambda: self._set_transaction_type("PAYMENT"))
        mode_box.addWidget(self.btn_type_akrajat)

        form_header.addLayout(mode_box)
        form_main_layout.addLayout(form_header)

        # LIVE KHATA POSITION BANNER STRIP
        self.khata_alert_box = QFrame()
        self.khata_alert_box.setObjectName("khata_alert_box")
        khata_layout = QHBoxLayout(self.khata_alert_box)
        khata_layout.setContentsMargins(6, 2, 6, 2)
        khata_layout.setSpacing(8)

        self.info_icon = QLabel("ⓘ")
        self.info_icon.setStyleSheet("font-weight: 900; font-size: 14px; border: none; background: transparent;")
        khata_layout.addWidget(self.info_icon)

        self.lbl_balance_text = QLabel("LIVE KHATA POSITION: Select an account to view live position")
        self.lbl_balance_text.setStyleSheet("font-size: 12px; font-weight: 700; border: none; background: transparent;")
        khata_layout.addWidget(self.lbl_balance_text)
        khata_layout.addStretch()

        self.btn_view_khata = QPushButton("Open Full Ledger ↗")
        self.btn_view_khata.setCursor(Qt.PointingHandCursor)
        self.btn_view_khata.clicked.connect(self._open_account_khata)
        khata_layout.addWidget(self.btn_view_khata)

        form_main_layout.addWidget(self.khata_alert_box)

        # 4-Column Grid for Form Fields (Clean English Labels)
        f_grid = QGridLayout()
        f_grid.setHorizontalSpacing(14)
        f_grid.setVerticalSpacing(8)

        def make_field_lbl(text):
            lbl = QLabel(text)
            lbl.setProperty("class", "form-field-label")
            is_d = theme_mgr.is_dark_mode()
            lbl_col = "#FFFFFF" if is_d else "#334155"
            lbl.setStyleSheet(f"font-weight: 700; font-size: 11.5px; color: {lbl_col}; border: none; background: transparent;")
            return lbl

        # Row 0: Labels for Row 1
        f_grid.addWidget(make_field_lbl("Voucher #:"), 0, 0)
        f_grid.addWidget(make_field_lbl("Date *:"), 0, 1)
        f_grid.addWidget(make_field_lbl("Account Category *:"), 0, 2)
        f_grid.addWidget(make_field_lbl("Counterparty / Khata *:"), 0, 3)

        # Row 1: Inputs
        v_box = QHBoxLayout()
        v_box.setContentsMargins(0, 0, 0, 0)
        v_box.setSpacing(0)
        self.txt_txn_no = QLineEdit()
        self.txt_txn_no.setPlaceholderText("Auto")
        self.txt_txn_no.setFixedHeight(36)
        self.txt_txn_no.returnPressed.connect(self._on_txn_no_entered)
        v_box.addWidget(self.txt_txn_no)

        self.lbl_lock = QLabel("🔒")
        self.lbl_lock.setFixedHeight(36)
        self.lbl_lock.setFixedWidth(30)
        self.lbl_lock.setAlignment(Qt.AlignCenter)
        v_box.addWidget(self.lbl_lock)
        f_grid.addLayout(v_box, 1, 0)

        self.dt_txn_date = QDateEdit(QDate.currentDate())
        configure_date_edit(self.dt_txn_date, min_width=110, min_height=36)
        f_grid.addWidget(self.dt_txn_date, 1, 1)

        self.cmb_category = QComboBox()
        self.cmb_category.setFixedHeight(36)
        self.cmb_category.currentIndexChanged.connect(self._on_category_changed)
        f_grid.addWidget(self.cmb_category, 1, 2)

        self.cmb_account = QComboBox()
        self.cmb_account.setFixedHeight(36)
        self.cmb_account.currentIndexChanged.connect(self._on_account_changed)
        f_grid.addWidget(self.cmb_account, 1, 3)

        # Row 2: Labels for Row 2
        f_grid.addWidget(make_field_lbl("Amount (PKR) *:"), 2, 0)
        f_grid.addWidget(make_field_lbl("Payment Mode:"), 2, 1)
        f_grid.addWidget(make_field_lbl("Bank / Account #:"), 2, 2)
        f_grid.addWidget(make_field_lbl("Cheque / Slip #:"), 2, 3)

        # Row 3: Inputs
        self.txt_amount = CurrencyEdit()
        self.txt_amount.setPlaceholderText("Rs. 0.00")
        self.txt_amount.setFixedHeight(36)
        self.txt_amount.setStyleSheet("font-size: 13.5px; font-weight: 800; padding-left: 10px;")
        f_grid.addWidget(self.txt_amount, 3, 0)

        self.cmb_method = QComboBox()
        self.cmb_method.addItems(["Cash", "Bank Transfer", "Cheque", "Online Transfer", "Other"])
        self.cmb_method.setFixedHeight(36)
        self.cmb_method.currentIndexChanged.connect(self._on_method_changed)
        f_grid.addWidget(self.cmb_method, 3, 1)

        self.txt_bank_acc = QLineEdit()
        self.txt_bank_acc.setPlaceholderText("e.g. HBL - 1245678901 (Optional)")
        self.txt_bank_acc.setFixedHeight(36)
        self.txt_bank_acc.setEnabled(False)
        f_grid.addWidget(self.txt_bank_acc, 3, 2)

        self.txt_cheque = QLineEdit()
        self.txt_cheque.setPlaceholderText("e.g. CHQ-482019 (Optional)")
        self.txt_cheque.setFixedHeight(36)
        self.txt_cheque.setEnabled(False)
        f_grid.addWidget(self.txt_cheque, 3, 3)

        # Row 4: Labels for Row 3
        f_grid.addWidget(make_field_lbl("Reference / Batch #:"), 4, 0)
        f_grid.addWidget(make_field_lbl("Narration / Description:"), 4, 1, 1, 3)

        # Row 5: Inputs
        self.txt_ref = QLineEdit()
        self.txt_ref.setPlaceholderText("e.g. INV-2026-084 or Batch #4")
        self.txt_ref.setFixedHeight(36)
        f_grid.addWidget(self.txt_ref, 5, 0)

        self.cmb_narration = QComboBox()
        self.cmb_narration.setEditable(True)
        self.cmb_narration.setFixedHeight(36)
        self.cmb_narration.lineEdit().setPlaceholderText("Advance paid against 50,000 kacha brick moulding batch...")
        f_grid.addWidget(self.cmb_narration, 5, 1, 1, 3)

        # Row 6: Action row
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 8, 0, 0)
        row_actions.setSpacing(10)

        self.chk_negative_cash = QCheckBox("Authorize Cash Overdraw (Admin Override)")
        self.chk_negative_cash.setStyleSheet("font-size: 11.5px; font-weight: 600; color: #64748B;")
        self.chk_negative_cash.setVisible(current_session.is_admin)
        row_actions.addWidget(self.chk_negative_cash)
        row_actions.addStretch()

        self.btn_clear = QPushButton("Clear Form")
        self.btn_clear.setFixedHeight(36)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #334155; font-weight: 600; font-size: 12.5px; "
            "border-radius: 6px; padding: 0 16px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #F8FAFC; border-color: #94A3B8; }"
        )
        self.btn_clear.clicked.connect(self.clear_form)
        row_actions.addWidget(self.btn_clear)

        # Delete button for edit mode (hidden by default)
        self.btn_delete_form = QPushButton("Delete Transaction")
        self.btn_delete_form.setFixedHeight(36)
        self.btn_delete_form.setCursor(Qt.PointingHandCursor)
        self.btn_delete_form.setStyleSheet(
            "QPushButton { background-color: #EF4444; color: #FFFFFF; font-weight: 800; font-size: 12.5px; "
            "border-radius: 6px; padding: 0 16px; border: none; } "
            "QPushButton:hover { background-color: #DC2626; }"
        )
        self.btn_delete_form.clicked.connect(self._on_delete_current_from_form)
        self.btn_delete_form.setVisible(False)
        row_actions.addWidget(self.btn_delete_form)

        self.btn_print_slip = QPushButton("🖨  Print Slip")
        self.btn_print_slip.setFixedHeight(36)
        self.btn_print_slip.setCursor(Qt.PointingHandCursor)
        self.btn_print_slip.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #334155; font-weight: 600; font-size: 12.5px; "
            "border-radius: 6px; padding: 0 16px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #F8FAFC; border-color: #94A3B8; }"
        )
        self.btn_print_slip.clicked.connect(self._on_print_slip_clicked)
        row_actions.addWidget(self.btn_print_slip)

        self.btn_save = QPushButton("✓  Save Receipt (Amdan)")
        self.btn_save.setFixedHeight(36)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: #FFFFFF; font-weight: 700; font-size: 12.5px; "
            "border-radius: 6px; padding: 0 22px; border: none; } "
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_save.clicked.connect(self._on_save_transaction)
        row_actions.addWidget(self.btn_save)

        f_grid.addLayout(row_actions, 6, 0, 1, 4)

        f_grid.setColumnStretch(0, 1)
        f_grid.setColumnStretch(1, 1)
        f_grid.setColumnStretch(2, 1)
        f_grid.setColumnStretch(3, 1)

        form_main_layout.addLayout(f_grid)
        container_layout.addWidget(self.form_card)

        # =========================================================================
        # 5. LOWER SECTION: RECENT TRANSACTIONS (LAST 5 ENTRIES) & QUICK LOOKUP
        # =========================================================================
        recent_panel = QFrame()
        recent_panel.setObjectName("recent_panel")
        recent_panel.setProperty("class", "card-panel")
        rec_layout = QVBoxLayout(recent_panel)
        rec_layout.setContentsMargins(18, 14, 18, 14)
        rec_layout.setSpacing(12)

        # Header of Lower Panel
        p_hdr = QHBoxLayout()
        lbl_p_title = QLabel("Recent Transactions (Last 5 Entries)")
        lbl_p_title.setProperty("class", "heading-secondary")
        lbl_p_title.setStyleSheet("font-size: 15px; font-weight: 800; border: none;")
        p_hdr.addWidget(lbl_p_title)

        self.lbl_table_count = QLabel("Showing Recent Entries")
        self.lbl_table_count.setProperty("class", "subtext")
        self.lbl_table_count.setStyleSheet("font-size: 12px; font-weight: 700; border: none; margin-left: 8px;")
        p_hdr.addWidget(self.lbl_table_count)
        p_hdr.addStretch()

        self.btn_open_a4_rep = QPushButton("View Full A4 Cashbook Report")
        self.btn_open_a4_rep.setCursor(Qt.PointingHandCursor)
        self.btn_open_a4_rep.setMinimumHeight(34)
        self.btn_open_a4_rep.setProperty("class", "btn-success")
        self.btn_open_a4_rep.clicked.connect(self._open_a4_report)
        p_hdr.addWidget(self.btn_open_a4_rep)
        rec_layout.addLayout(p_hdr)

        # Quick Lookup Bar Card
        lookup_frame = QFrame()
        lookup_frame.setObjectName("lookup_frame")
        lookup_frame.setProperty("class", "card-panel")
        l_layout = QHBoxLayout(lookup_frame)
        l_layout.setContentsMargins(6, 4, 6, 4)
        l_layout.setSpacing(10)

        lbl_l = QLabel("Access Any Transaction by ID or Txn #:")
        lbl_l.setStyleSheet("font-weight: 700; font-size: 12px; border: none;")
        l_layout.addWidget(lbl_l)

        self.txt_lookup = QLineEdit()
        self.txt_lookup.setPlaceholderText("Enter Txn # (e.g. RCT-000005, PAY-000002) or Transaction ID (e.g. 5) to edit / reverse...")
        self.txt_lookup.setMinimumHeight(36)
        self.txt_lookup.setStyleSheet("font-size: 12px;")
        self.txt_lookup.returnPressed.connect(self._on_lookup_transaction)
        l_layout.addWidget(self.txt_lookup, stretch=1)

        self.btn_lookup = QPushButton("Load for Edit")
        self.btn_lookup.setCursor(Qt.PointingHandCursor)
        self.btn_lookup.setMinimumHeight(36)
        self.btn_lookup.setProperty("class", "btn-primary")
        self.btn_lookup.clicked.connect(self._on_lookup_transaction)
        l_layout.addWidget(self.btn_lookup)

        rec_layout.addWidget(lookup_frame)

        # Compact Table for Recent 5 Entries
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Txn #", "Date", "Type", "Category", "Account Name",
            "Amount (PKR)", "Method", "Description", "Ref", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Fixed)
        self.table.setColumnWidth(9, 180)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(240)
        self.table.setMaximumHeight(270)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        rec_layout.addWidget(self.table)

        container_layout.addWidget(recent_panel)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial theme setup
        self._update_form_theme("RECEIPT")

    def _create_kpi_card(
        self,
        category: str,
        title: str,
        val: str,
        badge_text: str,
        accent_color: str,
        badge_bg: str,
        badge_fg: str,
        icon_text: str,
        card_type: str = "cash"
    ) -> QFrame:
        card = QFrame()
        card.setObjectName(f"kpi_card_{card_type}")
        card._category = category
        card._title = title
        card._accent = accent_color
        card._badge_text = badge_text
        card._badge_bg = badge_bg
        card._badge_fg = badge_fg
        card._icon_text = icon_text
        card._card_type = card_type

        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # 1. Top row: Category uppercase and Icon badge
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        lbl_cat = QLabel(category)
        lbl_cat.setObjectName("cat_label")
        top_row.addWidget(lbl_cat)
        top_row.addStretch()

        icon_lbl = QLabel(icon_text)
        icon_lbl.setObjectName("icon_badge")
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setAlignment(Qt.AlignCenter)
        top_row.addWidget(icon_lbl)
        layout.addLayout(top_row)

        # 2. Card Title
        lbl_title = QLabel(title)
        lbl_title.setObjectName("kpi_title")
        layout.addWidget(lbl_title)

        # 3. Value Label
        lbl_val = QLabel(val)
        lbl_val.setObjectName("val_label")
        layout.addWidget(lbl_val)

        # 4. Status pill badge
        bot_row = QHBoxLayout()
        bot_row.setContentsMargins(0, 0, 0, 0)
        lbl_badge = QLabel(badge_text)
        lbl_badge.setObjectName("badge_label")
        bot_row.addWidget(lbl_badge)
        bot_row.addStretch()
        layout.addLayout(bot_row)

        self._apply_kpi_style(card)
        return card

    def _apply_kpi_style(self, card: QFrame):
        is_dark = theme_mgr.is_dark_mode()
        ctype = getattr(card, "_card_type", "cash")

        # Option 2: Ultra-Soft Pastel Tint (50-level) Palette
        if is_dark:
            color_map = {
                "cash": {
                    "bg": "rgba(16, 185, 129, 0.08)",
                    "border": "rgba(16, 185, 129, 0.25)",
                    "title": "#F8FAFC",
                    "cat": "#6EE7B7",
                    "badge_bg": "rgba(16, 185, 129, 0.18)",
                    "badge_fg": "#34D399",
                    "val": "#34D399",
                },
                "amdan": {
                    "bg": "rgba(37, 99, 235, 0.08)",
                    "border": "rgba(59, 130, 246, 0.25)",
                    "title": "#F8FAFC",
                    "cat": "#93C5FD",
                    "badge_bg": "rgba(37, 99, 235, 0.18)",
                    "badge_fg": "#60A5FA",
                    "val": "#60A5FA",
                },
                "akrajat": {
                    "bg": "rgba(245, 158, 11, 0.08)",
                    "border": "rgba(245, 158, 11, 0.25)",
                    "title": "#F8FAFC",
                    "cat": "#FCD34D",
                    "badge_bg": "rgba(245, 158, 11, 0.18)",
                    "badge_fg": "#FBBF24",
                    "val": "#FBBF24",
                },
                "bank": {
                    "bg": "rgba(99, 102, 241, 0.08)",
                    "border": "rgba(99, 102, 241, 0.25)",
                    "title": "#F8FAFC",
                    "cat": "#A5B4FC",
                    "badge_bg": "rgba(99, 102, 241, 0.18)",
                    "badge_fg": "#818CF8",
                    "val": "#818CF8",
                },
            }
        else:
            color_map = {
                "cash": {
                    "bg": "#F0FDF4",
                    "border": "#BBF7D0",
                    "title": "#0F172A",
                    "cat": "#047857",
                    "badge_bg": "#DCFCE7",
                    "badge_fg": "#15803D",
                    "val": "#15803D",
                },
                "amdan": {
                    "bg": "#EFF6FF",
                    "border": "#BFDBFE",
                    "title": "#0F172A",
                    "cat": "#1D4ED8",
                    "badge_bg": "#DBEAFE",
                    "badge_fg": "#1D4ED8",
                    "val": "#1D4ED8",
                },
                "akrajat": {
                    "bg": "#FFFBEB",
                    "border": "#FDE68A",
                    "title": "#0F172A",
                    "cat": "#B45309",
                    "badge_bg": "#FEF3C7",
                    "badge_fg": "#B45309",
                    "val": "#B45309",
                },
                "bank": {
                    "bg": "#EEF2FF",
                    "border": "#C7D2FE",
                    "title": "#0F172A",
                    "cat": "#4338CA",
                    "badge_bg": "#E0E7FF",
                    "badge_fg": "#4338CA",
                    "val": "#4338CA",
                },
            }

        cfg = color_map.get(ctype, color_map["cash"])
        card.setStyleSheet(
            f"QFrame#{card.objectName()} {{ background-color: {cfg['bg']}; border: 1px solid {cfg['border']}; border-radius: 12px; }}"
        )

        lbl_cat = card.findChild(QLabel, "cat_label")
        if lbl_cat:
            lbl_cat.setStyleSheet(
                f"font-size: 9.5px; font-weight: 700; color: {cfg['cat']}; letter-spacing: 0.6px; border: none; background: transparent;"
            )

        icon_lbl = card.findChild(QLabel, "icon_badge")
        if icon_lbl:
            icon_lbl.setStyleSheet(
                f"background-color: {cfg['badge_bg']}; color: {cfg['badge_fg']}; font-weight: 900; font-size: 12px; "
                f"border-radius: 5px; border: none;"
            )

        lbl_title = card.findChild(QLabel, "kpi_title")
        if lbl_title:
            lbl_title.setStyleSheet(
                f"font-size: 12.5px; font-weight: 600; color: {cfg['title']}; border: none; background: transparent;"
            )

        lbl_val = card.findChild(QLabel, "val_label")
        if lbl_val:
            val_col = cfg["val"]
            lbl_val.setStyleSheet(
                f"font-size: 19px; font-weight: 800; color: {val_col}; border: none; background: transparent; margin: 2px 0;"
            )

        lbl_badge = card.findChild(QLabel, "badge_label")
        if lbl_badge:
            lbl_badge.setStyleSheet(
                f"background-color: {cfg['badge_bg']}; color: {cfg['badge_fg']}; border-radius: 9px; "
                f"padding: 2px 8px; font-size: 10px; font-weight: 700; border: none;"
            )

    def _on_theme_changed(self, _theme: str):
        for card in [
            getattr(self, "card_cash", None),
            getattr(self, "card_amdan", None),
            getattr(self, "card_akrajat", None),
            getattr(self, "card_bank", None)
        ]:
            if card:
                self._apply_kpi_style(card)
        self._update_kpi_value_colors()
        self._update_form_theme(getattr(self, "current_txn_type", "RECEIPT"))

    def _update_kpi_value_colors(self):
        """Update text colors of rendered KPI cards without querying the database."""
        is_dark = theme_mgr.is_dark_mode()
        color_rules = [
            ("card_amdan", "#1D4ED8", "#60A5FA"),
            ("card_akrajat", "#B45309", "#FBBF24"),
            ("card_bank", "#4338CA", "#818CF8"),
        ]
        for card_attr, light_col, dark_col in color_rules:
            card = getattr(self, card_attr, None)
            if card:
                lbl = card.findChild(QLabel, "val_label")
                if lbl:
                    col = dark_col if is_dark else light_col
                    lbl.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {col}; border: none; background: transparent; margin: 2px 0;")

        card_cash = getattr(self, "card_cash", None)
        if card_cash:
            lbl = card_cash.findChild(QLabel, "val_label")
            if lbl:
                is_neg = "-" in lbl.text()
                col = ("#F87171" if is_dark else "#DC2626") if is_neg else ("#34D399" if is_dark else "#15803D")
                lbl.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {col}; border: none; background: transparent; margin: 2px 0;")

    def _set_transaction_type(self, txn_type: str):
        if (getattr(self, "is_edit_mode", False) or getattr(self, "current_txn_id", None)) and self.current_txn_type != txn_type:
            self.clear_form()

        self.current_txn_type = txn_type
        self._update_form_theme(txn_type)
        self._load_next_txn_no()
        self._load_narrations()
        self._update_balance_badge()

    def _update_form_theme(self, txn_type: str):
        is_receipt = (txn_type == "RECEIPT")
        is_dark = theme_mgr.is_dark_mode()

        # 1. Top Bar Header & Badges
        if hasattr(self, "lbl_main_title"):
            title_col = "#FFFFFF" if is_dark else "#0F172A"
            self.lbl_main_title.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {title_col}; border: none; background: transparent;")

        if hasattr(self, "lbl_urdu_badge"):
            if is_dark:
                self.lbl_urdu_badge.setStyleSheet(
                    "background-color: rgba(37, 99, 235, 0.2); color: #93C5FD; border: 1px solid #1D4ED8; "
                    "border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 700;"
                )
            else:
                self.lbl_urdu_badge.setStyleSheet(
                    "background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; "
                    "border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: 700;"
                )

        if hasattr(self, "lbl_sub_desc"):
            sub_col = "#E2E8F0" if is_dark else "#64748B"
            self.lbl_sub_desc.setStyleSheet(f"font-size: 11.5px; color: {sub_col}; border: none; background: transparent;")

        # Header utility buttons
        sec_btn_bg = "#1E293B" if is_dark else "#FFFFFF"
        sec_btn_fg = "#FFFFFF" if is_dark else "#334155"
        sec_btn_border = "#334155" if is_dark else "#CBD5E1"
        sec_btn_hover = "#334155" if is_dark else "#F8FAFC"
        top_btn_qss = (
            f"QPushButton {{ background-color: {sec_btn_bg}; color: {sec_btn_fg}; font-weight: 600; font-size: 11.5px; "
            f"border-radius: 6px; padding: 0 12px; border: 1px solid {sec_btn_border}; }} "
            f"QPushButton:hover {{ background-color: {sec_btn_hover}; border-color: #94A3B8; }}"
        )
        if hasattr(self, "btn_refresh_all"):
            self.btn_refresh_all.setStyleSheet(top_btn_qss)
        if hasattr(self, "btn_open_a4_top"):
            self.btn_open_a4_top.setStyleSheet(top_btn_qss)

        # 2. Form Card Container
        card_bg = "#1E293B" if is_dark else "#FFFFFF"
        border_col = "#334155" if is_dark else "#E2E8F0"
        accent_col = "#2563EB" if is_receipt else "#E11D48"

        self.form_card.setStyleSheet(
            f"#entry_form_card {{ background-color: {card_bg}; border: 1px solid {border_col}; border-radius: 12px; }}"
        )

        if hasattr(self, "form_accent_bar"):
            self.form_accent_bar.setStyleSheet(f"background-color: {accent_col}; border-radius: 2px;")

        # 3. Form Header Titles
        if hasattr(self, "lbl_form_mode"):
            mode_color = "#FFFFFF" if is_dark else "#0F172A"
            if self.current_txn_id:
                txn_num = self.txt_txn_no.text().strip() or f"ID #{self.current_txn_id}"
                if current_session.is_admin:
                    self.lbl_form_mode.setText(f"Edit Transaction: {txn_num} (Admin Mode)")
                else:
                    self.lbl_form_mode.setText(f"View Transaction: {txn_num} (Read-Only • Munshi)")
            else:
                self.lbl_form_mode.setText("New Receipt Voucher (Amdan)" if is_receipt else "New Payment Voucher (Akrajat)")
            self.lbl_form_mode.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {mode_color}; border: none; background: transparent;")

        if hasattr(self, "lbl_form_sub"):
            sub_color = "#E2E8F0" if is_dark else "#64748B"
            if self.current_txn_id:
                self.lbl_form_sub.setText("Modify existing ledger transaction")
            else:
                self.lbl_form_sub.setText(
                    "Record counterparty receipts or customer advances" if is_receipt
                    else "Record kiln expenses, labour disbursements, or supplier payments"
                )
            self.lbl_form_sub.setStyleSheet(f"font-size: 11.5px; color: {sub_color}; border: none; background: transparent;")

        # 4. Mode Toggle Buttons (Segmented Receipt vs Payment)
        if hasattr(self, "btn_type_amdan") and hasattr(self, "btn_type_akrajat"):
            inactive_bg = "#1E293B" if is_dark else "#F8FAFC"
            inactive_fg = "#94A3B8" if is_dark else "#475569"
            inactive_border = "#334155" if is_dark else "#CBD5E1"
            inactive_hover = "#334155" if is_dark else "#F1F5F9"

            inactive_qss = (
                f"QPushButton {{ background-color: {inactive_bg}; color: {inactive_fg}; font-weight: 600; font-size: 12.5px; "
                f"border-radius: 6px; padding: 0 16px; border: 1px solid {inactive_border}; }} "
                f"QPushButton:hover {{ background-color: {inactive_hover}; border-color: #94A3B8; }}"
            )

            if is_receipt:
                self.btn_type_amdan.setStyleSheet(
                    "QPushButton { background-color: #2563EB; color: #FFFFFF; font-weight: 700; font-size: 12.5px; "
                    "border-radius: 6px; padding: 0 16px; border: none; } "
                    "QPushButton:hover { background-color: #1D4ED8; }"
                )
                self.btn_type_akrajat.setStyleSheet(inactive_qss)
            else:
                self.btn_type_akrajat.setStyleSheet(
                    "QPushButton { background-color: #E11D48; color: #FFFFFF; font-weight: 700; font-size: 12.5px; "
                    "border-radius: 6px; padding: 0 16px; border: none; } "
                    "QPushButton:hover { background-color: #BE123C; }"
                )
                self.btn_type_amdan.setStyleSheet(inactive_qss)

        # 5. Live Khata Position Banner Strip
        if hasattr(self, "khata_alert_box"):
            if is_dark:
                self.khata_alert_box.setStyleSheet(
                    "#khata_alert_box { background-color: #0F172A; border: 1px solid #1E3A8A; "
                    "border-radius: 8px; padding: 6px 12px; }"
                )
            else:
                self.khata_alert_box.setStyleSheet(
                    "#khata_alert_box { background-color: #EFF6FF; border: 1px solid #BFDBFE; "
                    "border-radius: 8px; padding: 6px 12px; }"
                )

        if hasattr(self, "info_icon"):
            self.info_icon.setStyleSheet(
                f"color: {'#60A5FA' if is_dark else '#2563EB'}; font-weight: 900; font-size: 14px; border: none; background: transparent;"
            )

        if hasattr(self, "btn_view_khata"):
            khata_link_col = "#60A5FA" if is_dark else "#2563EB"
            self.btn_view_khata.setStyleSheet(
                f"QPushButton {{ background: transparent; border: none; color: {khata_link_col}; "
                f"font-weight: 700; font-size: 12px; padding: 2px 6px; }} "
                f"QPushButton:hover {{ text-decoration: underline; }}"
            )

        self._update_balance_badge()

        # 6. Voucher # Input & Lock Indicator
        if hasattr(self, "txt_txn_no") and hasattr(self, "lbl_lock"):
            input_bg = "#0F172A" if is_dark else "#F8FAFC"
            input_border = "#334155" if is_dark else "#CBD5E1"
            input_fg = "#FFFFFF" if is_dark else "#0F172A"
            self.txt_txn_no.setStyleSheet(
                f"QLineEdit {{ font-weight: 800; font-family: Consolas, monospace; font-size: 12.5px; "
                f"background-color: {input_bg}; color: {input_fg}; border: 1px solid {input_border}; "
                f"border-top-left-radius: 6px; border-bottom-left-radius: 6px; padding: 4px 10px; }}"
            )
            self.lbl_lock.setStyleSheet(
                f"background-color: {input_bg}; border: 1px solid {input_border}; border-left: none; "
                f"border-top-right-radius: 6px; border-bottom-right-radius: 6px; font-size: 11px; color: #94A3B8;"
            )

        # 7. Form Field Labels
        lbl_fg = "#FFFFFF" if is_dark else "#334155"
        for lbl in self.form_card.findChildren(QLabel):
            if lbl.property("class") == "form-field-label":
                lbl.setStyleSheet(f"font-weight: 700; font-size: 11.5px; color: {lbl_fg}; border: none; background: transparent;")

        # 8. Secondary Buttons (Clear Form, Print Slip)
        action_btn_qss = (
            f"QPushButton {{ background-color: {sec_btn_bg}; color: {sec_btn_fg}; font-weight: 600; font-size: 12.5px; "
            f"border-radius: 6px; padding: 0 16px; border: 1px solid {sec_btn_border}; }} "
            f"QPushButton:hover {{ background-color: {sec_btn_hover}; border-color: #94A3B8; }}"
        )
        if hasattr(self, "btn_clear"):
            self.btn_clear.setStyleSheet(action_btn_qss)
        if hasattr(self, "btn_print_slip"):
            self.btn_print_slip.setStyleSheet(action_btn_qss)

        # 9. Overdraw Checkbox
        if hasattr(self, "chk_negative_cash"):
            chk_col = "#94A3B8" if is_dark else "#64748B"
            self.chk_negative_cash.setStyleSheet(f"font-size: 11.5px; font-weight: 600; color: {chk_col};")

        # 10. Update Save Button
        if hasattr(self, "btn_save"):
            save_bg = "#2563EB" if is_receipt else "#E11D48"
            save_hover = "#1D4ED8" if is_receipt else "#BE123C"
            if self.current_txn_id:
                if current_session.is_admin:
                    self.btn_save.setEnabled(True)
                    self.btn_save.setText("Update Receipt (Amdan)" if is_receipt else "Update Payment (Akrajat)")
                    self.btn_save.setStyleSheet(
                        f"QPushButton {{ background-color: {save_bg}; color: #FFFFFF; font-weight: 700; font-size: 12.5px; "
                        f"border-radius: 6px; padding: 0 24px; border: none; }} "
                        f"QPushButton:hover {{ background-color: {save_hover}; }}"
                    )
                else:
                    self.btn_save.setEnabled(False)
                    self.btn_save.setText("View Only (Admin Required to Edit)")
                    self.btn_save.setStyleSheet(
                        "QPushButton { background-color: #94A3B8; color: #FFFFFF; font-weight: 700; font-size: 12px; "
                        "border-radius: 6px; padding: 0 20px; border: none; }"
                    )
            else:
                self.btn_save.setEnabled(True)
                self.btn_save.setText("✓  Save Receipt (Amdan)" if is_receipt else "✓  Save Payment (Akrajat)")
                self.btn_save.setStyleSheet(
                    f"QPushButton {{ background-color: {save_bg}; color: #FFFFFF; font-weight: 700; font-size: 12.5px; "
                    f"border-radius: 6px; padding: 0 24px; border: none; }} "
                    f"QPushButton:hover {{ background-color: {save_hover}; }}"
                )

    def _on_print_slip_clicked(self):
        """Preview and print voucher for current entry or selection."""
        if getattr(self, "current_txn_id", None):
            txn_data = MoneyTransactionService.get_transaction_by_id(self.current_txn_id)
            if txn_data:
                dlg = VoucherWindow(txn_data, self)
                dlg.exec()
                return

        amt = self.txt_amount.get_amount()
        if amt <= 0:
            ToastNotification.show_warning(self, "Empty Amount", "Please enter an amount and select an account to preview/print the slip.")
            return

        acc_name = self.cmb_account.currentText()
        cat_name = self.cmb_category.currentText()
        temp_data = {
            "TransactionNo": self.txt_txn_no.text().strip() or "RCT-000001",
            "TransactionDate": self.dt_txn_date.date().toPython(),
            "TransactionType": self.current_txn_type,
            "Amount": amt,
            "AccountID": self.cmb_account.currentData() or "WRK-0001",
            "AccountName": acc_name,
            "CategoryName": cat_name,
            "PaymentMethod": self.cmb_method.currentText(),
            "Description": self.cmb_narration.currentText().strip() or "Cash voucher",
            "ReferenceNo": self.txt_ref.text().strip() or ""
        }
        dlg = VoucherWindow(temp_data, self)
        dlg.exec()

    def _on_method_changed(self):
        method = self.cmb_method.currentText()
        is_bank = not method.startswith("Cash")
        self.txt_bank_acc.setEnabled(is_bank)
        self.txt_cheque.setEnabled(is_bank)
        if not is_bank:
            self.txt_bank_acc.clear()
            self.txt_cheque.clear()

    def _load_next_txn_no(self):
        if not self.current_txn_id:
            next_no = MoneyTransactionService.get_next_transaction_no(self.current_txn_type)
            self.txt_txn_no.setText(next_no)

    def _load_narrations(self):
        current_text = self.cmb_narration.currentText()
        suggestions = MoneyTransactionService.get_suggested_narrations(self.current_txn_type)

        self._ignore_signals = True
        self.cmb_narration.clear()
        self.cmb_narration.addItems(suggestions)
        if current_text:
            self.cmb_narration.setEditText(current_text)
        else:
            self.cmb_narration.setEditText("")
        self._ignore_signals = False

    def refresh_all_data(self):
        """Reload categories, accounts, cash summary KPI, and register table."""
        self._load_categories()
        self._load_next_txn_no()
        self._load_narrations()
        self.refresh_cash_kpi()
        self._load_register_table()

    def refresh_cash_kpi(self):
        """Update KPI metrics at top with high-contrast semantic values."""
        try:
            summary = MoneyTransactionService.get_cash_summary()
            is_dark = theme_mgr.is_dark_mode()

            net_cash = summary.get("net_cash", 0.0)
            if net_cash >= 0:
                cash_color = "#34D399" if is_dark else "#15803D"
            else:
                cash_color = "#F87171" if is_dark else "#DC2626"
            
            lbl_cash = self.card_cash.findChild(QLabel, "val_label")
            if lbl_cash:
                lbl_cash.setText(f"Rs. {net_cash:,.2f}")
                lbl_cash.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {cash_color}; border: none; background: transparent; margin: 2px 0;")

            amdan_val = summary.get("cash_amdan", 0.0)
            lbl_amdan = self.card_amdan.findChild(QLabel, "val_label")
            if lbl_amdan:
                lbl_amdan.setText(f"Rs. {amdan_val:,.2f}")
                amdan_color = "#60A5FA" if is_dark else "#1D4ED8"
                lbl_amdan.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {amdan_color}; border: none; background: transparent; margin: 2px 0;")

            akrajat_val = summary.get("cash_akrajat", 0.0)
            lbl_akrajat = self.card_akrajat.findChild(QLabel, "val_label")
            if lbl_akrajat:
                lbl_akrajat.setText(f"Rs. {akrajat_val:,.2f}")
                akrajat_color = "#FBBF24" if is_dark else "#B45309"
                lbl_akrajat.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {akrajat_color}; border: none; background: transparent; margin: 2px 0;")

            bank_val = summary.get("net_bank", 0.0)
            lbl_bank = self.card_bank.findChild(QLabel, "val_label")
            if lbl_bank:
                lbl_bank.setText(f"Rs. {bank_val:,.2f}")
                bank_color = "#818CF8" if is_dark else "#4338CA"
                lbl_bank.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {bank_color}; border: none; background: transparent; margin: 2px 0;")
        except Exception as e:
            logger.warning("Error refreshing cash KPI: %s", e)

    def _load_categories(self):
        self._ignore_signals = True
        prev_cat_id = self.cmb_category.currentData()
        self.cmb_category.clear()

        cats = MoneyTransactionService.get_categories()
        for c in cats:
            self.cmb_category.addItem(c["AccountTypeName"], c["AccountTypeID"])

        # Restore or select Customer/Pathera
        if prev_cat_id:
            idx = self.cmb_category.findData(prev_cat_id)
            if idx >= 0:
                self.cmb_category.setCurrentIndex(idx)

        self._ignore_signals = False
        self._on_category_changed()

    def _on_category_changed(self):
        if self._ignore_signals:
            return
        cat_id = self.cmb_category.currentData()
        if not cat_id:
            return

        self._ignore_signals = True
        self.cmb_account.clear()

        # Load active accounts for this category with clean unicode bullet
        accounts = MoneyTransactionService.get_accounts_by_category(cat_id, include_omitted=current_session.is_admin)
        for a in accounts:
            urdu_text = f" ({a['UrduName']})" if a["UrduName"] else ""
            display_name = f"{a['WorkerID']} • {a['EnglishName']}{urdu_text}"
            self.cmb_account.addItem(display_name, a["WorkerID"])

        self._ignore_signals = False
        self._on_account_changed()

    def _on_account_changed(self):
        if self._ignore_signals:
            return
        self._update_balance_badge()

    def _update_balance_badge(self):
        is_dark = theme_mgr.is_dark_mode()
        acc_id = self.cmb_account.currentData() if hasattr(self, "cmb_account") else None
        if not acc_id:
            lbl_col = "#94A3B8" if is_dark else "#475569"
            if hasattr(self, "lbl_balance_text"):
                self.lbl_balance_text.setText("Account Balance: Select an account to view live position")
                self.lbl_balance_text.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {lbl_col}; border: none; background: transparent;")
            return

        try:
            report = LedgerService.calculate_worker_ledger(acc_id, date(2000, 1, 1), date.today())
            if report:
                c_bal = report.get("closing_balance", 0.0)
                label = report.get("statement_label", "")
                if c_bal >= 0:
                    color = "#34D399" if is_dark else "#16A34A"
                else:
                    color = "#F87171" if is_dark else "#DC2626"
                self.lbl_balance_text.setText(f"Live Khata Position: {label}")
                self.lbl_balance_text.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {color}; border: none; background: transparent;")
            else:
                info_col = "#38BDF8" if is_dark else "#0284C7"
                self.lbl_balance_text.setText("Live Khata Position: Clean account (No prior transactions)")
                self.lbl_balance_text.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {info_col}; border: none; background: transparent;")
        except Exception as e:
            self.lbl_balance_text.setText(f"Account: {acc_id}")

    def _open_account_khata(self):
        acc_id = self.cmb_account.currentData()
        if not acc_id:
            ToastNotification.show_error(self, "Selection Required", "Please select an account first.")
            return

        from app.ui.views.ledger_report_window import LedgerReportWindow
        today = date.today()
        # Open ledger covering from past year to today
        from_date = date(today.year - 1, 1, 1)
        try:
            ledger_data = LedgerService.calculate_worker_ledger(acc_id, from_date, today)
            if not ledger_data:
                ToastNotification.show_error(self, "Data Error", f"Could not load ledger for account {acc_id}.")
                return
            report_win = LedgerReportWindow(ledger_data, self)
            report_win.exec()
        except Exception as e:
            ToastNotification.show_error(self, "Ledger Error", f"Error generating ledger report: {e}")

    def _on_save_transaction(self):
        acc_id = self.cmb_account.currentData()
        if not acc_id:
            ToastNotification.show_error(self, "Validation Error", "Please select an account first.")
            return

        amount = self.txt_amount.get_value()
        if amount <= 0:
            ToastNotification.show_error(self, "Invalid Amount", "Transaction amount must be strictly greater than zero.")
            return

        description = self.cmb_narration.currentText().strip()

        txn_type = self.current_txn_type
        txn_date = self.dt_txn_date.date().toPython()
        method = self.cmb_method.currentText()
        bank_acc = self.txt_bank_acc.text().strip() if method != "Cash" else None
        cheque_no = self.txt_cheque.text().strip() if method != "Cash" else None
        reference = self.txt_ref.text().strip() or None
        allow_neg = self.chk_negative_cash.isChecked() if current_session.is_admin else False

        if self.is_edit_mode and self.current_txn_id:
            succ, msg = MoneyTransactionService.update_transaction(
                transaction_id=self.current_txn_id,
                txn_date=txn_date,
                account_id=acc_id,
                amount=amount,
                description=description,
                payment_method=method,
                bank_account=bank_acc,
                cheque_number=cheque_no,
                reference_type="Manual Edit",
                reference_id=reference
            )
            if succ:
                ToastNotification.show_success(self, "Transaction Updated", msg)
                self.clear_form()
                self.refresh_all_data()
            else:
                ToastNotification.show_error(self, "Update Failed", msg)
        else:
            succ, msg, res_dict = MoneyTransactionService.save_transaction(
                txn_type=txn_type,
                txn_date=txn_date,
                account_id=acc_id,
                amount=amount,
                description=description,
                payment_method=method,
                bank_account=bank_acc,
                cheque_number=cheque_no,
                reference_type="Manual Entry",
                reference_id=reference,
                allow_negative_cash=allow_neg
            )

            if succ and res_dict:
                ToastNotification.show_success(self, "Transaction Saved", msg)

                ask = QMessageBox.question(
                    self,
                    "Print Voucher?",
                    f"{msg}\n\nWould you like to print / preview the official voucher now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if ask == QMessageBox.Yes:
                    self._open_voucher_by_id(res_dict["TransactionID"])

                self.clear_form()
                self.refresh_all_data()
            else:
                ToastNotification.show_error(self, "Save Failed", msg)

    def clear_form(self):
        """Reset form controls to clean state."""
        self.is_edit_mode = False
        self.current_txn_id = None
        self._set_form_editable(True)
        if hasattr(self, "btn_delete_form"):
            self.btn_delete_form.setVisible(False)
        self.btn_clear.setText("Clear / New Form")
        self.txt_amount.clear()
        self.cmb_narration.setEditText("")
        self.txt_ref.clear()
        self.txt_bank_acc.clear()
        self.txt_cheque.clear()
        self.dt_txn_date.setDate(QDate.currentDate())
        self.cmb_method.setCurrentIndex(0)
        self.chk_negative_cash.setChecked(False)
        self._load_next_txn_no()
        self._update_form_theme(self.current_txn_type)
        self._update_balance_badge()

    def has_unsaved_changes(self) -> bool:
        """Check if form has data the user might want to save."""
        amount_text = self.txt_amount.text().strip()
        narration_text = self.cmb_narration.currentText().strip()
        return bool(amount_text and amount_text != "0" and amount_text != "0.00" and narration_text)

    def prompt_unsaved_changes(self) -> bool:
        """Ask user about unsaved data. Returns True if safe to leave, False to stay."""
        result = ToastNotification.confirm_unsaved_changes(self, "Cash Transaction Form")
        if result == "save":
            self._on_save_transaction()
            return True
        elif result == "discard":
            self.clear_form()
            return True
        return False

    def _load_register_table(self):
        """Load only the latest 5 transactions for high-speed recent activity view."""
        txns = MoneyTransactionService.get_transactions(limit=5)

        # Clean up any existing cell widgets to prevent ghost widgets at (0, 0)
        for r in range(self.table.rowCount()):
            old_w = self.table.cellWidget(r, 9)
            if old_w:
                self.table.removeCellWidget(r, 9)
                old_w.setParent(None)
                old_w.deleteLater()
        self.table.clearContents()

        self.table.setRowCount(len(txns))
        self.lbl_table_count.setText(f"Showing Recent {len(txns)} Entries")

        for r, t in enumerate(txns):
            t_id = t["TransactionID"]
            t_no = t["TransactionNo"]
            t_type = t["TransactionType"]
            is_amdan = (t_type == "RECEIPT")

            self.table.setRowHeight(r, 42)

            # Col 0: Txn #
            it_no = QTableWidgetItem(t_no)
            it_no.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(r, 0, it_no)

            # Col 1: Date
            self.table.setItem(r, 1, QTableWidgetItem(t["DateStr"]))

            # Col 2: Type Badge
            type_text = "AMDAN" if is_amdan else "AKRAJAT"
            it_type = QTableWidgetItem(type_text)
            it_type.setFont(QFont("Segoe UI", 9, QFont.Bold))
            it_type.setForeground(QColor("#059669" if is_amdan else "#DC2626"))
            self.table.setItem(r, 2, it_type)

            # Col 3: Category
            self.table.setItem(r, 3, QTableWidgetItem(t["CategoryName"]))

            # Col 4: Account Name
            urdu_part = f" ({t['UrduName']})" if t['UrduName'] else ""
            it_acc = QTableWidgetItem(f"{t['AccountID']} • {t['AccountName']}{urdu_part}")
            self.table.setItem(r, 4, it_acc)

            # Col 5: Amount
            amt_str = f"Rs. {t['Amount']:,.2f}"
            it_amt = QTableWidgetItem(amt_str)
            it_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_amt.setFont(QFont("Segoe UI", 9, QFont.Bold))
            it_amt.setForeground(QColor("#059669" if is_amdan else "#DC2626"))
            self.table.setItem(r, 5, it_amt)

            # Col 6: Payment Method
            self.table.setItem(r, 6, QTableWidgetItem(t["PaymentMethod"]))

            # Col 7: Description
            self.table.setItem(r, 7, QTableWidgetItem(t["Description"]))

            # Col 8: Reference
            self.table.setItem(r, 8, QTableWidgetItem(t["ReferenceID"] or t["ReferenceType"] or "-"))

            # Col 9: Actions (Print Voucher, Edit/Delete if Admin)
            action_widget = QWidget()
            act_layout = QHBoxLayout(action_widget)
            act_layout.setContentsMargins(2, 2, 2, 2)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignCenter)

            btn_voucher = QPushButton(" Print")
            btn_voucher.setIcon(_create_svg_icon(_SVG_PRINT, 13))
            btn_voucher.setIconSize(QSize(13, 13))
            btn_voucher.setToolTip("View & Print Voucher (واؤچر دیکھیں اور پرنٹ کریں)")
            btn_voucher.setFixedHeight(28)
            btn_voucher.setCursor(Qt.PointingHandCursor)
            btn_voucher.setStyleSheet(
                "QPushButton { background-color: #0284C7; color: #FFFFFF; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 0 8px; border: none; } "
                "QPushButton:hover { background-color: #0369A1; }"
            )
            btn_voucher.clicked.connect(lambda _, x=t_id: self._open_voucher_by_id(x))
            act_layout.addWidget(btn_voucher)

            if current_session.is_admin:
                btn_edit = QPushButton(" Edit")
                btn_edit.setIcon(_create_svg_icon(_SVG_EDIT, 13))
                btn_edit.setIconSize(QSize(13, 13))
                btn_edit.setToolTip("Edit Transaction (تبدیل کریں)")
                btn_edit.setFixedHeight(28)
                btn_edit.setCursor(Qt.PointingHandCursor)
                btn_edit.setStyleSheet(
                    "QPushButton { background-color: #F59E0B; color: #FFFFFF; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 0 8px; border: none; } "
                    "QPushButton:hover { background-color: #D97706; }"
                )
                btn_edit.clicked.connect(lambda _, x=t_id: self._load_transaction_into_form(x))
                act_layout.addWidget(btn_edit)

                btn_del = QPushButton(" Del")
                btn_del.setIcon(_create_svg_icon(_SVG_DELETE, 13))
                btn_del.setIconSize(QSize(13, 13))
                btn_del.setToolTip("Delete / Reverse Transaction (ختم کریں)")
                btn_del.setFixedHeight(28)
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setStyleSheet(
                    "QPushButton { background-color: #EF4444; color: #FFFFFF; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 0 8px; border: none; } "
                    "QPushButton:hover { background-color: #DC2626; }"
                )
                btn_del.clicked.connect(lambda _, x=t_id: self._delete_transaction(x))
                act_layout.addWidget(btn_del)
            else:
                btn_view = QPushButton(" View")
                btn_view.setToolTip("View Transaction Details (دیکھیں)")
                btn_view.setFixedHeight(28)
                btn_view.setCursor(Qt.PointingHandCursor)
                btn_view.setStyleSheet(
                    "QPushButton { background-color: #64748B; color: #FFFFFF; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 0 8px; border: none; } "
                    "QPushButton:hover { background-color: #475569; }"
                )
                btn_view.clicked.connect(lambda _, x=t_id: self._load_transaction_into_form(x))
                act_layout.addWidget(btn_view)

            self.table.setCellWidget(r, 9, action_widget)
            self.table.setRowHeight(r, 42)

    def _on_lookup_transaction(self):
        ident = self.txt_lookup.text().strip()
        if not ident:
            ToastNotification.show_error(self, "Lookup Required", "Please enter a Transaction # or ID to search.")
            return
        txn = MoneyTransactionService.get_transaction_by_id_or_no(ident, preferred_type=self.current_txn_type)
        if not txn:
            ToastNotification.show_error(self, "Not Found", f"No transaction found matching '{ident}'. Please verify the ID or Txn Number.")
            return
        self._load_transaction_into_form(txn["TransactionID"])

    def _open_a4_report(self):
        from app.services.register_service import RegisterService
        from app.ui.views.ledger_report_window import TabularSummaryReportWindow

        # Open filter dialog allowing user to choose date range and Amdan/Akrajat/Both
        filter_dlg = CashbookReportFilterDialog(parent=self, default_type=self.current_txn_type)
        if filter_dlg.exec() != QDialog.Accepted:
            return

        f_date = filter_dlg.selected_from_date
        t_date = filter_dlg.selected_to_date
        mode = filter_dlg.selected_type  # "ALL", "RECEIPT", or "PAYMENT"

        # Fetch register data
        txn_type_arg = mode if mode in ("RECEIPT", "PAYMENT") else None
        data = RegisterService.get_cashbook_register(f_date, t_date, txn_type=txn_type_arg)
        rows = data.get("rows", [])
        k = data.get("kpis", {})

        f_str = f_date.strftime("%d-%b-%Y")
        t_str = t_date.strftime("%d-%b-%Y")

        if mode == "RECEIPT":
            title = "Amdan (Receipts / آمدن) Register Report"
            subtitle = f"Cash Inflow Statement • {f_str} to {t_str}"
            cols = [
                {"header": "Txn #", "key": "TransactionNo", "width": "11%"},
                {"header": "Date", "key": "TransactionDate", "width": "11%"},
                {"header": "Account Name", "key": "AccountName", "width": "26%"},
                {"header": "Category", "key": "CategoryName", "width": "14%"},
                {"header": "Method", "key": "PaymentMethod", "width": "10%"},
                {"header": "Amdan (Rs.)", "key": "Amdan", "width": "14%", "align": "right", "is_currency": True, "color": "#16A34A"},
                {"header": "Description", "key": "Description", "width": "14%"}
            ]
            kpis = [
                ("Total Amdan (آمدن)", f"Rs. {k.get('total_amdan', 0):,.2f}", "#16A34A"),
                ("Total Receipts", f"{len(rows)} Records", "#2563EB"),
                ("From Date", f_str, "#475569"),
                ("To Date", t_str, "#475569"),
            ]
        elif mode == "PAYMENT":
            title = "Akrajat (Payments / اخراجات) Register Report"
            subtitle = f"Cash Outflow Statement • {f_str} to {t_str}"
            cols = [
                {"header": "Txn #", "key": "TransactionNo", "width": "11%"},
                {"header": "Date", "key": "TransactionDate", "width": "11%"},
                {"header": "Account Name", "key": "AccountName", "width": "26%"},
                {"header": "Category", "key": "CategoryName", "width": "14%"},
                {"header": "Method", "key": "PaymentMethod", "width": "10%"},
                {"header": "Akrajat (Rs.)", "key": "Akrajat", "width": "14%", "align": "right", "is_currency": True, "color": "#DC2626"},
                {"header": "Description", "key": "Description", "width": "14%"}
            ]
            kpis = [
                ("Total Akrajat (اخراجات)", f"Rs. {k.get('total_akrajat', 0):,.2f}", "#DC2626"),
                ("Total Payments", f"{len(rows)} Records", "#2563EB"),
                ("From Date", f_str, "#475569"),
                ("To Date", t_str, "#475569"),
            ]
        else:
            title = "Amdan & Akrajat (Cashbook) Register Report"
            subtitle = f"Cash Flow & Transaction Audit Statement • {f_str} to {t_str}"
            cols = [
                {"header": "Txn #", "key": "TransactionNo", "width": "10%"},
                {"header": "Date", "key": "TransactionDate", "width": "10%"},
                {"header": "Type", "key": "TransactionType", "width": "8%"},
                {"header": "Account Name", "key": "AccountName", "width": "20%"},
                {"header": "Category", "key": "CategoryName", "width": "12%"},
                {"header": "Method", "key": "PaymentMethod", "width": "8%"},
                {"header": "Amdan (Rs.)", "key": "Amdan", "width": "10%", "align": "right", "is_currency": True, "color": "#16A34A"},
                {"header": "Akrajat (Rs.)", "key": "Akrajat", "width": "10%", "align": "right", "is_currency": True, "color": "#DC2626"},
                {"header": "Balance (Rs.)", "key": "RunningCash", "width": "12%", "align": "right", "is_currency": True}
            ]
            kpis = [
                ("Opening Cash", f"Rs. {k.get('opening_cash', 0):,.2f}", "#2563EB"),
                ("Total Amdan", f"Rs. {k.get('total_amdan', 0):,.2f}", "#16A34A"),
                ("Total Akrajat", f"Rs. {k.get('total_akrajat', 0):,.2f}", "#DC2626"),
                ("Closing Cash", f"Rs. {k.get('closing_cash', 0):,.2f}", "#2563EB"),
            ]

        dlg = TabularSummaryReportWindow(
            title=title,
            subtitle=subtitle,
            columns=cols,
            rows=rows,
            kpi_items=kpis,
            from_date=f_date,
            to_date=t_date,
            parent=self
        )
        dlg.exec()

    def _open_voucher_by_id(self, transaction_id: int):
        txn_data = MoneyTransactionService.get_transaction_by_id(transaction_id)
        if not txn_data:
            ToastNotification.show_error(self, "Error", "Transaction details not found.")
            return

        dlg = VoucherWindow(txn_data, self)
        dlg.exec()

    def _set_form_editable(self, editable: bool):
        """Enable or disable form inputs based on Admin edit permissions."""
        self.dt_txn_date.setEnabled(editable)
        self.cmb_category.setEnabled(editable)
        self.cmb_account.setEnabled(editable)
        self.txt_amount.setEnabled(editable)
        self.cmb_method.setEnabled(editable)
        is_bank = (self.cmb_method.currentText() != "Cash")
        self.txt_bank_acc.setEnabled(editable and is_bank)
        self.txt_cheque.setEnabled(editable and is_bank)
        self.cmb_narration.setEnabled(editable)
        self.txt_ref.setEnabled(editable)
        if hasattr(self, "btn_type_amdan"):
            self.btn_type_amdan.setEnabled(editable)
        if hasattr(self, "btn_type_akrajat"):
            self.btn_type_akrajat.setEnabled(editable)
        if hasattr(self, "chk_negative_cash"):
            self.chk_negative_cash.setEnabled(editable and current_session.is_admin)

    def _on_txn_no_entered(self):
        text = self.txt_txn_no.text().strip()
        if not text or text.lower() in ("new", "auto", "auto-generated"):
            self.clear_form()
            ToastNotification.show_info(self, "New Form", "Switched to new transaction entry.")
            return

        txn = MoneyTransactionService.get_transaction_by_id_or_no(text, preferred_type=self.current_txn_type)
        if not txn:
            ToastNotification.show_error(self, "Not Found", f"No transaction found matching '{text}'.")
            return

        self._load_transaction_into_form(txn["TransactionID"])

    def _on_prev_transaction(self):
        txn = MoneyTransactionService.get_adjacent_transaction(self.current_txn_id, direction="prev")
        if not txn:
            ToastNotification.show_info(self, "Beginning", "No earlier transactions found.")
            return
        self._load_transaction_into_form(txn["TransactionID"])

    def _on_next_transaction(self):
        if not self.current_txn_id:
            ToastNotification.show_info(self, "New Form", "Already at new transaction form.")
            return
        txn = MoneyTransactionService.get_adjacent_transaction(self.current_txn_id, direction="next")
        if not txn:
            self.clear_form()
            ToastNotification.show_info(self, "New Form", "Reached latest entry. Switched to new transaction form.")
            return
        self._load_transaction_into_form(txn["TransactionID"])

    def _on_delete_current_from_form(self):
        if not self.current_txn_id or not current_session.is_admin:
            return
        self._delete_transaction(self.current_txn_id)
        self.clear_form()

    def _load_transaction_into_form(self, transaction_id: int):
        txn = MoneyTransactionService.get_transaction_by_id(transaction_id)
        if not txn:
            ToastNotification.show_error(self, "Error", "Transaction not found.")
            return

        self.current_txn_id = transaction_id
        self.txt_txn_no.setText(txn["TransactionNo"])

        # Switch transaction type
        self.current_txn_type = txn["TransactionType"]

        # Set Date
        t_date = txn["TransactionDate"]
        self.dt_txn_date.setDate(QDate(t_date.year, t_date.month, t_date.day))

        # Set Category & Account
        cat_id = txn.get("AccountTypeID")
        if cat_id:
            c_idx = self.cmb_category.findData(cat_id)
            if c_idx >= 0 and c_idx != self.cmb_category.currentIndex():
                self.cmb_category.setCurrentIndex(c_idx)
                self._on_category_changed()

        acc_id = txn["AccountID"]
        idx = self.cmb_account.findData(acc_id)
        if idx >= 0:
            self.cmb_account.setCurrentIndex(idx)
        else:
            acc_name = txn.get("AccountName") or acc_id
            self.cmb_account.addItem(f"{acc_id} • {acc_name}", acc_id)
            self.cmb_account.setCurrentIndex(self.cmb_account.count() - 1)

        # Set Amount & Details
        self.txt_amount.set_value(txn["Amount"])
        m_idx = self.cmb_method.findText(txn["PaymentMethod"])
        if m_idx >= 0:
            self.cmb_method.setCurrentIndex(m_idx)
        else:
            for i in range(self.cmb_method.count()):
                if self.cmb_method.itemText(i) in txn.get("PaymentMethod", "") or txn.get("PaymentMethod", "").startswith(self.cmb_method.itemText(i)):
                    self.cmb_method.setCurrentIndex(i)
                    break

        self.txt_bank_acc.setText(txn.get("BankAccount") or "")
        self.txt_cheque.setText(txn.get("ChequeNumber") or "")
        self.cmb_narration.setEditText(txn.get("Description") or "")
        self.txt_ref.setText(txn.get("ReferenceID") or "")

        # Check Admin permission: Edit only for Admin
        is_admin = current_session.is_admin
        self.is_edit_mode = is_admin
        self._set_form_editable(is_admin)

        if hasattr(self, "btn_delete_form"):
            self.btn_delete_form.setVisible(is_admin)

        self.btn_clear.setText("+ New Transaction")
        self._update_form_theme(self.current_txn_type)
        self._update_balance_badge()

        if is_admin:
            ToastNotification.show_info(self, "Edit Mode", f"Loaded '{txn['TransactionNo']}' for editing.")
        else:
            ToastNotification.show_warning(self, "View Only", f"Viewing '{txn['TransactionNo']}'. Only Admin can edit.")

    _load_transaction_for_edit = _load_transaction_into_form

    def _delete_transaction(self, transaction_id: int):
        confirm = QMessageBox.question(
            self,
            "Delete Transaction?",
            "Are you sure you want to delete and reverse this financial transaction?\n\nThis will immediately reverse its effect in Cash In-Hand and the Account Ledger.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        succ, msg = MoneyTransactionService.delete_transaction(transaction_id, reason="Admin manual reversal")
        if succ:
            ToastNotification.show_success(self, "Transaction Deleted", msg)
            self.refresh_all_data()
        else:
            ToastNotification.show_error(self, "Deletion Failed", msg)

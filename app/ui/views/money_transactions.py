from datetime import date, datetime
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QScrollArea, QMessageBox, QGroupBox, QCheckBox
)
from PySide6.QtCore import Qt, QDate, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from app.services.money_transaction_service import MoneyTransactionService
from app.services.ledger_service import LedgerService
from app.ui.components.formatted_inputs import CurrencyEdit
from app.ui.components.toast import ToastNotification
from app.ui.views.voucher_window import VoucherWindow
from app.security.session import current_session


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

        # 1. TOP TITLE HEADER
        top_bar = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("💰 Cash Transaction / Amdan & Akrajat (نقد لین دین / آمدن و اخراجات)")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        sub = QLabel("Unified financial movement engine for all accounts • Automatic ledger posting & real-time cash balance")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        top_bar.addLayout(title_box)
        top_bar.addStretch()

        self.btn_refresh_all = QPushButton("🔄 Refresh All Data")
        self.btn_refresh_all.setMinimumHeight(36)
        self.btn_refresh_all.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_all.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 0 16px; border: 1px solid #0369A1; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_refresh_all.clicked.connect(self.refresh_all_data)
        top_bar.addWidget(self.btn_refresh_all)

        main_layout.addLayout(top_bar)

        # 2. OUTER SCROLL AREA ENCLOSING ENTIRE WORKSPACE
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; } "
            "QScrollBar:vertical { background-color: #F1F5F9; width: 14px; margin: 0px; border-radius: 7px; border: 1px solid #E2E8F0; } "
            "QScrollBar::handle:vertical { background-color: #94A3B8; min-height: 40px; border-radius: 6px; margin: 2px; } "
            "QScrollBar::handle:vertical:hover { background-color: #64748B; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } "
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }"
        )

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 10)
        container_layout.setSpacing(14)

        # 3. REAL-TIME CASH SUMMARY KPI CARDS
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px; }")
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setSpacing(12)

        self.card_cash = self._create_kpi_card("💵 Cash in Hand (موجودہ نقد)", "Rs. 0.00", "#16A34A", "#F0FDF4")
        self.card_amdan = self._create_kpi_card("🟢 Total Amdan (آمدن / وصولی)", "Rs. 0.00", "#0284C7", "#F0F9FF")
        self.card_akrajat = self._create_kpi_card("🔴 Total Akrajat (اخراجات / ادائیگی)", "Rs. 0.00", "#DC2626", "#FEF2F2")
        self.card_bank = self._create_kpi_card("🏦 Bank Net Movement", "Rs. 0.00", "#7C3AED", "#F5F3FF")

        kpi_layout.addWidget(self.card_cash)
        kpi_layout.addWidget(self.card_amdan)
        kpi_layout.addWidget(self.card_akrajat)
        kpi_layout.addWidget(self.card_bank)
        container_layout.addWidget(kpi_frame)

        # =========================================================================
        # 4. UPPER SECTION: TRANSACTION ENTRY FORM CARD
        # =========================================================================
        self.form_card = QFrame()
        self.form_card.setObjectName("entry_form_card")

        form_main_layout = QVBoxLayout(self.form_card)
        form_main_layout.setContentsMargins(16, 14, 16, 14)
        form_main_layout.setSpacing(10)

        # Top Bar of Form Card: Mode indicator on left, prominent Segmented Buttons on right
        form_header = QHBoxLayout()
        self.lbl_form_mode = QLabel("🟢 New Amdan / Receipt Entry (آمدن / وصولی)")
        self.lbl_form_mode.setStyleSheet("font-size: 16px; font-weight: 800; color: #059669; border: none; background: transparent;")
        form_header.addWidget(self.lbl_form_mode)
        form_header.addStretch()

        # HIGH-CONTRAST SEGMENTED TOGGLE BUTTONS FOR AMDAN VS AKRAJAT
        type_box = QFrame()
        type_box.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 4px; }")
        type_layout = QHBoxLayout(type_box)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(6)

        self.btn_type_amdan = QPushButton("📥 Amdan / Receipt (آمدن / وصولی)")
        self.btn_type_amdan.setMinimumHeight(40)
        self.btn_type_amdan.setCursor(Qt.PointingHandCursor)
        self.btn_type_amdan.clicked.connect(lambda: self._set_transaction_type("RECEIPT"))
        type_layout.addWidget(self.btn_type_amdan)

        self.btn_type_akrajat = QPushButton("📤 Akrajat / Payment (اخراجات / ادائیگی)")
        self.btn_type_akrajat.setMinimumHeight(40)
        self.btn_type_akrajat.setCursor(Qt.PointingHandCursor)
        self.btn_type_akrajat.clicked.connect(lambda: self._set_transaction_type("PAYMENT"))
        type_layout.addWidget(self.btn_type_akrajat)

        form_header.addWidget(type_box)
        form_main_layout.addLayout(form_header)

        # 4-Column Grid for Form Fields
        f_grid = QGridLayout()
        f_grid.setHorizontalSpacing(14)
        f_grid.setVerticalSpacing(8)

        def make_field_lbl(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("font-weight: 700; font-size: 11px; color: #334155; border: none; background: transparent;")
            return lbl

        # Row 0: Transaction #, Date, Category, Select Account
        f_grid.addWidget(make_field_lbl("Transaction #:"), 0, 0)
        self.txt_txn_no = QLineEdit("Auto-Generated")
        self.txt_txn_no.setReadOnly(True)
        self.txt_txn_no.setMinimumHeight(34)
        self.txt_txn_no.setStyleSheet("background-color: #F1F5F9; color: #0F172A; font-weight: bold; font-size: 13px; border: 1px solid #CBD5E1; border-radius: 6px; padding: 0 8px;")
        f_grid.addWidget(self.txt_txn_no, 1, 0)

        f_grid.addWidget(make_field_lbl("Date (تاریخ):"), 0, 1)
        self.dt_txn_date = QDateEdit(QDate.currentDate())
        self.dt_txn_date.setCalendarPopup(True)
        self.dt_txn_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_txn_date.setMinimumHeight(34)
        f_grid.addWidget(self.dt_txn_date, 1, 1)

        f_grid.addWidget(make_field_lbl("Account Category (کھاتہ قسم):"), 0, 2)
        self.cmb_category = QComboBox()
        self.cmb_category.setMinimumHeight(34)
        self.cmb_category.currentIndexChanged.connect(self._on_category_changed)
        f_grid.addWidget(self.cmb_category, 1, 2)

        f_grid.addWidget(make_field_lbl("Select Account / Person (کھاتہ دار):"), 0, 3)
        self.cmb_account = QComboBox()
        self.cmb_account.setMinimumHeight(34)
        self.cmb_account.currentIndexChanged.connect(self._on_account_changed)
        f_grid.addWidget(self.cmb_account, 1, 3)

        # Row 2: Live Balance Preview Badge spanning all 4 columns
        self.badge_balance = QFrame()
        self.badge_balance.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 6px; padding: 6px 12px; }")
        b_layout = QHBoxLayout(self.badge_balance)
        b_layout.setContentsMargins(4, 2, 4, 2)
        self.lbl_balance_text = QLabel("Account Balance: Select an account to view live position")
        self.lbl_balance_text.setStyleSheet("font-size: 12px; font-weight: 700; color: #475569;")
        b_layout.addWidget(self.lbl_balance_text)
        b_layout.addStretch()

        self.btn_view_khata = QPushButton("📑 View Full Khata Ledger (کھاتہ دیکھیں)")
        self.btn_view_khata.setCursor(Qt.PointingHandCursor)
        self.btn_view_khata.setMinimumHeight(28)
        self.btn_view_khata.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 11px; border-radius: 4px; padding: 0 14px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_view_khata.clicked.connect(self._open_account_khata)
        b_layout.addWidget(self.btn_view_khata)

        f_grid.addWidget(self.badge_balance, 2, 0, 1, 4)

        # Row 3: Amount, Payment Method, Bank Account, Cheque #
        f_grid.addWidget(make_field_lbl("Amount (رقم PKR):"), 3, 0)
        self.txt_amount = CurrencyEdit()
        self.txt_amount.setPlaceholderText("0.00")
        self.txt_amount.setMinimumHeight(36)
        self.txt_amount.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A; padding-left: 8px;")
        f_grid.addWidget(self.txt_amount, 4, 0)

        f_grid.addWidget(make_field_lbl("Payment Method:"), 3, 1)
        self.cmb_method = QComboBox()
        self.cmb_method.addItems(["Cash", "Bank", "Cheque", "Online Transfer", "Other"])
        self.cmb_method.setMinimumHeight(36)
        self.cmb_method.currentIndexChanged.connect(self._on_method_changed)
        f_grid.addWidget(self.cmb_method, 4, 1)

        f_grid.addWidget(make_field_lbl("Bank / Account #:"), 3, 2)
        self.txt_bank_acc = QLineEdit()
        self.txt_bank_acc.setPlaceholderText("e.g. HBL - 123456789 (Optional)")
        self.txt_bank_acc.setMinimumHeight(36)
        self.txt_bank_acc.setEnabled(False)
        f_grid.addWidget(self.txt_bank_acc, 4, 2)

        f_grid.addWidget(make_field_lbl("Cheque / Slip #:"), 3, 3)
        self.txt_cheque = QLineEdit()
        self.txt_cheque.setPlaceholderText("e.g. CHQ-482019 (Optional)")
        self.txt_cheque.setMinimumHeight(36)
        self.txt_cheque.setEnabled(False)
        f_grid.addWidget(self.txt_cheque, 4, 3)

        # Row 5: Description / Narration (span 3 cols), Reference (1 col)
        f_grid.addWidget(make_field_lbl("Description / Narration (تفصیل):"), 5, 0, 1, 3)
        self.cmb_narration = QComboBox()
        self.cmb_narration.setEditable(True)
        self.cmb_narration.setMinimumHeight(34)
        self.cmb_narration.lineEdit().setPlaceholderText("Enter or select description...")
        f_grid.addWidget(self.cmb_narration, 6, 0, 1, 3)

        f_grid.addWidget(make_field_lbl("Reference / Linked Bill (اختیاری حوالہ):"), 5, 3)
        self.txt_ref = QLineEdit()
        self.txt_ref.setPlaceholderText("e.g. Sale INV-0042 / Batch Ref")
        self.txt_ref.setMinimumHeight(34)
        f_grid.addWidget(self.txt_ref, 6, 3)

        # Row 7: Action Buttons & Admin Checkbox
        row_actions = QHBoxLayout()
        row_actions.setContentsMargins(0, 4, 0, 0)
        row_actions.setSpacing(12)

        self.chk_negative_cash = QCheckBox("⚠️ Authorize Negative Cash Overdraw (Admin Policy)")
        self.chk_negative_cash.setStyleSheet(
            "QCheckBox { color: #B91C1C; font-weight: 800; font-size: 11px; background-color: #FEF2F2; "
            "border: 1.5px solid #FCA5A5; border-radius: 6px; padding: 8px 14px; } "
            "QCheckBox:hover { background-color: #FEE2E2; border-color: #F87171; }"
        )
        self.chk_negative_cash.setVisible(current_session.is_admin)
        row_actions.addWidget(self.chk_negative_cash)
        row_actions.addStretch()

        # HIGH-VISIBILITY SECONDARY CLEAR BUTTON
        self.btn_clear = QPushButton("✨ Clear / New Form")
        self.btn_clear.setMinimumHeight(44)
        self.btn_clear.setMinimumWidth(180)
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.setStyleSheet(
            "QPushButton { "
            "   background-color: #F1F5F9; "
            "   color: #0F172A; "
            "   font-weight: 800; "
            "   font-size: 13px; "
            "   border-radius: 6px; "
            "   padding: 0 24px; "
            "   border: 2px solid #64748B; "
            "} "
            "QPushButton:hover { "
            "   background-color: #E2E8F0; "
            "   border-color: #334155; "
            "   color: #0F172A; "
            "} "
            "QPushButton:pressed { background-color: #CBD5E1; }"
        )
        self.btn_clear.clicked.connect(self.clear_form)
        row_actions.addWidget(self.btn_clear)

        # HIGH-VISIBILITY PRIMARY SAVE BUTTON
        self.btn_save = QPushButton("💾 Save Receipt (Amdan)")
        self.btn_save.setMinimumHeight(44)
        self.btn_save.setMinimumWidth(230)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        row_actions.addWidget(self.btn_save)
        self.btn_save.clicked.connect(self._on_save_transaction)

        f_grid.addLayout(row_actions, 7, 0, 1, 4)

        # Set column stretch factors for balanced layout
        f_grid.setColumnStretch(0, 1)
        f_grid.setColumnStretch(1, 1)
        f_grid.setColumnStretch(2, 1)
        f_grid.setColumnStretch(3, 1)

        form_main_layout.addLayout(f_grid)
        container_layout.addWidget(self.form_card)

        # =========================================================================
        # 5. LOWER SECTION: FULL-WIDTH REGISTER / TRANSACTION HISTORY
        # =========================================================================
        register_panel = QFrame()
        register_panel.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; }")
        reg_layout = QVBoxLayout(register_panel)
        reg_layout.setContentsMargins(14, 12, 14, 12)
        reg_layout.setSpacing(10)

        # Title bar of Register
        reg_title_bar = QHBoxLayout()
        lbl_reg = QLabel("📋 Amdan & Akrajat Register (لین دین رجسٹر)")
        lbl_reg.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A; border: none;")
        reg_title_bar.addWidget(lbl_reg)
        reg_title_bar.addStretch()

        self.lbl_table_count = QLabel("Total Transactions: 0")
        self.lbl_table_count.setStyleSheet("font-size: 12px; font-weight: 700; color: #64748B; border: none;")
        reg_title_bar.addWidget(self.lbl_table_count)
        reg_layout.addLayout(reg_title_bar)

        # Horizontal Filter Toolbar
        filt_bar = QHBoxLayout()
        filt_bar.setSpacing(8)

        filt_bar.addWidget(QLabel("Type:"))
        self.cmb_filt_type = QComboBox()
        self.cmb_filt_type.addItems(["All Types", "Receipts (Amdan)", "Payments (Akrajat)"])
        self.cmb_filt_type.setMinimumHeight(32)
        self.cmb_filt_type.currentIndexChanged.connect(self._apply_table_filters)
        filt_bar.addWidget(self.cmb_filt_type)

        filt_bar.addWidget(QLabel("Category:"))
        self.cmb_filt_category = QComboBox()
        self.cmb_filt_category.setMinimumHeight(32)
        self.cmb_filt_category.currentIndexChanged.connect(self._apply_table_filters)
        filt_bar.addWidget(self.cmb_filt_category)

        filt_bar.addWidget(QLabel("From:"))
        self.dt_filt_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.dt_filt_from.setCalendarPopup(True)
        self.dt_filt_from.setMinimumHeight(32)
        self.dt_filt_from.dateChanged.connect(self._apply_table_filters)
        filt_bar.addWidget(self.dt_filt_from)

        filt_bar.addWidget(QLabel("To:"))
        self.dt_filt_to = QDateEdit(QDate.currentDate())
        self.dt_filt_to.setCalendarPopup(True)
        self.dt_filt_to.setMinimumHeight(32)
        self.dt_filt_to.dateChanged.connect(self._apply_table_filters)
        filt_bar.addWidget(self.dt_filt_to)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("🔍 Search by account name, Txn #, narration, or reference...")
        self.txt_search.setMinimumHeight(32)
        self.txt_search.textChanged.connect(self._apply_table_filters)
        filt_bar.addWidget(self.txt_search)

        btn_reset_filt = QPushButton("Reset Filters")
        btn_reset_filt.setMinimumHeight(32)
        btn_reset_filt.setStyleSheet("QPushButton { background-color: #FFFFFF; color: #475569; font-weight: 700; font-size: 11px; padding: 0 12px; border-radius: 4px; border: 1px solid #CBD5E1; } QPushButton:hover { background-color: #F1F5F9; }")
        btn_reset_filt.clicked.connect(self._reset_filters)
        filt_bar.addWidget(btn_reset_filt)

        reg_layout.addLayout(filt_bar)

        # Full-Width Register Table with ample room
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Txn #", "Date", "Type", "Category", "Account Name",
            "Amount (PKR)", "Method", "Description", "Ref", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.Fixed)
        self.table.setColumnWidth(9, 150)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(48)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setMinimumHeight(440)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #FFFFFF; border: 1px solid #E2E8F0; gridline-color: #F1F5F9; } "
            "QHeaderView::section { background-color: #F8FAFC; color: #1E293B; font-weight: 800; font-size: 11px; padding: 6px; border: 1px solid #E2E8F0; } "
            "QScrollBar:vertical { background-color: #F1F5F9; width: 12px; margin: 0px; border-radius: 6px; } "
            "QScrollBar::handle:vertical { background-color: #94A3B8; min-height: 30px; border-radius: 5px; margin: 1px; } "
            "QScrollBar::handle:vertical:hover { background-color: #64748B; } "
            "QScrollBar:horizontal { background-color: #F1F5F9; height: 12px; margin: 0px; border-radius: 6px; } "
            "QScrollBar::handle:horizontal { background-color: #94A3B8; min-width: 30px; border-radius: 5px; margin: 1px; } "
            "QScrollBar::handle:horizontal:hover { background-color: #64748B; }"
        )
        reg_layout.addWidget(self.table)

        container_layout.addWidget(register_panel)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        # Initial theme setup
        self._update_form_theme("RECEIPT")

    def _create_kpi_card(self, title: str, val: str, accent: str, bg: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: 1px solid #CBD5E1; border-left: 4px solid {accent}; border-radius: 6px; padding: 8px 12px; }}"
        )
        l = QVBoxLayout(card)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(2)

        t = QLabel(title)
        t.setStyleSheet("font-size: 11px; font-weight: 700; color: #475569; border: none;")
        v = QLabel(val)
        v.setObjectName("val_label")
        v.setStyleSheet(f"font-size: 18px; font-weight: 900; color: {accent}; border: none;")

        l.addWidget(t)
        l.addWidget(v)
        return card

    def _set_transaction_type(self, txn_type: str):
        self.current_txn_type = txn_type
        self._update_form_theme(txn_type)
        self._load_next_txn_no()
        self._load_narrations()
        self._update_balance_badge()

    def _update_form_theme(self, txn_type: str):
        is_receipt = (txn_type == "RECEIPT")

        # 1. Update form card border
        border_color = "#059669" if is_receipt else "#DC2626"
        header_color = "#047857" if is_receipt else "#B91C1C"

        self.form_card.setStyleSheet(
            f"#entry_form_card {{ background-color: #FFFFFF; border: 2px solid {border_color}; border-radius: 8px; }}"
        )

        if hasattr(self, "lbl_form_mode"):
            if is_receipt:
                self.lbl_form_mode.setText("🟢 New Amdan / Receipt Entry (آمدن / وصولی)")
                self.lbl_form_mode.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {header_color}; border: none; background: transparent;")
            else:
                self.lbl_form_mode.setText("🔴 New Akrajat / Payment Entry (اخراجات / ادائیگی)")
                self.lbl_form_mode.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {header_color}; border: none; background: transparent;")

        # 2. Update Segmented Toggle Buttons Styling
        if hasattr(self, "btn_type_amdan") and hasattr(self, "btn_type_akrajat"):
            if is_receipt:
                self.btn_type_amdan.setStyleSheet(
                    "QPushButton { "
                    "   background-color: #059669; "
                    "   color: #FFFFFF; "
                    "   font-weight: 900; "
                    "   font-size: 13px; "
                    "   border-radius: 6px; "
                    "   padding: 0 20px; "
                    "   border: 2px solid #047857; "
                    "} "
                    "QPushButton:hover { background-color: #047857; }"
                )
                self.btn_type_akrajat.setStyleSheet(
                    "QPushButton { "
                    "   background-color: #FFFFFF; "
                    "   color: #334155; "
                    "   font-weight: 800; "
                    "   font-size: 13px; "
                    "   border-radius: 6px; "
                    "   padding: 0 20px; "
                    "   border: 2px solid #CBD5E1; "
                    "} "
                    "QPushButton:hover { background-color: #FEF2F2; color: #DC2626; border-color: #F87171; }"
                )
            else:
                self.btn_type_akrajat.setStyleSheet(
                    "QPushButton { "
                    "   background-color: #DC2626; "
                    "   color: #FFFFFF; "
                    "   font-weight: 900; "
                    "   font-size: 13px; "
                    "   border-radius: 6px; "
                    "   padding: 0 20px; "
                    "   border: 2px solid #B91C1C; "
                    "} "
                    "QPushButton:hover { background-color: #B91C1C; }"
                )
                self.btn_type_amdan.setStyleSheet(
                    "QPushButton { "
                    "   background-color: #FFFFFF; "
                    "   color: #334155; "
                    "   font-weight: 800; "
                    "   font-size: 13px; "
                    "   border-radius: 6px; "
                    "   padding: 0 20px; "
                    "   border: 2px solid #CBD5E1; "
                    "} "
                    "QPushButton:hover { background-color: #F0FDF4; color: #059669; border-color: #34D399; }"
                )

        # 3. Update Primary Save Button Styling
        if hasattr(self, "btn_save"):
            if is_receipt:
                save_text = "💾 Update Receipt" if self.is_edit_mode else "💾 Save Receipt (Amdan)"
                self.btn_save.setText(save_text)
                self.btn_save.setStyleSheet(
                    "QPushButton { "
                    "   background-color: #059669; "
                    "   color: #FFFFFF; "
                    "   font-weight: 900; "
                    "   font-size: 14px; "
                    "   border-radius: 6px; "
                    "   padding: 0 32px; "
                    "   border: 2px solid #047857; "
                    "} "
                    "QPushButton:hover { background-color: #047857; border-color: #065F46; } "
                    "QPushButton:pressed { background-color: #064E3B; }"
                )
            else:
                save_text = "💾 Update Payment" if self.is_edit_mode else "💾 Save Payment (Akrajat)"
                self.btn_save.setText(save_text)
                self.btn_save.setStyleSheet(
                    "QPushButton { "
                    "   background-color: #DC2626; "
                    "   color: #FFFFFF; "
                    "   font-weight: 900; "
                    "   font-size: 14px; "
                    "   border-radius: 6px; "
                    "   padding: 0 32px; "
                    "   border: 2px solid #B91C1C; "
                    "} "
                    "QPushButton:hover { background-color: #B91C1C; border-color: #991B1B; } "
                    "QPushButton:pressed { background-color: #7F1D1D; }"
                )

    def _on_method_changed(self):
        method = self.cmb_method.currentText()
        is_bank = (method != "Cash")
        self.txt_bank_acc.setEnabled(is_bank)
        self.txt_cheque.setEnabled(is_bank)
        if not is_bank:
            self.txt_bank_acc.clear()
            self.txt_cheque.clear()

    def _load_next_txn_no(self):
        if not self.is_edit_mode:
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
        """Update KPI metrics at top."""
        try:
            summary = MoneyTransactionService.get_cash_summary()
            net_cash = summary.get("net_cash", 0.0)
            cash_color = "#16A34A" if net_cash >= 0 else "#DC2626"
            self.card_cash.findChild(QLabel, "val_label").setText(f"Rs. {net_cash:,.2f}")
            self.card_cash.findChild(QLabel, "val_label").setStyleSheet(f"font-size: 18px; font-weight: 900; color: {cash_color}; border: none;")

            self.card_amdan.findChild(QLabel, "val_label").setText(f"Rs. {summary.get('cash_amdan', 0.0):,.2f}")
            self.card_akrajat.findChild(QLabel, "val_label").setText(f"Rs. {summary.get('cash_akrajat', 0.0):,.2f}")
            self.card_bank.findChild(QLabel, "val_label").setText(f"Rs. {summary.get('net_bank', 0.0):,.2f}")
        except Exception as e:
            print(f"Error refreshing cash KPI: {e}")

    def _load_categories(self):
        self._ignore_signals = True
        prev_cat_id = self.cmb_category.currentData()
        self.cmb_category.clear()
        self.cmb_filt_category.clear()

        self.cmb_filt_category.addItem("All Categories", None)

        cats = MoneyTransactionService.get_categories()
        for c in cats:
            self.cmb_category.addItem(c["AccountTypeName"], c["AccountTypeID"])
            self.cmb_filt_category.addItem(c["AccountTypeName"], c["AccountTypeID"])

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
        acc_id = self.cmb_account.currentData()
        if not acc_id:
            self.lbl_balance_text.setText("Account Balance: Select an account to view live position")
            self.lbl_balance_text.setStyleSheet("font-size: 12px; font-weight: 700; color: #475569;")
            return

        try:
            report = LedgerService.calculate_worker_ledger(acc_id, date(2000, 1, 1), date.today())
            if report:
                c_bal = report.get("closing_balance", 0.0)
                status = report.get("statement_status", "BALANCED")
                label = report.get("statement_label", "")

                color = "#16A34A" if c_bal >= 0 else "#DC2626"
                self.lbl_balance_text.setText(f"Live Khata Position: {label}")
                self.lbl_balance_text.setStyleSheet(f"font-size: 12px; font-weight: 800; color: {color};")
            else:
                self.lbl_balance_text.setText("Live Khata Position: Clean account (No prior transactions)")
                self.lbl_balance_text.setStyleSheet("font-size: 12px; font-weight: 700; color: #0284C7;")
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
        if not description:
            ToastNotification.show_error(self, "Missing Narration", "Please enter a description / narration for this transaction.")
            return

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

    def _load_register_table(self):
        """Load transactions into the grid based on current filter values."""
        t_type_idx = self.cmb_filt_type.currentIndex()
        txn_type = None
        if t_type_idx == 1:
            txn_type = "RECEIPT"
        elif t_type_idx == 2:
            txn_type = "PAYMENT"

        cat_id = self.cmb_filt_category.currentData()
        from_date = self.dt_filt_from.date().toPython()
        to_date = self.dt_filt_to.date().toPython()
        search_q = self.txt_search.text().strip()

        txns = MoneyTransactionService.get_transactions(
            start_date=from_date,
            end_date=to_date,
            txn_type=txn_type,
            category_id=cat_id,
            search_query=search_q
        )

        self.table.setRowCount(len(txns))
        self.lbl_table_count.setText(f"Total Transactions: {len(txns)}")

        for r, t in enumerate(txns):
            t_id = t["TransactionID"]
            t_no = t["TransactionNo"]
            t_type = t["TransactionType"]
            is_amdan = (t_type == "RECEIPT")

            self.table.setRowHeight(r, 48)

            # Col 0: Txn #
            it_no = QTableWidgetItem(t_no)
            it_no.setFont(QFont("Segoe UI", 9, QFont.Bold))
            self.table.setItem(r, 0, it_no)

            # Col 1: Date
            self.table.setItem(r, 1, QTableWidgetItem(t["DateStr"]))

            # Col 2: Type Badge
            type_text = "🟢 AMDAN (آمدن)" if is_amdan else "🔴 AKRAJAT (اخراجات)"
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
            act_layout.setContentsMargins(4, 4, 4, 4)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignCenter)

            btn_voucher = QPushButton("🖨️")
            btn_voucher.setToolTip("View & Print Voucher")
            btn_voucher.setFixedSize(38, 32)
            btn_voucher.setCursor(Qt.PointingHandCursor)
            btn_voucher.setStyleSheet(
                "QPushButton { background-color: #0284C7; color: #FFFFFF; font-size: 15px; font-weight: bold; border-radius: 6px; border: 1px solid #0369A1; } "
                "QPushButton:hover { background-color: #0369A1; }"
            )
            btn_voucher.clicked.connect(lambda _, x=t_id: self._open_voucher_by_id(x))
            act_layout.addWidget(btn_voucher)

            if current_session.is_admin:
                btn_edit = QPushButton("✏️")
                btn_edit.setToolTip("Edit Transaction (Admin)")
                btn_edit.setFixedSize(38, 32)
                btn_edit.setCursor(Qt.PointingHandCursor)
                btn_edit.setStyleSheet(
                    "QPushButton { background-color: #F59E0B; color: #FFFFFF; font-size: 15px; font-weight: bold; border-radius: 6px; border: 1px solid #D97706; } "
                    "QPushButton:hover { background-color: #D97706; }"
                )
                btn_edit.clicked.connect(lambda _, x=t_id: self._load_transaction_for_edit(x))
                act_layout.addWidget(btn_edit)

                btn_del = QPushButton("🗑️")
                btn_del.setToolTip("Delete / Reverse Transaction (Admin)")
                btn_del.setFixedSize(38, 32)
                btn_del.setCursor(Qt.PointingHandCursor)
                btn_del.setStyleSheet(
                    "QPushButton { background-color: #EF4444; color: #FFFFFF; font-size: 15px; font-weight: bold; border-radius: 6px; border: 1px solid #DC2626; } "
                    "QPushButton:hover { background-color: #DC2626; }"
                )
                btn_del.clicked.connect(lambda _, x=t_id: self._delete_transaction(x))
                act_layout.addWidget(btn_del)

            self.table.setCellWidget(r, 9, action_widget)

    def _apply_table_filters(self):
        self._load_register_table()

    def _reset_filters(self):
        self._ignore_signals = True
        self.cmb_filt_type.setCurrentIndex(0)
        self.cmb_filt_category.setCurrentIndex(0)
        self.dt_filt_from.setDate(QDate.currentDate().addMonths(-1))
        self.dt_filt_to.setDate(QDate.currentDate())
        self.txt_search.clear()
        self._ignore_signals = False
        self._load_register_table()

    def _open_voucher_by_id(self, transaction_id: int):
        txn_data = MoneyTransactionService.get_transaction_by_id(transaction_id)
        if not txn_data:
            ToastNotification.show_error(self, "Error", "Transaction details not found.")
            return

        dlg = VoucherWindow(txn_data, self)
        dlg.exec()

    def _load_transaction_for_edit(self, transaction_id: int):
        txn = MoneyTransactionService.get_transaction_by_id(transaction_id)
        if not txn:
            ToastNotification.show_error(self, "Error", "Transaction not found.")
            return

        self.is_edit_mode = True
        self.current_txn_id = transaction_id
        self.txt_txn_no.setText(txn["TransactionNo"])

        self.current_txn_type = txn["TransactionType"]
        self._update_form_theme(self.current_txn_type)

        # Set Date
        t_date = txn["TransactionDate"]
        self.dt_txn_date.setDate(QDate(t_date.year, t_date.month, t_date.day))

        # Set Account
        acc_id = txn["AccountID"]
        idx = self.cmb_account.findData(acc_id)
        if idx >= 0:
            self.cmb_account.setCurrentIndex(idx)

        # Set Amount & Details
        self.txt_amount.set_value(txn["Amount"])
        m_idx = self.cmb_method.findText(txn["PaymentMethod"])
        if m_idx >= 0:
            self.cmb_method.setCurrentIndex(m_idx)

        self.txt_bank_acc.setText(txn["BankAccount"])
        self.txt_cheque.setText(txn["ChequeNumber"])
        self.cmb_narration.setEditText(txn["Description"])
        self.txt_ref.setText(txn["ReferenceID"])

        self._update_form_theme(self.current_txn_type)
        ToastNotification.show_info(self, "Edit Mode", f"Loaded '{txn['TransactionNo']}' for editing.")

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

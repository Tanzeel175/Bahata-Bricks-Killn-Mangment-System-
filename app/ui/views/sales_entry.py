from datetime import date, datetime
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QScrollArea, QMessageBox, QGroupBox, QSplitter
)
from PySide6.QtCore import Qt, QDate, Signal, QTimer
from PySide6.QtGui import QFont, QDoubleValidator
from app.services.sales_service import SalesService
from app.services.ledger_service import LedgerService
from app.services.labour_service import LabourService
from app.ui.components.toast import ToastNotification
from app.ui.views.sales_receipt_window import SalesReceiptWindow
from app.security.session import current_session


class SalesEntryView(QWidget):
    """
    Sales Entry & Multi-Product Billing Form.
    Allows creating receipts with multiple products, assigning transport and delivery person,
    calculating piece-rate totals, posting to Customer Khata, and generating printable receipts.
    """

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_sale_id: Optional[int] = None
        self.is_edit_mode: bool = False
        self.is_dirty: bool = False
        self._ignore_signals: bool = False

        self.receipt_items: List[Dict[str, Any]] = []
        self.editing_item_index: Optional[int] = None

        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. TOP HEADER TITLE
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("🧾 Sales Entry & Billing (سیلز رسید)")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        sub = QLabel("Record multi-product brick sales, assign transport/driver, and automatically update Customer Khata Ledger")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        header_box.addLayout(title_box)
        header_box.addStretch()

        main_layout.addLayout(header_box)

        # Scroll Area for main content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 0)
        container_layout.setSpacing(10)

        # 2. RECEIPT METADATA CARD
        meta_card = QFrame()
        meta_card.setObjectName("meta_card")
        meta_card.setStyleSheet("#meta_card { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; }")
        meta_layout = QVBoxLayout(meta_card)
        meta_layout.setContentsMargins(12, 12, 12, 12)
        meta_layout.setSpacing(10)

        lbl_meta_title = QLabel("📌 Receipt Information & Customer Details")
        lbl_meta_title.setStyleSheet("font-weight: 800; color: #0284C7; font-size: 13px; border: none; background: transparent;")
        meta_layout.addWidget(lbl_meta_title)

        # Row 1: Invoice No, Sale Date, Customer, Balance Badge
        row1 = QHBoxLayout()
        row1.setSpacing(10)

        v1 = QVBoxLayout()
        l_inv = QLabel("Invoice / Receipt #:")
        l_inv.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.txt_invoice_no = QLineEdit("Auto-Generated")
        self.txt_invoice_no.setReadOnly(True)
        self.txt_invoice_no.setMinimumHeight(32)
        self.txt_invoice_no.setStyleSheet("background-color: #F1F5F9; color: #0F172A; font-weight: bold;")
        v1.addWidget(l_inv)
        v1.addWidget(self.txt_invoice_no)

        v2 = QVBoxLayout()
        l_date = QLabel("Sale Date:")
        l_date.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.dt_sale_date = QDateEdit(QDate.currentDate())
        self.dt_sale_date.setCalendarPopup(True)
        self.dt_sale_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_sale_date.setMinimumHeight(32)
        v2.addWidget(l_date)
        v2.addWidget(self.dt_sale_date)

        v3 = QVBoxLayout()
        l_cust = QLabel("Customer (گاہک):")
        l_cust.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.cmb_customer = QComboBox()
        self.cmb_customer.setMinimumHeight(32)
        self.cmb_customer.currentIndexChanged.connect(self._on_customer_changed)
        v3.addWidget(l_cust)
        v3.addWidget(self.cmb_customer)

        v4 = QVBoxLayout()
        l_bal = QLabel("Customer Khata Balance:")
        l_bal.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.lbl_customer_balance = QLabel("Balance: Rs. 0.00")
        self.lbl_customer_balance.setMinimumHeight(32)
        self.lbl_customer_balance.setStyleSheet(
            "QLabel { background-color: #F8FAFC; color: #0F172A; font-weight: bold; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; font-size: 12px; }"
        )
        v4.addWidget(l_bal)
        v4.addWidget(self.lbl_customer_balance)

        row1.addLayout(v1, stretch=1)
        row1.addLayout(v2, stretch=1)
        row1.addLayout(v3, stretch=2)
        row1.addLayout(v4, stretch=2)
        meta_layout.addLayout(row1)

        # Row 2: Transport Source, Delivery Person / Driver, Vehicle #, Remarks
        row2 = QHBoxLayout()
        row2.setSpacing(10)

        v_tmode = QVBoxLayout()
        l_tm = QLabel("Transport Source (ٹرانسپورٹ):")
        l_tm.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.cmb_transport_mode = QComboBox()
        self.cmb_transport_mode.setMinimumHeight(32)
        for tm in SalesService.get_transport_modes():
            self.cmb_transport_mode.addItem(tm)
        self.cmb_transport_mode.currentIndexChanged.connect(self._on_transport_mode_changed)
        v_tmode.addWidget(l_tm)
        v_tmode.addWidget(self.cmb_transport_mode)

        v_driver = QVBoxLayout()
        l_dr = QLabel("Delivery Person / Driver (ڈرائیور / ریڑھا والا):")
        l_dr.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.cmb_driver = QComboBox()
        self.cmb_driver.setEditable(True)
        self.cmb_driver.setMinimumHeight(32)
        v_driver.addWidget(l_dr)
        v_driver.addWidget(self.cmb_driver)

        v_veh = QVBoxLayout()
        l_vh = QLabel("Vehicle / Cart #:")
        l_vh.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.txt_vehicle_no = QLineEdit()
        self.txt_vehicle_no.setPlaceholderText("e.g. LES-1234 or Rehra #3")
        self.txt_vehicle_no.setMinimumHeight(32)
        v_veh.addWidget(l_vh)
        v_veh.addWidget(self.txt_vehicle_no)

        v_rem = QVBoxLayout()
        l_rm = QLabel("Remarks / Delivery Site (ریمارکس):")
        l_rm.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Site location or special notes")
        self.txt_remarks.setMinimumHeight(32)
        v_rem.addWidget(l_rm)
        v_rem.addWidget(self.txt_remarks)

        row2.addLayout(v_tmode, stretch=2)
        row2.addLayout(v_driver, stretch=2)
        row2.addLayout(v_veh, stretch=1)
        row2.addLayout(v_rem, stretch=2)
        meta_layout.addLayout(row2)

        container_layout.addWidget(meta_card)

        # 3. MULTI-PRODUCT LINE ITEM ENTRY CARD
        items_card = QFrame()
        items_card.setObjectName("items_card")
        items_card.setStyleSheet("#items_card { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; }")
        items_layout = QVBoxLayout(items_card)
        items_layout.setContentsMargins(12, 12, 12, 12)
        items_layout.setSpacing(10)

        lbl_items_title = QLabel("🧱 Multi-Product Line Items Entry (اینٹوں کا اندراج)")
        lbl_items_title.setStyleSheet("font-weight: 800; color: #0284C7; font-size: 13px; border: none; background: transparent;")
        items_layout.addWidget(lbl_items_title)

        # Item Inputs Bar
        item_input_bar = QHBoxLayout()
        item_input_bar.setSpacing(8)

        v_p = QVBoxLayout()
        lp = QLabel("Select Product:")
        lp.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.cmb_product = QComboBox()
        self.cmb_product.setMinimumHeight(32)
        self.cmb_product.currentIndexChanged.connect(self._on_product_selection_changed)
        v_p.addWidget(lp)
        v_p.addWidget(self.cmb_product)

        v_q = QVBoxLayout()
        lq = QLabel("Quantity (Pcs):")
        lq.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.txt_quantity = QLineEdit()
        self.txt_quantity.setPlaceholderText("e.g. 5000")
        self.txt_quantity.setMinimumHeight(32)
        self.txt_quantity.textChanged.connect(self._calculate_line_total)
        v_q.addWidget(lq)
        v_q.addWidget(self.txt_quantity)

        v_r = QVBoxLayout()
        lr = QLabel("Rate per 1,000 (PKR):")
        lr.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.txt_rate = QLineEdit()
        self.txt_rate.setPlaceholderText("e.g. 14000")
        self.txt_rate.setMinimumHeight(32)
        self.txt_rate.textChanged.connect(self._calculate_line_total)
        v_r.addWidget(lr)
        v_r.addWidget(self.txt_rate)

        v_tot = QVBoxLayout()
        lt = QLabel("Line Total (PKR):")
        lt.setStyleSheet("font-weight: 600; font-size: 11px; color: #475569; border: none; background: transparent;")
        self.lbl_line_total = QLabel("Rs. 0.00")
        self.lbl_line_total.setMinimumHeight(32)
        self.lbl_line_total.setStyleSheet(
            "QLabel { background-color: #F0FDF4; color: #16A34A; font-weight: bold; border: 1px solid #BBF7D0; border-radius: 4px; padding: 4px 8px; font-size: 13px; }"
        )
        v_tot.addWidget(lt)
        v_tot.addWidget(self.lbl_line_total)

        v_act = QVBoxLayout()
        v_act.addSpacing(18)
        btn_box = QHBoxLayout()
        self.btn_add_item = QPushButton("➕ Add to Receipt")
        self.btn_add_item.setMinimumHeight(32)
        self.btn_add_item.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 4px; padding: 4px 14px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_add_item.clicked.connect(self._on_add_or_update_item_clicked)

        self.btn_cancel_edit_item = QPushButton("❌ Cancel")
        self.btn_cancel_edit_item.setMinimumHeight(32)
        self.btn_cancel_edit_item.setStyleSheet(
            "QPushButton { background-color: #94A3B8; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 4px; padding: 4px 10px; border: none; } "
            "QPushButton:hover { background-color: #64748B; }"
        )
        self.btn_cancel_edit_item.setVisible(False)
        self.btn_cancel_edit_item.clicked.connect(self._cancel_item_edit)

        btn_box.addWidget(self.btn_add_item)
        btn_box.addWidget(self.btn_cancel_edit_item)
        v_act.addLayout(btn_box)

        item_input_bar.addLayout(v_p, stretch=3)
        item_input_bar.addLayout(v_q, stretch=2)
        item_input_bar.addLayout(v_r, stretch=2)
        item_input_bar.addLayout(v_tot, stretch=2)
        item_input_bar.addLayout(v_act, stretch=2)
        items_layout.addLayout(item_input_bar)

        # Receipt Items Table Widget
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(6)
        self.items_table.setHorizontalHeaderLabels(["#", "Product Name", "Quantity (Pcs)", "Rate (/1000)", "Total Amount (PKR)", "Actions"])
        self.items_table.horizontalHeader().setFixedHeight(40)
        self.items_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.verticalHeader().setDefaultSectionSize(54)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.items_table.setSelectionMode(QTableWidget.SingleSelection)
        self.items_table.setAutoScroll(False)
        self.items_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.items_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.items_table.setMinimumHeight(115)
        self.items_table.setColumnWidth(0, 50)
        self.items_table.setColumnWidth(1, 250)
        self.items_table.setColumnWidth(2, 140)
        self.items_table.setColumnWidth(3, 140)
        self.items_table.setColumnWidth(4, 160)
        self.items_table.setColumnWidth(5, 140)
        self.items_table.setStyleSheet(
            "QTableWidget { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; gridline-color: #F1F5F9; font-size: 13px; }"
            "QHeaderView::section { background-color: #F1F5F9; color: #1E293B; font-weight: 700; font-size: 12px; padding: 6px 10px; border: none; border-bottom: 2px solid #CBD5E1; border-right: 1px solid #E2E8F0; min-height: 40px; height: 40px; max-height: 40px; }"
            "QTableWidget::item { padding-top: 10px; padding-bottom: 10px; padding-left: 10px; padding-right: 10px; border-bottom: 1px solid #E2E8F0; }"
        )
        items_layout.addWidget(self.items_table)

        # Grand Total Summary Banner
        sum_box = QHBoxLayout()
        sum_box.addStretch()

        self.lbl_grand_summary = QLabel("Items: 0  |  Total Bricks: 0  |  Grand Total: Rs. 0.00")
        self.lbl_grand_summary.setStyleSheet(
            "QLabel { background-color: #F0FDF4; color: #166534; font-weight: 800; font-size: 14px; border: 2px solid #22C55E; border-radius: 6px; padding: 8px 18px; }"
        )
        sum_box.addWidget(self.lbl_grand_summary)
        items_layout.addLayout(sum_box)

        container_layout.addWidget(items_card)

        # 4. ACTION BUTTONS BAR
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        def make_pill(text, bg_color, hover_color, text_color="#FFFFFF"):
            btn = QPushButton(text)
            btn.setMinimumHeight(38)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {bg_color}; color: {text_color}; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 18px; border: none; }} "
                f"QPushButton:hover {{ background-color: {hover_color}; }} "
            )
            return btn

        self.btn_save = make_pill("💾 Save & Post to Ledger", "#0284C7", "#0369A1")
        self.btn_save.clicked.connect(self._on_save_clicked)

        self.btn_print = make_pill("🖨️ Print Receipt", "#10B981", "#059669")
        self.btn_print.clicked.connect(self._on_print_clicked)

        self.btn_new = make_pill("🔄 New Sale", "#64748B", "#475569")
        self.btn_new.clicked.connect(self._on_new_clicked)

        self.btn_delete = make_pill("🗑️ Delete Sale", "#EF4444", "#DC2626")
        self.btn_delete.setVisible(current_session.is_admin)
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        self.btn_close = make_pill("❌ Close", "#94A3B8", "#64748B")
        self.btn_close.clicked.connect(self._on_close_clicked)

        btn_bar.addWidget(self.btn_save)
        btn_bar.addWidget(self.btn_print)
        btn_bar.addWidget(self.btn_new)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_close)

        container_layout.addLayout(btn_bar)

        # 5. SALES HISTORY & SEARCH CARD
        hist_card = QFrame()
        hist_card.setObjectName("hist_card")
        hist_card.setStyleSheet("#hist_card { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; }")
        hist_layout = QVBoxLayout(hist_card)
        hist_layout.setContentsMargins(12, 12, 12, 12)
        hist_layout.setSpacing(8)

        lbl_hist_title = QLabel("📜 Recent Sales Receipts & History")
        lbl_hist_title.setStyleSheet("font-weight: 800; color: #0F172A; font-size: 13px; border: none; background: transparent;")
        hist_layout.addWidget(lbl_hist_title)

        # History Filters
        h_filter_bar = QHBoxLayout()
        h_filter_bar.setSpacing(8)

        self.dt_hist_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.dt_hist_from.setCalendarPopup(True)
        self.dt_hist_from.setDisplayFormat("yyyy-MM-dd")
        self.dt_hist_from.setMinimumHeight(30)

        self.dt_hist_to = QDateEdit(QDate.currentDate())
        self.dt_hist_to.setCalendarPopup(True)
        self.dt_hist_to.setDisplayFormat("yyyy-MM-dd")
        self.dt_hist_to.setMinimumHeight(30)

        self.txt_hist_search = QLineEdit()
        self.txt_hist_search.setPlaceholderText("Search by invoice #, customer, driver...")
        self.txt_hist_search.setMinimumHeight(30)
        self.txt_hist_search.textChanged.connect(self._load_sales_history)

        btn_search_refresh = make_pill("🔍 Search / Refresh", "#0284C7", "#0369A1")
        btn_search_refresh.clicked.connect(self._load_sales_history)

        h_filter_bar.addWidget(QLabel("From:"))
        h_filter_bar.addWidget(self.dt_hist_from)
        h_filter_bar.addWidget(QLabel("To:"))
        h_filter_bar.addWidget(self.dt_hist_to)
        h_filter_bar.addWidget(self.txt_hist_search, stretch=1)
        h_filter_bar.addWidget(btn_search_refresh)

        hist_layout.addLayout(h_filter_bar)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels(["Invoice #", "Date", "Customer", "Items Summary", "Transport", "Driver", "Total (PKR)", "Created By"])
        self.history_table.horizontalHeader().setMinimumHeight(40)
        self.history_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.history_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.history_table.setLayoutDirection(Qt.LeftToRight)
        self.history_table.setAutoScroll(False)
        self.history_table.setMinimumHeight(240)
        self.history_table.setColumnWidth(0, 100)
        self.history_table.setColumnWidth(1, 100)
        self.history_table.setColumnWidth(2, 170)
        self.history_table.setColumnWidth(3, 230)
        self.history_table.setColumnWidth(4, 120)
        self.history_table.setColumnWidth(5, 130)
        self.history_table.setColumnWidth(6, 130)
        self.history_table.setStyleSheet(
            "QTableWidget { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px; gridline-color: #F1F5F9; font-size: 13px; }"
            "QHeaderView::section { background-color: #F1F5F9; color: #1E293B; font-weight: 700; font-size: 12px; padding: 6px 10px; border: none; border-bottom: 2px solid #CBD5E1; border-right: 1px solid #E2E8F0; min-height: 40px; height: 40px; max-height: 40px; }"
            "QTableWidget::item { padding: 6px 10px; border-bottom: 1px solid #F1F5F9; }"
        )
        self.history_table.itemDoubleClicked.connect(self._on_history_row_double_clicked)
        hist_layout.addWidget(self.history_table)

        container_layout.addWidget(hist_card)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    # --- DATA LOADING & COMBO UPDATES ---
    def refresh_data(self):
        self._load_customers()
        self._load_sale_products()
        self._on_transport_mode_changed()
        self._load_sales_history()
        if not self.is_edit_mode:
            self.txt_invoice_no.setText(SalesService.get_next_invoice_no())

    def _load_customers(self):
        self.cmb_customer.blockSignals(True)
        self.cmb_customer.clear()
        customers = SalesService.get_customers()
        for c in customers:
            display = f"{c['EnglishName']}"
            if c.get('UrduName'):
                display += f" ({c['UrduName']})"
            self.cmb_customer.addItem(display, c['CustomerID'])
        self.cmb_customer.blockSignals(False)
        self._on_customer_changed()

    def _load_sale_products(self):
        self.cmb_product.blockSignals(True)
        self.cmb_product.clear()
        prods = SalesService.get_sale_products()
        for p in prods:
            self.cmb_product.addItem(p['ProductName'], p)
        self.cmb_product.blockSignals(False)
        self._on_product_selection_changed()

    def _on_transport_mode_changed(self):
        mode = self.cmb_transport_mode.currentText()
        drivers = SalesService.get_delivery_persons_by_mode(mode)
        current_text = self.cmb_driver.currentText()

        self.cmb_driver.blockSignals(True)
        self.cmb_driver.clear()
        for d in drivers:
            name = d["Name"]
            if d.get("UrduName"):
                name += f" ({d['UrduName']})"
            self.cmb_driver.addItem(name, d["WorkerID"])

        if current_text:
            self.cmb_driver.setEditText(current_text)
        self.cmb_driver.blockSignals(False)

    def _on_customer_changed(self):
        cust_id = self.cmb_customer.currentData()
        if not cust_id:
            self.lbl_customer_balance.setText("Balance: Rs. 0.00")
            return

        # Fetch Customer Ledger to show real-time Khata Balance
        today = date.today()
        ledger = LedgerService.calculate_worker_ledger(cust_id, date(2020, 1, 1), today)
        if ledger:
            bal = ledger.get("closing_balance", 0.0)
            status = ledger.get("statement_status", "BALANCED")
            if status == "RECEIVABLE":
                self.lbl_customer_balance.setText(f"Khata Balance: -Rs. {abs(bal):,.2f} (Receivable / Baqi)")
                self.lbl_customer_balance.setStyleSheet("QLabel { background-color: #FEF2F2; color: #DC2626; font-weight: bold; border: 1px solid #FECACA; border-radius: 4px; padding: 4px 8px; font-size: 12px; }")
            elif status == "ADVANCE":
                self.lbl_customer_balance.setText(f"Khata Balance: +Rs. {bal:,.2f} (Advance / Jama)")
                self.lbl_customer_balance.setStyleSheet("QLabel { background-color: #F0FDF4; color: #16A34A; font-weight: bold; border: 1px solid #BBF7D0; border-radius: 4px; padding: 4px 8px; font-size: 12px; }")
            else:
                self.lbl_customer_balance.setText("Khata Balance: Rs. 0.00 (Cleared)")
                self.lbl_customer_balance.setStyleSheet("QLabel { background-color: #F8FAFC; color: #334155; font-weight: bold; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; font-size: 12px; }")
        else:
            self.lbl_customer_balance.setText("Khata Balance: Rs. 0.00")

    def _on_product_selection_changed(self):
        p_data = self.cmb_product.currentData()
        if p_data:
            rate = p_data.get("UnitRate", 0.0)
            self.txt_rate.setText(f"{rate:g}")
        self._calculate_line_total()

    def _calculate_line_total(self):
        try:
            qty_str = self.txt_quantity.text().replace(",", "").strip()
            rate_str = self.txt_rate.text().replace(",", "").strip()
            qty = float(qty_str) if qty_str else 0.0
            rate = float(rate_str) if rate_str else 0.0
            total = (qty / 1000.0) * rate
            self.lbl_line_total.setText(f"Rs. {total:,.2f}")
        except ValueError:
            self.lbl_line_total.setText("Rs. 0.00")

    # --- MULTI-PRODUCT ITEM MANAGEMENT ---
    def _on_add_or_update_item_clicked(self):
        p_data = self.cmb_product.currentData()
        if not p_data:
            ToastNotification.warning(self, "Please select a product first.")
            return

        try:
            qty = float(self.txt_quantity.text().replace(",", "").strip())
            rate = float(self.txt_rate.text().replace(",", "").strip())
        except ValueError:
            ToastNotification.warning(self, "Please enter valid numeric values for Quantity and Rate.")
            return

        if qty <= 0:
            ToastNotification.warning(self, "Quantity must be greater than 0.")
            return

        if rate <= 0:
            ToastNotification.warning(self, "Rate per 1,000 must be greater than 0.")
            return

        line_total = (qty / 1000.0) * rate
        item_data = {
            "ProductID": p_data["ProductID"],
            "ProductName": p_data["ProductName"],
            "Quantity": qty,
            "RatePer1000": rate,
            "TotalAmount": line_total
        }

        if self.editing_item_index is not None and 0 <= self.editing_item_index < len(self.receipt_items):
            self.receipt_items[self.editing_item_index] = item_data
            self.editing_item_index = None
            self.btn_add_item.setText("➕ Add to Receipt")
            self.btn_cancel_edit_item.setVisible(False)
        else:
            self.receipt_items.append(item_data)

        self.txt_quantity.clear()
        self._calculate_line_total()
        self._render_items_table()
        self.is_dirty = True

    def _cancel_item_edit(self):
        self.editing_item_index = None
        self.btn_add_item.setText("➕ Add to Receipt")
        self.btn_cancel_edit_item.setVisible(False)
        self.txt_quantity.clear()
        self._calculate_line_total()

    def _render_items_table(self):
        self.items_table.setRowCount(len(self.receipt_items))
        grand_total = 0.0
        total_qty = 0.0

        for row, item in enumerate(self.receipt_items):
            grand_total += item["TotalAmount"]
            total_qty += item["Quantity"]

            item_num = QTableWidgetItem(str(row + 1))
            item_num.setTextAlignment(Qt.AlignCenter)

            item_prod = QTableWidgetItem(item["ProductName"])
            item_prod.setFont(QFont("Segoe UI", 9, QFont.Bold))
            item_prod.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_qty = QTableWidgetItem(f"{item['Quantity']:,.0f}")
            item_qty.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            item_rate = QTableWidgetItem(f"Rs. {item['RatePer1000']:,.2f}")
            item_rate.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            item_tot = QTableWidgetItem(f"Rs. {item['TotalAmount']:,.2f}")
            item_tot.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_tot.setFont(QFont("Segoe UI", 9, QFont.Bold))

            # Action Buttons: Edit / Remove
            btn_frame = QWidget()
            b_layout = QHBoxLayout(btn_frame)
            b_layout.setContentsMargins(4, 6, 4, 6)
            b_layout.setSpacing(4)
            b_layout.setAlignment(Qt.AlignCenter)

            btn_edit = QPushButton("✏️")
            btn_edit.setToolTip("Edit item")
            btn_edit.setFocusPolicy(Qt.NoFocus)
            btn_edit.setFixedHeight(28)
            btn_edit.setStyleSheet("QPushButton { background-color: #0284C7; color: white; border-radius: 4px; font-size: 12px; padding: 2px 8px; }")
            btn_edit.clicked.connect(lambda _, r=row: self._edit_item_row(r))

            btn_del = QPushButton("🗑️")
            btn_del.setToolTip("Remove item")
            btn_del.setFocusPolicy(Qt.NoFocus)
            btn_del.setFixedHeight(28)
            btn_del.setStyleSheet("QPushButton { background-color: #EF4444; color: white; border-radius: 4px; font-size: 12px; padding: 2px 8px; }")
            btn_del.clicked.connect(lambda _, r=row: self._remove_item_row(r))

            b_layout.addWidget(btn_edit)
            b_layout.addWidget(btn_del)

            self.items_table.setItem(row, 0, item_num)
            self.items_table.setItem(row, 1, item_prod)
            self.items_table.setItem(row, 2, item_qty)
            self.items_table.setItem(row, 3, item_rate)
            self.items_table.setItem(row, 4, item_tot)
            self.items_table.setCellWidget(row, 5, btn_frame)
            self.items_table.setRowHeight(row, 54)

        self.lbl_grand_summary.setText(
            f"Items: {len(self.receipt_items)}  |  Total Bricks: {total_qty:,.0f}  |  Grand Total: Rs. {grand_total:,.2f}"
        )
        req_h = 42 + (len(self.receipt_items) * 54) + 16
        final_h = max(115, req_h)
        self.items_table.setMinimumHeight(final_h)
        self.items_table.setFixedHeight(final_h)
        self.items_table.clearSelection()
        self.items_table.verticalScrollBar().setValue(0)
        self.items_table.scrollToTop()
        QTimer.singleShot(0, self._force_reset_items_table_scroll)

    def _force_reset_items_table_scroll(self):
        self.items_table.verticalScrollBar().setValue(0)
        if self.items_table.rowCount() > 0:
            item = self.items_table.item(0, 0)
            if item:
                self.items_table.scrollToItem(item, QTableWidget.PositionAtTop)

    def _edit_item_row(self, row: int):
        if 0 <= row < len(self.receipt_items):
            item = self.receipt_items[row]
            self.editing_item_index = row

            # Select product in combo
            for i in range(self.cmb_product.count()):
                p = self.cmb_product.itemData(i)
                if p and p["ProductID"] == item["ProductID"]:
                    self.cmb_product.setCurrentIndex(i)
                    break

            self.txt_quantity.setText(f"{item['Quantity']:g}")
            self.txt_rate.setText(f"{item['RatePer1000']:g}")
            self.btn_add_item.setText("✏️ Update Line Item")
            self.btn_cancel_edit_item.setVisible(True)
            self._calculate_line_total()

    def _remove_item_row(self, row: int):
        if 0 <= row < len(self.receipt_items):
            self.receipt_items.pop(row)
            self._render_items_table()
            self.is_dirty = True

    # --- SAVE, PRINT, NEW, DELETE ---
    def _on_save_clicked(self):
        cust_id = self.cmb_customer.currentData()
        if not cust_id:
            ToastNotification.warning(self, "Please select a Customer before saving.")
            return

        if not self.receipt_items or len(self.receipt_items) == 0:
            ToastNotification.warning(self, "Please add at least one product item to the sales receipt.")
            return

        qdate = self.dt_sale_date.date()
        sale_date = date(qdate.year(), qdate.month(), qdate.day())
        transport_mode = self.cmb_transport_mode.currentText().strip()
        driver_name = self.cmb_driver.currentText().strip()
        vehicle_no = self.txt_vehicle_no.text().strip()
        remarks = self.txt_remarks.text().strip()

        succ, msg, res = SalesService.save_sales_receipt(
            sale_date=sale_date,
            customer_id=cust_id,
            transport_mode=transport_mode,
            driver_name=driver_name,
            vehicle_number=vehicle_no,
            remarks=remarks,
            items_list=self.receipt_items,
            sale_id=self.current_sale_id,
            is_edit_mode=self.is_edit_mode
        )

        if succ and res:
            saved_inv = res["InvoiceNo"]
            ToastNotification.success(self, f"Sales Receipt '{saved_inv}' saved and posted to ledger successfully!")
            self._load_sales_history()
            self._reset_form_for_new_entry(show_toast=False)
            self.cmb_customer.setFocus()
        else:
            ToastNotification.error(self, f"Save Failed:\n{msg}")

    def _on_print_clicked(self):
        if not self.current_sale_id:
            ToastNotification.warning(self, "Please select or load a sales receipt from history to print.")
            return

        sale_dict = SalesService.get_sale_by_id(self.current_sale_id)
        if not sale_dict:
            ToastNotification.error(self, "Could not load sales receipt data for printing.")
            return

        win = SalesReceiptWindow(sale_dict, parent=self)
        win.exec()

    def _reset_form_for_new_entry(self, show_toast: bool = False):
        self.current_sale_id = None
        self.is_edit_mode = False
        self.is_dirty = False
        self.receipt_items.clear()
        self.editing_item_index = None

        self.txt_invoice_no.setText(SalesService.get_next_invoice_no())
        self.dt_sale_date.setDate(QDate.currentDate())
        self.txt_vehicle_no.clear()
        self.txt_remarks.clear()
        self.txt_quantity.clear()
        self.btn_add_item.setText("➕ Add to Receipt")
        self.btn_cancel_edit_item.setVisible(False)

        self._render_items_table()
        self._calculate_line_total()
        self._on_customer_changed()
        if show_toast:
            ToastNotification.info(self, "New sales receipt form ready.")

    def _on_new_clicked(self):
        self._reset_form_for_new_entry(show_toast=True)

    def _on_delete_clicked(self):
        if not self.current_sale_id:
            ToastNotification.warning(self, "No sales receipt is currently loaded to delete.")
            return

        choice = QMessageBox.question(
            self,
            "Confirm Delete Sales Receipt",
            f"Are you sure you want to delete and reverse Sales Receipt '{self.txt_invoice_no.text()}'?\n\nThis will remove the transaction from the Customer Khata Ledger.",
            QMessageBox.Yes | QMessageBox.No
        )
        if choice != QMessageBox.Yes:
            return

        succ, msg = SalesService.delete_sales_receipt(self.current_sale_id)
        if succ:
            ToastNotification.success(self, msg)
            self._reset_form_for_new_entry(show_toast=False)
            self._load_sales_history()
        else:
            ToastNotification.error(self, msg)

    def _on_close_clicked(self):
        self.close_requested.emit()

    # --- SALES HISTORY TABLE ---
    def _load_sales_history(self):
        q_from = self.dt_hist_from.date()
        q_to = self.dt_hist_to.date()
        f_date = date(q_from.year(), q_from.month(), q_from.day())
        t_date = date(q_to.year(), q_to.month(), q_to.day())
        search_txt = self.txt_hist_search.text().strip()

        sales = SalesService.search_sales(from_date=f_date, to_date=t_date, search_text=search_txt)
        self.history_table.setRowCount(len(sales))

        for row, s in enumerate(sales):
            item_inv = QTableWidgetItem(s["InvoiceNo"])
            item_inv.setFont(QFont("Segoe UI", 9, QFont.Bold))
            item_inv.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_inv.setData(Qt.UserRole, s["SaleID"])

            item_date = QTableWidgetItem(s["SaleDate"])
            item_date.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_cust = QTableWidgetItem(s["CustomerName"])
            item_cust.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_items = QTableWidgetItem(s["ItemsSummary"])
            item_items.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_tmode = QTableWidgetItem(s["TransportMode"])
            item_tmode.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_driver = QTableWidgetItem(s["DriverName"])
            item_driver.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            item_amt = QTableWidgetItem(f"Rs. {s['TotalAmount']:,.2f}")
            item_amt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_amt.setFont(QFont("Segoe UI", 9, QFont.Bold))

            item_user = QTableWidgetItem(s["CreatedBy"])
            item_user.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.history_table.setItem(row, 0, item_inv)
            self.history_table.setItem(row, 1, item_date)
            self.history_table.setItem(row, 2, item_cust)
            self.history_table.setItem(row, 3, item_items)
            self.history_table.setItem(row, 4, item_tmode)
            self.history_table.setItem(row, 5, item_driver)
            self.history_table.setItem(row, 6, item_amt)
            self.history_table.setItem(row, 7, item_user)
            self.history_table.setRowHeight(row, 46)

        self.history_table.verticalScrollBar().setValue(0)
        self.history_table.scrollToTop()

    def _on_history_row_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        inv_item = self.history_table.item(row, 0)
        if not inv_item:
            return

        sale_id = inv_item.data(Qt.UserRole)
        if not sale_id:
            return

        sale_dict = SalesService.get_sale_by_id(sale_id)
        if not sale_dict:
            ToastNotification.error(self, f"Could not load Sale #{sale_id}.")
            return

        # Load into form
        self.current_sale_id = sale_dict["SaleID"]
        self.is_edit_mode = True
        self.is_dirty = False

        self.txt_invoice_no.setText(sale_dict["InvoiceNo"])
        dt_parts = [int(p) for p in sale_dict["SaleDate"].split("-")]
        self.dt_sale_date.setDate(QDate(dt_parts[0], dt_parts[1], dt_parts[2]))

        # Customer combo
        for i in range(self.cmb_customer.count()):
            if self.cmb_customer.itemData(i) == sale_dict["CustomerID"]:
                self.cmb_customer.setCurrentIndex(i)
                break

        # Transport combo
        for i in range(self.cmb_transport_mode.count()):
            if self.cmb_transport_mode.itemText(i) == sale_dict["TransportMode"]:
                self.cmb_transport_mode.setCurrentIndex(i)
                break

        self.cmb_driver.setEditText(sale_dict["DriverName"])
        self.txt_vehicle_no.setText(sale_dict["VehicleNumber"])
        self.txt_remarks.setText(sale_dict["Remarks"])

        # Load line items
        self.receipt_items = []
        for d in sale_dict["Details"]:
            self.receipt_items.append({
                "ProductID": d["ProductID"],
                "ProductName": d["ProductName"],
                "Quantity": d["Quantity"],
                "RatePer1000": d["RatePer1000"],
                "TotalAmount": d["TotalAmount"]
            })

        self._render_items_table()
        self._on_customer_changed()
        ToastNotification.info(self, f"Loaded Sales Receipt '{sale_dict['InvoiceNo']}' for editing.")

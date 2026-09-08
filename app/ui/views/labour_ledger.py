from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDateEdit,
    QPushButton, QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, QDate, Signal

from app.ui.components.toast import ToastNotification
from app.services.ledger_service import LedgerService
from app.ui.views.payment_dialog import RecordPaymentDialog
from app.ui.views.ledger_report_window import LedgerReportWindow


class LabourLedgerView(QWidget):
    """
    Spacious, Fully-Scrollable Labour Ledger Selection Dashboard.
    Prevents UI overlap, adapts to any window size (minimized/maximized),
    and launches the dedicated popup Report Window.
    """

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_categories()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Main Outer Scroll Area - never allow horizontal scrolling
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { background-color: #F8FAFC; border: none; }")

        # Outer centering container
        outer_container = QWidget()
        outer_container.setStyleSheet("QWidget { background-color: transparent; }")
        outer_layout = QVBoxLayout(outer_container)
        outer_layout.setContentsMargins(14, 10, 14, 14)
        outer_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Centered Panel with comfortable max width (760px)
        panel = QWidget()
        panel.setMaximumWidth(760)
        panel.setMinimumWidth(320)
        panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(10)

        # 2. Header Banner Card
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1E3A8A, stop:1 #2563EB); "
            "border-radius: 10px; padding: 12px 18px; }"
        )
        h_vbox = QVBoxLayout(header_frame)
        h_vbox.setContentsMargins(0, 0, 0, 0)
        h_vbox.setSpacing(4)

        title = QLabel("📑 Customer & Labour Khata Ledger (کسٹمر اور لیبر کھاتہ)")
        title.setStyleSheet("font-size: 17px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Generate, print, and export professional A4 Khata statements for Customers & Labour accounts.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 11px; color: #BFDBFE; font-weight: 500;")
        h_vbox.addWidget(title)
        h_vbox.addWidget(subtitle)
        panel_layout.addWidget(header_frame)

        # 3. Criteria & Date Range Selection Card
        criteria_card = QFrame()
        criteria_card.setStyleSheet(
            "QFrame#criteriaCard { background-color: #FFFFFF; border: 1px solid #CBD5E1; "
            "border-radius: 10px; padding: 14px 18px; }"
        )
        criteria_card.setObjectName("criteriaCard")
        c_layout = QVBoxLayout(criteria_card)
        c_layout.setContentsMargins(2, 2, 2, 2)
        c_layout.setSpacing(10)

        card_title = QLabel("🎯 Select Account & Date Range (کھاتہ اور تاریخ کا انتخاب)")
        card_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #0F172A; border: none; background: transparent;")
        c_layout.addWidget(card_title)

        # Form Grid Layout (2x2)
        from PySide6.QtWidgets import QGridLayout
        form_grid = QGridLayout()
        form_grid.setHorizontalSpacing(16)
        form_grid.setVerticalSpacing(8)

        combo_style = (
            "QComboBox { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; "
            "padding: 5px 10px; font-size: 12px; font-weight: 600; color: #0F172A; min-height: 24px; } "
            "QComboBox:focus { border: 2px solid #0284C7; } "
            "QComboBox::drop-down { border: none; width: 22px; }"
        )
        date_style = (
            "QDateEdit { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; "
            "padding: 5px 10px; font-size: 12px; font-weight: 600; color: #0F172A; min-height: 24px; } "
            "QDateEdit:focus { border: 2px solid #0284C7; } "
            "QDateEdit::drop-down { border: none; width: 22px; }"
        )
        lbl_style = "font-weight: 700; font-size: 11px; color: #334155; border: none; background: transparent;"

        # Row 0: Category & Worker
        lbl_cat = QLabel("Account Category (کھاتہ قسم):")
        lbl_cat.setStyleSheet(lbl_style)
        self.cmb_category = QComboBox()
        self.cmb_category.setStyleSheet(combo_style)
        self.cmb_category.currentTextChanged.connect(self._on_category_changed)

        lbl_worker = QLabel("Select Account / Customer / Labourer (کھاتہ دار):")
        lbl_worker.setStyleSheet(lbl_style)
        self.cmb_worker = QComboBox()
        self.cmb_worker.setStyleSheet(combo_style)
        self.cmb_worker.currentIndexChanged.connect(self._on_worker_changed)

        form_grid.addWidget(lbl_cat, 0, 0)
        form_grid.addWidget(self.cmb_category, 1, 0)
        form_grid.addWidget(lbl_worker, 0, 1)
        form_grid.addWidget(self.cmb_worker, 1, 1)

        # Row 1: From Date & To Date
        lbl_from = QLabel("From Date (تاریخ آغاز):")
        lbl_from.setStyleSheet(lbl_style)
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd")
        self.dt_from.setStyleSheet(date_style)
        today = QDate.currentDate()
        self.dt_from.setDate(QDate(today.year(), today.month(), 1))

        lbl_to = QLabel("To Date (تاریخ اختتام):")
        lbl_to.setStyleSheet(lbl_style)
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd")
        self.dt_to.setDate(today)
        self.dt_to.setStyleSheet(date_style)

        form_grid.addWidget(lbl_from, 2, 0)
        form_grid.addWidget(self.dt_from, 3, 0)
        form_grid.addWidget(lbl_to, 2, 1)
        form_grid.addWidget(self.dt_to, 3, 1)

        c_layout.addLayout(form_grid)

        # Quick Date Presets Row
        presets_layout = QHBoxLayout()
        presets_layout.setContentsMargins(0, 4, 0, 0)
        presets_layout.setSpacing(8)

        lbl_presets = QLabel("Quick Date:")
        lbl_presets.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; border: none; background: transparent;")
        presets_layout.addWidget(lbl_presets)

        preset_btn_style = (
            "QPushButton { background-color: #F1F5F9; color: #475569; font-weight: 600; font-size: 11px; "
            "border: 1px solid #CBD5E1; border-radius: 5px; padding: 4px 10px; } "
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }"
        )

        btn_this_month = QPushButton("This Month")
        btn_this_month.setStyleSheet(preset_btn_style)
        btn_this_month.setCursor(Qt.PointingHandCursor)
        btn_this_month.clicked.connect(self._set_preset_this_month)
        presets_layout.addWidget(btn_this_month)

        btn_last_30 = QPushButton("Last 30 Days")
        btn_last_30.setStyleSheet(preset_btn_style)
        btn_last_30.setCursor(Qt.PointingHandCursor)
        btn_last_30.clicked.connect(self._set_preset_last_30)
        presets_layout.addWidget(btn_last_30)

        btn_this_year = QPushButton("Full Year")
        btn_this_year.setStyleSheet(preset_btn_style)
        btn_this_year.setCursor(Qt.PointingHandCursor)
        btn_this_year.clicked.connect(self._set_preset_full_year)
        presets_layout.addWidget(btn_this_year)

        presets_layout.addStretch()
        c_layout.addLayout(presets_layout)

        panel_layout.addWidget(criteria_card)

        # 4. Selected Labourer / Account Details Card
        info_card = QFrame()
        info_card.setStyleSheet(
            "QFrame#infoCard { background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 10px; padding: 12px 16px; }"
        )
        info_card.setObjectName("infoCard")
        info_vlayout = QVBoxLayout(info_card)
        info_vlayout.setContentsMargins(2, 2, 2, 2)
        info_vlayout.setSpacing(8)

        info_header_row = QHBoxLayout()
        info_header_row.setContentsMargins(0, 0, 0, 0)
        info_title = QLabel("👤 Selected Account & Live Khata Balance")
        info_title.setStyleSheet("font-size: 13px; font-weight: 800; color: #1E293B; border: none; background: transparent;")
        info_header_row.addWidget(info_title)
        info_header_row.addStretch()

        self.lbl_info_balance = QLabel("Balance: Loading...")
        self.lbl_info_balance.setStyleSheet(
            "font-size: 12px; font-weight: 800; color: #0284C7; background-color: #F0F9FF; "
            "border: 1px solid #BAE6FD; border-radius: 6px; padding: 3px 10px;"
        )
        info_header_row.addWidget(self.lbl_info_balance)
        info_vlayout.addLayout(info_header_row)

        # Details Grid (Compact 4-column item strip)
        info_grid = QHBoxLayout()
        info_grid.setSpacing(8)

        # Stat Item 1: Name
        box_name = QFrame()
        box_name.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 8px; }")
        bn_layout = QVBoxLayout(box_name)
        bn_layout.setContentsMargins(0, 0, 0, 0)
        bn_layout.setSpacing(2)
        lbl_h_name = QLabel("Account Name:")
        lbl_h_name.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_name = QLabel("—")
        self.lbl_info_name.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A; border: none;")
        bn_layout.addWidget(lbl_h_name)
        bn_layout.addWidget(self.lbl_info_name)

        # Stat Item 2: Worker ID
        box_id = QFrame()
        box_id.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 8px; }")
        bi_layout = QVBoxLayout(box_id)
        bi_layout.setContentsMargins(0, 0, 0, 0)
        bi_layout.setSpacing(2)
        lbl_h_id = QLabel("Account ID:")
        lbl_h_id.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_id = QLabel("—")
        self.lbl_info_id.setStyleSheet("font-size: 12px; font-weight: 800; color: #0284C7; border: none;")
        bi_layout.addWidget(lbl_h_id)
        bi_layout.addWidget(self.lbl_info_id)

        # Stat Item 3: CNIC
        box_cnic = QFrame()
        box_cnic.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 8px; }")
        bc_layout = QVBoxLayout(box_cnic)
        bc_layout.setContentsMargins(0, 0, 0, 0)
        bc_layout.setSpacing(2)
        lbl_h_cnic = QLabel("CNIC Number:")
        lbl_h_cnic.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_cnic = QLabel("—")
        self.lbl_info_cnic.setStyleSheet("font-size: 11px; font-weight: 700; color: #334155; border: none;")
        bc_layout.addWidget(lbl_h_cnic)
        bc_layout.addWidget(self.lbl_info_cnic)

        # Stat Item 4: Mobile
        box_mob = QFrame()
        box_mob.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 6px 8px; }")
        bm_layout = QVBoxLayout(box_mob)
        bm_layout.setContentsMargins(0, 0, 0, 0)
        bm_layout.setSpacing(2)
        lbl_h_mob = QLabel("Mobile Number:")
        lbl_h_mob.setStyleSheet("font-size: 10px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_mobile = QLabel("—")
        self.lbl_info_mobile.setStyleSheet("font-size: 11px; font-weight: 700; color: #334155; border: none;")
        bm_layout.addWidget(lbl_h_mob)
        bm_layout.addWidget(self.lbl_info_mobile)

        info_grid.addWidget(box_name, stretch=2)
        info_grid.addWidget(box_id, stretch=1)
        info_grid.addWidget(box_cnic, stretch=1)
        info_grid.addWidget(box_mob, stretch=1)
        info_vlayout.addLayout(info_grid)

        panel_layout.addWidget(info_card)

        # 5. Primary Action Button & Shortcuts
        btn_box = QVBoxLayout()
        btn_box.setContentsMargins(0, 4, 0, 0)
        btn_box.setSpacing(8)

        self.btn_generate = QPushButton("📄 Generate & View Ledger Report (کھاتہ رپورٹ دیکھیں)")
        self.btn_generate.setMinimumHeight(44)
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #0369A1); "
            "color: #FFFFFF; font-weight: 800; font-size: 14px; border-radius: 8px; padding: 0 24px; border: none; } "
            "QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #075985); } "
            "QPushButton:pressed { background-color: #0c4a6e; }"
        )
        self.btn_generate.clicked.connect(self.open_ledger_report_window)
        btn_box.addWidget(self.btn_generate)

        # Secondary Transaction Shortcuts Row
        shortcuts_row = QHBoxLayout()
        shortcuts_row.setSpacing(12)

        self.btn_amdan_akrajat = QPushButton("💰 New Amdan / Akrajat Entry")
        self.btn_amdan_akrajat.setMinimumHeight(38)
        self.btn_amdan_akrajat.setCursor(Qt.PointingHandCursor)
        self.btn_amdan_akrajat.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #0284C7; font-weight: 700; font-size: 12px; "
            "border: 1px solid #BAE6FD; border-radius: 8px; padding: 0 16px; } "
            "QPushButton:hover { background-color: #F0F9FF; border-color: #0284C7; }"
        )
        self.btn_amdan_akrajat.clicked.connect(self._on_open_amdan_akrajat)
        shortcuts_row.addWidget(self.btn_amdan_akrajat, stretch=1)

        self.btn_payment = QPushButton("💸 Record Quick Payment / Advance")
        self.btn_payment.setMinimumHeight(38)
        self.btn_payment.setCursor(Qt.PointingHandCursor)
        self.btn_payment.setStyleSheet(
            "QPushButton { background-color: #FFFFFF; color: #16A34A; font-weight: 700; font-size: 12px; "
            "border: 1px solid #BBF7D0; border-radius: 8px; padding: 0 16px; } "
            "QPushButton:hover { background-color: #F0FDF4; border-color: #16A34A; }"
        )
        self.btn_payment.clicked.connect(self._on_record_payment)
        shortcuts_row.addWidget(self.btn_payment, stretch=1)

        btn_box.addLayout(shortcuts_row)
        panel_layout.addLayout(btn_box)

        outer_layout.addWidget(panel)
        scroll_area.setWidget(outer_container)
        root_layout.addWidget(scroll_area)

    def _load_categories(self):
        categories = LedgerService.get_supported_categories()
        self.cmb_category.clear()
        self.cmb_category.addItems(categories)
        if categories:
            self._on_category_changed(categories[0])

    def _on_category_changed(self, category_name: str):
        workers = LedgerService.get_workers_by_category(category_name)
        self.cmb_worker.clear()
        for w in workers:
            display_text = f"{w['WorkerID']} — {w['EnglishName']}"
            if w.get('UrduName'):
                display_text += f" ({w['UrduName']})"
            self.cmb_worker.addItem(display_text, userData=w)

        if not workers:
            self.cmb_worker.addItem("No active labourers found in this category", userData=None)

        self._on_worker_changed()

    def _set_preset_this_month(self):
        today = QDate.currentDate()
        self.dt_from.setDate(QDate(today.year(), today.month(), 1))
        self.dt_to.setDate(today)

    def _set_preset_last_30(self):
        today = QDate.currentDate()
        self.dt_from.setDate(today.addDays(-30))
        self.dt_to.setDate(today)

    def _set_preset_full_year(self):
        today = QDate.currentDate()
        self.dt_from.setDate(QDate(today.year(), 1, 1))
        self.dt_to.setDate(today)

    def _on_worker_changed(self):
        w_data = self.cmb_worker.currentData()
        if w_data and w_data.get("WorkerID"):
            name = w_data.get('EnglishName', '—')
            if w_data.get('UrduName'):
                name += f" ({w_data['UrduName']})"
            self.lbl_info_name.setText(name)
            self.lbl_info_id.setText(w_data.get('WorkerID', '—'))
            self.lbl_info_cnic.setText(w_data.get('CNIC') or "Not Provided")
            self.lbl_info_mobile.setText(w_data.get('Mobile') or "Not Provided")

            # Calculate live balance
            try:
                worker_id = w_data["WorkerID"]
                ledger_data = LedgerService.calculate_worker_ledger(worker_id, date(2000, 1, 1), date.today())
                if ledger_data:
                    status = ledger_data.get("statement_status", "BALANCED")
                    closing = ledger_data.get("closing_balance", 0.0)
                    if status == "RECEIVABLE":
                        self.lbl_info_balance.setText(f"🔴 Receivable (باقی): Rs. {abs(closing):,.2f}")
                        self.lbl_info_balance.setStyleSheet(
                            "font-size: 13px; font-weight: 800; color: #DC2626; background-color: #FEF2F2; "
                            "border: 1px solid #FECACA; border-radius: 6px; padding: 4px 12px;"
                        )
                    elif status == "ADVANCE":
                        self.lbl_info_balance.setText(f"🟢 Advance (پیشگی): Rs. {abs(closing):,.2f}")
                        self.lbl_info_balance.setStyleSheet(
                            "font-size: 13px; font-weight: 800; color: #16A34A; background-color: #F0FDF4; "
                            "border: 1px solid #BBF7D0; border-radius: 6px; padding: 4px 12px;"
                        )
                    elif status == "PAYABLE":
                        self.lbl_info_balance.setText(f"🟠 Payable (واجب الادا): Rs. {abs(closing):,.2f}")
                        self.lbl_info_balance.setStyleSheet(
                            "font-size: 13px; font-weight: 800; color: #D97706; background-color: #FFFBEB; "
                            "border: 1px solid #FDE68A; border-radius: 6px; padding: 4px 12px;"
                        )
                    else:
                        self.lbl_info_balance.setText("⚪ Zero Balance (0.00)")
                        self.lbl_info_balance.setStyleSheet(
                            "font-size: 13px; font-weight: 800; color: #475569; background-color: #F1F5F9; "
                            "border: 1px solid #CBD5E1; border-radius: 6px; padding: 4px 12px;"
                        )
                else:
                    self.lbl_info_balance.setText("Balance: —")
            except Exception:
                self.lbl_info_balance.setText("Balance: —")
        else:
            self.lbl_info_name.setText("—")
            self.lbl_info_id.setText("—")
            self.lbl_info_cnic.setText("—")
            self.lbl_info_mobile.setText("—")
            self.lbl_info_balance.setText("Balance: —")
            self.lbl_info_balance.setStyleSheet(
                "font-size: 13px; font-weight: 800; color: #64748B; background-color: #F1F5F9; "
                "border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px 12px;"
            )

    def open_ledger_report_window(self):
        w_data = self.cmb_worker.currentData()
        if not w_data:
            ToastNotification.show_error(self, "Selection Required", "Please select a valid labourer.")
            return

        from_date = self.dt_from.date().toPython()
        to_date = self.dt_to.date().toPython()

        if from_date > to_date:
            ToastNotification.show_error(self, "Invalid Date Range", "From Date cannot be greater than To Date.")
            return

        worker_id = w_data["WorkerID"]
        ledger_data = LedgerService.calculate_worker_ledger(worker_id, from_date, to_date)
        if not ledger_data:
            ToastNotification.show_error(self, "Data Error", f"Could not load ledger for worker {worker_id}.")
            return

        # Open dedicated popup report window
        report_win = LedgerReportWindow(ledger_data, self)
        report_win.exec()

    def _on_record_payment(self):
        w_data = self.cmb_worker.currentData()
        if not w_data:
            ToastNotification.show_error(self, "Selection Required", "Please select a valid labourer first.")
            return

        dlg = RecordPaymentDialog(w_data["WorkerID"], w_data["EnglishName"], self)
        dlg.exec()

    def _on_open_amdan_akrajat(self):
        main_win = self.window()
        if hasattr(main_win, "open_money_transactions_tab"):
            main_win.open_money_transactions_tab()

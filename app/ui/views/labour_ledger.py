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

        # 1. Main Outer Scroll Area to ensure scrollability on all screens
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: #F8FAFC; border: none; }")

        container = QWidget()
        container.setStyleSheet("QWidget { background-color: transparent; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(18, 18, 18, 18)
        container_layout.setSpacing(16)

        # 2. Header Banner Card
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "QFrame { background-color: #1E3A8A; border-radius: 10px; padding: 18px 24px; }"
        )
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title = QLabel("📑 Customer & Labour Khata Ledger (کسٹمر اور لیبر کھاتہ)")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #FFFFFF;")
        subtitle = QLabel("Generate, print, and export professional A4 Khata statements for Customers, Pathera, Bahri Wala, and Nakkasi Wala accounts.")
        subtitle.setStyleSheet("font-size: 13px; color: #93C5FD; font-weight: 500;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        h_layout.addLayout(title_box)
        h_layout.addStretch()

        self.btn_payment = QPushButton("💸 Record Payment / Advance")
        self.btn_payment.setMinimumHeight(40)
        self.btn_payment.setCursor(Qt.PointingHandCursor)
        self.btn_payment.setStyleSheet(
            "QPushButton { background-color: #16A34A; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 8px; padding: 0 20px; border: none; } "
            "QPushButton:hover { background-color: #15803D; }"
        )
        self.btn_payment.clicked.connect(self._on_record_payment)
        h_layout.addWidget(self.btn_payment)

        container_layout.addWidget(header_frame)

        # 3. Criteria & Date Range Selection Card
        criteria_card = QFrame()
        criteria_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 10px; padding: 18px 22px; }"
        )
        c_main_layout = QVBoxLayout(criteria_card)
        c_main_layout.setContentsMargins(4, 4, 4, 4)
        c_main_layout.setSpacing(14)

        card_title = QLabel("📋 Ledger Criteria & Date Range")
        card_title.setStyleSheet("font-size: 15px; font-weight: 800; color: #1E293B; border: none; background: transparent;")
        c_main_layout.addWidget(card_title)

        # Two Side-by-Side Column Form
        form_cols_layout = QHBoxLayout()
        form_cols_layout.setSpacing(24)

        # --- Column 1: Category & From Date ---
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(6)

        lbl_cat = QLabel("Account Category:")
        lbl_cat.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none; background: transparent;")
        self.cmb_category = QComboBox()
        self.cmb_category.setMinimumHeight(38)
        self.cmb_category.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 10px;")
        self.cmb_category.currentTextChanged.connect(self._on_category_changed)

        lbl_from = QLabel("From Date (Period Start):")
        lbl_from.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none; background: transparent;")
        self.dt_from = QDateEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("yyyy-MM-dd")
        self.dt_from.setMinimumHeight(38)
        self.dt_from.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 10px;")
        today = QDate.currentDate()
        self.dt_from.setDate(QDate(today.year(), today.month(), 1))

        col1_layout.addWidget(lbl_cat)
        col1_layout.addWidget(self.cmb_category)
        col1_layout.addSpacing(10)
        col1_layout.addWidget(lbl_from)
        col1_layout.addWidget(self.dt_from)

        # --- Column 2: Labourer & To Date ---
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(6)

        lbl_worker = QLabel("Select Account / Customer / Labourer:")
        lbl_worker.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none; background: transparent;")
        self.cmb_worker = QComboBox()
        self.cmb_worker.setMinimumHeight(38)
        self.cmb_worker.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 10px;")
        self.cmb_worker.currentIndexChanged.connect(self._on_worker_changed)

        lbl_to = QLabel("To Date (Period End):")
        lbl_to.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none; background: transparent;")
        self.dt_to = QDateEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("yyyy-MM-dd")
        self.dt_to.setDate(today)
        self.dt_to.setMinimumHeight(38)
        self.dt_to.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 10px;")

        col2_layout.addWidget(lbl_worker)
        col2_layout.addWidget(self.cmb_worker)
        col2_layout.addSpacing(10)
        col2_layout.addWidget(lbl_to)
        col2_layout.addWidget(self.dt_to)

        form_cols_layout.addLayout(col1_layout, stretch=1)
        form_cols_layout.addLayout(col2_layout, stretch=1)
        c_main_layout.addLayout(form_cols_layout)

        container_layout.addWidget(criteria_card)

        # 4. Selected Labourer Details Card
        info_card = QFrame()
        info_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px 20px; }"
        )
        info_vlayout = QVBoxLayout(info_card)
        info_vlayout.setContentsMargins(4, 4, 4, 4)
        info_vlayout.setSpacing(10)

        info_title = QLabel("👤 Selected Labourer Information")
        info_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #475569; border: none; background: transparent;")
        info_vlayout.addWidget(info_title)

        info_grid = QHBoxLayout()
        info_grid.setSpacing(16)

        # Stat Item 1: Name
        box_name = QFrame()
        box_name.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; }")
        bn_layout = QVBoxLayout(box_name)
        bn_layout.setContentsMargins(0, 0, 0, 0)
        bn_layout.setSpacing(2)
        lbl_h_name = QLabel("Full Name:")
        lbl_h_name.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_name = QLabel("—")
        self.lbl_info_name.setStyleSheet("font-size: 14px; font-weight: 800; color: #0F172A; border: none;")
        bn_layout.addWidget(lbl_h_name)
        bn_layout.addWidget(self.lbl_info_name)

        # Stat Item 2: Worker ID
        box_id = QFrame()
        box_id.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; }")
        bi_layout = QVBoxLayout(box_id)
        bi_layout.setContentsMargins(0, 0, 0, 0)
        bi_layout.setSpacing(2)
        lbl_h_id = QLabel("Worker ID:")
        lbl_h_id.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_id = QLabel("—")
        self.lbl_info_id.setStyleSheet("font-size: 14px; font-weight: 800; color: #0284C7; border: none;")
        bi_layout.addWidget(lbl_h_id)
        bi_layout.addWidget(self.lbl_info_id)

        # Stat Item 3: CNIC
        box_cnic = QFrame()
        box_cnic.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; }")
        bc_layout = QVBoxLayout(box_cnic)
        bc_layout.setContentsMargins(0, 0, 0, 0)
        bc_layout.setSpacing(2)
        lbl_h_cnic = QLabel("CNIC Number:")
        lbl_h_cnic.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_cnic = QLabel("—")
        self.lbl_info_cnic.setStyleSheet("font-size: 14px; font-weight: 700; color: #334155; border: none;")
        bc_layout.addWidget(lbl_h_cnic)
        bc_layout.addWidget(self.lbl_info_cnic)

        # Stat Item 4: Mobile
        box_mob = QFrame()
        box_mob.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 10px; }")
        bm_layout = QVBoxLayout(box_mob)
        bm_layout.setContentsMargins(0, 0, 0, 0)
        bm_layout.setSpacing(2)
        lbl_h_mob = QLabel("Mobile Number:")
        lbl_h_mob.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; border: none;")
        self.lbl_info_mobile = QLabel("—")
        self.lbl_info_mobile.setStyleSheet("font-size: 14px; font-weight: 700; color: #334155; border: none;")
        bm_layout.addWidget(lbl_h_mob)
        bm_layout.addWidget(self.lbl_info_mobile)

        info_grid.addWidget(box_name, stretch=1)
        info_grid.addWidget(box_id, stretch=1)
        info_grid.addWidget(box_cnic, stretch=1)
        info_grid.addWidget(box_mob, stretch=1)
        info_vlayout.addLayout(info_grid)

        container_layout.addWidget(info_card)

        # 5. Primary Action Button
        btn_box = QHBoxLayout()
        btn_box.setContentsMargins(0, 8, 0, 8)
        btn_box.addStretch()

        self.btn_generate = QPushButton("📄 Generate & View Ledger Report")
        self.btn_generate.setMinimumHeight(48)
        self.btn_generate.setCursor(Qt.PointingHandCursor)
        self.btn_generate.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 800; font-size: 15px; border-radius: 8px; padding: 0 36px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_generate.clicked.connect(self.open_ledger_report_window)
        btn_box.addWidget(self.btn_generate)
        btn_box.addStretch()

        container_layout.addLayout(btn_box)
        container_layout.addStretch()

        scroll_area.setWidget(container)
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

    def _on_worker_changed(self):
        w_data = self.cmb_worker.currentData()
        if w_data:
            self.lbl_info_name.setText(w_data.get('EnglishName', '—'))
            self.lbl_info_id.setText(w_data.get('WorkerID', '—'))
            self.lbl_info_cnic.setText(w_data.get('CNIC', '—'))
            self.lbl_info_mobile.setText(w_data.get('Mobile', '—'))
        else:
            self.lbl_info_name.setText("—")
            self.lbl_info_id.setText("—")
            self.lbl_info_cnic.setText("—")
            self.lbl_info_mobile.setText("—")

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

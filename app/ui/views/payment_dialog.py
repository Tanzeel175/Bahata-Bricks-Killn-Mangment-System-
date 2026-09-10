from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QDate
from app.ui.components.formatted_inputs import CurrencyEdit
from app.ui.components.toast import ToastNotification
from app.services.ledger_service import LedgerService


class RecordPaymentDialog(QDialog):
    """
    Spacious & Scrollable Modal Dialog to record cash or advance payments.
    Prevents UI element overlap and adapts cleanly to any screen size.
    """

    def __init__(self, worker_id: str, worker_name: str, parent=None):
        super().__init__(parent)
        self.worker_id = worker_id
        self.worker_name = worker_name
        self.setWindowTitle(f"💸 Record Payment — {worker_name} ({worker_id})")
        self.setMinimumSize(480, 520)
        self.resize(520, 580)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")
        self._init_ui()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(10)

        # 1. Outer Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("QWidget { background-color: transparent; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(14)

        # 2. Header Info Card
        header = QFrame()
        header.setStyleSheet("QFrame { background-color: #EFF6FF; border-radius: 8px; padding: 14px 18px; border: 1px solid #BFDBFE; }")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(4)

        title = QLabel(f"Record Payment for {self.worker_name}")
        title.setStyleSheet("font-size: 15px; font-weight: 800; color: #1E40AF; border: none;")
        sub = QLabel(f"Worker ID: {self.worker_id}")
        sub.setStyleSheet("font-size: 12px; color: #3B82F6; font-weight: 600; border: none;")
        h_layout.addWidget(title)
        h_layout.addWidget(sub)
        container_layout.addWidget(header)

        # 3. Form Card (Clean QFrame)
        form_card = QFrame()
        form_card.setStyleSheet("QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 16px 20px; }")
        f_layout = QVBoxLayout(form_card)
        f_layout.setContentsMargins(4, 4, 4, 4)
        f_layout.setSpacing(6)

        form_title = QLabel("Payment Information")
        form_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #1E293B; border: none; margin-bottom: 8px;")
        f_layout.addWidget(form_title)

        # Field 1: Payment Date
        lbl_date = QLabel("Payment Date:")
        lbl_date.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none;")
        self.dt_payment_date = QDateEdit()
        self.dt_payment_date.setCalendarPopup(True)
        self.dt_payment_date.setDate(QDate.currentDate())
        self.dt_payment_date.setDisplayFormat("yyyy-MM-dd")
        self.dt_payment_date.setMinimumHeight(38)
        self.dt_payment_date.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 8px;")
        f_layout.addWidget(lbl_date)
        f_layout.addWidget(self.dt_payment_date)
        f_layout.addSpacing(8)

        # Field 2: Payment Type Dropdown
        lbl_type = QLabel("Payment Type:")
        lbl_type.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none;")
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Cash Payment", "Advance Payment", "Bank Transfer", "Deduction", "Other"])
        self.cmb_type.setMinimumHeight(38)
        self.cmb_type.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 8px;")
        f_layout.addWidget(lbl_type)
        f_layout.addWidget(self.cmb_type)
        f_layout.addSpacing(8)

        # Field 3: Amount Input
        lbl_amount = QLabel("Amount (PKR):")
        lbl_amount.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none;")
        self.txt_amount = CurrencyEdit()
        self.txt_amount.setPlaceholderText("0.00")
        self.txt_amount.setMinimumHeight(38)
        self.txt_amount.setStyleSheet("font-size: 14px; font-weight: 700; padding-left: 8px;")
        self.txt_amount.returnPressed.connect(self._on_save)
        f_layout.addWidget(lbl_amount)
        f_layout.addWidget(self.txt_amount)
        f_layout.addSpacing(8)

        # Field 4: Remarks
        lbl_remarks = QLabel("Remarks / Description:")
        lbl_remarks.setStyleSheet("font-weight: 700; font-size: 12px; color: #334155; border: none;")
        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Optional notes (e.g. Weekly Cash Advance)")
        self.txt_remarks.setMinimumHeight(38)
        self.txt_remarks.setStyleSheet("font-size: 13px; padding-left: 8px;")
        self.txt_remarks.returnPressed.connect(self._on_save)
        f_layout.addWidget(lbl_remarks)
        f_layout.addWidget(self.txt_remarks)

        container_layout.addWidget(form_card)

        scroll_area.setWidget(container)
        root_layout.addWidget(scroll_area)

        # 4. Action Buttons Footer
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(8, 6, 8, 6)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setAutoDefault(False)
        self.btn_cancel.setDefault(False)
        self.btn_cancel.setMinimumHeight(38)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet("QPushButton { background-color: #F1F5F9; color: #475569; font-weight: 700; font-size: 13px; border-radius: 6px; padding: 0 20px; border: 1px solid #CBD5E1; } QPushButton:hover { background-color: #E2E8F0; }")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("💾 Save Payment")
        self.btn_save.setAutoDefault(True)
        self.btn_save.setDefault(True)
        self.btn_save.setMinimumHeight(38)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("QPushButton { background-color: #16A34A; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 6px; padding: 0 24px; border: none; } QPushButton:hover { background-color: #15803D; }")
        self.btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        root_layout.addLayout(btn_layout)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._on_save()
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_save(self):
        amount = self.txt_amount.get_value()
        if amount <= 0:
            ToastNotification.show_error(self, "Invalid Amount", "Please enter a payment amount greater than zero.")
            return

        p_date = self.dt_payment_date.date().toPython()
        p_type = self.cmb_type.currentText()
        remarks = self.txt_remarks.text().strip()

        succ, msg = LedgerService.save_labour_payment(
            worker_id=self.worker_id,
            payment_date=p_date,
            amount=amount,
            payment_type=p_type,
            remarks=remarks
        )

        if succ:
            ToastNotification.show_success(self, "Payment Saved", msg)
            self.accept()
        else:
            ToastNotification.show_error(self, "Save Failed", msg)

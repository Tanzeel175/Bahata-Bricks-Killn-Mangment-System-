from datetime import date
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt, QDate, Signal
from app.ui.components.formatted_inputs import CurrencyEdit
from app.ui.components.toast import ToastNotification
from app.services.ledger_service import LedgerService
from app.database.connection import get_db_session
from app.database.schema import LabourAccount
from app.ui.styles import configure_date_edit


class RecordPaymentDialog(QDialog):
    """
    Spacious & Scrollable Modal Dialog to record cash or advance payments.
    Prevents UI element overlap and adapts cleanly to any screen size.
    """
    payment_saved = Signal()

    def __init__(self, worker_id: str = "", worker_name: str = "", parent=None):
        super().__init__(parent)
        self.worker_id = worker_id or ""
        self.worker_name = worker_name or ""
        self.cmb_worker_select = None

        if self.worker_id and not self.worker_name:
            try:
                with get_db_session() as session:
                    acc = session.query(LabourAccount).filter_by(WorkerID=self.worker_id).first()
                    if acc:
                        self.worker_name = acc.EnglishName or self.worker_id
            except Exception:
                self.worker_name = self.worker_id

        disp_title = f" — {self.worker_name} ({self.worker_id})" if self.worker_id else ""
        self.setWindowTitle(f"Record Payment{disp_title}")
        self.setMinimumSize(480, 520)
        self.resize(520, 580)
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
        container.setObjectName("paymentDialogContainer")
        container.setStyleSheet("#paymentDialogContainer { background-color: transparent; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(8, 8, 8, 8)
        container_layout.setSpacing(14)

        # 2. Header Info Card
        from app.ui.theme_manager import theme_mgr
        is_dark = theme_mgr.is_dark_mode()

        header = QFrame()
        header.setObjectName("headerCard")
        hdr_bg = "#1E293B" if is_dark else "#EFF6FF"
        hdr_border = "#334155" if is_dark else "#BFDBFE"
        header.setStyleSheet(f"QFrame#headerCard {{ background-color: {hdr_bg}; border-radius: 8px; padding: 14px 18px; border: 1px solid {hdr_border}; }}")
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(4)

        title_color = "#38BDF8" if is_dark else "#1E40AF"
        sub_color = "#93C5FD" if is_dark else "#3B82F6"
        if self.worker_id:
            title = QLabel(f"Record Payment for {self.worker_name}")
            sub = QLabel(f"Worker / Account ID: {self.worker_id}")
        else:
            title = QLabel("Record Payment / Advance (ادائیگی درج کریں)")
            sub = QLabel("Select an account and enter payment details")
        title.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {title_color}; border: none;")
        sub.setStyleSheet(f"font-size: 12px; color: {sub_color}; font-weight: 600; border: none;")
        h_layout.addWidget(title)
        h_layout.addWidget(sub)
        container_layout.addWidget(header)

        # 3. Form Card (Theme-adaptive QFrame)
        form_card = QFrame()
        form_card.setObjectName("form_card")
        form_card.setProperty("class", "card-panel")
        f_layout = QVBoxLayout(form_card)
        f_layout.setContentsMargins(14, 14, 14, 14)
        f_layout.setSpacing(6)

        form_title = QLabel("Payment Information")
        form_title.setProperty("class", "heading-secondary")
        form_title.setStyleSheet("font-size: 14px; font-weight: 800; border: none; margin-bottom: 8px;")
        f_layout.addWidget(form_title)

        if not self.worker_id:
            lbl_w = QLabel("Select Account / Worker (کھاتہ منتخب کریں):")
            lbl_w.setStyleSheet("font-weight: 700; font-size: 12px; border: none;")
            self.cmb_worker_select = QComboBox()
            self.cmb_worker_select.setMinimumHeight(38)
            self.cmb_worker_select.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 8px;")
            try:
                with get_db_session() as session:
                    accounts = session.query(LabourAccount).filter_by(IsActive=True, IsOmitted=False).order_by(LabourAccount.EnglishName).all()
                    for a in accounts:
                        type_str = f" ({a.account_type.AccountTypeName})" if a.account_type else ""
                        self.cmb_worker_select.addItem(f"{a.EnglishName}{type_str} — {a.WorkerID}", a.WorkerID)
            except Exception:
                pass
            f_layout.addWidget(lbl_w)
            f_layout.addWidget(self.cmb_worker_select)
            f_layout.addSpacing(8)

        # Field 1: Payment Date
        lbl_date = QLabel("Payment Date:")
        lbl_date.setStyleSheet("font-weight: 700; font-size: 12px; border: none;")
        self.dt_payment_date = QDateEdit()
        self.dt_payment_date.setDate(QDate.currentDate())
        configure_date_edit(self.dt_payment_date, min_width=130, min_height=38)
        f_layout.addWidget(lbl_date)
        f_layout.addWidget(self.dt_payment_date)
        f_layout.addSpacing(8)

        # Field 2: Payment Type Dropdown
        lbl_type = QLabel("Payment Type:")
        lbl_type.setStyleSheet("font-weight: 700; font-size: 12px; border: none;")
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Cash Payment", "Advance Payment", "Bank Transfer", "Deduction", "Other"])
        self.cmb_type.setMinimumHeight(38)
        self.cmb_type.setStyleSheet("font-size: 13px; font-weight: 600; padding-left: 8px;")
        f_layout.addWidget(lbl_type)
        f_layout.addWidget(self.cmb_type)
        f_layout.addSpacing(8)

        # Field 3: Amount Input
        lbl_amount = QLabel("Amount (PKR):")
        lbl_amount.setStyleSheet("font-weight: 700; font-size: 12px; border: none;")
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
        lbl_remarks.setStyleSheet("font-weight: 700; font-size: 12px; border: none;")
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
        self.btn_cancel.setProperty("class", "btn-secondary")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Save Payment")
        self.btn_save.setAutoDefault(True)
        self.btn_save.setDefault(True)
        self.btn_save.setMinimumHeight(38)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setProperty("class", "btn-success")
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
        target_worker_id = self.worker_id
        if not target_worker_id and self.cmb_worker_select:
            target_worker_id = self.cmb_worker_select.currentData()

        if not target_worker_id:
            ToastNotification.show_error(self, "Selection Required", "Please select a worker or account.")
            return

        amount = self.txt_amount.get_value()
        if amount <= 0:
            ToastNotification.show_error(self, "Invalid Amount", "Please enter a payment amount greater than zero.")
            return

        p_date = self.dt_payment_date.date().toPython()
        p_type = self.cmb_type.currentText()
        remarks = self.txt_remarks.text().strip()

        succ, msg = LedgerService.save_labour_payment(
            worker_id=target_worker_id,
            payment_date=p_date,
            amount=amount,
            payment_type=p_type,
            remarks=remarks
        )

        if succ:
            ToastNotification.show_success(self, "Payment Saved", msg)
            self.payment_saved.emit()
            self.accept()
        else:
            ToastNotification.show_error(self, "Save Failed", msg)

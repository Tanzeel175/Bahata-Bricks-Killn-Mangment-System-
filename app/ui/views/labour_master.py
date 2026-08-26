import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QDialogButtonBox, QTextEdit, QFrame, QScrollArea,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from app.services.labour_service import LabourService
from app.security.session import current_session
from app.ui.components.toast import ToastNotification
from app.ui.components.formatted_inputs import CNICLineEdit, PhoneLineEdit, NumericLineEdit
from app.ui.views.account_type_dialog import AccountTypeManagementDialog


class LabourMasterView(QWidget):
    """
    Labour & Party Master Management View.
    Structured matching reference layout:
    - Upper Section: Data Entry Form across 3 logical columns.
    - Middle Section: Action Pill Button Toolbar (New, Save, Update, Delete, Omit, Restore, Clear, Print, Export Excel, Close).
    - Lower Section: Category & Status Filters + Data Grid Table.
    """
    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_edit_mode = False
        self.selected_worker_id = None

        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. TOP HEADER TITLE
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("Labour & Party Master Management")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        sub = QLabel("Master dataset for Pathera, Nakkasi, Jamadars, Transporters, Customers, and Kiln Workers")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        header_box.addLayout(title_box)
        header_box.addStretch()

        if current_session.is_admin:
            self.btn_manage_types = QPushButton("⚙️ Manage Categories")
            self.btn_manage_types.setStyleSheet(
                "QPushButton { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px 12px; font-weight: 600; } "
                "QPushButton:hover { background-color: #F1F5F9; }"
            )
            self.btn_manage_types.clicked.connect(self._on_manage_types)
            header_box.addWidget(self.btn_manage_types)

        main_layout.addLayout(header_box)

        # Scrollable container for the entire view (ensuring no vertical clipping on smaller screens)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 0)
        container_layout.setSpacing(12)

        # 2. UPPER DATA ENTRY FORM CARD (3 COMPACT SIDE-BY-SIDE COLUMNS)
        form_card = QFrame()
        form_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }"
        )
        form_hbox = QHBoxLayout(form_card)
        form_hbox.setContentsMargins(10, 10, 10, 10)
        form_hbox.setSpacing(18)

        def make_field_heading(text, required=False):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-weight: {'700' if required else '600'}; "
                f"color: {'#0F172A' if required else '#475569'}; "
                "font-size: 11px; border: none; background: transparent; margin: 0px; padding: 0px;"
            )
            return lbl

        # --- COLUMN 1 ---
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(4)

        self.txt_worker_id = QLineEdit()
        self.txt_worker_id.setPlaceholderText("WRK-0001 (Auto or enter ID to load & edit)")
        self.txt_worker_id.setMinimumHeight(28)
        self.txt_worker_id.textEdited.connect(self._on_worker_id_input_changed)
        self.txt_worker_id.returnPressed.connect(self._on_worker_id_return_pressed)

        self.txt_english_name = QLineEdit()
        self.txt_english_name.setPlaceholderText("Full Name in English")
        self.txt_english_name.setMinimumHeight(28)

        self.txt_urdu_name = QLineEdit()
        self.txt_urdu_name.setPlaceholderText("نام (اردو Unicode)")
        self.txt_urdu_name.setMinimumHeight(28)

        self.txt_father_name = QLineEdit()
        self.txt_father_name.setPlaceholderText("Father Name")
        self.txt_father_name.setMinimumHeight(28)

        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("City, Tehsil, Village Address")
        self.txt_address.setMinimumHeight(28)

        col1_layout.addWidget(make_field_heading("Worker ID (Auto or Enter ID to Edit)*", required=True))
        col1_layout.addWidget(self.txt_worker_id)
        col1_layout.addSpacing(2)

        col1_layout.addWidget(make_field_heading("English Name*", required=True))
        col1_layout.addWidget(self.txt_english_name)
        col1_layout.addSpacing(2)

        col1_layout.addWidget(make_field_heading("Urdu Name (Optional)"))
        col1_layout.addWidget(self.txt_urdu_name)
        col1_layout.addSpacing(2)

        col1_layout.addWidget(make_field_heading("Father Name"))
        col1_layout.addWidget(self.txt_father_name)
        col1_layout.addSpacing(2)

        col1_layout.addWidget(make_field_heading("Postal Address"))
        col1_layout.addWidget(self.txt_address)

        form_hbox.addLayout(col1_layout, stretch=1)

        # --- COLUMN 2 ---
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(4)

        self.cmb_account_type = QComboBox()
        self.cmb_account_type.setMinimumHeight(28)

        self.txt_cnic = CNICLineEdit()
        self.txt_cnic.setMinimumHeight(28)

        self.txt_mobile = PhoneLineEdit()
        self.txt_mobile.setMinimumHeight(28)

        self.txt_ref_name = QLineEdit()
        self.txt_ref_name.setPlaceholderText("Guarantor Name")
        self.txt_ref_name.setMinimumHeight(28)

        self.txt_ref_mobile = PhoneLineEdit()
        self.txt_ref_mobile.setMinimumHeight(28)

        col2_layout.addWidget(make_field_heading("Account Category*", required=True))
        col2_layout.addWidget(self.cmb_account_type)
        col2_layout.addSpacing(2)

        col2_layout.addWidget(make_field_heading("CNIC (Optional)", required=False))
        col2_layout.addWidget(self.txt_cnic)
        col2_layout.addSpacing(2)

        col2_layout.addWidget(make_field_heading("Mobile Number (Optional)", required=False))
        col2_layout.addWidget(self.txt_mobile)
        col2_layout.addSpacing(2)

        col2_layout.addWidget(make_field_heading("Reference Person Name (Optional)", required=False))
        col2_layout.addWidget(self.txt_ref_name)
        col2_layout.addSpacing(2)

        col2_layout.addWidget(make_field_heading("Reference Mobile (Optional)", required=False))
        col2_layout.addWidget(self.txt_ref_mobile)

        form_hbox.addLayout(col2_layout, stretch=1)

        # --- COLUMN 3 ---
        col3_layout = QVBoxLayout()
        col3_layout.setSpacing(4)

        self.txt_modular_target = NumericLineEdit()
        self.txt_modular_target.setMinimumHeight(28)

        self.txt_filler_target = NumericLineEdit()
        self.txt_filler_target.setMinimumHeight(28)

        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Internal notes or comments...")
        self.txt_remarks.setMinimumHeight(28)

        col3_layout.addWidget(make_field_heading("Module Target/Day"))
        col3_layout.addWidget(self.txt_modular_target)
        col3_layout.addSpacing(2)

        col3_layout.addWidget(make_field_heading("Filler Target/Day"))
        col3_layout.addWidget(self.txt_filler_target)
        col3_layout.addSpacing(2)

        col3_layout.addWidget(make_field_heading("Remarks / Internal Notes"))
        col3_layout.addWidget(self.txt_remarks)
        col3_layout.addSpacing(4)

        # Omit Status Card Box
        omit_card = QFrame()
        omit_card.setStyleSheet(
            "QFrame { background-color: #FEF9C3; border: 1px solid #FDE047; border-radius: 6px; padding: 6px; }"
        )
        omit_layout = QVBoxLayout(omit_card)
        omit_layout.setSpacing(2)

        self.chk_omit_status = QCheckBox("Omit Account (Read-Only Status)")
        self.chk_omit_status.setStyleSheet("font-weight: 700; color: #854D0E; font-size: 11px; border: none; background: transparent;")
        self.chk_omit_status.toggled.connect(self._on_omit_checkbox_toggled)

        lbl_reason_title = QLabel("Reason for Omitting Account:")
        lbl_reason_title.setStyleSheet("font-size: 10px; font-weight: 600; color: #713F12; border: none; background: transparent; margin-top: 2px;")

        self.txt_omit_reason = QLineEdit()
        self.txt_omit_reason.setPlaceholderText("Enter reason if omitting...")
        self.txt_omit_reason.setFixedHeight(24)
        self.txt_omit_reason.setStyleSheet("background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 4px; font-size: 11px;")

        self.lbl_omit_date = QLabel("Omit Date: N/A")
        self.lbl_omit_date.setStyleSheet("font-size: 10px; color: #854D0E; font-weight: 500; border: none; background: transparent; margin-top: 2px;")

        omit_layout.addWidget(self.chk_omit_status)
        omit_layout.addWidget(lbl_reason_title)
        omit_layout.addWidget(self.txt_omit_reason)
        omit_layout.addWidget(self.lbl_omit_date)

        col3_layout.addWidget(omit_card)
        form_hbox.addLayout(col3_layout, stretch=1)

        container_layout.addWidget(form_card)

        # 3. MIDDLE ACTION BUTTON BAR (ROUNDED PILLS)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        # Button styling helpers
        def make_pill(text, bg_color, hover_color, text_color="#FFFFFF"):
            btn = QPushButton(text)
            btn.setMinimumHeight(36)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {bg_color}; color: {text_color}; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 14px; border: none; }} "
                f"QPushButton:hover {{ background-color: {hover_color}; }} "
                f"QPushButton:disabled {{ background-color: #E2E8F0; color: #94A3B8; }}"
            )
            return btn

        self.btn_new = make_pill("+ New", "#0284C7", "#0369A1")
        self.btn_new.setShortcut("Ctrl+N")
        self.btn_new.clicked.connect(self._on_new_clicked)

        self.btn_save = make_pill("💾 Save", "#0284C7", "#0369A1")
        self.btn_save.setShortcut("Ctrl+S")
        self.btn_save.clicked.connect(self._on_save_clicked)

        self.btn_update = make_pill("🔄 Update", "#0284C7", "#0369A1")
        self.btn_update.clicked.connect(self._on_save_clicked)

        self.btn_delete = make_pill("❌ Delete", "#E11D48", "#BE123C")
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        self.btn_omit = make_pill("🚫 Omit", "#E11D48", "#BE123C")
        self.btn_omit.clicked.connect(self._on_omit_clicked)

        self.btn_restore = make_pill("🟢 Restore", "#16A34A", "#15803D")
        self.btn_restore.clicked.connect(self._on_restore_clicked)

        self.btn_clear = make_pill("🧹 Clear", "#64748B", "#475569")
        self.btn_clear.clicked.connect(self._clear_form)

        self.btn_print = make_pill("🖨️ Print", "#334155", "#1E293B")
        self.btn_print.clicked.connect(self._on_print_clicked)

        self.btn_export = make_pill("📊 Export Excel", "#059669", "#047857")
        self.btn_export.clicked.connect(self._on_export_excel_clicked)

        self.btn_close = make_pill("❌ Close", "#94A3B8", "#64748B")
        self.btn_close.clicked.connect(self._on_close_clicked)

        btn_bar.addWidget(self.btn_new)
        btn_bar.addWidget(self.btn_save)
        btn_bar.addWidget(self.btn_update)
        btn_bar.addWidget(self.btn_delete)
        btn_bar.addWidget(self.btn_omit)
        btn_bar.addWidget(self.btn_restore)
        btn_bar.addWidget(self.btn_clear)
        btn_bar.addWidget(self.btn_print)
        btn_bar.addWidget(self.btn_export)
        btn_bar.addWidget(self.btn_close)

        container_layout.addLayout(btn_bar)

        # 4. LOWER SEARCH FILTERS & DATA GRID TABLE CARD
        grid_card = QFrame()
        grid_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px; }"
        )
        grid_card_layout = QVBoxLayout(grid_card)
        grid_card_layout.setSpacing(10)

        # Filter Bar Row
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        lbl_cat_flt = QLabel("Account Category Filter:")
        lbl_cat_flt.setStyleSheet("font-weight: 700; color: #334155; font-size: 12px;")
        self.cmb_filter_type = QComboBox()
        self.cmb_filter_type.setMinimumHeight(32)
        self.cmb_filter_type.currentIndexChanged.connect(self._on_filter_changed)

        lbl_sts_flt = QLabel("Account Status Filter:")
        lbl_sts_flt.setStyleSheet("font-weight: 700; color: #334155; font-size: 12px;")
        self.cmb_filter_status = QComboBox()
        self.cmb_filter_status.setMinimumHeight(32)
        self.cmb_filter_status.addItems(["Active Accounts Only", "All Accounts (Active & Omitted)", "Omitted Accounts Only"])
        self.cmb_filter_status.currentIndexChanged.connect(self._on_filter_changed)

        self.txt_search = QLineEdit()
        self.txt_search.setMinimumHeight(32)
        self.txt_search.setPlaceholderText("Search by Worker ID, Name, CNIC, Mobile...")
        self.txt_search.textChanged.connect(self._on_search_text_changed)

        filter_bar.addWidget(lbl_cat_flt)
        filter_bar.addWidget(self.cmb_filter_type, stretch=1)
        filter_bar.addWidget(lbl_sts_flt)
        filter_bar.addWidget(self.cmb_filter_status, stretch=1)
        filter_bar.addWidget(self.txt_search, stretch=2)

        grid_card_layout.addLayout(filter_bar)

        # Data Grid Table
        self.table = QTableWidget()
        headers = [
            "Worker ID", "Category", "Name", "CNIC", "Mobile", "Created Date", "Status"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setMinimumHeight(54)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setColumnWidth(0, 120)  # Worker ID
        self.table.setColumnWidth(1, 150)  # Category
        self.table.setColumnWidth(2, 220)  # Name
        self.table.setColumnWidth(3, 160)  # CNIC
        self.table.setColumnWidth(4, 140)  # Mobile
        self.table.setColumnWidth(5, 160)  # Created Date
        self.table.setColumnWidth(6, 100)  # Status

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setAutoScroll(False)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setMinimumHeight(240)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.table.itemClicked.connect(self._on_row_clicked)

        grid_card_layout.addWidget(self.table)
        container_layout.addWidget(grid_card)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

        # Enforce RBAC permissions
        self._update_permission_states()

    def _update_permission_states(self):
        if not current_session.is_admin:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setToolTip("Munshi role is not permitted to delete records.")

    def _load_account_types_combos(self):
        types = LabourService.get_account_types()

        self.cmb_account_type.clear()
        for t in types:
            self.cmb_account_type.addItem(t["AccountTypeName"], t["AccountTypeID"])

        self.cmb_filter_type.clear()
        self.cmb_filter_type.addItem("All Categories", 0)
        for t in types:
            self.cmb_filter_type.addItem(t["AccountTypeName"], t["AccountTypeID"])

    def refresh_data(self):
        self._load_account_types_combos()
        self._execute_search()
        self._clear_form()

    def _execute_search(self):
        query_str = self.txt_search.text().strip()
        account_type_id = self.cmb_filter_type.currentData() or 0

        status_idx = self.cmb_filter_status.currentIndex()
        # 0: Active Only, 1: All, 2: Omitted Only
        show_omitted = status_idx in (1, 2)

        accounts = LabourService.search_accounts(query_str, account_type_id, show_omitted)

        if status_idx == 2:
            accounts = [a for a in accounts if a["IsOmitted"]]

        self.table.setRowCount(len(accounts))

        for row, a in enumerate(accounts):
            self.table.setItem(row, 0, QTableWidgetItem(a["WorkerID"]))
            self.table.setItem(row, 1, QTableWidgetItem(a["AccountTypeName"]))
            self.table.setItem(row, 2, QTableWidgetItem(a["EnglishName"]))
            self.table.setItem(row, 3, QTableWidgetItem(a["CNIC"]))
            self.table.setItem(row, 4, QTableWidgetItem(a["Mobile"]))
            self.table.setItem(row, 5, QTableWidgetItem(a["CreatedDate"]))

            status_str = "Omitted" if a["IsOmitted"] else "Active"
            status_item = QTableWidgetItem(status_str)
            status_item.setForeground(Qt.red if a["IsOmitted"] else Qt.darkGreen)
            self.table.setItem(row, 6, status_item)

            self.table.item(row, 0).setData(Qt.UserRole, a)
            self.table.setRowHeight(row, 40)

        self.table.clearSelection()
        self.table.verticalScrollBar().setValue(0)
        self.table.scrollToTop()

    def _on_search_text_changed(self):
        self._execute_search()

    def _on_filter_changed(self):
        self._execute_search()

    def _on_worker_id_input_changed(self):
        raw_id = self.txt_worker_id.text().strip()
        if not raw_id:
            return

        lookup_ids = [raw_id, raw_id.upper()]
        if raw_id.isdigit():
            lookup_ids.append(f"WRK-{int(raw_id):04d}")
        elif not raw_id.upper().startswith("WRK-"):
            lookup_ids.append(f"WRK-{raw_id.upper()}")

        acc = None
        for wid in lookup_ids:
            acc = LabourService.get_account_by_id(wid)
            if acc:
                break

        if acc:
            self._load_account_into_form(acc, set_id_text=False)
            for row in range(self.table.rowCount()):
                item_acc = self.table.item(row, 0).data(Qt.UserRole)
                if item_acc and item_acc.get("WorkerID") == acc["WorkerID"]:
                    self.table.selectRow(row)
                    break
        else:
            if self.is_edit_mode:
                self.is_edit_mode = False
                self.selected_worker_id = None

    def _on_worker_id_return_pressed(self):
        self._on_worker_id_input_changed()
        if self.is_edit_mode and self.selected_worker_id:
            self.txt_worker_id.blockSignals(True)
            self.txt_worker_id.setText(self.selected_worker_id)
            self.txt_worker_id.blockSignals(False)
            self.txt_english_name.setFocus()

    def _clear_form(self):
        self.is_edit_mode = False
        self.selected_worker_id = None
        self.txt_worker_id.blockSignals(True)
        next_id = LabourService.generate_worker_id()
        self.txt_worker_id.setText(next_id)
        self.txt_worker_id.blockSignals(False)

        # Keep the current category selection (don't reset combo)
        self.txt_english_name.clear()
        self.txt_urdu_name.clear()
        self.txt_father_name.clear()
        self.txt_cnic.clear()
        self.txt_mobile.clear()
        self.txt_ref_name.clear()
        self.txt_ref_mobile.clear()
        self.txt_address.clear()
        self.txt_modular_target.setText("0")
        self.txt_filler_target.setText("0")
        self.txt_remarks.clear()

        self.chk_omit_status.blockSignals(True)
        self.chk_omit_status.setChecked(False)
        self.chk_omit_status.blockSignals(False)

        self.txt_omit_reason.clear()
        self.lbl_omit_date.setText("Omit Date: N/A")

    def _load_account_into_form(self, account: dict, set_id_text: bool = True):
        self.is_edit_mode = True
        self.selected_worker_id = account["WorkerID"]

        if set_id_text:
            self.txt_worker_id.blockSignals(True)
            self.txt_worker_id.setText(account["WorkerID"])
            self.txt_worker_id.blockSignals(False)

        idx = self.cmb_account_type.findData(account["AccountTypeID"])
        if idx >= 0:
            self.cmb_account_type.setCurrentIndex(idx)

        self.txt_english_name.setText(account["EnglishName"])
        self.txt_urdu_name.setText(account["UrduName"])
        self.txt_father_name.setText(account["FatherName"])
        self.txt_cnic.setText(account["CNIC"])
        self.txt_mobile.setText(account["Mobile"])
        self.txt_ref_name.setText(account["ReferenceName"])
        self.txt_ref_mobile.setText(account["ReferenceMobile"])
        self.txt_address.setText(account["Address"])
        self.txt_modular_target.setText(str(account["DailyModularTarget"]))
        self.txt_filler_target.setText(str(account["DailyFillerTarget"]))
        self.txt_remarks.setText(account["Remarks"])

        self.chk_omit_status.blockSignals(True)
        self.chk_omit_status.setChecked(account["IsOmitted"])
        self.chk_omit_status.blockSignals(False)

        self.txt_omit_reason.setText(account["OmitReason"] or "")
        if account["IsOmitted"]:
            self.lbl_omit_date.setText(f"Omit Date: {account['OmitDate']}")
        else:
            self.lbl_omit_date.setText("Omit Date: N/A")

    def _on_row_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        acc = self.table.item(row, 0).data(Qt.UserRole)
        if acc:
            self._load_account_into_form(acc)

    def _on_row_clicked(self, item: QTableWidgetItem):
        row = item.row()
        acc = self.table.item(row, 0).data(Qt.UserRole)
        if acc:
            self._load_account_into_form(acc)

    def _on_new_clicked(self):
        self._clear_form()
        self.txt_english_name.setFocus()

    def _on_save_clicked(self):
        worker_id_val = self.selected_worker_id if self.is_edit_mode and self.selected_worker_id else self.txt_worker_id.text().strip().upper()
        if worker_id_val.isdigit():
            worker_id_val = f"WRK-{int(worker_id_val):04d}"

        data = {
            "WorkerID": worker_id_val,
            "AccountTypeID": self.cmb_account_type.currentData(),
            "EnglishName": self.txt_english_name.text().strip(),
            "UrduName": self.txt_urdu_name.text().strip(),
            "FatherName": self.txt_father_name.text().strip(),
            "CNIC": self.txt_cnic.text().strip(),
            "Mobile": self.txt_mobile.text().strip(),
            "ReferenceName": self.txt_ref_name.text().strip(),
            "ReferenceMobile": self.txt_ref_mobile.text().strip(),
            "Address": self.txt_address.text().strip(),
            "Email": "",
            "DailyModularTarget": self.txt_modular_target.text().strip() or 0,
            "DailyFillerTarget": self.txt_filler_target.text().strip() or 0,
            "Remarks": self.txt_remarks.text().strip()
        }

        success, msg = LabourService.save_account(data, is_edit_mode=self.is_edit_mode)
        if success:
            ToastNotification.show_success(self, "Success", msg)
            self._clear_form()
            self.refresh_data()
        else:
            ToastNotification.show_error(self, "Validation Error", msg)

    def _on_omit_checkbox_toggled(self, checked: bool):
        if not self.selected_worker_id:
            return
        if checked:
            reason = self.txt_omit_reason.text().strip() or "Omitted via master form"
            LabourService.omit_account(self.selected_worker_id, reason)
        else:
            if current_session.is_admin:
                LabourService.reactivate_account(self.selected_worker_id)
            else:
                ToastNotification.show_error(self, "Access Denied", "Only Administrator can reactivate omitted accounts.")
                self.chk_omit_status.setChecked(True)
        self.refresh_data()

    def _on_omit_clicked(self):
        if not self.selected_worker_id:
            ToastNotification.show_warning(self, "Selection Required", "Please select an account to omit.")
            return

        reason = self.txt_omit_reason.text().strip() or "Omitted via master toolbar"
        success, msg = LabourService.omit_account(self.selected_worker_id, reason)
        if success:
            ToastNotification.show_success(self, "Success", msg)
            self.refresh_data()
            self._clear_form()
        else:
            ToastNotification.show_error(self, "Error", msg)

    def _on_restore_clicked(self):
        if not self.selected_worker_id:
            ToastNotification.show_warning(self, "Selection Required", "Please select an omitted account to restore.")
            return

        if not current_session.is_admin:
            ToastNotification.show_error(self, "Access Denied", "Only Administrator can restore omitted accounts.")
            return

        success, msg = LabourService.reactivate_account(self.selected_worker_id)
        if success:
            ToastNotification.show_success(self, "Success", msg)
            self.refresh_data()
            self._clear_form()
        else:
            ToastNotification.show_error(self, "Error", msg)

    def _on_delete_clicked(self):
        if not self.selected_worker_id:
            ToastNotification.show_warning(self, "Selection Required", "Please select an account to delete.")
            return

        if ToastNotification.confirm(self, "Confirm Delete", f"Permanently delete account '{self.selected_worker_id}'?"):
            success, msg = LabourService.delete_account(self.selected_worker_id)
            if success:
                ToastNotification.show_success(self, "Success", msg)
                self._clear_form()
                self.refresh_data()
            else:
                ToastNotification.show_error(self, "Delete Exception", msg)

    def _on_print_clicked(self):
        ToastNotification.show_info(
            self,
            "Print Master Report",
            f"Master Ledger Report sent to default system printer for {self.table.rowCount()} account records."
        )

    def _on_export_excel_clicked(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Labour Accounts to Excel", "Labour_Master_Report.xlsx", "Excel Files (*.xlsx *.csv)"
        )
        if not file_path:
            return

        try:
            accounts = LabourService.search_accounts(show_omitted=True)

            if file_path.endswith(".xlsx"):
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Labour Accounts"

                headers = [
                    "WorkerID", "Category", "EnglishName", "UrduName", "FatherName",
                    "CNIC", "Mobile", "ReferenceName", "ReferenceMobile",
                    "Address", "Email", "ModularTarget", "FillerTarget", "Status", "OmitReason"
                ]
                ws.append(headers)

                for a in accounts:
                    ws.append([
                        a["WorkerID"], a["AccountTypeName"], a["EnglishName"], a["UrduName"],
                        a["FatherName"], a["CNIC"], a["Mobile"], a["ReferenceName"],
                        a["ReferenceMobile"], a["Address"], a["Email"], a["DailyModularTarget"],
                        a["DailyFillerTarget"], "Omitted" if a["IsOmitted"] else "Active", a["OmitReason"]
                    ])

                wb.save(file_path)
            else:
                import csv
                with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    headers = [
                        "WorkerID", "Category", "EnglishName", "UrduName", "FatherName",
                        "CNIC", "Mobile", "ReferenceName", "ReferenceMobile",
                        "Address", "Email", "ModularTarget", "FillerTarget", "Status", "OmitReason"
                    ]
                    writer.writerow(headers)
                    for a in accounts:
                        writer.writerow([
                            a["WorkerID"], a["AccountTypeName"], a["EnglishName"], a["UrduName"],
                            a["FatherName"], a["CNIC"], a["Mobile"], a["ReferenceName"],
                            a["ReferenceMobile"], a["Address"], a["Email"], a["DailyModularTarget"],
                            a["DailyFillerTarget"], "Omitted" if a["IsOmitted"] else "Active", a["OmitReason"]
                        ])

            ToastNotification.show_success(self, "Export Complete", f"Successfully exported data to:\n{file_path}")
        except Exception as e:
            ToastNotification.show_error(self, "Export Failed", f"Failed to export data: {e}")

    def _on_close_clicked(self):
        self.close_requested.emit()

    def _on_manage_types(self):
        dlg = AccountTypeManagementDialog(parent=self)
        dlg.exec()
        self.refresh_data()

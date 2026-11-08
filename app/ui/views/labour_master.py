import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QDialogButtonBox, QTextEdit, QFrame, QScrollArea,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont
from app.services.labour_service import LabourService
from app.security.session import current_session
from app.ui.components.toast import ToastNotification
from app.ui.components.formatted_inputs import CNICLineEdit, PhoneLineEdit, NumericLineEdit
from app.ui.views.account_type_dialog import AccountTypeManagementDialog
from app.ui.theme_manager import theme_mgr, _CHECK_SVG_PATH


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
        theme_mgr.theme_changed.connect(self._on_theme_changed)
        self.refresh_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. TOP MODULE SUBHEADER (Matching BAHTA Stitch Header)
        header_box = QHBoxLayout()
        header_box.setContentsMargins(0, 0, 0, 4)
        header_box.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        self.lbl_view_title = QLabel("Labour & Party Master Management")
        self.lbl_view_title.setProperty("class", "heading-primary")
        self.lbl_view_title.setStyleSheet("font-size: 19px; font-weight: 800; letter-spacing: -0.01em; border: none; background: transparent;")
        title_row.addWidget(self.lbl_view_title)

        self.mod_badge = QLabel("Active Module")
        self.mod_badge.setStyleSheet(
            "border-radius: 9999px; font-size: 11px; font-weight: 700; padding: 2px 10px;"
        )
        title_row.addWidget(self.mod_badge)
        title_row.addStretch()
        title_box.addLayout(title_row)

        self.lbl_view_sub = QLabel("Master dataset for Pathera, Nakkasi, Jamadars, Transporters, Customers, and Kiln Workers.")
        self.lbl_view_sub.setStyleSheet("font-size: 12px; font-weight: 500; border: none; background: transparent;")
        title_box.addWidget(self.lbl_view_sub)
        header_box.addLayout(title_box)
        header_box.addStretch()

        # Top Header Action Buttons
        top_actions_box = QHBoxLayout()
        top_actions_box.setSpacing(8)

        if current_session.is_admin:
            self.btn_manage_types = QPushButton("Manage Categories")
            self.btn_manage_types.setProperty("class", "btn-secondary")
            self.btn_manage_types.setMinimumHeight(34)
            self.btn_manage_types.setCursor(Qt.PointingHandCursor)
            self.btn_manage_types.clicked.connect(self._on_manage_types)
            top_actions_box.addWidget(self.btn_manage_types)

        self.btn_export_top = QPushButton("Export View")
        self.btn_export_top.setProperty("class", "btn-primary")
        self.btn_export_top.setMinimumHeight(34)
        self.btn_export_top.setCursor(Qt.PointingHandCursor)
        self.btn_export_top.clicked.connect(self._on_export_excel_clicked)
        top_actions_box.addWidget(self.btn_export_top)

        header_box.addLayout(top_actions_box)
        main_layout.addLayout(header_box)

        # Scrollable container for the entire view (ensuring laptop friendliness)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        container.setObjectName("labourScrollContainer")
        container.setStyleSheet("#labourScrollContainer { background-color: transparent; }")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 8)
        container_layout.setSpacing(14)

        # 2. UPPER DATA ENTRY FORM CARD (3 COMPACT BALANCED COLUMNS)
        form_card = QFrame()
        form_card.setObjectName("form_card")
        form_card.setProperty("class", "card-panel")
        form_card_vbox = QVBoxLayout(form_card)
        form_card_vbox.setContentsMargins(0, 0, 0, 16)
        form_card_vbox.setSpacing(14)

        # Card Header Strip
        form_header = QFrame()
        form_header.setObjectName("formCardHeader")
        form_header.setStyleSheet("padding: 10px 18px;")
        fh_layout = QHBoxLayout(form_header)
        fh_layout.setContentsMargins(0, 0, 0, 0)
        fh_layout.setSpacing(8)

        fh_icon = QLabel("🪪")
        fh_icon.setStyleSheet("font-size: 14px;")
        fh_layout.addWidget(fh_icon)

        self.fh_title = QLabel("WORKER PROFILE & MASTER DETAILS")
        self.fh_title.setStyleSheet("font-size: 11.5px; font-weight: 800; letter-spacing: 0.8px; border: none; background: transparent;")
        fh_layout.addWidget(self.fh_title)
        fh_layout.addStretch()

        fh_note = QLabel('Fields marked with <font color="#E11D48"><b>*</b></font> are mandatory')
        fh_note.setProperty("class", "form-field-subtext")
        fh_note.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        fh_layout.addWidget(fh_note)

        form_card_vbox.addWidget(form_header)

        # 3-Column Form Grid Container
        form_body = QWidget()
        form_hbox = QHBoxLayout(form_body)
        form_hbox.setContentsMargins(18, 0, 18, 0)
        form_hbox.setSpacing(20)

        def make_field_heading(text, required=False, subtext=None):
            box = QHBoxLayout()
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(4)
            lbl = QLabel(text)
            lbl.setProperty("class", "form-field-label")
            is_d = theme_mgr.is_dark_mode()
            lbl_col = "#FFFFFF" if is_d else "#334155"
            lbl.setStyleSheet(
                f"font-weight: {'700' if required else '600'}; "
                f"font-size: 11.5px; color: {lbl_col}; border: none; background: transparent; margin: 0px;"
            )
            box.addWidget(lbl)
            if required:
                req = QLabel("*")
                req.setStyleSheet("color: #E11D48; font-weight: bold; font-size: 12px; margin: 0px;")
                box.addWidget(req)
            if subtext:
                box.addStretch()
                sub_lbl = QLabel(subtext)
                sub_lbl.setProperty("class", "form-field-subtext")
                sub_col = "#CBD5E1" if is_d else "#64748B"
                sub_lbl.setStyleSheet(f"font-size: 10.5px; color: {sub_col}; font-weight: 500; border: none; background: transparent;")
                box.addWidget(sub_lbl)
            else:
                box.addStretch()
            return box

        # --- COLUMN 1: Primary Identification ---
        col1_layout = QVBoxLayout()
        col1_layout.setSpacing(4)

        # Worker ID input with prefix group
        wid_box = QHBoxLayout()
        wid_box.setSpacing(0)
        id_badge = QLabel("ID")
        self.id_badge = QLabel("ID")
        self.id_badge.setFixedWidth(36)
        self.id_badge.setAlignment(Qt.AlignCenter)
        wid_box.addWidget(self.id_badge)

        self.txt_worker_id = QLineEdit()
        self.txt_worker_id.setPlaceholderText("WRK-0001 (Auto or edit)")
        self.txt_worker_id.setMinimumHeight(32)
        self.txt_worker_id.textEdited.connect(self._on_worker_id_input_changed)
        self.txt_worker_id.returnPressed.connect(self._on_worker_id_return_pressed)
        wid_box.addWidget(self.txt_worker_id, stretch=1)

        self.btn_edit_id = QPushButton("Edit")
        self.btn_edit_id.setCursor(Qt.PointingHandCursor)
        self.btn_edit_id.clicked.connect(self._on_worker_id_return_pressed)
        wid_box.addWidget(self.btn_edit_id)

        self.txt_english_name = QLineEdit()
        self.txt_english_name.setPlaceholderText("Full Name in English")
        self.txt_english_name.setMinimumHeight(32)

        self.txt_urdu_name = QLineEdit()
        self.txt_urdu_name.setPlaceholderText("اردو میں نام درج کریں")
        self.txt_urdu_name.setLayoutDirection(Qt.RightToLeft)
        self.txt_urdu_name.setAlignment(Qt.AlignRight)
        urdu_f = QFont("Noto Nastaliq Urdu", 11)
        self.txt_urdu_name.setFont(urdu_f)
        self.txt_urdu_name.setMinimumHeight(32)

        self.txt_father_name = QLineEdit()
        self.txt_father_name.setPlaceholderText("Father Name")
        self.txt_father_name.setMinimumHeight(32)

        self.txt_address = QLineEdit()
        self.txt_address.setPlaceholderText("City, Tehsil, Village Address")
        self.txt_address.setMinimumHeight(32)

        col1_layout.addLayout(make_field_heading("Worker ID", required=True, subtext="(Auto or Enter ID to Edit)"))
        col1_layout.addLayout(wid_box)
        col1_layout.addSpacing(4)

        col1_layout.addLayout(make_field_heading("English Name", required=True))
        col1_layout.addWidget(self.txt_english_name)
        col1_layout.addSpacing(4)

        col1_layout.addLayout(make_field_heading("Urdu Name", required=False, subtext="نام (اردو Unicode)"))
        col1_layout.addWidget(self.txt_urdu_name)
        col1_layout.addSpacing(4)

        col1_layout.addLayout(make_field_heading("Father Name"))
        col1_layout.addWidget(self.txt_father_name)
        col1_layout.addSpacing(4)

        col1_layout.addLayout(make_field_heading("Postal Address"))
        col1_layout.addWidget(self.txt_address)

        form_hbox.addLayout(col1_layout, stretch=1)

        # --- COLUMN 2: Category & Contact Details ---
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(4)

        self.cmb_account_type = QComboBox()
        self.cmb_account_type.setMinimumHeight(32)

        self.txt_cnic = CNICLineEdit()
        self.txt_cnic.setMinimumHeight(32)

        self.txt_mobile = PhoneLineEdit()
        self.txt_mobile.setMinimumHeight(32)

        self.txt_ref_name = QLineEdit()
        self.txt_ref_name.setPlaceholderText("Guarantor Name")
        self.txt_ref_name.setMinimumHeight(32)

        self.txt_ref_mobile = PhoneLineEdit()
        self.txt_ref_mobile.setMinimumHeight(32)

        col2_layout.addLayout(make_field_heading("Account Category", required=True))
        col2_layout.addWidget(self.cmb_account_type)
        col2_layout.addSpacing(4)

        col2_layout.addLayout(make_field_heading("CNIC", required=False, subtext="(National ID / Optional)"))
        col2_layout.addWidget(self.txt_cnic)
        col2_layout.addSpacing(4)

        col2_layout.addLayout(make_field_heading("Mobile Number", required=False, subtext="(Optional)"))
        col2_layout.addWidget(self.txt_mobile)
        col2_layout.addSpacing(4)

        col2_layout.addLayout(make_field_heading("Reference Person Name", required=False, subtext="(Guarantor)"))
        col2_layout.addWidget(self.txt_ref_name)
        col2_layout.addSpacing(4)

        col2_layout.addLayout(make_field_heading("Reference Mobile", required=False, subtext="(Optional)"))
        col2_layout.addWidget(self.txt_ref_mobile)

        form_hbox.addLayout(col2_layout, stretch=1)

        # --- COLUMN 3: Targets, Status & Controls ---
        col3_layout = QVBoxLayout()
        col3_layout.setSpacing(4)

        self.txt_modular_target = NumericLineEdit()
        self.txt_modular_target.setMinimumHeight(32)

        self.txt_filler_target = NumericLineEdit()
        self.txt_filler_target.setMinimumHeight(32)

        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Internal notes or comments...")
        self.txt_remarks.setMinimumHeight(32)

        col3_layout.addLayout(make_field_heading("Module Target/Day"))
        col3_layout.addWidget(self.txt_modular_target)
        col3_layout.addSpacing(4)

        col3_layout.addLayout(make_field_heading("Filler Target/Day"))
        col3_layout.addWidget(self.txt_filler_target)
        col3_layout.addSpacing(4)

        col3_layout.addLayout(make_field_heading("Remarks / Internal Notes"))
        col3_layout.addWidget(self.txt_remarks)
        col3_layout.addSpacing(6)

        # Omit Status Warning Card Box
        self.omit_card = QFrame()
        self.omit_card.setObjectName("omitCard")
        self.omit_card.setStyleSheet("padding: 8px 12px;")
        omit_layout = QVBoxLayout(self.omit_card)
        omit_layout.setSpacing(3)

        self.chk_omit_status = QCheckBox("Omit Account (Read-Only Status)")
        self.chk_omit_status.toggled.connect(self._on_omit_checkbox_toggled)

        self.lbl_reason_title = QLabel("Reason for Omitting Account:")
        self.lbl_reason_title.setStyleSheet("font-size: 10.5px; font-weight: 600; border: none; background: transparent; margin-top: 2px;")

        self.txt_omit_reason = QLineEdit()
        self.txt_omit_reason.setPlaceholderText("Enter reason if omitting...")
        self.txt_omit_reason.setFixedHeight(26)
        self.txt_omit_reason.setStyleSheet("border-radius: 4px; font-size: 11px;")

        self.lbl_omit_date = QLabel("Omit Date: N/A")
        self.lbl_omit_date.setStyleSheet("font-size: 10px; font-weight: 600; border: none; background: transparent; margin-top: 2px;")

        omit_layout.addWidget(self.chk_omit_status)
        omit_layout.addWidget(self.lbl_reason_title)
        omit_layout.addWidget(self.txt_omit_reason)
        omit_layout.addWidget(self.lbl_omit_date)

        col3_layout.addWidget(self.omit_card)
        form_hbox.addLayout(col3_layout, stretch=1)

        form_card_vbox.addWidget(form_body)
        container_layout.addWidget(form_card)

        # 3. MIDDLE ACTION BUTTON BAR (Matching BAHTA Stitch Action Palette)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        def make_pill(text, bg_color, hover_color, text_color="#FFFFFF", border_color=None):
            btn = QPushButton(text)
            btn.setMinimumHeight(36)
            btn.setCursor(Qt.PointingHandCursor)
            border_qss = f"border: 1px solid {border_color};" if border_color else "border: none;"
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {bg_color}; color: {text_color}; font-weight: 700; "
                f"font-size: 12px; border-radius: 6px; padding: 6px 14px; {border_qss} }} "
                f"QPushButton:hover {{ background-color: {hover_color}; }} "
                f"QPushButton:disabled {{ background-color: #E2E8F0; color: #94A3B8; border: none; }}"
            )
            return btn

        self.btn_new = make_pill("+ New", "#2563EB", "#1D4ED8")
        self.btn_new.setShortcut("Ctrl+N")
        self.btn_new.clicked.connect(self._on_new_clicked)

        self.btn_save = make_pill("Save", "#0284C7", "#0369A1")
        self.btn_save.setShortcut("Ctrl+S")
        self.btn_save.clicked.connect(self._on_save_clicked)

        self.btn_update = make_pill("Update", "#4F46E5", "#4338CA")
        self.btn_update.clicked.connect(self._on_save_clicked)

        self.btn_delete = make_pill("Delete", "#E11D48", "#BE123C")
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        self.btn_omit = make_pill("Omit", "#DB2777", "#BE185D")
        self.btn_omit.clicked.connect(self._on_omit_clicked)

        self.btn_restore = make_pill("Restore", "#059669", "#047857")
        self.btn_restore.clicked.connect(self._on_restore_clicked)

        self.btn_clear = make_pill("Clear", "#475569", "#334155")
        self.btn_clear.clicked.connect(self._clear_form)

        self.btn_print = make_pill("Print", "#0F172A", "#1E293B")
        self.btn_print.clicked.connect(self._on_print_clicked)

        self.btn_export = make_pill("Export Excel", "#0D9488", "#0F766E")
        self.btn_export.clicked.connect(self._on_export_excel_clicked)

        self.btn_close = make_pill("Close", "#E2E8F0", "#CBD5E1", text_color="#334155", border_color="#CBD5E1")
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

        # 4. LOWER MASTER RECORDS TABLE CONTAINER (Matching Stitch Data Grid)
        grid_card = QFrame()
        grid_card.setObjectName("grid_card")
        grid_card.setProperty("class", "card-panel")
        grid_card_layout = QVBoxLayout(grid_card)
        grid_card_layout.setContentsMargins(16, 14, 16, 16)
        grid_card_layout.setSpacing(12)

        # Filter Bar Row with Record Count Badge
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        lbl_cat_flt = QLabel("Account Category Filter:")
        lbl_cat_flt.setProperty("class", "form-field-label")
        lbl_cat_flt.setStyleSheet("font-weight: 700; font-size: 11.5px;")
        self.cmb_filter_type = QComboBox()
        self.cmb_filter_type.setMinimumHeight(32)
        self.cmb_filter_type.currentIndexChanged.connect(self._on_filter_changed)

        lbl_sts_flt = QLabel("Account Status Filter:")
        lbl_sts_flt.setProperty("class", "form-field-label")
        lbl_sts_flt.setStyleSheet("font-weight: 700; font-size: 11.5px;")
        self.cmb_filter_status = QComboBox()
        self.cmb_filter_status.setMinimumHeight(32)
        self.cmb_filter_status.addItems(["Active Accounts Only", "All Accounts (Active & Omitted)", "Omitted Accounts Only"])
        self.cmb_filter_status.currentIndexChanged.connect(self._on_filter_changed)

        self.txt_search = QLineEdit()
        self.txt_search.setMinimumHeight(32)
        self.txt_search.setPlaceholderText("Search by Name, ID, Phone, CNIC... (Ctrl+K)")
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)
        self._search_timer.timeout.connect(self._execute_search)
        self.txt_search.textChanged.connect(self._on_search_text_changed)

        self.lbl_record_count = QLabel("0 Accounts")
        self.lbl_record_count.setStyleSheet(
            "background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; "
            "border-radius: 6px; font-size: 11.5px; font-weight: 700; padding: 4px 12px;"
        )

        filter_bar.addWidget(lbl_cat_flt)
        filter_bar.addWidget(self.cmb_filter_type, stretch=1)
        filter_bar.addWidget(lbl_sts_flt)
        filter_bar.addWidget(self.cmb_filter_status, stretch=1)
        filter_bar.addWidget(self.txt_search, stretch=2)
        filter_bar.addWidget(self.lbl_record_count)

        grid_card_layout.addLayout(filter_bar)

        # Data Grid Table
        self.table = QTableWidget()
        headers = [
            "#", "Worker ID", "Category", "Worker Name", "CNIC", "Mobile", "Created Date", "Status"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setMinimumHeight(40)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setColumnWidth(0, 48)   # #
        self.table.setColumnWidth(1, 110)  # Worker ID
        self.table.setColumnWidth(2, 130)  # Category
        self.table.setColumnWidth(3, 240)  # Name
        self.table.setColumnWidth(4, 140)  # CNIC
        self.table.setColumnWidth(5, 130)  # Mobile
        self.table.setColumnWidth(6, 120)  # Created Date
        self.table.setColumnWidth(7, 100)  # Status

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setAutoScroll(False)
        self.table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.table.setMinimumHeight(280)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.table.itemClicked.connect(self._on_row_clicked)

        grid_card_layout.addWidget(self.table)
        container_layout.addWidget(grid_card)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

        # Enforce RBAC permissions
        self._update_permission_states()
        self._on_theme_changed()

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

        self.table.setUpdatesEnabled(False)
        self.table.blockSignals(True)
        self.table.setRowCount(len(accounts))
        if hasattr(self, "lbl_record_count"):
            self.lbl_record_count.setText(f"{len(accounts)} Accounts")

        mono_font = QFont("Consolas", 10)
        mono_font.setStyleHint(QFont.Monospace)

        for row, a in enumerate(accounts):
            # 0: # (Index)
            num_item = QTableWidgetItem(f"{row + 1}")
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setForeground(QColor("#64748B"))
            num_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 0, num_item)

            # 1: Worker ID
            wid_item = QTableWidgetItem(a.get("WorkerID", ""))
            wid_item.setFont(mono_font)
            is_dark_table = theme_mgr.is_dark_mode()
            wid_item.setForeground(QColor("#F8FAFC" if is_dark_table else "#0F172A"))
            wid_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 1, wid_item)

            # 2: Category
            cat_item = QTableWidgetItem(a.get("AccountTypeName", "") or "—")
            cat_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 2, cat_item)

            # 3: Worker Name (Bilingual if Urdu is present)
            eng = a.get("EnglishName", "")
            urdu = a.get("UrduName", "")
            display_name = f"{eng}  ({urdu})" if urdu else eng
            name_item = QTableWidgetItem(display_name)
            name_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 3, name_item)

            # 4: CNIC
            cnic_item = QTableWidgetItem(a.get("CNIC", "") or "—")
            cnic_item.setFont(mono_font)
            cnic_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 4, cnic_item)

            # 5: Mobile
            mob_item = QTableWidgetItem(a.get("Mobile", "") or "—")
            mob_item.setFont(mono_font)
            mob_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 5, mob_item)

            # 6: Created Date
            dt_item = QTableWidgetItem(a.get("CreatedDate", "") or "—")
            dt_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 6, dt_item)

            # 7: Status
            is_omitted = bool(a.get("IsOmitted"))
            status_str = "Omitted" if is_omitted else "Active"
            status_item = QTableWidgetItem(status_str)
            status_item.setTextAlignment(Qt.AlignCenter)
            if is_omitted:
                status_item.setForeground(QColor("#B45309"))
            else:
                status_item.setForeground(QColor("#15803D"))
            status_item.setData(Qt.UserRole, a)
            self.table.setItem(row, 7, status_item)

            self.table.setRowHeight(row, 38)

        self.table.blockSignals(False)
        self.table.setUpdatesEnabled(True)

        self.table.clearSelection()
        self.table.verticalScrollBar().setValue(0)
        self.table.scrollToTop()

    def _on_search_text_changed(self):
        if hasattr(self, "_search_timer"):
            self._search_timer.start()
        else:
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

    def _on_theme_changed(self, _theme: str = ""):
        is_dark = theme_mgr.is_dark_mode()

        # 1. Module Badge
        if hasattr(self, "mod_badge"):
            if is_dark:
                self.mod_badge.setStyleSheet(
                    "background-color: rgba(37, 99, 235, 0.2); color: #93C5FD; border: 1px solid #1D4ED8; "
                    "border-radius: 9999px; font-size: 11px; font-weight: 700; padding: 2px 10px;"
                )
            else:
                self.mod_badge.setStyleSheet(
                    "background-color: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; "
                    "border-radius: 9999px; font-size: 11px; font-weight: 700; padding: 2px 10px;"
                )

        # 2. Worker ID Group
        if hasattr(self, "id_badge"):
            badge_bg = "#0F172A" if is_dark else "#F1F5F9"
            badge_border = "#334155" if is_dark else "#CBD5E1"
            badge_fg = "#94A3B8" if is_dark else "#64748B"
            self.id_badge.setStyleSheet(
                f"background-color: {badge_bg}; border: 1.5px solid {badge_border}; border-right: none; "
                f"border-top-left-radius: 6px; border-bottom-left-radius: 6px; "
                f"font-weight: 700; color: {badge_fg}; font-size: 11px; min-height: 28px;"
            )

        if hasattr(self, "txt_worker_id"):
            wid_bg = "#0F172A" if is_dark else "#F8FAFC"
            wid_fg = "#F8FAFC" if is_dark else "#0F172A"
            wid_border = "#334155" if is_dark else "#CBD5E1"
            self.txt_worker_id.setStyleSheet(
                f"QLineEdit {{ border-radius: 0px; font-weight: 800; color: {wid_fg}; background-color: {wid_bg}; border: 1.5px solid {wid_border}; }}"
            )

        if hasattr(self, "table"):
            id_col = QColor("#F8FAFC" if is_dark else "#0F172A")
            for r in range(self.table.rowCount()):
                it = self.table.item(r, 1)
                if it:
                    it.setForeground(id_col)

        if hasattr(self, "btn_edit_id"):
            btn_bg = "#0F172A" if is_dark else "#F1F5F9"
            btn_border = "#334155" if is_dark else "#CBD5E1"
            btn_fg = "#E2E8F0" if is_dark else "#334155"
            btn_hover = "#1E293B" if is_dark else "#E2E8F0"
            self.btn_edit_id.setStyleSheet(
                f"QPushButton {{ background-color: {btn_bg}; border: 1.5px solid {btn_border}; border-left: none; "
                f"border-top-right-radius: 6px; border-bottom-right-radius: 6px; padding: 4px 12px; "
                f"font-weight: 600; color: {btn_fg}; font-size: 11.5px; min-height: 28px; }} "
                f"QPushButton:hover {{ background-color: {btn_hover}; }}"
            )

        # 3. Omit Card Checkbox & Labels
        if hasattr(self, "chk_omit_status"):
            chk_color = "#FFFFFF" if is_dark else "#854D0E"
            chk_ind_bg = "#0F172A" if is_dark else "#FFFFFF"
            self.chk_omit_status.setStyleSheet(
                f"QCheckBox {{ font-weight: 700; color: {chk_color}; font-size: 11.5px; border: none; background: transparent; }} "
                f"QCheckBox::indicator {{ width: 16px; height: 16px; border: 1.5px solid #CA8A04; border-radius: 4px; background-color: {chk_ind_bg}; }} "
                f"QCheckBox::indicator:checked {{ background-color: #CA8A04; border-color: #A16207; image: url(\"{_CHECK_SVG_PATH}\"); }}"
            )

        if hasattr(self, "lbl_reason_title"):
            rt_col = "#FFFFFF" if is_dark else "#713F12"
            self.lbl_reason_title.setStyleSheet(f"font-size: 10.5px; font-weight: 700; color: {rt_col}; border: none; background: transparent; margin-top: 2px;")

        if hasattr(self, "lbl_omit_date"):
            od_col = "#F1F5F9" if is_dark else "#854D0E"
            self.lbl_omit_date.setStyleSheet(f"font-size: 10px; color: {od_col}; font-weight: 600; border: none; background: transparent; margin-top: 2px;")

        # 4. Form Field Headings & Subtexts
        lbl_col = "#FFFFFF" if is_dark else "#334155"
        sub_col = "#CBD5E1" if is_dark else "#64748B"
        for lbl in self.findChildren(QLabel):
            cls = lbl.property("class")
            if cls == "form-field-label":
                lbl.setStyleSheet(f"font-size: 11.5px; font-weight: 700; color: {lbl_col}; border: none; background: transparent; margin: 0px;")
            elif cls == "form-field-subtext":
                lbl.setStyleSheet(f"font-size: 10.5px; font-weight: 500; color: {sub_col}; border: none; background: transparent;")

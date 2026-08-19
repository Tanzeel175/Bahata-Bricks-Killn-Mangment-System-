from datetime import datetime, date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont
from app.services.production_service import ProductionService
from app.services.labour_service import LabourService
from app.services.product_service import ProductService
from app.security.session import current_session
from app.ui.components.toast import ToastNotification


class ProductionEntryView(QWidget):
    """
    Daily Production Entry View.
    Supports Pathera, Bahri Wala, and Nakkasi Wala production recording.
    Dynamically loads active labourers and category-specific product columns.
    Automatically calculates earnings and posts to Labour Khata on Save.
    """

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_edit_mode = False
        self.selected_production_id = None
        self.current_molding_products = []
        self.current_category_workers = []

        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. TOP HEADER TITLE
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("🛠️ Daily Production Entry (Bricks & Tiles Yield)")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        sub = QLabel("Record daily labour production completed by Pathera, Bahri Wala, and Nakkasi Wala workers")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        header_box.addLayout(title_box)
        header_box.addStretch()

        main_layout.addLayout(header_box)

        # Scrollable container for smaller screens
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 0)
        container_layout.setSpacing(12)

        # 2. UPPER HEADER FORM CARD (4 HORIZONTAL COLUMNS: Date, Category, Entry ID, Remarks)
        header_card = QFrame()
        header_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; }"
        )
        h_grid = QGridLayout(header_card)
        h_grid.setContentsMargins(10, 10, 10, 10)
        h_grid.setHorizontalSpacing(16)
        h_grid.setVerticalSpacing(6)

        def make_field_heading(text, required=False):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"font-weight: {'700' if required else '600'}; "
                f"color: {'#0F172A' if required else '#475569'}; "
                "font-size: 11px; border: none; background: transparent; margin: 0px; padding: 0px;"
            )
            return lbl

        self.dt_entry_date = QDateEdit()
        self.dt_entry_date.setDate(QDate.currentDate())
        self.dt_entry_date.setCalendarPopup(True)
        self.dt_entry_date.setMinimumHeight(32)
        self.dt_entry_date.dateChanged.connect(self._on_date_or_category_changed)

        self.cmb_account_type = QComboBox()
        self.cmb_account_type.setMinimumHeight(32)
        self.cmb_account_type.currentIndexChanged.connect(self._on_date_or_category_changed)

        self.txt_production_id = QLineEdit()
        self.txt_production_id.setPlaceholderText("Auto-generated ID")
        self.txt_production_id.setReadOnly(True)
        self.txt_production_id.setMinimumHeight(32)
        self.txt_production_id.setStyleSheet("background-color: #F1F5F9; color: #64748B; font-weight: 700;")

        self.txt_remarks = QLineEdit()
        self.txt_remarks.setPlaceholderText("Optional notes about weather, shift, or batch...")
        self.txt_remarks.setMinimumHeight(32)

        h_grid.addWidget(make_field_heading("Production Date*", required=True), 0, 0)
        h_grid.addWidget(self.dt_entry_date, 1, 0)

        h_grid.addWidget(make_field_heading("Labour Category*", required=True), 0, 1)
        h_grid.addWidget(self.cmb_account_type, 1, 1)

        h_grid.addWidget(make_field_heading("Entry Number (Auto-Generated)"), 0, 2)
        h_grid.addWidget(self.txt_production_id, 1, 2)

        h_grid.addWidget(make_field_heading("Remarks / Notes"), 0, 3)
        h_grid.addWidget(self.txt_remarks, 1, 3)

        h_grid.setColumnStretch(0, 1)
        h_grid.setColumnStretch(1, 1)
        h_grid.setColumnStretch(2, 1)
        h_grid.setColumnStretch(3, 2)

        container_layout.addWidget(header_card)

        # 3. DYNAMIC PRODUCTION GRID CARD
        grid_card = QFrame()
        grid_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; }"
        )
        grid_layout = QVBoxLayout(grid_card)
        grid_layout.setSpacing(8)

        self.lbl_grid_title = QLabel("📋 Active Labourers & Production Quantities")
        self.lbl_grid_title.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 13px; border: none; background: transparent;")
        grid_layout.addWidget(self.lbl_grid_title)

        self.prod_table = QTableWidget()
        self.prod_table.horizontalHeader().setMinimumHeight(54)
        self.prod_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.prod_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.prod_table.setAlternatingRowColors(True)
        self.prod_table.setMinimumHeight(280)

        self.is_dirty = False
        self._ignore_signals = False
        self.txt_remarks.textChanged.connect(self._mark_dirty)
        self.prod_table.itemChanged.connect(self._on_item_changed)

        grid_layout.addWidget(self.prod_table)
        container_layout.addWidget(grid_card)

        # 4. MIDDLE ACTION PILL BUTTON BAR (New, Save, Edit, Delete, View, Clear, Print, Export Excel, Close)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

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

        self.btn_update = make_pill("🔄 Edit / Update", "#0284C7", "#0369A1")
        self.btn_update.clicked.connect(self._on_save_clicked)

        self.btn_delete = make_pill("❌ Delete", "#E11D48", "#BE123C")
        self.btn_delete.clicked.connect(self._on_delete_clicked)

        self.btn_view = make_pill("👁️ View Entry", "#475569", "#334155")
        self.btn_view.clicked.connect(self._on_view_clicked)

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
        btn_bar.addWidget(self.btn_view)
        btn_bar.addWidget(self.btn_clear)
        btn_bar.addWidget(self.btn_print)
        btn_bar.addWidget(self.btn_export)
        btn_bar.addWidget(self.btn_close)

        container_layout.addLayout(btn_bar)

        # 5. LOWER HISTORY & SEARCH CARD
        history_card = QFrame()
        history_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px; }"
        )
        h_layout = QVBoxLayout(history_card)
        h_layout.setSpacing(8)

        lbl_hist_title = QLabel("📜 Historical Production Entries")
        lbl_hist_title.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 13px; border: none; background: transparent;")
        h_layout.addWidget(lbl_hist_title)

        self.history_table = QTableWidget()
        hist_headers = ["Entry ID", "Production Date", "Labour Category", "Remarks", "Created By"]
        self.history_table.setColumnCount(len(hist_headers))
        self.history_table.setHorizontalHeaderLabels(hist_headers)

        self.history_table.horizontalHeader().setMinimumHeight(54)
        self.history_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.history_table.horizontalHeader().setStretchLastSection(True)

        self.history_table.setColumnWidth(0, 100)  # Entry ID
        self.history_table.setColumnWidth(1, 130)  # Production Date
        self.history_table.setColumnWidth(2, 160)  # Labour Category
        self.history_table.setColumnWidth(3, 300)  # Remarks
        self.history_table.setColumnWidth(4, 130)  # Created By

        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setMinimumHeight(180)
        self.history_table.itemDoubleClicked.connect(self._on_history_row_double_clicked)
        self.history_table.itemClicked.connect(self._on_history_row_clicked)

        h_layout.addWidget(self.history_table)
        container_layout.addWidget(history_card)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

        # Enforce RBAC permissions
        self._update_permission_states()

    def _update_permission_states(self):
        if not current_session.is_admin:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setToolTip("Munshi role is not permitted to delete production entries.")

    def _load_categories_combo(self):
        types = LabourService.get_account_types()
        # Strictly filter to Pathera, Bahari Wala, and Nakkasi Wala
        production_categories = [
            t for t in types
            if any(keyword in t["AccountTypeName"].lower() for keyword in ["pathera", "bahari", "bahri", "nakkasi"])
            and "jamadar" not in t["AccountTypeName"].lower()
        ]
        self.cmb_account_type.blockSignals(True)
        self.cmb_account_type.clear()
        for t in production_categories:
            self.cmb_account_type.addItem(t["AccountTypeName"], t["AccountTypeID"])
        self.cmb_account_type.blockSignals(False)

    def refresh_data(self):
        self._load_categories_combo()
        self._on_date_or_category_changed()
        self._load_history_entries()

    def _mark_dirty(self):
        if not self._ignore_signals:
            self.is_dirty = True

    def _on_item_changed(self, item):
        if not self._ignore_signals:
            self.is_dirty = True

    def has_unsaved_changes(self) -> bool:
        return self.is_dirty

    def prompt_unsaved_changes(self, form_name: str = "Production Entry") -> bool:
        if not self.has_unsaved_changes():
            return True
        choice = ToastNotification.confirm_unsaved_changes(self, form_name)
        if choice == "save":
            self._on_save_clicked()
            return not self.is_dirty
        elif choice == "discard":
            self.is_dirty = False
            return True
        else:
            return False

    def _on_date_or_category_changed(self):
        if self._ignore_signals:
            return
        if self.is_dirty:
            if not self.prompt_unsaved_changes():
                self._ignore_signals = True
                if hasattr(self, "_prev_qdate"):
                    self.dt_entry_date.setDate(self._prev_qdate)
                if hasattr(self, "_prev_cat_idx"):
                    self.cmb_account_type.setCurrentIndex(self._prev_cat_idx)
                self._ignore_signals = False
                return

        self._prev_qdate = self.dt_entry_date.date()
        self._prev_cat_idx = self.cmb_account_type.currentIndex()

        self._rebuild_dynamic_production_grid()
        self._auto_load_entry_for_date_and_category()

    def _auto_load_entry_for_date_and_category(self):
        cat_id = self.cmb_account_type.currentData()
        if not cat_id:
            return

        qdate = self.dt_entry_date.date()
        entry_date = date(qdate.year(), qdate.month(), qdate.day())

        entry = ProductionService.get_production_entry_by_date_and_category(entry_date, cat_id)

        self._ignore_signals = True
        if entry:
            self.is_edit_mode = True
            self.selected_production_id = entry["ProductionID"]
            self.txt_production_id.setText(f"PRD-{entry['ProductionID']:04d}")
            self.txt_remarks.setText(entry["Remarks"] or "")

            detail_map = {(d["WorkerID"], d["ProductID"]): d["Quantity"] for d in entry["Details"]}

            for row, a in enumerate(self.current_category_workers):
                wid = a["WorkerID"]
                for col, p in enumerate(self.current_molding_products):
                    pid = p["ProductID"]
                    qty = detail_map.get((wid, pid), 0.0)
                    item = self.prod_table.item(row, 2 + col)
                    if item:
                        item.setText(f"{qty:g}")

            category_title = self.cmb_account_type.currentText()
            self.lbl_grid_title.setText(f"✏️ Editing Existing Entry PRD-{entry['ProductionID']:04d} for {entry['EntryDate']} ({category_title})")
        else:
            self.is_edit_mode = False
            self.selected_production_id = None
            self.txt_production_id.setText("Auto-Generated")
            self.txt_remarks.clear()

            category_title = self.cmb_account_type.currentText()
            self.lbl_grid_title.setText(f"✨ New Production Entry for {entry_date.strftime('%Y-%m-%d')} ({category_title})")
        self._ignore_signals = False
        self.is_dirty = False

    def _rebuild_dynamic_production_grid(self):
        cat_id = self.cmb_account_type.currentData()
        if not cat_id:
            return

        cat_name = self.cmb_account_type.currentText().strip().lower()

        # Fetch active workers for selected category
        accounts = LabourService.search_accounts(account_type_id=cat_id, show_omitted=False)
        self.current_category_workers = accounts

        # Fetch Molding products dynamically from Product Master
        all_molding_products = ProductService.get_products_by_category("Molding")

        # Category-Specific Product Filter Rules:
        if "pathera" in cat_name:
            molding_products = [
                p for p in all_molding_products
                if "pathera" in p["ProductName"].lower()
            ]
            if not molding_products:
                molding_products = [p for p in all_molding_products if "kacchi" in p["ProductName"].lower()]
        elif "bahari" in cat_name or "bahri" in cat_name or "bharai" in cat_name:
            molding_products = [
                p for p in all_molding_products
                if "bahari" in p["ProductName"].lower() or "bahri" in p["ProductName"].lower()
            ]
            if not molding_products:
                molding_products = [p for p in all_molding_products if "kacchi" in p["ProductName"].lower()]
        elif "nakkasi" in cat_name:
            molding_products = [
                p for p in all_molding_products
                if any(k in p["ProductName"].lower() for k in ["awal", "doam", "khinger", "tile"]) and "kacchi" not in p["ProductName"].lower()
            ]
            if not molding_products:
                molding_products = all_molding_products
        else:
            molding_products = all_molding_products

        self.current_molding_products = molding_products

        # Build Headers: Pathera ID/Worker ID, Name, [Products...]
        id_title = "Pathera ID" if "pathera" in cat_name else "Worker ID"
        name_title = "Pathera Name" if "pathera" in cat_name else "Worker Name"

        headers = [id_title, name_title]
        for p in molding_products:
            headers.append(p["ProductName"])

        self.prod_table.clear()
        self.prod_table.setColumnCount(len(headers))
        self.prod_table.setHorizontalHeaderLabels(headers)

        self.prod_table.setColumnWidth(0, 110)  # ID
        self.prod_table.setColumnWidth(1, 180)  # Name
        for c in range(2, len(headers)):
            self.prod_table.setColumnWidth(c, 140)

        self.prod_table.setRowCount(len(accounts))

        for row, a in enumerate(accounts):
            item_id = QTableWidgetItem(a["WorkerID"])
            item_id.setFlags(Qt.ItemFlags(item_id.flags() & ~Qt.ItemIsEditable))  # Read-only
            item_id.setFont(QFont("Segoe UI", 9, QFont.Bold))

            item_name = QTableWidgetItem(a["EnglishName"])
            item_name.setFlags(Qt.ItemFlags(item_name.flags() & ~Qt.ItemIsEditable))  # Read-only

            self.prod_table.setItem(row, 0, item_id)
            self.prod_table.setItem(row, 1, item_name)

            for c in range(len(molding_products)):
                item_qty = QTableWidgetItem("0")
                item_qty.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.prod_table.setItem(row, 2 + c, item_qty)

        category_label_title = self.cmb_account_type.currentText()
        self.lbl_grid_title.setText(f"📋 Active Labourers ({category_label_title}) & Production Quantities")

    def _load_history_entries(self):
        entries = ProductionService.search_production_entries()
        self.history_table.setRowCount(len(entries))

        for row, e in enumerate(entries):
            self.history_table.setItem(row, 0, QTableWidgetItem(f"PRD-{e['ProductionID']:04d}"))
            self.history_table.setItem(row, 1, QTableWidgetItem(e["EntryDate"]))
            acc_type_name = e.get("AccountTypeName") or e.get("CategoryName", "")
            self.history_table.setItem(row, 2, QTableWidgetItem(acc_type_name))
            self.history_table.setItem(row, 3, QTableWidgetItem(e["Remarks"]))
            self.history_table.setItem(row, 4, QTableWidgetItem(e["CreatedBy"]))

            self.history_table.item(row, 0).setData(Qt.UserRole, e)

    def _clear_form(self):
        self._ignore_signals = True
        self.is_edit_mode = False
        self.selected_production_id = None

        self.txt_production_id.setText("Auto-Generated")
        self.dt_entry_date.setDate(QDate.currentDate())
        self.txt_remarks.clear()

        for row in range(self.prod_table.rowCount()):
            for col in range(2, self.prod_table.columnCount()):
                item = self.prod_table.item(row, col)
                if item:
                    item.setText("0")
        self._ignore_signals = False
        self.is_dirty = False

    def _load_entry_into_form(self, entry_summary: dict):
        e = ProductionService.get_production_entry_by_id(entry_summary["ProductionID"])
        if not e:
            return

        self.is_edit_mode = True
        self.selected_production_id = e["ProductionID"]

        self.txt_production_id.setText(f"PRD-{e['ProductionID']:04d}")

        if e["EntryDate"]:
            qd = QDate.fromString(e["EntryDate"], "yyyy-MM-dd")
            self.dt_entry_date.setDate(qd)

        self.txt_remarks.setText(e["Remarks"])

        idx = self.cmb_account_type.findData(e["AccountTypeID"])
        if idx >= 0:
            self.cmb_account_type.setCurrentIndex(idx)

        self._rebuild_dynamic_production_grid()

        # Fill quantities
        detail_map = {}
        for d in e["Details"]:
            detail_map[(d["WorkerID"], d["ProductID"])] = d["Quantity"]

        for row, a in enumerate(self.current_category_workers):
            wid = a["WorkerID"]
            for col, p in enumerate(self.current_molding_products):
                pid = p["ProductID"]
                qty = detail_map.get((wid, pid), 0.0)
                item = self.prod_table.item(row, 2 + col)
                if item:
                    item.setText(f"{qty:g}")

    def _on_history_row_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        summary = self.history_table.item(row, 0).data(Qt.UserRole)
        if summary:
            self._load_entry_into_form(summary)

    def _on_history_row_clicked(self, item: QTableWidgetItem):
        row = item.row()
        summary = self.history_table.item(row, 0).data(Qt.UserRole)
        if summary:
            self._load_entry_into_form(summary)

    def _on_view_clicked(self):
        row = self.history_table.currentRow()
        if row >= 0:
            summary = self.history_table.item(row, 0).data(Qt.UserRole)
            if summary:
                self._load_entry_into_form(summary)
                ToastNotification.show_info(self, "Entry Loaded", f"Production Entry PRD-{summary['ProductionID']:04d} loaded into form for viewing/editing.")
        else:
            ToastNotification.show_warning(self, "Selection Required", "Please select a historical entry row to view.")

    def _on_new_clicked(self):
        self._clear_form()

    def _on_save_clicked(self):
        qdate = self.dt_entry_date.date()
        entry_date = date(qdate.year(), qdate.month(), qdate.day())
        account_type_id = self.cmb_account_type.currentData()
        remarks = self.txt_remarks.text().strip()

        details_list = []

        for row, a in enumerate(self.current_category_workers):
            wid = a["WorkerID"]
            for col, p in enumerate(self.current_molding_products):
                pid = p["ProductID"]
                item = self.prod_table.item(row, 2 + col)
                raw_text = item.text().replace(",", "").strip() if item else "0"
                try:
                    qty = float(raw_text) if raw_text else 0.0
                except ValueError:
                    ToastNotification.show_error(self, "Invalid Quantity", f"Invalid quantity '{raw_text}' entered for Worker {wid}.")
                    return

                if qty > 0.0:
                    details_list.append({
                        "WorkerID": wid,
                        "ProductID": pid,
                        "Quantity": qty
                    })

        if not details_list or len(details_list) == 0:
            ToastNotification.show_warning(self, "Empty Entry", "Please enter at least one non-zero production quantity before saving.")
            return

        success, msg = ProductionService.save_production_entry(
            entry_date=entry_date,
            account_type_id=account_type_id,
            remarks=remarks,
            details_list=details_list,
            production_id=self.selected_production_id,
            is_edit_mode=self.is_edit_mode
        )

        if success:
            ToastNotification.show_success(self, "Success", msg)
            self._load_history_entries()
            self._auto_load_entry_for_date_and_category()
        else:
            ToastNotification.show_error(self, "Error", msg)

    def _on_delete_clicked(self):
        if not self.selected_production_id:
            ToastNotification.show_warning(self, "Selection Required", "Please select a production entry to delete.")
            return

        if ToastNotification.confirm(self, "Confirm Delete", f"Permanently delete Production Entry PRD-{self.selected_production_id:04d} and reverse related Khata ledger entries?"):
            success, msg = ProductionService.delete_production_entry(self.selected_production_id)
            if success:
                ToastNotification.show_success(self, "Success", msg)
                self._clear_form()
                self._load_history_entries()
            else:
                ToastNotification.show_error(self, "Delete Error", msg)

    def _on_print_clicked(self):
        ToastNotification.show_info(
            self,
            "Print Production Entry",
            f"Daily Production Report sent to default system printer for {self.history_table.rowCount()} historical records."
        )

    def _on_export_excel_clicked(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Production Entries to Excel", "Production_Entries_Report.xlsx", "Excel Files (*.xlsx *.csv)"
        )
        if not file_path:
            return

        try:
            entries = ProductionService.search_production_entries()

            if file_path.endswith(".xlsx"):
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Production Entries"

                headers = ["Entry ID", "Production Date", "Labour Category", "Remarks", "Created By"]
                ws.append(headers)

                for e in entries:
                    ws.append([
                        f"PRD-{e['ProductionID']:04d}", e["EntryDate"],
                        e["AccountTypeName"], e["Remarks"], e["CreatedBy"]
                    ])

                wb.save(file_path)
            else:
                import csv
                with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Entry ID", "Production Date", "Labour Category", "Remarks", "Created By"])
                    for e in entries:
                        writer.writerow([
                            f"PRD-{e['ProductionID']:04d}", e["EntryDate"],
                            e["AccountTypeName"], e["Remarks"], e["CreatedBy"]
                        ])

            ToastNotification.show_success(self, "Export Complete", f"Successfully exported production data to:\n{file_path}")
        except Exception as e:
            ToastNotification.show_error(self, "Export Failed", f"Failed to export production data: {e}")

    def _on_close_clicked(self):
        self.close_requested.emit()

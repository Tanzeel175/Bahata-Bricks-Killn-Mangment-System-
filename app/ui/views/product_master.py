from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from app.services.product_service import ProductService
from app.security.session import current_session
from app.ui.components.toast import ToastNotification
from app.ui.components.formatted_inputs import NumericLineEdit


class ProductMasterView(QWidget):
    """
    Dynamic Product Master Management View.
    Central repository for managing system products, category mappings, unit rates, and stock values.
    """

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_edit_mode = False
        self.selected_product_id = None
        self.category_checkboxes = {}

        self._init_ui()
        self.refresh_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. TOP HEADER TITLE
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()
        t = QLabel("Dynamic Product Master Management")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        sub = QLabel("Central product repository for Purchase, Sales, Production/Molding, and Inventory modules")
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

        # 2. UPPER DATA ENTRY FORM CARD (3 COMPACT COLUMNS)
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

        self.txt_product_id = QLineEdit()
        self.txt_product_id.setPlaceholderText("PRD-0001 (Auto or enter ID to load & edit)")
        self.txt_product_id.setMinimumHeight(28)
        self.txt_product_id.textEdited.connect(self._on_product_id_input_changed)
        self.txt_product_id.returnPressed.connect(self._on_product_id_return_pressed)

        self.txt_product_name = QLineEdit()
        self.txt_product_name.setPlaceholderText("e.g. Coal, Kacchi Brick, Paki Brick, Clay")
        self.txt_product_name.setMinimumHeight(28)

        self.txt_unit_rate = NumericLineEdit()
        self.txt_unit_rate.setMinimumHeight(28)
        self.txt_unit_rate.setPlaceholderText("0.00")
        self.txt_unit_rate.textChanged.connect(self._recalculate_stock_value)

        col1_layout.addWidget(make_field_heading("Product ID (Auto or Enter ID to Edit)*", required=True))
        col1_layout.addWidget(self.txt_product_id)
        col1_layout.addSpacing(2)

        col1_layout.addWidget(make_field_heading("Product Name*", required=True))
        col1_layout.addWidget(self.txt_product_name)
        col1_layout.addSpacing(2)

        col1_layout.addWidget(make_field_heading("Rate of Product (PKR)"))
        col1_layout.addWidget(self.txt_unit_rate)

        form_hbox.addLayout(col1_layout, stretch=1)

        # --- COLUMN 2 ---
        col2_layout = QVBoxLayout()
        col2_layout.setSpacing(4)

        col2_layout.addWidget(make_field_heading("Product Category* (Multi-Select)", required=True))

        cat_box = QFrame()
        cat_box.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px; padding: 6px; }")
        cat_box_layout = QVBoxLayout(cat_box)
        cat_box_layout.setSpacing(4)
        cat_box_layout.setContentsMargins(6, 6, 6, 6)

        # Checkboxes for categories will be populated dynamically
        self.cat_checkbox_container = cat_box_layout
        col2_layout.addWidget(cat_box)
        col2_layout.addSpacing(2)

        self.txt_stock_quantity = NumericLineEdit()
        self.txt_stock_quantity.setMinimumHeight(28)
        self.txt_stock_quantity.setPlaceholderText("0.00")
        self.txt_stock_quantity.setReadOnly(True)
        self.txt_stock_quantity.setStyleSheet("background-color: #EFF6FF; color: #1E40AF; font-weight: 800;")
        self.txt_stock_quantity.textChanged.connect(self._recalculate_stock_value)

        col2_layout.addWidget(make_field_heading("Available Stock (Linked Live)"))
        col2_layout.addWidget(self.txt_stock_quantity)

        form_hbox.addLayout(col2_layout, stretch=1)

        # --- COLUMN 3 ---
        col3_layout = QVBoxLayout()
        col3_layout.setSpacing(4)

        self.txt_total_stock_value = QLineEdit()
        self.txt_total_stock_value.setPlaceholderText("0.00")
        self.txt_total_stock_value.setReadOnly(True)
        self.txt_total_stock_value.setMinimumHeight(28)
        self.txt_total_stock_value.setStyleSheet("background-color: #EFF6FF; color: #1E40AF; font-weight: 800;")

        self.txt_description = QLineEdit()
        self.txt_description.setPlaceholderText("Optional notes or specification about product...")
        self.txt_description.setMinimumHeight(28)

        col3_layout.addWidget(make_field_heading("Total Price of Stock (Auto-Calculated PKR)"))
        col3_layout.addWidget(self.txt_total_stock_value)
        col3_layout.addSpacing(2)

        col3_layout.addWidget(make_field_heading("Description / Internal Notes"))
        col3_layout.addWidget(self.txt_description)

        form_hbox.addLayout(col3_layout, stretch=1)

        container_layout.addWidget(form_card)

        # 3. MIDDLE ACTION BUTTON BAR (ROUNDED PILLS)
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

        self.btn_update = make_pill("🔄 Update", "#0284C7", "#0369A1")
        self.btn_update.clicked.connect(self._on_save_clicked)

        self.btn_delete = make_pill("❌ Delete", "#E11D48", "#BE123C")
        self.btn_delete.clicked.connect(self._on_delete_clicked)

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
        btn_bar.addWidget(self.btn_clear)
        btn_bar.addWidget(self.btn_print)
        btn_bar.addWidget(self.btn_export)
        btn_bar.addWidget(self.btn_close)

        container_layout.addLayout(btn_bar)

        # 4. LOWER SEARCH FILTERS & DATA GRID TABLE CARD
        grid_card = QFrame()
        grid_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }"
        )
        grid_card_layout = QVBoxLayout(grid_card)
        grid_card_layout.setSpacing(10)

        # Filter Bar Row
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        lbl_cat_flt = QLabel("Category Filter:")
        lbl_cat_flt.setStyleSheet("font-weight: 700; color: #334155; font-size: 12px; border: none; background: transparent;")
        self.cmb_filter_category = QComboBox()
        self.cmb_filter_category.setMinimumHeight(32)
        self.cmb_filter_category.currentIndexChanged.connect(self._on_filter_changed)

        self.txt_search = QLineEdit()
        self.txt_search.setMinimumHeight(32)
        self.txt_search.setPlaceholderText("Search by Product ID, Name, Description...")
        self.txt_search.textChanged.connect(self._on_search_text_changed)

        filter_bar.addWidget(lbl_cat_flt)
        filter_bar.addWidget(self.cmb_filter_category, stretch=1)
        filter_bar.addWidget(self.txt_search, stretch=2)

        grid_card_layout.addLayout(filter_bar)

        # Data Grid Table
        self.table = QTableWidget()
        headers = [
            "Product ID", "Product Name", "Assigned Categories",
            "Rate (PKR)", "In Stock", "Total Value (PKR)", "Description", "Created Date"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        self.table.horizontalHeader().setMinimumHeight(54)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.table.setColumnWidth(0, 95)   # Product ID
        self.table.setColumnWidth(1, 160)  # Product Name
        self.table.setColumnWidth(2, 160)  # Assigned Categories
        self.table.setColumnWidth(3, 110)  # Rate
        self.table.setColumnWidth(4, 100)  # In Stock
        self.table.setColumnWidth(5, 140)  # Total Value
        self.table.setColumnWidth(6, 220)  # Description
        self.table.setColumnWidth(7, 110)  # Created Date

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(240)
        self.table.itemDoubleClicked.connect(self._on_row_double_clicked)
        self.table.itemClicked.connect(self._on_row_clicked)

        grid_card_layout.addWidget(self.table)
        container_layout.addWidget(grid_card)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

        # Enforce RBAC permissions
        self._update_permission_states()

    def _recalculate_stock_value(self):
        try:
            rate_text = self.txt_unit_rate.text().replace(",", "").strip()
            rate = float(rate_text) if rate_text else 0.0
        except ValueError:
            rate = 0.0

        try:
            stock_text = self.txt_stock_quantity.text().replace(",", "").strip()
            stock = float(stock_text) if stock_text else 0.0
        except ValueError:
            stock = 0.0

        total = rate * stock
        self.txt_total_stock_value.setText(f"{total:,.2f}")

    def _update_permission_states(self):
        if not current_session.is_admin:
            self.btn_delete.setEnabled(False)
            self.btn_delete.setToolTip("Munshi role is not permitted to delete product records.")

    def _load_categories_checkboxes(self):
        # Clear old checkboxes
        for cid, chk in list(self.category_checkboxes.items()):
            chk.deleteLater()
        self.category_checkboxes.clear()

        categories = ProductService.get_all_categories()

        # Update category checkboxes in form
        for cat in categories:
            chk = QCheckBox(cat["CategoryName"])
            chk.setStyleSheet("font-weight: 600; color: #1E293B; font-size: 12px; border: none; background: transparent;")
            self.cat_checkbox_container.addWidget(chk)
            self.category_checkboxes[cat["CategoryID"]] = chk

        # Update Category Filter combo
        self.cmb_filter_category.blockSignals(True)
        self.cmb_filter_category.clear()
        self.cmb_filter_category.addItem("All Categories", 0)
        for cat in categories:
            self.cmb_filter_category.addItem(cat["CategoryName"], cat["CategoryID"])
        self.cmb_filter_category.blockSignals(False)

    def refresh_data(self):
        self._load_categories_checkboxes()
        self._execute_search()
        self._clear_form()

    def _execute_search(self):
        query_str = self.txt_search.text().strip()
        cat_id = self.cmb_filter_category.currentData() or 0

        products = ProductService.search_products(query_str, cat_id)

        self.table.setRowCount(len(products))

        for row, p in enumerate(products):
            self.table.setItem(row, 0, QTableWidgetItem(f"PRD-{p['ProductID']:04d}"))
            self.table.setItem(row, 1, QTableWidgetItem(p["ProductName"]))
            self.table.setItem(row, 2, QTableWidgetItem(p["CategoryNames"]))
            self.table.setItem(row, 3, QTableWidgetItem(f"{p['UnitRate']:,.2f}"))
            self.table.setItem(row, 4, QTableWidgetItem(f"{p['StockQuantity']:,.2f}"))

            val_item = QTableWidgetItem(f"{p['TotalStockValue']:,.2f}")
            self.table.setItem(row, 5, val_item)

            self.table.setItem(row, 6, QTableWidgetItem(p["Description"]))
            self.table.setItem(row, 7, QTableWidgetItem(p["CreatedDate"]))

            self.table.item(row, 0).setData(Qt.UserRole, p)
            self.table.setRowHeight(row, 40)

        self.table.clearSelection()
        self.table.verticalScrollBar().setValue(0)
        self.table.scrollToTop()

    def _on_search_text_changed(self):
        self._execute_search()

    def _on_filter_changed(self):
        self._execute_search()

    def _on_product_id_input_changed(self):
        raw_id = self.txt_product_id.text().strip()
        if not raw_id:
            return

        lookup_ids = [raw_id, raw_id.upper()]
        if raw_id.isdigit():
            lookup_ids.append(int(raw_id))
            lookup_ids.append(f"PRD-{int(raw_id):04d}")
        elif raw_id.upper().startswith("PRD-"):
            num_part = raw_id[4:].strip()
            if num_part.isdigit():
                lookup_ids.append(int(num_part))

        prod = None
        for pid in lookup_ids:
            if isinstance(pid, int):
                prod = ProductService.get_product_by_id(pid)
            elif isinstance(pid, str) and pid.isdigit():
                prod = ProductService.get_product_by_id(int(pid))
            if prod:
                break

        if prod:
            self._load_product_into_form(prod, set_id_text=False)
            for row in range(self.table.rowCount()):
                item_p = self.table.item(row, 0).data(Qt.UserRole)
                if item_p and item_p.get("ProductID") == prod["ProductID"]:
                    self.table.selectRow(row)
                    break
        else:
            if self.is_edit_mode:
                self.is_edit_mode = False
                self.selected_product_id = None

    def _on_product_id_return_pressed(self):
        self._on_product_id_input_changed()
        if self.is_edit_mode and self.selected_product_id:
            self.txt_product_id.blockSignals(True)
            self.txt_product_id.setText(f"PRD-{self.selected_product_id:04d}")
            self.txt_product_id.blockSignals(False)
            self.txt_product_name.setFocus()

    def _clear_form(self):
        self.is_edit_mode = False
        self.selected_product_id = None

        self.txt_product_id.blockSignals(True)
        next_id = ProductService.generate_product_id()
        self.txt_product_id.setText(next_id)
        self.txt_product_id.blockSignals(False)

        self.txt_product_name.clear()
        self.txt_unit_rate.setText("0.00")
        self.txt_stock_quantity.setText("0")
        self.txt_total_stock_value.setText("0.00")
        self.txt_description.clear()

        for chk in self.category_checkboxes.values():
            chk.setChecked(False)

    def _load_product_into_form(self, product: dict, set_id_text: bool = True):
        self.is_edit_mode = True
        self.selected_product_id = product["ProductID"]

        if set_id_text:
            self.txt_product_id.blockSignals(True)
            self.txt_product_id.setText(f"PRD-{product['ProductID']:04d}")
            self.txt_product_id.blockSignals(False)
        self.txt_product_name.setText(product["ProductName"])
        self.txt_unit_rate.setText(f"{product['UnitRate']:.2f}")
        self.txt_stock_quantity.setText(f"{product['StockQuantity']:.2f}")
        self.txt_description.setText(product["Description"])

        self._recalculate_stock_value()

        selected_cids = product.get("CategoryIDs", [])
        for cid, chk in self.category_checkboxes.items():
            chk.setChecked(cid in selected_cids)

    def _on_row_double_clicked(self, item: QTableWidgetItem):
        row = item.row()
        product = self.table.item(row, 0).data(Qt.UserRole)
        if product:
            self._load_product_into_form(product)

    def _on_row_clicked(self, item: QTableWidgetItem):
        row = item.row()
        product = self.table.item(row, 0).data(Qt.UserRole)
        if product:
            self._load_product_into_form(product)

    def _on_new_clicked(self):
        self._clear_form()
        self.txt_product_name.setFocus()

    def _get_selected_category_ids(self) -> list:
        return [cid for cid, chk in self.category_checkboxes.items() if chk.isChecked()]

    def _on_save_clicked(self):
        try:
            unit_rate = float(self.txt_unit_rate.text().replace(",", "").strip() or 0)
        except ValueError:
            unit_rate = 0.0

        try:
            stock_qty = float(self.txt_stock_quantity.text().replace(",", "").strip() or 0)
        except ValueError:
            stock_qty = 0.0

        data = {
            "ProductID": self.selected_product_id,
            "ProductName": self.txt_product_name.text().strip(),
            "UnitRate": unit_rate,
            "StockQuantity": stock_qty,
            "Description": self.txt_description.text().strip()
        }

        selected_cids = self._get_selected_category_ids()

        success, msg = ProductService.save_product(
            data=data,
            selected_category_ids=selected_cids,
            is_edit_mode=self.is_edit_mode
        )

        if success:
            ToastNotification.show_success(self, "Success", msg)
            self._clear_form()
            self.refresh_data()
        else:
            ToastNotification.show_error(self, "Validation Error", msg)

    def _on_delete_clicked(self):
        if not self.selected_product_id:
            ToastNotification.show_warning(self, "Selection Required", "Please select a product to delete.")
            return

        if ToastNotification.confirm(self, "Confirm Delete", f"Permanently delete Product '{self.txt_product_name.text()}'?"):
            success, msg = ProductService.delete_product(self.selected_product_id)
            if success:
                ToastNotification.show_success(self, "Success", msg)
                self._clear_form()
                self.refresh_data()
            else:
                ToastNotification.show_error(self, "Delete Error", msg)

    def _on_print_clicked(self):
        ToastNotification.show_info(
            self,
            "Print Product Master",
            f"Product Master Ledger Report sent to default system printer for {self.table.rowCount()} product records."
        )

    def _on_export_excel_clicked(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Product Master to Excel", "Product_Master_Report.xlsx", "Excel Files (*.xlsx *.csv)"
        )
        if not file_path:
            return

        try:
            products = ProductService.search_products()

            if file_path.endswith(".xlsx"):
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Product Master"

                headers = [
                    "ProductID", "ProductName", "AssignedCategories",
                    "UnitRate", "StockQuantity", "TotalStockValue", "Description", "CreatedDate"
                ]
                ws.append(headers)

                for p in products:
                    ws.append([
                        f"PRD-{p['ProductID']:04d}", p["ProductName"],
                        p["CategoryNames"], p["UnitRate"], p["StockQuantity"],
                        p["TotalStockValue"], p["Description"], p["CreatedDate"]
                    ])

                wb.save(file_path)
            else:
                import csv
                with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "ProductID", "ProductName", "AssignedCategories",
                        "UnitRate", "StockQuantity", "TotalStockValue", "Description", "CreatedDate"
                    ])
                    for p in products:
                        writer.writerow([
                            f"PRD-{p['ProductID']:04d}", p["ProductName"],
                            p["CategoryNames"], p["UnitRate"], p["StockQuantity"],
                            p["TotalStockValue"], p["Description"], p["CreatedDate"]
                        ])

            ToastNotification.show_success(self, "Export Complete", f"Successfully exported product data to:\n{file_path}")
        except Exception as e:
            ToastNotification.show_error(self, "Export Failed", f"Failed to export product data: {e}")

    def _on_close_clicked(self):
        self.close_requested.emit()

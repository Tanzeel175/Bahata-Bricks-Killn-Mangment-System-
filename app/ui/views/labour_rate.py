from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QFrame, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from app.services.production_service import ProductionService
from app.services.labour_service import LabourService
from app.services.product_service import ProductService
from app.ui.components.toast import ToastNotification


class LabourRateView(QWidget):
    """
    Labour Rate Management View.
    Allows specifying payment rates (per 1,000 units of production) for each worker and product.
    Supports Pathera, Bahri Wala, and Nakkasi Wala rate configurations.
    """

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
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
        t = QLabel("💰 Labour Payment Rate Management")
        t.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        sub = QLabel("Configure piece-rate payment rates per 1,000 production units for each labour worker & product")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")
        title_box.addWidget(t)
        title_box.addWidget(sub)
        header_box.addLayout(title_box)
        header_box.addStretch()

        main_layout.addLayout(header_box)

        # Scrollable container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 8, 0)
        container_layout.setSpacing(12)

        # 2. CATEGORY SELECTOR CARD
        cat_card = QFrame()
        cat_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; }"
        )
        c_layout = QHBoxLayout(cat_card)
        c_layout.setSpacing(16)

        lbl_cat = QLabel("Select Labour Category:")
        lbl_cat.setStyleSheet("font-weight: 700; color: #334155; font-size: 12px; border: none; background: transparent;")

        self.cmb_account_type = QComboBox()
        self.cmb_account_type.setMinimumHeight(32)
        self.cmb_account_type.currentIndexChanged.connect(self._on_category_changed)

        c_layout.addWidget(lbl_cat)
        c_layout.addWidget(self.cmb_account_type, stretch=1)
        c_layout.addStretch(2)

        container_layout.addWidget(cat_card)

        # 3. DYNAMIC RATE GRID CARD
        grid_card = QFrame()
        grid_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 12px; }"
        )
        grid_layout = QVBoxLayout(grid_card)
        grid_layout.setSpacing(8)

        self.lbl_grid_title = QLabel("📊 Payment Rates per 1,000 Units (PKR)")
        self.lbl_grid_title.setStyleSheet("font-weight: 700; color: #1E293B; font-size: 13px; border: none; background: transparent;")
        grid_layout.addWidget(self.lbl_grid_title)

        self.rate_table = QTableWidget()
        self.rate_table.horizontalHeader().setMinimumHeight(54)
        self.rate_table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.rate_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.rate_table.setAlternatingRowColors(True)
        self.rate_table.setMinimumHeight(340)

        grid_layout.addWidget(self.rate_table)
        container_layout.addWidget(grid_card)

        # 4. ACTION BUTTON BAR (Save, Refresh, Close)
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        def make_pill(text, bg_color, hover_color, text_color="#FFFFFF"):
            btn = QPushButton(text)
            btn.setMinimumHeight(36)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {bg_color}; color: {text_color}; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 16px; border: none; }} "
                f"QPushButton:hover {{ background-color: {hover_color}; }} "
            )
            return btn

        self.btn_save_rates = make_pill("💾 Save All Rates", "#0284C7", "#0369A1")
        self.btn_save_rates.clicked.connect(self._on_save_all_rates_clicked)

        self.btn_refresh = make_pill("🔄 Refresh", "#64748B", "#475569")
        self.btn_refresh.clicked.connect(self.refresh_data)

        self.btn_close = make_pill("❌ Close", "#94A3B8", "#64748B")
        self.btn_close.clicked.connect(self._on_close_clicked)

        btn_bar.addWidget(self.btn_save_rates)
        btn_bar.addWidget(self.btn_refresh)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_close)

        self.is_dirty = False
        self._ignore_signals = False
        self.rate_table.itemChanged.connect(self._on_item_changed)

        container_layout.addLayout(btn_bar)

        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

    def _on_item_changed(self, item):
        if not self._ignore_signals:
            self.is_dirty = True

    def has_unsaved_changes(self) -> bool:
        return self.is_dirty

    def prompt_unsaved_changes(self, form_name: str = "Labour Payment Rates") -> bool:
        if not self.has_unsaved_changes():
            return True
        choice = ToastNotification.confirm_unsaved_changes(self, form_name)
        if choice == "save":
            self._on_save_all_rates_clicked()
            return not self.is_dirty
        elif choice == "discard":
            self.is_dirty = False
            return True
        else:
            return False

    def _load_categories_combo(self):
        types = LabourService.get_account_types()
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
        self._on_category_changed()

    def _on_category_changed(self):
        if self._ignore_signals:
            return
        if self.is_dirty:
            if not self.prompt_unsaved_changes():
                self._ignore_signals = True
                if hasattr(self, "_prev_cat_idx"):
                    self.cmb_account_type.setCurrentIndex(self._prev_cat_idx)
                self._ignore_signals = False
                return

        self._prev_cat_idx = self.cmb_account_type.currentIndex()
        self._rebuild_dynamic_rate_grid()

    def _rebuild_dynamic_rate_grid(self):
        cat_id = self.cmb_account_type.currentData()
        if not cat_id:
            return

        cat_name = self.cmb_account_type.currentText().strip().lower()

        accounts = LabourService.search_accounts(account_type_id=cat_id, show_omitted=False)
        self.current_category_workers = accounts

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

        id_title = "Pathera ID" if "pathera" in cat_name else "Worker ID"
        name_title = "Pathera Name" if "pathera" in cat_name else "Worker Name"

        headers = [id_title, name_title]
        for p in molding_products:
            headers.append(f"{p['ProductName']} Rate (/1000)")

        self.rate_table.clear()
        self.rate_table.setColumnCount(len(headers))
        self.rate_table.setHorizontalHeaderLabels(headers)

        self.rate_table.setColumnWidth(0, 110)  # ID
        self.rate_table.setColumnWidth(1, 180)  # Name
        for c in range(2, len(headers)):
            self.rate_table.setColumnWidth(c, 160)

        self.rate_table.setRowCount(len(accounts))

        self._ignore_signals = True
        for row, a in enumerate(accounts):
            wid = a["WorkerID"]
            item_id = QTableWidgetItem(wid)
            item_id.setFlags(Qt.ItemFlags(item_id.flags() & ~Qt.ItemIsEditable))
            item_id.setFont(QFont("Segoe UI", 9, QFont.Bold))

            item_name = QTableWidgetItem(a["EnglishName"])
            item_name.setFlags(Qt.ItemFlags(item_name.flags() & ~Qt.ItemIsEditable))

            self.rate_table.setItem(row, 0, item_id)
            self.rate_table.setItem(row, 1, item_name)

            # Load worker rates
            rates = ProductionService.get_worker_rates(wid)

            for col, p in enumerate(molding_products):
                pid = p["ProductID"]
                rate_val = rates.get(pid, 0.0)
                item_rate = QTableWidgetItem(f"{rate_val:,.2f}")
                item_rate.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.rate_table.setItem(row, 2 + col, item_rate)
        self._ignore_signals = False
        self.is_dirty = False

        category_label_title = self.cmb_account_type.currentText()
        self.lbl_grid_title.setText(f"📊 Payment Rates per 1,000 Units ({category_label_title})")

    def _on_save_all_rates_clicked(self):
        saved_count = 0
        for row, a in enumerate(self.current_category_workers):
            wid = a["WorkerID"]
            rate_dict = {}
            for col, p in enumerate(self.current_molding_products):
                pid = p["ProductID"]
                item = self.rate_table.item(row, 2 + col)
                raw_text = item.text().replace(",", "").strip() if item else "0"
                try:
                    r_val = float(raw_text) if raw_text else 0.0
                except ValueError:
                    ToastNotification.show_error(self, "Invalid Rate", f"Invalid rate '{raw_text}' for Worker {wid}.")
                    return
                rate_dict[pid] = r_val

            success, msg = ProductionService.save_worker_rates(wid, rate_dict)
            if success:
                saved_count += 1
            else:
                ToastNotification.show_error(self, "Error Saving Rates", msg)
                return

        self.is_dirty = False
        ToastNotification.show_success(
            self,
            "Rates Saved",
            f"Successfully saved per-1,000 production rates for {saved_count} workers."
        )

    def _on_close_clicked(self):
        self.close_requested.emit()

from typing import List, Tuple, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTabBar, QMenuBar,
    QMenu, QToolBar, QLabel, QPushButton, QFileDialog, QFrame, QApplication,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QScrollArea, QStackedWidget
)
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtCore import Qt, QTimer, QEvent
from app.config import APP_NAME, APP_SUBTITLE, APP_VERSION, COMPANY_NAME
from app.security.session import current_session
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.labour_service import LabourService
from app.services.user_service import UserService
from app.ui.components.status_bar import AppStatusBar
from app.ui.components.toast import ToastNotification
from app.ui.components.office_ui import MetricCard
from app.ui.theme_manager import theme_mgr
from app.ui.views.labour_master import LabourMasterView
from app.ui.views.user_management import UserManagementView
from app.ui.views.audit_logs import AuditLogsView
from app.ui.views.product_master import ProductMasterView
from app.ui.views.production_entry import ProductionEntryView
from app.ui.views.labour_rate import LabourRateView
from app.ui.views.sales_entry import SalesEntryView
from app.ui.views.money_transactions import MoneyTransactionsView
from app.ui.views.central_registers import CentralRegistersView


class SidebarNav(QFrame):
    """Premium ERP navigation matching BAHTA ERP Stitch Design."""

    EXPANDED_WIDTH = 215
    COLLAPSED_WIDTH = 58

    def __init__(self, main_win, parent=None):
        super().__init__(parent)
        self.main_win = main_win
        self.is_collapsed = False
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self.setObjectName("premiumSidebar")
        self.nav_buttons: List[Tuple[QPushButton, str, str]] = []  # (button, full_text, icon_text)
        self.section_labels: List[QLabel] = []
        self._init_ui()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 12, 8, 12)
        outer_layout.setSpacing(4)

        # Brand header with logo badge and collapse toggle
        header_row = QHBoxLayout()
        header_row.setContentsMargins(4, 2, 4, 8)
        header_row.setSpacing(8)

        self.logo_badge = QLabel("B")
        self.logo_badge.setFixedSize(30, 30)
        self.logo_badge.setAlignment(Qt.AlignCenter)
        self.logo_badge.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #D97706, stop:1 #2563EB); "
            "color: #FFFFFF; font-weight: 900; font-size: 14px; border-radius: 6px;"
        )
        header_row.addWidget(self.logo_badge)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(1)
        self.brand_label = QLabel("BAHTA ERP")
        self.brand_label.setObjectName("sidebarBrand")
        self.brand_label.setStyleSheet("font-size: 13.5px; font-weight: 800; color: #FFFFFF; letter-spacing: 0.5px;")

        self.company_label = QLabel("Enterprise Brick Kiln")
        self.company_label.setObjectName("sidebarCompany")
        self.company_label.setStyleSheet("font-size: 9.5px; font-weight: 600; color: #94A3B8; letter-spacing: 0.6px;")

        brand_box.addWidget(self.brand_label)
        brand_box.addWidget(self.company_label)
        header_row.addLayout(brand_box)
        header_row.addStretch()

        self.btn_toggle = QPushButton("<")
        self.btn_toggle.setToolTip("Toggle sidebar width")
        self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setFixedSize(22, 22)
        self.btn_toggle.setStyleSheet(
            "QPushButton { background: #1B2F4F; color: #94A3B8; border: 1px solid #2B4E80; border-radius: 4px; font-size: 11px; font-weight: bold; } "
            "QPushButton:hover { background: #2563EB; color: #FFFFFF; }"
        )
        self.btn_toggle.clicked.connect(self.toggle_collapse)
        header_row.addWidget(self.btn_toggle)

        outer_layout.addLayout(header_row)

        def section(title):
            label = QLabel(title)
            label.setObjectName("sidebarSection")
            label.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.8px; margin-top: 10px; margin-bottom: 2px;")
            self.section_labels.append(label)
            outer_layout.addWidget(label)

        def item(full_title, short_badge, slot, active=False, count_badge=None):
            btn_text = f"{full_title}  {count_badge}" if count_badge else full_title
            button = QPushButton(btn_text)
            button.setObjectName("sidebarActive" if active else "sidebarItem")
            button.setMinimumHeight(36)
            button.setToolTip(full_title)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(slot)
            self.nav_buttons.append((button, btn_text, short_badge))
            outer_layout.addWidget(button)
            return button

        section("WORKSPACE")
        self.btn_dashboard_nav = item("Dashboard", "DB", self.main_win.open_dashboard_tab, True)

        section("OPERATIONS CONTROL")
        self.btn_labour_nav = item("Labour Accounts", "LA", self.main_win.open_labour_master_tab)
        self.btn_product_nav = item("Product Master", "PM", self.main_win.open_product_master_tab)
        self.btn_production_nav = item("Daily Production", "PR", self.main_win.open_production_entry_tab)
        self.btn_sales_nav = item("Sales & Billing", "SB", self.main_win.open_sales_entry_tab)
        self.btn_rate_nav = item("Labour Rates", "LR", self.main_win.open_labour_rate_tab)
        self.btn_central_registers_nav = item("Central Registers", "CR", self.main_win.open_central_registers_tab)
        self.btn_cash_nav = item("Cashbook Journal", "CB", self.main_win.open_money_transactions_tab)

        self.btn_user_nav = None
        self.btn_audit_nav = None
        if current_session.is_admin:
            section("SECURITY & AUDIT")
            self.btn_user_nav = item("User Security", "US", self.main_win.open_user_management_tab)
            self.btn_audit_nav = item("Audit Trail", "AT", self.main_win.open_audit_logs_tab)

        outer_layout.addStretch()

        section("PREFERENCES")
        is_dark = theme_mgr.is_dark_mode()
        icon = "☼" if is_dark else "☾"
        status_pill = "On" if is_dark else "Off"
        self.btn_theme = item(
            f"{icon}  Dark Theme ({status_pill})",
            icon,
            self._toggle_theme
        )

        self.btn_logout = item("Sign Out", "SO", self.main_win._on_logout)
        self.btn_logout.setObjectName("sidebarLogout")

    def _toggle_theme(self):
        theme_mgr.toggle_theme()
        self.update_theme_button()

    def update_theme_button(self):
        is_dark = theme_mgr.is_dark_mode()
        icon = "☼" if is_dark else "☾"
        status_pill = "On" if is_dark else "Off"
        full_text = f"{icon}  Dark Theme ({status_pill})"
        short_badge = icon
        if hasattr(self, "btn_theme") and self.btn_theme:
            self.btn_theme.setText(short_badge if self.is_collapsed else full_text)
            self.btn_theme.setToolTip(full_text)

    def set_active_button(self, active_button: QPushButton):
        """Highlight the active sidebar navigation button and unhighlight others."""
        for btn, full_text, icon_char in self.nav_buttons:
            if btn == getattr(self, "btn_logout", None) or btn.objectName() == "sidebarLogout":
                continue
            is_active = (btn == active_button)
            target_name = "sidebarActive" if is_active else "sidebarItem"
            if btn.objectName() != target_name:
                btn.setObjectName(target_name)
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.update()

    def set_active_by_view(self, view_widget):
        """Map a view widget instance to its corresponding sidebar navigation button."""
        if view_widget is None:
            return

        type_name = view_widget.__class__.__name__
        mapping = {
            "DashboardWidget": getattr(self, "btn_dashboard_nav", None),
            "LabourMasterView": getattr(self, "btn_labour_nav", None),
            "ProductMasterView": getattr(self, "btn_product_nav", None),
            "ProductionEntryView": getattr(self, "btn_production_nav", None),
            "SalesEntryView": getattr(self, "btn_sales_nav", None),
            "LabourRateView": getattr(self, "btn_rate_nav", None),
            "CentralRegistersView": getattr(self, "btn_central_registers_nav", None),
            "MoneyTransactionsView": getattr(self, "btn_cash_nav", None),
            "UserManagementView": getattr(self, "btn_user_nav", None),
            "AuditLogsView": getattr(self, "btn_audit_nav", None),
        }
        target_btn = mapping.get(type_name)
        if target_btn:
            self.set_active_button(target_btn)

    def toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(self.COLLAPSED_WIDTH)
            self.brand_label.setText("B")
            self.company_label.hide()
            self.btn_toggle.setText(">")
            for lbl in self.section_labels:
                lbl.hide()
            for btn, full, short_badge in self.nav_buttons:
                btn.setText(short_badge)
                btn.setStyleSheet("text-align: center; padding: 6px 0; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        else:
            self.setFixedWidth(self.EXPANDED_WIDTH)
            self.brand_label.setText("BAHTA ERP")
            self.company_label.show()
            self.btn_toggle.setText("<")
            for lbl in self.section_labels:
                lbl.show()
            for btn, full, short_badge in self.nav_buttons:
                btn.setText(full)
                btn.setStyleSheet("")


class DashboardWidget(QWidget):
    """
    Executive ERP Dashboard View matching BAHTA Operations Control Stitch Design.
    Features:
    - Live Console Hero Header with shift cycle indicator
    - 4 High-impact KPI Metric Cards with progress indicator bars
    - Workforce Distribution breakdown table with headcount & ratio
    - Operational Shortcuts quick actions grid
    - Real-time Audit Trail & Security events log
    """

    def __init__(self, main_win=None, parent=None):
        super().__init__(parent)
        self.main_win = main_win
        self._init_ui()
        self.refresh_dashboard()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setObjectName("dashboardContainer")
        container.setStyleSheet("#dashboardContainer { background-color: transparent; }")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(2, 2, 8, 8)
        layout.setSpacing(16)

        # 1. Executive Operations Header Banner Card (Pixel-by-pixel match to reference design)
        banner = QFrame()
        banner.setObjectName("operationsBanner")
        banner.setStyleSheet(
            "QFrame#operationsBanner { "
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0A1931, stop:0.55 #0F244C, stop:1 #132D60); "
            "border: 1px solid #1E293B; border-radius: 10px; color: #FFFFFF; }"
        )
        b_layout = QHBoxLayout(banner)
        b_layout.setContentsMargins(20, 14, 20, 14)
        b_layout.setSpacing(16)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        # Top Badge row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)
        live_badge = QLabel("LIVE CONSOLE")
        live_badge.setStyleSheet(
            "background-color: #0E2A5C; color: #60A5FA; "
            "border: 1px solid #1D4ED8; border-radius: 4px; "
            "font-size: 10px; font-weight: 800; padding: 2px 7px; letter-spacing: 0.5px;"
        )
        badge_row.addWidget(live_badge)

        erp_label = QLabel("Brick Kiln Enterprise ERP")
        erp_label.setStyleSheet("font-size: 11.5px; color: #94A3B8; font-weight: 600;")
        badge_row.addWidget(erp_label)
        badge_row.addStretch()
        title_box.addLayout(badge_row)

        # Title row with crisp two-tone typography
        t = QLabel(
            '<span style="color: #FFFFFF; font-weight: 800; font-size: 19px; letter-spacing: -0.01em;">BAHTA MANAGEMENT SYSTEM</span> '
            '<span style="color: #64748B; font-weight: 400; font-size: 19px;">—</span> '
            '<span style="color: #93C5FD; font-weight: 500; font-size: 19px;">Operations Control</span>'
        )
        t.setTextFormat(Qt.RichText)
        title_box.addWidget(t)

        # Subtitle row with company name and vibrant active shift status
        sub = QLabel(
            '<span style="color: #94A3B8; font-size: 12px; font-weight: 500;">Bahta Kiln Operations Ltd.</span>  '
            '<span style="color: #64748B; font-size: 12px;">•</span>  '
            '<span style="color: #10B981; font-size: 12px; font-weight: 600;">Shift active: Primary Kiln Firing Cycle #4</span>'
        )
        sub.setTextFormat(Qt.RichText)
        title_box.addWidget(sub)

        b_layout.addLayout(title_box)
        b_layout.addStretch()

        self.btn_dash_refresh = QPushButton("↻  Refresh Metrics")
        self.btn_dash_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_dash_refresh.setFixedHeight(34)
        self.btn_dash_refresh.setStyleSheet(
            "QPushButton { background-color: rgba(255, 255, 255, 0.10); color: #FFFFFF; "
            "border: 1px solid rgba(255, 255, 255, 0.22); border-radius: 6px; padding: 0 16px; "
            "font-weight: 700; font-size: 12px; } "
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.20); border-color: rgba(255, 255, 255, 0.38); } "
            "QPushButton:pressed { background-color: rgba(255, 255, 255, 0.28); }"
        )
        self.btn_dash_refresh.clicked.connect(self.refresh_dashboard)
        b_layout.addWidget(self.btn_dash_refresh, alignment=Qt.AlignVCenter)

        layout.addWidget(banner)

        # 2. KPI Metric Cards Row (4 Columns matching Stitch layout)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(14)

        self.card_total = MetricCard(
            title="Total Workforce & Parties", initial_value="0",
            caption="All registered operational parties", accent_color="#2563EB",
            badge_text="+2 this month", badge_bg="#DCFCE7", badge_fg="#15803D", icon_symbol="👥"
        )
        self.card_active = MetricCard(
            title="Active Accounts", initial_value="0",
            caption="Available for work & billing", accent_color="#16A34A",
            badge_text="100% Active", badge_bg="#DCFCE7", badge_fg="#15803D", icon_symbol="✓"
        )
        self.card_omitted = MetricCard(
            title="Suspended Accounts", initial_value="0",
            caption="Omitted from daily records", accent_color="#64748B",
            badge_text="Zero Flags", badge_bg="#F1F5F9", badge_fg="#475569", icon_symbol="⊘"
        )
        self.card_users = MetricCard(
            title="Authorized System Users", initial_value="0",
            caption="Active RBAC profiles enrolled", accent_color="#0284C7",
            badge_text="Admin & Munshi", badge_bg="#E0F2FE", badge_fg="#0369A1", icon_symbol="🔒"
        )

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_active)
        kpi_layout.addWidget(self.card_omitted)
        kpi_layout.addWidget(self.card_users)

        layout.addLayout(kpi_layout)

        # 3. Two-Column Analytical Workspace
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left Column: Category Breakdown Table Card
        cat_card = QFrame()
        cat_card.setObjectName("distributionCard")
        cat_card.setProperty("class", "card-panel")
        cat_box = QVBoxLayout(cat_card)
        cat_box.setContentsMargins(16, 14, 16, 14)
        cat_box.setSpacing(10)

        # Header strip for Category Breakdown
        cat_header = QHBoxLayout()
        cat_header_text = QVBoxLayout()
        cat_header_text.setSpacing(2)
        self.cat_title = QLabel("Workforce Distribution by Category")
        self.cat_sub = QLabel("Categorized kiln labour and counterparty profiles")
        cat_header_text.addWidget(self.cat_title)
        cat_header_text.addWidget(self.cat_sub)
        cat_header.addLayout(cat_header_text)
        cat_header.addStretch()

        self.lbl_classes_badge = QLabel("5 Classes")
        cat_header.addWidget(self.lbl_classes_badge)
        cat_box.addLayout(cat_header)

        self.cat_table = QTableWidget()
        self.cat_table.setColumnCount(4)
        self.cat_table.setHorizontalHeaderLabels(["#", "Account Category", "Headcount", "Ratio"])
        self.cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.cat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cat_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cat_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.cat_table.setAlternatingRowColors(True)
        self.cat_table.setMinimumHeight(280)

        cat_box.addWidget(self.cat_table)
        content_layout.addWidget(cat_card, stretch=6)

        # Right Column: Shortcuts & Audit Trail
        right_box = QVBoxLayout()
        right_box.setSpacing(14)

        # Operational Shortcuts Card
        shortcuts_card = QFrame()
        shortcuts_card.setObjectName("shortcutsCard")
        shortcuts_card.setProperty("class", "card-panel")
        sc_layout = QVBoxLayout(shortcuts_card)
        sc_layout.setContentsMargins(16, 14, 16, 14)
        sc_layout.setSpacing(10)

        sc_title_box = QVBoxLayout()
        sc_title_box.setSpacing(2)
        self.sc_title = QLabel("Operational Shortcuts")
        self.sc_sub = QLabel("Quick action system launcher")
        sc_title_box.addWidget(self.sc_title)
        sc_title_box.addWidget(self.sc_sub)
        sc_layout.addLayout(sc_title_box)

        sc_btn_row = QHBoxLayout()
        sc_btn_row.setSpacing(8)

        btn_go_labour = QPushButton("Labour Directory")
        btn_go_labour.setProperty("class", "btn-primary")
        btn_go_labour.setMinimumHeight(34)
        btn_go_labour.setCursor(Qt.PointingHandCursor)
        if self.main_win:
            btn_go_labour.clicked.connect(self.main_win.open_labour_master_tab)
        sc_btn_row.addWidget(btn_go_labour)

        btn_go_cash = QPushButton("Cashbook Entry")
        btn_go_cash.setProperty("class", "btn-secondary")
        btn_go_cash.setMinimumHeight(34)
        btn_go_cash.setCursor(Qt.PointingHandCursor)
        if self.main_win:
            btn_go_cash.clicked.connect(self.main_win.open_money_transactions_tab)
        sc_btn_row.addWidget(btn_go_cash)

        if current_session.is_admin:
            btn_go_users = QPushButton("User Security")
            btn_go_users.setProperty("class", "btn-secondary")
            btn_go_users.setMinimumHeight(34)
            btn_go_users.setCursor(Qt.PointingHandCursor)
            if self.main_win:
                btn_go_users.clicked.connect(self.main_win.open_user_management_tab)
            sc_btn_row.addWidget(btn_go_users)

            btn_go_backup = QPushButton("Backup DB")
            btn_go_backup.setProperty("class", "btn-secondary")
            btn_go_backup.setMinimumHeight(34)
            btn_go_backup.setCursor(Qt.PointingHandCursor)
            if self.main_win:
                btn_go_backup.clicked.connect(self.main_win._on_backup_db)
            sc_btn_row.addWidget(btn_go_backup)

        sc_layout.addLayout(sc_btn_row)
        right_box.addWidget(shortcuts_card)

        # Recent System Audit Events Card
        audit_card = QFrame()
        audit_card.setObjectName("auditCard")
        audit_card.setProperty("class", "card-panel")
        audit_box = QVBoxLayout(audit_card)
        audit_box.setContentsMargins(16, 14, 16, 14)
        audit_box.setSpacing(10)

        aud_title_box = QVBoxLayout()
        aud_title_box.setSpacing(2)
        self.aud_title = QLabel("Recent System Audit Events")
        self.aud_sub = QLabel("Security logs and administrative actions")
        aud_title_box.addWidget(self.aud_title)
        aud_title_box.addWidget(self.aud_sub)
        audit_box.addLayout(aud_title_box)

        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(4)
        self.audit_table.setHorizontalHeaderLabels(["User", "Action", "Details", "Timestamp"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.audit_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.audit_table.setAlternatingRowColors(True)
        self.audit_table.setMinimumHeight(180)

        audit_box.addWidget(self.audit_table)
        right_box.addWidget(audit_card)

        content_layout.addLayout(right_box, stretch=7)
        layout.addLayout(content_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

        self._apply_theme()
        theme_mgr.theme_changed.connect(lambda _: self._apply_theme())

    def _apply_theme(self):
        is_dark = theme_mgr.is_dark_mode()
        title_col = "#FFFFFF" if is_dark else "#0F172A"
        sub_col = "#E2E8F0" if is_dark else "#64748B"
        badge_bg = "#1E293B" if is_dark else "#EFF6FF"
        badge_fg = "#93C5FD" if is_dark else "#1D4ED8"
        badge_border = "#334155" if is_dark else "#BFDBFE"

        for title_lbl in (getattr(self, "cat_title", None), getattr(self, "sc_title", None), getattr(self, "aud_title", None)):
            if title_lbl:
                title_lbl.setStyleSheet(f"font-size: 13.5px; font-weight: 700; color: {title_col}; border: none; background: transparent;")

        for sub_lbl in (getattr(self, "cat_sub", None), getattr(self, "sc_sub", None), getattr(self, "aud_sub", None)):
            if sub_lbl:
                sub_lbl.setStyleSheet(f"font-size: 11px; color: {sub_col}; border: none; background: transparent;")

        if hasattr(self, "lbl_classes_badge") and self.lbl_classes_badge:
            self.lbl_classes_badge.setStyleSheet(
                f"background-color: {badge_bg}; color: {badge_fg}; border: 1px solid {badge_border}; "
                f"border-radius: 4px; font-size: 10.5px; font-weight: 700; padding: 2px 8px;"
            )

    def refresh_dashboard(self):
        try:
            summary = LabourService.get_dashboard_summary()

            total_accs = summary.get("total_accounts", 0)
            active_accs = summary.get("active_accounts", 0)
            omitted_accs = summary.get("omitted_accounts", 0)

            # Update KPI Values
            self.card_total.set_value(str(total_accs), f"+{total_accs} registered")
            pct_active = f"{(active_accs/total_accs*100):.0f}% Active" if total_accs > 0 else "100% Active"
            self.card_active.set_value(str(active_accs), pct_active)
            flag_text = "Zero Flags" if omitted_accs == 0 else f"{omitted_accs} Flags"
            self.card_omitted.set_value(str(omitted_accs), flag_text)

            if current_session.is_admin:
                users = UserService.get_all_users()
                self.card_users.set_value(str(len(users)), "Admin & Munshi")
            else:
                self.card_users.set_value("N/A", "Restricted")

            # Update Category Breakdown Table (Batch UI rendering)
            breakdown = summary.get("category_breakdown", {})
            self.cat_table.setUpdatesEnabled(False)
            self.cat_table.blockSignals(True)
            self.cat_table.setRowCount(len(breakdown))
            if hasattr(self, "lbl_classes_badge"):
                self.lbl_classes_badge.setText(f"{len(breakdown)} Classes")

            for r, (cat_name, count) in enumerate(breakdown.items()):
                ratio = f"{(count / total_accs * 100):.1f}%" if total_accs > 0 else "0.0%"
                item_idx = QTableWidgetItem(str(r + 1))
                item_idx.setTextAlignment(Qt.AlignCenter)
                item_name = QTableWidgetItem(cat_name)
                item_count = QTableWidgetItem(str(count))
                item_count.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item_ratio = QTableWidgetItem(ratio)
                item_ratio.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                self.cat_table.setItem(r, 0, item_idx)
                self.cat_table.setItem(r, 1, item_name)
                self.cat_table.setItem(r, 2, item_count)
                self.cat_table.setItem(r, 3, item_ratio)
            self.cat_table.blockSignals(False)
            self.cat_table.setUpdatesEnabled(True)

            # Update Recent Audit Trail Table (Batch UI rendering)
            logs = summary.get("recent_logs", [])
            self.audit_table.setUpdatesEnabled(False)
            self.audit_table.blockSignals(True)
            self.audit_table.setRowCount(len(logs))
            for r, log in enumerate(logs):
                self.audit_table.setItem(r, 0, QTableWidgetItem(log.get("Username", "system")))
                self.audit_table.setItem(r, 1, QTableWidgetItem(log.get("Action", "")))
                self.audit_table.setItem(r, 2, QTableWidgetItem(log.get("Details", "")))
                self.audit_table.setItem(r, 3, QTableWidgetItem(log.get("Timestamp", "")))
            self.audit_table.blockSignals(False)
            self.audit_table.setUpdatesEnabled(True)
        except Exception as e:
            print(f"Dashboard refresh error: {e}")


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Enterprise ERP v{APP_VERSION}")
        self.setMinimumSize(960, 580)

        theme_mgr.theme_changed.connect(self._on_global_theme_changed)

        self._init_menu_bar()
        self._init_main_layout()
        self._init_status_bar()

        # Session activity timer
        self.activity_timer = QTimer(self)
        self.activity_timer.timeout.connect(self._check_session_timeout)
        self.activity_timer.start(30000)

        # Install event filter to track mouse/keyboard activity
        QApplication.instance().installEventFilter(self)

    def fit_screen_with_margins(self, margin: int = 5):
        """Fit window to the active screen with exact margins on all four sides (outer frame)."""
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            target_x = avail.x() + margin
            target_y = avail.y() + margin
            target_w = max(960, avail.width() - (2 * margin))
            target_h = max(580, avail.height() - (2 * margin))

            # Compute window frame overhead (titlebar + borders)
            frame_w = self.frameGeometry().width() - self.geometry().width()
            frame_h = self.frameGeometry().height() - self.geometry().height()
            if frame_h <= 0:
                frame_h = 32
            if frame_w <= 0:
                frame_w = 0

            self.move(target_x, target_y)
            self.resize(max(960, target_w - frame_w), max(580, target_h - frame_h))

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_positioned", False):
            self._positioned = True
            self.fit_screen_with_margins(5)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if not self.isMaximized() and not self.isMinimized():
                screen = self.screen() or QApplication.primaryScreen()
                if screen:
                    avail = screen.availableGeometry()
                    fg = self.frameGeometry()
                    if (fg.width() > avail.width() or 
                        fg.height() > avail.height() or 
                        fg.x() < avail.x() or 
                        fg.y() < avail.y()):
                        self.fit_screen_with_margins(5)
        super().changeEvent(event)

    def _on_global_theme_changed(self, _theme: str):
        if hasattr(self, "sidebar") and hasattr(self.sidebar, "update_theme_button"):
            self.sidebar.update_theme_button()
        pref = theme_mgr.get_theme_preference()
        if hasattr(self, "act_light"):
            self.act_light.setChecked(pref == "light")
            self.act_dark.setChecked(pref == "dark")
            self.act_system.setChecked(pref == "system")

    def eventFilter(self, obj, event):
        # Passive pointer movement must not keep an unattended financial session alive.
        if event.type() in (QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.Wheel):
            current_session.touch_activity()
        return super().eventFilter(obj, event)

    def _check_session_timeout(self):
        if current_session.is_authenticated and current_session.is_expired():
            self.activity_timer.stop()
            ToastNotification.show_warning(
                self,
                "Session Expired",
                "Your session has timed out due to 15 minutes of inactivity. Please log in again."
            )
            self._on_logout()

    def _init_menu_bar(self):
        menu_bar = self.menuBar()

        # File Menu
        menu_file = menu_bar.addMenu("&File")

        act_logout = QAction("Sign &Out", self)
        act_logout.triggered.connect(self._on_logout)
        menu_file.addAction(act_logout)

        act_exit = QAction("E&xit", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # Modules Menu
        menu_modules = menu_bar.addMenu("&Modules")

        act_labour = QAction("Labour Accounts", self)
        act_labour.triggered.connect(self.open_labour_master_tab)
        menu_modules.addAction(act_labour)

        act_product = QAction("Product Master", self)
        act_product.triggered.connect(self.open_product_master_tab)
        menu_modules.addAction(act_product)

        act_production = QAction("Daily Production Entry", self)
        act_production.triggered.connect(self.open_production_entry_tab)
        menu_modules.addAction(act_production)

        act_sales = QAction("Sales & Billing", self)
        act_sales.triggered.connect(self.open_sales_entry_tab)
        menu_modules.addAction(act_sales)

        act_rate = QAction("Labour Rates", self)
        act_rate.triggered.connect(self.open_labour_rate_tab)
        menu_modules.addAction(act_rate)

        act_cash = QAction("Cash Transactions (Amdan & Akrajat)", self)
        act_cash.triggered.connect(self.open_money_transactions_tab)
        menu_modules.addAction(act_cash)

        act_registers = QAction("Central Registers & Khatas", self)
        act_registers.triggered.connect(self.open_central_registers_tab)
        menu_modules.addAction(act_registers)

        # User Management Menu (Admin only)
        if current_session.is_admin:
            act_users = QAction("User Management", self)
            act_users.triggered.connect(self.open_user_management_tab)
            menu_modules.addAction(act_users)

        # Database Tools Menu (Admin only)
        if current_session.is_admin:
            menu_tools = menu_bar.addMenu("&Database Tools")

            act_backup = QAction("Backup Database...", self)
            act_backup.triggered.connect(self._on_backup_db)
            menu_tools.addAction(act_backup)

            act_restore = QAction("Restore Database...", self)
            act_restore.triggered.connect(self._on_restore_db)
            menu_tools.addAction(act_restore)

        # Settings & Theme Menu
        menu_settings = menu_bar.addMenu("&Settings")
        menu_theme = menu_settings.addMenu("&Theme")

        theme_group = QActionGroup(self)
        theme_group.setExclusive(True)

        current_pref = theme_mgr.get_theme_preference()

        self.act_light = QAction("&Light Mode", self)
        self.act_light.setCheckable(True)
        self.act_light.setChecked(current_pref == "light")
        self.act_light.triggered.connect(lambda: self._set_theme_pref("light"))
        theme_group.addAction(self.act_light)
        menu_theme.addAction(self.act_light)

        self.act_dark = QAction("&Dark Mode", self)
        self.act_dark.setCheckable(True)
        self.act_dark.setChecked(current_pref == "dark")
        self.act_dark.triggered.connect(lambda: self._set_theme_pref("dark"))
        theme_group.addAction(self.act_dark)
        menu_theme.addAction(self.act_dark)

        self.act_system = QAction("&Follow System", self)
        self.act_system.setCheckable(True)
        self.act_system.setChecked(current_pref == "system")
        self.act_system.triggered.connect(lambda: self._set_theme_pref("system"))
        theme_group.addAction(self.act_system)
        menu_theme.addAction(self.act_system)

    def _set_theme_pref(self, pref: str):
        theme_mgr.set_theme_preference(pref)
        if hasattr(self, "sidebar") and hasattr(self.sidebar, "update_theme_button"):
            self.sidebar.update_theme_button()

    def _init_main_layout(self):
        central_widget = QWidget()
        main_hbox = QHBoxLayout(central_widget)
        main_hbox.setContentsMargins(0, 0, 0, 0)
        main_hbox.setSpacing(0)

        # 1. Left Navigation Sidebar Panel
        self.sidebar = SidebarNav(main_win=self)
        main_hbox.addWidget(self.sidebar)

        # 2. Right Workspace (Tabbed Workspace)
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._on_close_tab)
        self._prev_tab_index = 0
        self._switching_tab = False
        self.tab_widget.currentChanged.connect(self._on_tab_current_changed)

        # Dashboard Tab
        self.dashboard_view = DashboardWidget(main_win=self)
        self.tab_widget.addTab(self.dashboard_view, "Dashboard")
        # Dashboard is permanent - remove the close button from tab 0
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        self.tab_widget.tabBar().setTabButton(0, QTabBar.ButtonPosition.LeftSide, None)

        # Heavy modules load only when selected. Creating the labour and user-management
        # screens eagerly made startup noticeably slow on larger databases.

        main_hbox.addWidget(self.tab_widget, stretch=1)
        self.setCentralWidget(central_widget)

    def _init_status_bar(self):
        self.status_bar = AppStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.refresh_user_status()

    def open_dashboard_tab(self):
        self.tab_widget.setCurrentIndex(0)
        self.dashboard_view.refresh_dashboard()
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(self.dashboard_view)

    def open_labour_master_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), LabourMasterView):
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = LabourMasterView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "Labour Accounts")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_user_management_tab(self):
        if not current_session.is_admin:
            ToastNotification.show_error(self, "Access Denied", "Only Administrator can access User Management.")
            return
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), UserManagementView):
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = UserManagementView()
        self.tab_widget.addTab(view, "User Security")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_audit_logs_tab(self):
        if not current_session.is_admin:
            ToastNotification.show_error(self, "Access Denied", "Only Administrator can access Audit Trail Logs.")
            return
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), AuditLogsView):
                self.tab_widget.widget(idx).refresh_logs()
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = AuditLogsView()
        self.tab_widget.addTab(view, "Audit Trail Logs")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_product_master_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), ProductMasterView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = ProductMasterView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "Product Master")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_production_entry_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), ProductionEntryView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = ProductionEntryView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "Daily Production")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_sales_entry_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), SalesEntryView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = SalesEntryView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "Sales & Invoicing")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_labour_rate_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), LabourRateView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = LabourRateView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "Labour Payment Rates")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_central_registers_tab(self, default_mode: str = None):
        for idx in range(self.tab_widget.count()):
            w = self.tab_widget.widget(idx)
            if isinstance(w, CentralRegistersView):
                if default_mode:
                    w.switch_mode(default_mode)
                else:
                    w.refresh_view()
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(w)
                return
        view = CentralRegistersView(default_mode=default_mode)
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "Central Registers")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def open_labour_ledger_tab(self):
        self.open_central_registers_tab(default_mode="LABOUR")

    def open_money_transactions_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), MoneyTransactionsView):
                self.tab_widget.widget(idx).refresh_all_data()
                self.tab_widget.setCurrentIndex(idx)
                if hasattr(self, "sidebar") and self.sidebar:
                    self.sidebar.set_active_by_view(self.tab_widget.widget(idx))
                return
        view = MoneyTransactionsView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "Cashbook Journal")
        self.tab_widget.setCurrentWidget(view)
        if hasattr(self, "sidebar") and self.sidebar:
            self.sidebar.set_active_by_view(view)

    def _on_tab_current_changed(self, new_index: int):
        if getattr(self, "_switching_tab", False):
            return

        if hasattr(self, "_prev_tab_index") and self._prev_tab_index != new_index and self._prev_tab_index < self.tab_widget.count():
            prev_widget = self.tab_widget.widget(self._prev_tab_index)
            if prev_widget and hasattr(prev_widget, "has_unsaved_changes") and prev_widget.has_unsaved_changes():
                if not prev_widget.prompt_unsaved_changes():
                    self._switching_tab = True
                    self.tab_widget.setCurrentIndex(self._prev_tab_index)
                    self._switching_tab = False
                    return

        self._prev_tab_index = new_index
        if new_index >= 0:
            current_tab = self.tab_widget.widget(new_index)
            if hasattr(self, "sidebar") and self.sidebar:
                self.sidebar.set_active_by_view(current_tab)

    def _on_close_tab(self, index: int):
        if index > 0:  # Don't close dashboard tab
            target_widget = self.tab_widget.widget(index)
            if target_widget and hasattr(target_widget, "has_unsaved_changes") and target_widget.has_unsaved_changes():
                if not target_widget.prompt_unsaved_changes():
                    return
            self.tab_widget.removeTab(index)

    def _on_backup_db(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Backup Folder Destination")
        if dir_path:
            success, msg = BackupService.backup_database(dir_path)
            if success:
                ToastNotification.show_success(self, "Backup Successful", msg)
            else:
                ToastNotification.show_error(self, "Backup Failed", msg)

    def _on_restore_db(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Database Backup File to Restore", filter="DB Backup (*.db *.bak)")
        if file_path:
            if ToastNotification.confirm(self, "Confirm Restore", "Restoring a database will overwrite current data. Continue?"):
                success, msg = BackupService.restore_database(file_path)
                if success:
                    ToastNotification.show_success(self, "Restore Successful", msg)
                else:
                    ToastNotification.show_error(self, "Restore Failed", msg)

    def _on_logout(self):
        AuthService.logout()
        self.close()

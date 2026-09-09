from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QMenuBar,
    QMenu, QToolBar, QLabel, QPushButton, QFileDialog, QFrame, QApplication,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QScrollArea, QStackedWidget
)
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtCore import Qt, QTimer, QEvent
from app.config import APP_NAME, APP_SUBTITLE, APP_VERSION, COMPANY_NAME
from app.security.session import current_session
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService
from app.services.labour_service import LabourService
from app.services.user_service import UserService
from app.ui.components.status_bar import AppStatusBar
from app.ui.components.toast import ToastNotification
from app.ui.styles import LIGHT_THEME_QSS
from app.ui.views.labour_master import LabourMasterView
from app.ui.views.user_management import UserManagementView
from app.ui.views.audit_logs import AuditLogsView
from app.ui.views.product_master import ProductMasterView
from app.ui.views.production_entry import ProductionEntryView
from app.ui.views.labour_rate import LabourRateView
from app.ui.views.sales_entry import SalesEntryView
from app.ui.views.money_transactions import MoneyTransactionsView


class SidebarNav(QFrame):
    """Left Navigation Sidebar Panel matching reference UI design."""

    def __init__(self, main_win, parent=None):
        super().__init__(parent)
        self.main_win = main_win
        self.setFixedWidth(230)
        self.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border-right: 1px solid #E2E8F0; }"
        )
        self._init_ui()

    def _init_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(12)

        # Brand Title Header
        brand_label = QLabel("BAHTA ERP")
        brand_label.setStyleSheet("font-size: 22px; font-weight: 900; color: #0284C7;")
        layout.addWidget(brand_label)

        # Section 1: MAIN MODULES
        lbl_sec1 = QLabel("MAIN MODULES")
        lbl_sec1.setStyleSheet("font-size: 11px; font-weight: 800; color: #94A3B8; margin-top: 10px;")
        layout.addWidget(lbl_sec1)

        self.btn_labour_nav = QPushButton("Labour / Party Master")
        self.btn_labour_nav.setMinimumHeight(38)
        self.btn_labour_nav.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 19px; text-align: left; padding-left: 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_labour_nav.clicked.connect(self.main_win.open_labour_master_tab)
        layout.addWidget(self.btn_labour_nav)

        self.btn_product_nav = QPushButton("Product Master")
        self.btn_product_nav.setMinimumHeight(38)
        self.btn_product_nav.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 19px; text-align: left; padding-left: 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_product_nav.clicked.connect(self.main_win.open_product_master_tab)
        layout.addWidget(self.btn_product_nav)

        self.btn_production_nav = QPushButton("Production Entry")
        self.btn_production_nav.setMinimumHeight(38)
        self.btn_production_nav.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 19px; text-align: left; padding-left: 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_production_nav.clicked.connect(self.main_win.open_production_entry_tab)
        layout.addWidget(self.btn_production_nav)

        self.btn_sales_nav = QPushButton("🧾 Sales Entry & Billing")
        self.btn_sales_nav.setMinimumHeight(38)
        self.btn_sales_nav.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 19px; text-align: left; padding-left: 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_sales_nav.clicked.connect(self.main_win.open_sales_entry_tab)
        layout.addWidget(self.btn_sales_nav)

        self.btn_rate_nav = QPushButton("Labour Rates")
        self.btn_rate_nav.setMinimumHeight(38)
        self.btn_rate_nav.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 19px; text-align: left; padding-left: 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_rate_nav.clicked.connect(self.main_win.open_labour_rate_tab)
        layout.addWidget(self.btn_rate_nav)

        self.btn_ledger_nav = QPushButton("📑 Customer & Labour Khata")
        self.btn_ledger_nav.setMinimumHeight(38)
        self.btn_ledger_nav.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 19px; text-align: left; padding-left: 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_ledger_nav.clicked.connect(self.main_win.open_labour_ledger_tab)
        layout.addWidget(self.btn_ledger_nav)

        self.btn_cash_nav = QPushButton("💰 Cash & Amdan / Akrajat")
        self.btn_cash_nav.setMinimumHeight(38)
        self.btn_cash_nav.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 19px; text-align: left; padding-left: 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_cash_nav.clicked.connect(self.main_win.open_money_transactions_tab)
        layout.addWidget(self.btn_cash_nav)

        # Section 3: SECURITY & AUDIT
        lbl_sec2 = QLabel("SECURITY & AUDIT")
        lbl_sec2.setStyleSheet("font-size: 11px; font-weight: 800; color: #94A3B8; margin-top: 14px;")
        layout.addWidget(lbl_sec2)

        if current_session.is_admin:
            self.btn_user_nav = QPushButton("User Security Mgmt")
            self.btn_user_nav.setMinimumHeight(36)
            self.btn_user_nav.setStyleSheet(
                "QPushButton { background-color: #F8FAFC; color: #334155; font-weight: 600; font-size: 12px; border-radius: 18px; text-align: left; padding-left: 16px; border: 1px solid #CBD5E1; } "
                "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }"
            )
            self.btn_user_nav.clicked.connect(self.main_win.open_user_management_tab)
            layout.addWidget(self.btn_user_nav)

        self.btn_audit_nav = QPushButton("👁️ Audit Trail Logs")
        self.btn_audit_nav.setMinimumHeight(36)
        self.btn_audit_nav.setStyleSheet(
            "QPushButton { background-color: #F8FAFC; color: #334155; font-weight: 600; font-size: 12px; border-radius: 18px; text-align: left; padding-left: 16px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }"
        )
        self.btn_audit_nav.clicked.connect(self.main_win.open_audit_logs_tab)
        layout.addWidget(self.btn_audit_nav)

        layout.addStretch()

        # Bottom Section: Logout Session Button
        self.btn_logout = QPushButton("❌ Logout Session")
        self.btn_logout.setMinimumHeight(38)
        self.btn_logout.setStyleSheet(
            "QPushButton { background-color: #E11D48; color: #FFFFFF; font-weight: 700; font-size: 13px; border-radius: 8px; border: none; } "
            "QPushButton:hover { background-color: #BE123C; }"
        )
        self.btn_logout.clicked.connect(self.main_win._on_logout)
        layout.addWidget(self.btn_logout)

        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)


class DashboardWidget(QWidget):
    """
    Executive ERP Dashboard View.
    Features:
    - Welcome Banner & Live Status
    - Real-time KPI Metric Cards (Total Accounts, Active Accounts, Omitted Accounts, System Users)
    - Account Category Distribution Breakdown Table
    - Recent System Audit Trail & Security Events Table
    - Quick Action System Launcher
    """

    def __init__(self, main_win=None, parent=None):
        super().__init__(parent)
        self.main_win = main_win
        self._init_ui()
        self.refresh_dashboard()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 12, 4)
        layout.setSpacing(14)

        # 1. Executive Welcome Banner
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background-color: #1E3A8A; "
            "border-radius: 10px; padding: 18px 24px; }"
        )
        b_layout = QHBoxLayout(banner)

        title_box = QVBoxLayout()
        t = QLabel(f"🔥 {APP_NAME} - Operations Dashboard")
        t.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        sub = QLabel(f"{APP_SUBTITLE}  •  {COMPANY_NAME}")
        sub.setStyleSheet("font-size: 13px; color: #93C5FD; font-weight: 600;")
        title_box.addWidget(t)
        title_box.addWidget(sub)

        b_layout.addLayout(title_box)
        b_layout.addStretch()

        self.btn_dash_refresh = QPushButton("🔄 Refresh Analytics")
        self.btn_dash_refresh.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: #FFFFFF; border: 1px solid #60A5FA; border-radius: 6px; padding: 6px 14px; font-weight: 700; } "
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_dash_refresh.clicked.connect(self.refresh_dashboard)
        b_layout.addWidget(self.btn_dash_refresh)

        layout.addWidget(banner)

        # 2. KPI Metric Cards Row (4 Cards)
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_total = self._create_kpi_card("📊 Total Accounts", "0", "#2563EB", "#EFF6FF")
        self.card_active = self._create_kpi_card("🟢 Active Accounts", "0", "#16A34A", "#F0FDF4")
        self.card_omitted = self._create_kpi_card("🚫 Omitted Accounts", "0", "#DC2626", "#FEF2F2")
        self.card_users = self._create_kpi_card("👤 System Users", "0", "#D97706", "#FFFBEB")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_active)
        kpi_layout.addWidget(self.card_omitted)
        kpi_layout.addWidget(self.card_users)

        layout.addLayout(kpi_layout)

        # 3. Two-Column Analytical Workspace
        content_layout = QHBoxLayout()
        content_layout.setSpacing(14)

        # Left Column: Category Breakdown Table
        cat_group = QGroupBox("📁 Account Categories Breakdown")
        cat_box = QVBoxLayout(cat_group)

        self.cat_table = QTableWidget()
        self.cat_table.setColumnCount(2)
        self.cat_table.setHorizontalHeaderLabels(["Account Category", "Registered Accounts"])
        self.cat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cat_table.setAlternatingRowColors(True)
        self.cat_table.setMinimumHeight(240)

        cat_box.addWidget(self.cat_table)
        content_layout.addWidget(cat_group, stretch=1)

        # Right Column: Quick Action Launcher & System Audit Logs
        right_box = QVBoxLayout()

        # Quick Actions Box
        qa_group = QGroupBox("⚡ Quick Action Shortcuts")
        qa_layout = QHBoxLayout(qa_group)
        qa_layout.setSpacing(8)

        btn_go_labour = QPushButton("🧱 Labour Master")
        btn_go_labour.setProperty("class", "btn-primary")
        btn_go_labour.setMinimumHeight(36)
        if self.main_win:
            btn_go_labour.clicked.connect(self.main_win.open_labour_master_tab)
        qa_layout.addWidget(btn_go_labour)

        btn_go_cash = QPushButton("💰 Amdan & Akrajat")
        btn_go_cash.setMinimumHeight(36)
        if self.main_win:
            btn_go_cash.clicked.connect(self.main_win.open_money_transactions_tab)
        qa_layout.addWidget(btn_go_cash)

        if current_session.is_admin:
            btn_go_users = QPushButton("👤 User Management")
            btn_go_users.setMinimumHeight(36)
            if self.main_win:
                btn_go_users.clicked.connect(self.main_win.open_user_management_tab)
            qa_layout.addWidget(btn_go_users)

            btn_go_backup = QPushButton("💾 Backup Database")
            btn_go_backup.setMinimumHeight(36)
            if self.main_win:
                btn_go_backup.clicked.connect(self.main_win._on_backup_db)
            qa_layout.addWidget(btn_go_backup)

        right_box.addWidget(qa_group)

        # Audit Logs Box
        audit_group = QGroupBox("📜 Recent Audit Trail & Activity Log")
        audit_box = QVBoxLayout(audit_group)

        self.audit_table = QTableWidget()
        self.audit_table.setColumnCount(4)
        self.audit_table.setHorizontalHeaderLabels(["User", "Action", "Details", "Time"])
        self.audit_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.audit_table.setAlternatingRowColors(True)
        self.audit_table.setMinimumHeight(200)

        audit_box.addWidget(self.audit_table)
        right_box.addWidget(audit_group)

        content_layout.addLayout(right_box, stretch=1)
        layout.addLayout(content_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_kpi_card(self, title: str, val: str, accent_color: str, bg_color: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background-color: {bg_color}; border: 1px solid #CBD5E1; border-left: 4px solid {accent_color}; border-radius: 8px; padding: 14px 18px; }}"
        )
        l = QVBoxLayout(card)
        l.setSpacing(4)

        t = QLabel(title)
        t.setStyleSheet("font-size: 13px; font-weight: 600; color: #475569;")

        v = QLabel(val)
        v.setObjectName("val_label")
        v.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {accent_color};")

        l.addWidget(t)
        l.addWidget(v)
        return card

    def refresh_dashboard(self):
        try:
            summary = LabourService.get_dashboard_summary()

            # Update KPI Values
            self.card_total.findChild(QLabel, "val_label").setText(str(summary.get("total_accounts", 0)))
            self.card_active.findChild(QLabel, "val_label").setText(str(summary.get("active_accounts", 0)))
            self.card_omitted.findChild(QLabel, "val_label").setText(str(summary.get("omitted_accounts", 0)))

            if current_session.is_admin:
                users = UserService.get_all_users()
                self.card_users.findChild(QLabel, "val_label").setText(str(len(users)))
            else:
                self.card_users.findChild(QLabel, "val_label").setText("N/A")

            # Update Category Breakdown Table
            breakdown = summary.get("category_breakdown", {})
            self.cat_table.setRowCount(len(breakdown))
            for r, (cat_name, count) in enumerate(breakdown.items()):
                self.cat_table.setItem(r, 0, QTableWidgetItem(cat_name))
                self.cat_table.setItem(r, 1, QTableWidgetItem(str(count)))

            # Update Recent Audit Trail Table
            logs = summary.get("recent_logs", [])
            self.audit_table.setRowCount(len(logs))
            for r, log in enumerate(logs):
                self.audit_table.setItem(r, 0, QTableWidgetItem(log["Username"]))
                self.audit_table.setItem(r, 1, QTableWidgetItem(log["Action"]))
                self.audit_table.setItem(r, 2, QTableWidgetItem(log["Details"]))
                self.audit_table.setItem(r, 3, QTableWidgetItem(log["Timestamp"]))
        except Exception as e:
            print(f"Dashboard refresh error: {e}")


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Enterprise ERP v{APP_VERSION}")
        self.resize(1280, 800)
        self.setStyleSheet(LIGHT_THEME_QSS)

        self._init_menu_bar()
        self._init_main_layout()
        self._init_status_bar()

        # Session activity timer
        self.activity_timer = QTimer(self)
        self.activity_timer.timeout.connect(self._check_session_timeout)
        self.activity_timer.start(30000)

        # Install event filter to track mouse/keyboard activity
        QApplication.instance().installEventFilter(self)

        # Automatically launch maximized
        self.showMaximized()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.MouseMove):
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

        act_logout = QAction("🚪 Log &Out", self)
        act_logout.triggered.connect(self._on_logout)
        menu_file.addAction(act_logout)

        act_exit = QAction("❌ E&xit", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # Modules Menu
        menu_modules = menu_bar.addMenu("&Modules")

        act_labour = QAction("🧱 Labour & Account Master", self)
        act_labour.triggered.connect(self.open_labour_master_tab)
        menu_modules.addAction(act_labour)

        act_product = QAction("📦 Product Master", self)
        act_product.triggered.connect(self.open_product_master_tab)
        menu_modules.addAction(act_product)

        act_cash = QAction("💰 Cash Transactions (Amdan & Akrajat)", self)
        act_cash.triggered.connect(self.open_money_transactions_tab)
        menu_modules.addAction(act_cash)

        # User Management Menu (Admin only)
        if current_session.is_admin:
            act_users = QAction("👤 User Management", self)
            act_users.triggered.connect(self.open_user_management_tab)
            menu_modules.addAction(act_users)

        # Database Tools Menu (Admin only)
        if current_session.is_admin:
            menu_tools = menu_bar.addMenu("&Database Tools")

            act_backup = QAction("💾 Backup Database", self)
            act_backup.triggered.connect(self._on_backup_db)
            menu_tools.addAction(act_backup)

            act_restore = QAction("📂 Restore Database", self)
            act_restore.triggered.connect(self._on_restore_db)
            menu_tools.addAction(act_restore)

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
        self.tab_widget.addTab(self.dashboard_view, "🏠 Dashboard")

        # Labour Master Tab
        self.labour_view = LabourMasterView()
        self.labour_view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(self.labour_view, "🧱 Labour & Account Master")

        # User Management Tab (if Admin)
        if current_session.is_admin:
            self.user_view = UserManagementView()
            self.tab_widget.addTab(self.user_view, "👤 User Management")

        main_hbox.addWidget(self.tab_widget, stretch=1)
        self.setCentralWidget(central_widget)

    def _init_status_bar(self):
        self.status_bar = AppStatusBar(self)
        self.setStatusBar(self.status_bar)
        self.status_bar.refresh_user_status()

    def open_dashboard_tab(self):
        self.tab_widget.setCurrentIndex(0)
        self.dashboard_view.refresh_dashboard()

    def open_labour_master_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), LabourMasterView):
                self.tab_widget.setCurrentIndex(idx)
                return
        view = LabourMasterView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "🧱 Labour & Account Master")
        self.tab_widget.setCurrentWidget(view)

    def open_user_management_tab(self):
        if not current_session.is_admin:
            ToastNotification.show_error(self, "Access Denied", "Only Administrator can access User Management.")
            return
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), UserManagementView):
                self.tab_widget.setCurrentIndex(idx)
                return
        view = UserManagementView()
        self.tab_widget.addTab(view, "👤 User Management")
        self.tab_widget.setCurrentWidget(view)

    def open_audit_logs_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), AuditLogsView):
                self.tab_widget.widget(idx).refresh_logs()
                self.tab_widget.setCurrentIndex(idx)
                return
        view = AuditLogsView()
        self.tab_widget.addTab(view, "🛡️ Audit Trail Logs")
        self.tab_widget.setCurrentWidget(view)

    def open_product_master_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), ProductMasterView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                return
        view = ProductMasterView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "📦 Dynamic Product Master")
        self.tab_widget.setCurrentWidget(view)

    def open_production_entry_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), ProductionEntryView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                return
        view = ProductionEntryView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "🛠️ Daily Production Entry")
        self.tab_widget.setCurrentWidget(view)

    def open_sales_entry_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), SalesEntryView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                return
        view = SalesEntryView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "🧾 Sales Entry & Billing")
        self.tab_widget.setCurrentWidget(view)

    def open_labour_rate_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), LabourRateView):
                self.tab_widget.widget(idx).refresh_data()
                self.tab_widget.setCurrentIndex(idx)
                return
        view = LabourRateView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "💰 Labour Payment Rates")
        self.tab_widget.setCurrentWidget(view)

    def open_labour_ledger_tab(self):
        from app.ui.views.labour_ledger import LabourLedgerView
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), LabourLedgerView):
                self.tab_widget.widget(idx).refresh_view()
                self.tab_widget.setCurrentIndex(idx)
                return
        view = LabourLedgerView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "📑 Customer & Labour Khata")
        self.tab_widget.setCurrentWidget(view)

    def open_money_transactions_tab(self):
        for idx in range(self.tab_widget.count()):
            if isinstance(self.tab_widget.widget(idx), MoneyTransactionsView):
                self.tab_widget.widget(idx).refresh_all_data()
                self.tab_widget.setCurrentIndex(idx)
                return
        view = MoneyTransactionsView()
        view.close_requested.connect(self.open_dashboard_tab)
        self.tab_widget.addTab(view, "💰 Cash & Amdan / Akrajat")
        self.tab_widget.setCurrentWidget(view)

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
            if hasattr(current_tab, "refresh_view"):
                current_tab.refresh_view()
            elif hasattr(current_tab, "refresh_all_data"):
                current_tab.refresh_all_data()

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

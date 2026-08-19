from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from app.services.audit_service import AuditService
from app.ui.components.toast import ToastNotification


class AuditLogsView(QWidget):
    """
    Dedicated Read-Only Audit Trail Logs & Security History View.
    Strictly read-only and non-editable.
    """

    close_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_logs()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. HEADER TITLE
        header_box = QHBoxLayout()
        title_box = QVBoxLayout()

        title = QLabel("🛡️ Audit Trail Logs & System History")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")

        sub = QLabel("Read-Only immutable security ledger, access history, and data modification audit trail.")
        sub.setStyleSheet("font-size: 12px; color: #64748B;")

        title_box.addWidget(title)
        title_box.addWidget(sub)
        header_box.addLayout(title_box)
        header_box.addStretch()

        # Action Buttons in Header
        self.btn_refresh = QPushButton("🔄 Refresh Logs")
        self.btn_refresh.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; border-radius: 6px; padding: 6px 14px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_refresh.clicked.connect(self.refresh_logs)

        self.btn_export = QPushButton("📊 Export Excel")
        self.btn_export.setStyleSheet(
            "QPushButton { background-color: #059669; color: #FFFFFF; font-weight: 700; border-radius: 6px; padding: 6px 14px; border: none; } "
            "QPushButton:hover { background-color: #047857; }"
        )
        self.btn_export.clicked.connect(self._on_export_excel)

        header_box.addWidget(self.btn_refresh)
        header_box.addWidget(self.btn_export)
        main_layout.addLayout(header_box)

        # 2. FILTER CONTROLS CARD
        filter_card = QFrame()
        filter_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 10px; }"
        )
        f_layout = QHBoxLayout(filter_card)
        f_layout.setSpacing(12)

        lbl_cat = QLabel("Action Filter:")
        lbl_cat.setStyleSheet("font-weight: 700; color: #334155; font-size: 12px; border: none; background: transparent;")

        self.cmb_action_filter = QComboBox()
        self.cmb_action_filter.setMinimumHeight(30)
        self.cmb_action_filter.addItems([
            "All Security Actions",
            "LOGIN",
            "LOGOUT",
            "LABOUR_ACCOUNT",
            "USER_MGMT",
            "BACKUP"
        ])
        self.cmb_action_filter.currentIndexChanged.connect(self._on_filter_changed)

        self.txt_search = QLineEdit()
        self.txt_search.setMinimumHeight(30)
        self.txt_search.setPlaceholderText("Search logs by Username, Action, or Details...")
        self.txt_search.textChanged.connect(self._on_search_changed)

        f_layout.addWidget(lbl_cat)
        f_layout.addWidget(self.cmb_action_filter, stretch=1)
        f_layout.addWidget(self.txt_search, stretch=2)

        main_layout.addWidget(filter_card)

        # 3. READ-ONLY DATA TABLE CARD
        table_card = QFrame()
        table_card.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 8px; }"
        )
        t_layout = QVBoxLayout(table_card)

        self.table = QTableWidget()
        headers = ["Log ID", "Timestamp", "Username", "Security Action", "Event Details", "IP / Machine"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # STRICT READ-ONLY ENFORCEMENT: No edit triggers allowed!
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)

        # Column sizing
        self.table.horizontalHeader().setMinimumHeight(54)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setMinimumSectionSize(90)

        self.table.setColumnWidth(0, 80)   # Log ID
        self.table.setColumnWidth(1, 160)  # Timestamp
        self.table.setColumnWidth(2, 130)  # Username
        self.table.setColumnWidth(3, 180)  # Security Action
        self.table.setColumnWidth(4, 380)  # Event Details
        self.table.setColumnWidth(5, 120)  # IP Address

        t_layout.addWidget(self.table)
        main_layout.addWidget(table_card, stretch=1)

    def refresh_logs(self):
        query_str = self.txt_search.text().strip()

        raw_filter = self.cmb_action_filter.currentText()
        if raw_filter == "All Security Actions":
            action_filter = "ALL"
        else:
            action_filter = raw_filter

        logs = AuditService.get_audit_logs(query_str, action_filter)

        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            item_id = QTableWidgetItem(str(log["LogID"]))
            item_id.setTextAlignment(Qt.AlignCenter)

            item_time = QTableWidgetItem(log["Timestamp"])
            item_user = QTableWidgetItem(log["Username"])
            item_user.setFont(QFont("Segoe UI", 9, QFont.Bold))

            action_str = log["Action"]
            item_act = QTableWidgetItem(action_str)
            item_act.setFont(QFont("Segoe UI", 9, QFont.Bold))

            # Color-code action badges
            if "LOGIN_SUCCESS" in action_str or "CREATE" in action_str:
                item_act.setForeground(QColor("#16A34A"))  # Green
            elif "LOGIN_FAILED" in action_str or "DELETE" in action_str or "REVOKE" in action_str:
                item_act.setForeground(QColor("#DC2626"))  # Red
            elif "OMIT" in action_str or "LOCK" in action_str:
                item_act.setForeground(QColor("#D97706"))  # Amber
            elif "EDIT" in action_str or "UPDATE" in action_str:
                item_act.setForeground(QColor("#2563EB"))  # Blue
            else:
                item_act.setForeground(QColor("#475569"))  # Slate

            item_det = QTableWidgetItem(log["Details"])
            item_ip = QTableWidgetItem(log["IPAddress"])

            self.table.setItem(row, 0, item_id)
            self.table.setItem(row, 1, item_time)
            self.table.setItem(row, 2, item_user)
            self.table.setItem(row, 3, item_act)
            self.table.setItem(row, 4, item_det)
            self.table.setItem(row, 5, item_ip)

    def _on_search_changed(self):
        self.refresh_logs()

    def _on_filter_changed(self):
        self.refresh_logs()

    def _on_export_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Audit Logs", "Audit_Trail_Report.xlsx", "Excel Files (*.xlsx *.csv)"
        )
        if not file_path:
            return

        try:
            logs = AuditService.get_audit_logs(limit=1000)

            if file_path.endswith(".xlsx"):
                import openpyxl
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Audit Logs"

                headers = ["Log ID", "Timestamp", "Username", "Security Action", "Event Details", "IP Address"]
                ws.append(headers)

                for log in logs:
                    ws.append([
                        log["LogID"], log["Timestamp"], log["Username"],
                        log["Action"], log["Details"], log["IPAddress"]
                    ])

                wb.save(file_path)
            else:
                import csv
                with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Log ID", "Timestamp", "Username", "Security Action", "Event Details", "IP Address"])
                    for log in logs:
                        writer.writerow([
                            log["LogID"], log["Timestamp"], log["Username"],
                            log["Action"], log["Details"], log["IPAddress"]
                        ])

            ToastNotification.show_success(self, "Export Complete", f"Successfully exported audit logs to:\n{file_path}")
        except Exception as e:
            ToastNotification.show_error(self, "Export Failed", f"Failed to export audit logs: {e}")

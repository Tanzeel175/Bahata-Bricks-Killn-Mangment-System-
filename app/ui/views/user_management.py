from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QGroupBox, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt
from app.services.user_service import UserService
from app.ui.components.toast import ToastNotification
from app.ui.components.formatted_inputs import PhoneLineEdit


class UserDialog(QDialog):
    """Dialog for creating or editing system users."""

    def __init__(self, user_data: dict = None, parent=None):
        super().__init__(parent)
        self.is_edit = user_data is not None
        self.user_data = user_data or {}
        self.setWindowTitle("Edit User" if self.is_edit else "Create New User")
        self.setFixedWidth(440)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        form_group = QGroupBox("User Details")
        form = QFormLayout(form_group)
        form.setSpacing(10)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("e.g. munshi_ali")
        if self.is_edit:
            self.username_edit.setText(self.user_data.get("Username", ""))
            self.username_edit.setDisabled(True)

        self.fullname_edit = QLineEdit()
        self.fullname_edit.setPlaceholderText("e.g. Ali Raza")
        if self.is_edit:
            self.fullname_edit.setText(self.user_data.get("FullName", ""))

        self.role_combo = QComboBox()
        self.role_combo.addItems(["Administrator", "Munshi"])
        if self.is_edit:
            idx = self.role_combo.findText(self.user_data.get("Role", "Munshi"))
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("user@example.com")
        if self.is_edit:
            self.email_edit.setText(self.user_data.get("Email", ""))

        self.mobile_edit = PhoneLineEdit()
        if self.is_edit:
            self.mobile_edit.setText(self.user_data.get("Mobile", ""))

        self.active_cb = QCheckBox("Account Active")
        self.active_cb.setChecked(self.user_data.get("IsActive", True) if self.is_edit else True)

        form.addRow("Username *:", self.username_edit)
        form.addRow("Full Name *:", self.fullname_edit)
        form.addRow("Role *:", self.role_combo)
        form.addRow("Email:", self.email_edit)
        form.addRow("Mobile:", self.mobile_edit)
        form.addRow("Status:", self.active_cb)

        # Password fields (Required for New, Optional for Edit)
        if not self.is_edit:
            self.pw_edit = QLineEdit()
            self.pw_edit.setEchoMode(QLineEdit.Password)
            self.pw_edit.setPlaceholderText("Min 8 chars (A-Z, a-z, 0-9, special)")

            self.confirm_pw_edit = QLineEdit()
            self.confirm_pw_edit.setEchoMode(QLineEdit.Password)
            self.confirm_pw_edit.setPlaceholderText("Confirm password")

            form.addRow("Password *:", self.pw_edit)
            form.addRow("Confirm Password *:", self.confirm_pw_edit)

        layout.addWidget(form_group)

        # Dialog Buttons
        bbox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self._on_save)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _on_save(self):
        username = self.username_edit.text().strip()
        fullname = self.fullname_edit.text().strip()
        role = self.role_combo.currentText()
        email = self.email_edit.text().strip()
        mobile = self.mobile_edit.text().strip()
        is_active = self.active_cb.isChecked()

        if not username:
            ToastNotification.show_warning(self, "Validation Error", "Username is required.")
            return
        if not fullname:
            ToastNotification.show_warning(self, "Validation Error", "Full Name is required.")
            return

        if not self.is_edit:
            pw = self.pw_edit.text()
            cpw = self.confirm_pw_edit.text()
            if not pw:
                ToastNotification.show_warning(self, "Validation Error", "Password is required.")
                return
            if pw != cpw:
                ToastNotification.show_warning(self, "Validation Error", "Passwords do not match.")
                return

            data = {
                "Username": username,
                "FullName": fullname,
                "Password": pw,
                "Role": role,
                "Email": email,
                "Mobile": mobile,
                "IsActive": is_active
            }
            success, msg = UserService.create_user(data)
        else:
            data = {
                "FullName": fullname,
                "Role": role,
                "Email": email,
                "Mobile": mobile,
                "IsActive": is_active
            }
            success, msg = UserService.update_user(self.user_data["UserID"], data)

        if success:
            ToastNotification.show_success(self, "Success", msg)
            self.accept()
        else:
            ToastNotification.show_error(self, "Error", msg)


class ResetPasswordDialog(QDialog):
    """Dialog to reset user password."""

    def __init__(self, username: str, user_id: int, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.setWindowTitle(f"Reset Password - {username}")
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.pw_edit = QLineEdit()
        self.pw_edit.setEchoMode(QLineEdit.Password)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.Password)

        form.addRow("New Password *:", self.pw_edit)
        form.addRow("Confirm Password *:", self.confirm_edit)
        layout.addLayout(form)

        bbox = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self._on_save)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _on_save(self):
        pw = self.pw_edit.text()
        cpw = self.confirm_edit.text()
        if pw != cpw:
            ToastNotification.show_warning(self, "Validation Error", "Passwords do not match.")
            return

        success, msg = UserService.reset_password(self.user_id, pw)
        if success:
            ToastNotification.show_success(self, "Success", msg)
            self.accept()
        else:
            ToastNotification.show_error(self, "Error", msg)


class LoginHistoryDialog(QDialog):
    """Dialog displaying user authentication audit logs."""

    def __init__(self, username: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login & Audit History")
        self.resize(720, 420)

        layout = QVBoxLayout(self)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Log ID", "Username", "Action", "Details", "Timestamp"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        self._load_data(username)

    def _load_data(self, username: str):
        logs = UserService.get_login_history(username if username else None)
        self.table.setRowCount(len(logs))

        for row, log in enumerate(logs):
            self.table.setItem(row, 0, QTableWidgetItem(str(log["LogID"])))
            self.table.setItem(row, 1, QTableWidgetItem(log["Username"]))
            self.table.setItem(row, 2, QTableWidgetItem(log["Action"]))
            self.table.setItem(row, 3, QTableWidgetItem(log["Details"]))
            self.table.setItem(row, 4, QTableWidgetItem(log["Timestamp"]))


class UserManagementView(QWidget):
    """User Management Workspace View (Administrator Only)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.load_users()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header Title
        header_layout = QHBoxLayout()
        title = QLabel("User Account Management")
        title.setProperty("class", "heading-primary")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0F172A;")

        subtitle = QLabel("Manage system users, roles, password resets, and account locks")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")

        head_v = QVBoxLayout()
        head_v.addWidget(title)
        head_v.addWidget(subtitle)
        header_layout.addLayout(head_v)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Action Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.btn_new = QPushButton("➕ Create User")
        self.btn_new.setProperty("class", "btn-primary")
        self.btn_new.clicked.connect(self._on_new_user)

        self.btn_edit = QPushButton("✏️ Edit User")
        self.btn_edit.clicked.connect(self._on_edit_user)

        self.btn_lock = QPushButton("🔒 Lock / Unlock")
        self.btn_lock.clicked.connect(self._on_toggle_lock)

        self.btn_reset_pw = QPushButton("🔑 Reset Password")
        self.btn_reset_pw.clicked.connect(self._on_reset_password)

        self.btn_history = QPushButton("📜 View Login History")
        self.btn_history.clicked.connect(self._on_view_history)

        self.btn_delete = QPushButton("🗑️ Delete User")
        self.btn_delete.setProperty("class", "btn-danger")
        self.btn_delete.clicked.connect(self._on_delete_user)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.load_users)

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_lock)
        toolbar.addWidget(self.btn_reset_pw)
        toolbar.addWidget(self.btn_history)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        # Data Table
        self.table = QTableWidget()
        headers = [
            "ID", "Username", "Full Name", "Role", "Email", "Mobile",
            "Active", "Locked", "Failed Attempts", "Last Login"
        ]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def load_users(self):
        try:
            users = UserService.get_all_users()
            self.table.setRowCount(len(users))

            for row, u in enumerate(users):
                self.table.setItem(row, 0, QTableWidgetItem(str(u["UserID"])))
                self.table.setItem(row, 1, QTableWidgetItem(u["Username"]))
                self.table.setItem(row, 2, QTableWidgetItem(u["FullName"]))
                self.table.setItem(row, 3, QTableWidgetItem(u["Role"]))
                self.table.setItem(row, 4, QTableWidgetItem(u["Email"]))
                self.table.setItem(row, 5, QTableWidgetItem(u["Mobile"]))

                active_str = "Active" if u["IsActive"] else "Disabled"
                active_item = QTableWidgetItem(active_str)
                active_item.setForeground(Qt.green if u["IsActive"] else Qt.red)
                self.table.setItem(row, 6, active_item)

                locked_str = "Locked" if u["IsLocked"] else "Unlocked"
                locked_item = QTableWidgetItem(locked_str)
                locked_item.setForeground(Qt.red if u["IsLocked"] else Qt.darkGreen)
                self.table.setItem(row, 7, locked_item)

                self.table.setItem(row, 8, QTableWidgetItem(str(u["FailedAttempts"])))
                self.table.setItem(row, 9, QTableWidgetItem(u["LastLogin"]))

                # Attach raw dict to item data
                self.table.item(row, 0).setData(Qt.UserRole, u)

        except Exception as e:
            ToastNotification.show_error(self, "Error", f"Failed to load users: {e}")

    def _get_selected_user(self) -> dict:
        row = self.table.currentRow()
        if row < 0:
            ToastNotification.show_warning(self, "Selection Required", "Please select a user from the table.")
            return None
        return self.table.item(row, 0).data(Qt.UserRole)

    def _on_new_user(self):
        dlg = UserDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.load_users()

    def _on_edit_user(self):
        u = self._get_selected_user()
        if u:
            dlg = UserDialog(user_data=u, parent=self)
            if dlg.exec() == QDialog.Accepted:
                self.load_users()

    def _on_toggle_lock(self):
        u = self._get_selected_user()
        if u:
            new_lock_state = not u["IsLocked"]
            action_name = "lock" if new_lock_state else "unlock"
            if ToastNotification.confirm(self, "Confirm", f"Are you sure you want to {action_name} user '{u['Username']}'?"):
                success, msg = UserService.toggle_lock_status(u["UserID"], new_lock_state)
                if success:
                    ToastNotification.show_success(self, "Success", msg)
                    self.load_users()
                else:
                    ToastNotification.show_error(self, "Error", msg)

    def _on_reset_password(self):
        u = self._get_selected_user()
        if u:
            dlg = ResetPasswordDialog(u["Username"], u["UserID"], parent=self)
            dlg.exec()

    def _on_view_history(self):
        u = self._get_selected_user()
        username = u["Username"] if u else ""
        dlg = LoginHistoryDialog(username=username, parent=self)
        dlg.exec()

    def _on_delete_user(self):
        u = self._get_selected_user()
        if u:
            if ToastNotification.confirm(self, "Confirm Delete", f"Permanently delete user '{u['Username']}'?"):
                success, msg = UserService.delete_user(u["UserID"])
                if success:
                    ToastNotification.show_success(self, "Success", msg)
                    self.load_users()
                else:
                    ToastNotification.show_error(self, "Error", msg)

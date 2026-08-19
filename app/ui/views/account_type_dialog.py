from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QGroupBox, QDialogButtonBox
)
from app.services.labour_service import LabourService
from app.ui.components.toast import ToastNotification


class AccountTypeManagementDialog(QDialog):
    """Dialog allowing Administrators to append custom Account Types to the lookup table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Account Categories Lookup Management")
        self.setFixedSize(420, 480)
        self._init_ui()
        self.load_types()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("Account Categories Lookup")
        g_layout = QVBoxLayout(group)

        self.list_widget = QListWidget()
        g_layout.addWidget(self.list_widget)

        # Add new type section
        add_layout = QHBoxLayout()
        self.type_input = QLineEdit()
        self.type_input.setPlaceholderText("Enter new account category name...")

        self.btn_add = QPushButton("➕ Add Category")
        self.btn_add.setProperty("class", "btn-primary")
        self.btn_add.clicked.connect(self._on_add_type)

        add_layout.addWidget(self.type_input)
        add_layout.addWidget(self.btn_add)
        g_layout.addLayout(add_layout)

        layout.addWidget(group)

        bbox = QDialogButtonBox(QDialogButtonBox.Close)
        bbox.rejected.connect(self.accept)
        layout.addWidget(bbox)

    def load_types(self):
        self.list_widget.clear()
        types = LabourService.get_account_types()
        for t in types:
            tag = " (System)" if t["IsSystemDefined"] else " (Custom)"
            self.list_widget.addItem(f"• {t['AccountTypeName']}{tag}")

    def _on_add_type(self):
        name = self.type_input.text().strip()
        if not name:
            ToastNotification.show_warning(self, "Validation Error", "Category name cannot be empty.")
            return

        success, msg = LabourService.create_account_type(name)
        if success:
            ToastNotification.show_success(self, "Success", msg)
            self.type_input.clear()
            self.load_types()
        else:
            ToastNotification.show_error(self, "Error", msg)

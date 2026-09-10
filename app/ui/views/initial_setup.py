from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from app.services.auth_service import AuthService


class InitialSetupDialog(QDialog):
    """One-time local setup that creates the first administrator without default credentials."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bahata ERP — Secure first-time setup")
        self.setModal(True)
        self.setFixedWidth(460)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 30, 32, 28)
        layout.setSpacing(14)
        title = QLabel("Set up your administrator account")
        title.setObjectName("setupTitle")
        subtitle = QLabel("There are no default passwords. Choose credentials known only to your business owner.")
        subtitle.setWordWrap(True)
        subtitle.setObjectName("setupSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(10)
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Business owner or system administrator")
        self.username = QLineEdit()
        self.username.setPlaceholderText("At least 3 letters, numbers, dots or underscores")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("12+ characters, upper/lowercase, number and symbol")
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.Password)
        self.confirm.setPlaceholderText("Repeat password")
        form.addRow("Full name", self.full_name)
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)
        form.addRow("Confirm password", self.confirm)
        layout.addLayout(form)

        self.error = QLabel()
        self.error.setObjectName("setupError")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        buttons = QHBoxLayout()
        buttons.addStretch()
        create = QPushButton("Create secure administrator")
        create.setProperty("class", "btn-primary")
        create.clicked.connect(self._create)
        buttons.addWidget(create)
        layout.addLayout(buttons)

    def _create(self):
        self.error.hide()
        if self.password.text() != self.confirm.text():
            self.error.setText("The password confirmation does not match.")
            self.error.show()
            return
        ok, message = AuthService.create_initial_administrator(
            self.username.text(), self.full_name.text(), self.password.text()
        )
        if ok:
            self.accept()
        else:
            self.error.setText(message)
            self.error.show()

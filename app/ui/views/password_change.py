from PySide6.QtWidgets import QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from app.services.auth_service import AuthService


class PasswordChangeDialog(QDialog):
    """Mandatory password upgrade for a legacy, known default credential."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bahata ERP — Password update required")
        self.setModal(True)
        self.setFixedWidth(440)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 26)
        title = QLabel("Update the default password")
        title.setObjectName("setupTitle")
        layout.addWidget(title)
        message = QLabel("This account uses a known installation password. Set a private password before continuing.")
        message.setObjectName("setupSubtitle")
        message.setWordWrap(True)
        layout.addWidget(message)
        form = QFormLayout()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.Password)
        form.addRow("New password", self.password)
        form.addRow("Confirm password", self.confirm)
        layout.addLayout(form)
        self.error = QLabel()
        self.error.setObjectName("setupError")
        self.error.setWordWrap(True)
        self.error.hide()
        layout.addWidget(self.error)
        actions = QHBoxLayout()
        actions.addStretch()
        save = QPushButton("Save new password")
        save.setProperty("class", "btn-primary")
        save.clicked.connect(self._save)
        actions.addWidget(save)
        layout.addLayout(actions)

    def _save(self):
        self.error.hide()
        if self.password.text() != self.confirm.text():
            self.error.setText("The password confirmation does not match.")
            self.error.show()
            return
        ok, message = AuthService.change_own_password(self.password.text())
        if ok:
            self.accept()
        else:
            self.error.setText(message)
            self.error.show()

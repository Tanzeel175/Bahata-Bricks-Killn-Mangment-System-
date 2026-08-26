from PySide6.QtWidgets import QMessageBox, QWidget


class ToastNotification:
    """Helper for displaying professional feedback messages."""

    @staticmethod
    def show_info(parent: QWidget, title: str, message: str):
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    @staticmethod
    def show_success(parent: QWidget, title: str, message: str):
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    @staticmethod
    def show_warning(parent: QWidget, title: str, message: str):
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    @staticmethod
    def show_error(parent: QWidget, title: str, message: str):
        msg = QMessageBox(parent)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.exec()

    @staticmethod
    def success(parent: QWidget, message: str, title: str = "Success"):
        ToastNotification.show_success(parent, title, message)

    @staticmethod
    def info(parent: QWidget, message: str, title: str = "Information"):
        ToastNotification.show_info(parent, title, message)

    @staticmethod
    def warning(parent: QWidget, message: str, title: str = "Warning"):
        ToastNotification.show_warning(parent, title, message)

    @staticmethod
    def error(parent: QWidget, message: str, title: str = "Error"):
        ToastNotification.show_error(parent, title, message)

    @staticmethod
    def confirm(parent: QWidget, title: str, message: str) -> bool:
        reply = QMessageBox.question(
            parent,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes

    @staticmethod
    def confirm_unsaved_changes(parent: QWidget, form_name: str = "Form") -> str:
        msg_box = QMessageBox(parent)
        msg_box.setWindowTitle("⚠️ Unsaved Changes Warning")
        msg_box.setText(f"You have unsaved changes in {form_name}.")
        msg_box.setInformativeText("Would you like to save your changes before leaving?")
        msg_box.setIcon(QMessageBox.Warning)

        btn_save = msg_box.addButton("💾 Save Changes", QMessageBox.AcceptRole)
        btn_discard = msg_box.addButton("🗑️ Discard Changes", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("❌ Cancel", QMessageBox.RejectRole)

        msg_box.setDefaultButton(btn_save)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn_save:
            return "save"
        elif clicked == btn_discard:
            return "discard"
        else:
            return "cancel"

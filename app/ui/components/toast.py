from PySide6.QtWidgets import QMessageBox, QWidget
from app.ui.theme_manager import theme_mgr


class ToastNotification:
    """Helper for displaying professional feedback messages."""

    @staticmethod
    def _create_styled_box(parent: QWidget, icon: QMessageBox.Icon, title: str, message: str) -> QMessageBox:
        is_dark = theme_mgr.is_dark_mode()
        msg = QMessageBox(parent)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(message)

        bg_col = "#1E293B" if is_dark else "#FFFFFF"
        fg_col = "#F8FAFC" if is_dark else "#0F172A"
        border_col = "#334155" if is_dark else "#CBD5E1"
        btn_bg = "#2563EB"
        btn_hover = "#1D4ED8"

        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {bg_col} !important;
                border: 1px solid {border_col};
            }}
            QMessageBox QLabel {{
                background-color: transparent !important;
                color: {fg_col} !important;
                font-size: 13px;
                font-weight: 600;
            }}
            QMessageBox QPushButton {{
                background-color: {btn_bg};
                color: #FFFFFF !important;
                font-size: 12.5px;
                font-weight: 700;
                border-radius: 6px;
                padding: 6px 20px;
                min-width: 70px;
                border: none;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        return msg

    @staticmethod
    def show_info(parent: QWidget, title: str, message: str):
        msg = ToastNotification._create_styled_box(parent, QMessageBox.Information, title, message)
        msg.exec()

    @staticmethod
    def show_success(parent: QWidget, title: str, message: str):
        msg = ToastNotification._create_styled_box(parent, QMessageBox.Information, title, message)
        msg.exec()

    @staticmethod
    def show_warning(parent: QWidget, title: str, message: str):
        msg = ToastNotification._create_styled_box(parent, QMessageBox.Warning, title, message)
        msg.exec()

    @staticmethod
    def show_error(parent: QWidget, title: str, message: str):
        msg = ToastNotification._create_styled_box(parent, QMessageBox.Critical, title, message)
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
        msg = ToastNotification._create_styled_box(parent, QMessageBox.Question, title, message)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        return msg.exec() == QMessageBox.Yes

    @staticmethod
    def confirm_unsaved_changes(parent: QWidget, form_name: str = "Form") -> str:
        msg_box = ToastNotification._create_styled_box(
            parent,
            QMessageBox.Warning,
            "Unsaved Changes Warning",
            f"You have unsaved changes in {form_name}."
        )
        msg_box.setInformativeText("Would you like to save your changes before leaving?")

        btn_save = msg_box.addButton("Save Changes", QMessageBox.AcceptRole)
        btn_discard = msg_box.addButton("Discard Changes", QMessageBox.DestructiveRole)
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.RejectRole)

        msg_box.setDefaultButton(btn_save)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == btn_save:
            return "save"
        elif clicked == btn_discard:
            return "discard"
        else:
            return "cancel"

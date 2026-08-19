from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QFrame, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer, Signal
from app.config import APP_NAME, APP_SUBTITLE, COMPANY_NAME, APP_VERSION
from app.services.auth_service import AuthService
from app.ui.components.toast import ToastNotification
from app.ui.styles import LIGHT_THEME_QSS


class LoginWindow(QDialog):
    """
    Enterprise ERP Login Dialog.
    Features:
    - Company Branding & Software Title
    - Username & Password Inputs with Validation
    - Show Password Checkbox
    - Remember Username Checkbox
    - Real-time Clock & Date
    - Login & Exit Actions
    """
    login_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Authentication")
        self.setFixedSize(480, 560)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(LIGHT_THEME_QSS)

        self._init_ui()
        self._load_remembered_username()

    def _init_ui(self):
        # Container frame with rounded border and soft shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame(self)
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(
            "QFrame#MainContainer { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; }"
        )

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(36, 32, 36, 28)
        layout.setSpacing(14)

        # Header branding section
        brand_layout = QVBoxLayout()
        brand_layout.setAlignment(Qt.AlignCenter)

        # Company / Kiln Logo Icon Badge
        logo_label = QLabel("🔥")
        logo_label.setStyleSheet(
            "font-size: 40px; background-color: #EFF6FF; border-radius: 32px; padding: 12px; min-width: 64px; min-height: 64px;"
        )
        logo_label.setAlignment(Qt.AlignCenter)
        brand_layout.addWidget(logo_label, alignment=Qt.AlignCenter)

        title_label = QLabel(APP_NAME)
        title_label.setObjectName("TitleLabel")
        title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A; margin-top: 8px;")
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel(f"{APP_SUBTITLE}  •  v{APP_VERSION}")
        subtitle_label.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 500;")
        subtitle_label.setAlignment(Qt.AlignCenter)

        brand_layout.addWidget(title_label)
        brand_layout.addWidget(subtitle_label)
        layout.addLayout(brand_layout)

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #F1F5F9; margin-top: 4px; margin-bottom: 4px;")
        layout.addWidget(line)

        # Inputs section
        input_layout = QVBoxLayout()
        input_layout.setSpacing(12)

        # Username Field
        un_label = QLabel("Username")
        un_label.setStyleSheet("font-weight: 600; color: #334155; font-size: 13px;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(38)
        self.username_input.returnPressed.connect(self._focus_password)
        input_layout.addWidget(un_label)
        input_layout.addWidget(self.username_input)

        # Password Field
        pw_label = QLabel("Password")
        pw_label.setStyleSheet("font-weight: 600; color: #334155; font-size: 13px;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(38)
        self.password_input.returnPressed.connect(self._on_login_clicked)
        input_layout.addWidget(pw_label)
        input_layout.addWidget(self.password_input)

        layout.addLayout(input_layout)

        # Checkboxes row (Show Password & Remember Username)
        cb_layout = QHBoxLayout()
        self.show_password_cb = QCheckBox("Show Password")
        self.show_password_cb.toggled.connect(self._toggle_show_password)

        self.remember_un_cb = QCheckBox("Remember Username")
        self.remember_un_cb.setChecked(True)

        cb_layout.addWidget(self.show_password_cb)
        cb_layout.addStretch()
        cb_layout.addWidget(self.remember_un_cb)
        layout.addLayout(cb_layout)

        # Error feedback label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #DC2626; font-size: 12px; font-weight: 600;")
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Action Buttons (Login & Exit)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.login_btn = QPushButton("Login")
        self.login_btn.setProperty("class", "btn-primary")
        self.login_btn.setStyleSheet(
            "QPushButton { background-color: #1A73E8; color: #FFFFFF; font-weight: 700; font-size: 14px; border-radius: 6px; min-height: 40px; } "
            "QPushButton:hover { background-color: #1557B0; }"
        )
        self.login_btn.clicked.connect(self._on_login_clicked)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #475569; font-weight: 600; font-size: 14px; border: 1px solid #CBD5E1; border-radius: 6px; min-height: 40px; } "
            "QPushButton:hover { background-color: #E2E8F0; color: #0F172A; }"
        )
        self.exit_btn.clicked.connect(self._on_exit_clicked)

        btn_layout.addWidget(self.login_btn, stretch=2)
        btn_layout.addWidget(self.exit_btn, stretch=1)
        layout.addLayout(btn_layout)

        # Footer Date & Time display
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 10px;")
        self.clock_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.clock_label)

        main_layout.addWidget(self.container)

        # Start Clock Timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def _focus_password(self):
        self.password_input.setFocus()

    def _toggle_show_password(self, checked: bool):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)

    def _update_clock(self):
        now_str = datetime.now().strftime("%d-%b-%Y  |  %I:%M:%S %p")
        self.clock_label.setText(f"{COMPANY_NAME}\nSystem Time: {now_str}")

    def _load_remembered_username(self):
        saved_un = AuthService.get_remembered_username()
        if saved_un:
            self.username_input.setText(saved_un)
            self.remember_un_cb.setChecked(True)
            self.password_input.setFocus()
        else:
            self.username_input.setFocus()

    def _on_login_clicked(self):
        self.error_label.hide()
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username:
            self.error_label.setText("Please enter your username.")
            self.error_label.show()
            self.username_input.setFocus()
            return

        if not password:
            self.error_label.setText("Please enter your password.")
            self.error_label.show()
            self.password_input.setFocus()
            return

        # Attempt authentication
        success, message = AuthService.authenticate(username, password)
        if success:
            if self.remember_un_cb.isChecked():
                AuthService.save_remembered_username(username)
            else:
                AuthService.save_remembered_username("")

            self.login_successful.emit()
            self.accept()
        else:
            self.error_label.setText(message)
            self.error_label.show()
            self.password_input.clear()
            self.password_input.setFocus()

    def _on_exit_clicked(self):
        self.reject()
        QApplication.quit()

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
from app.ui.theme_manager import theme_mgr


class LoginWindow(QDialog):
    """
    Enterprise ERP Login Dialog with theme support (Light / Dark).
    """
    login_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} - Authentication")
        self.setFixedSize(480, 580)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowSystemMenuHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._init_ui()
        self._load_remembered_username()

    def _init_ui(self):
        # Container frame with rounded border and soft shadow
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.container = QFrame(self)
        self.container.setObjectName("MainContainer")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(36, 24, 36, 28)
        layout.setSpacing(12)

        # Top Bar with Theme Toggle and Close button
        top_bar = QHBoxLayout()
        top_bar.addStretch()

        is_dark = theme_mgr.is_dark_mode()
        self.theme_btn = QPushButton("☼ Light" if is_dark else "☽ Dark")
        self.theme_btn.setToolTip("Toggle Theme (Dark / Light)")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setFixedHeight(28)
        self.theme_btn.setMinimumWidth(85)
        self.theme_btn.setStyleSheet(
            "QPushButton { font-size: 11.5px; font-weight: 700; padding: 4px 10px; border-radius: 6px; } "
            "QPushButton:hover { background-color: #2563EB; color: #FFFFFF; border-color: #2563EB; }"
        )
        self.theme_btn.clicked.connect(self._toggle_theme)
        top_bar.addWidget(self.theme_btn)

        layout.addLayout(top_bar)

        # Header branding section
        brand_layout = QVBoxLayout()
        brand_layout.setAlignment(Qt.AlignCenter)

        # Company / Kiln Monogram Badge
        self.logo_label = QLabel("BK")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet(
            "font-size: 20px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px; "
            "background-color: #1E3A8A; border: 2px solid #3B82F6; "
            "border-radius: 26px; min-width: 52px; min-height: 52px; max-width: 52px; max-height: 52px;"
        )
        brand_layout.addWidget(self.logo_label, alignment=Qt.AlignCenter)

        self.title_label = QLabel(APP_NAME)
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setProperty("class", "heading-primary")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.subtitle_label = QLabel(f"{APP_SUBTITLE}  •  v{APP_VERSION}")
        self.subtitle_label.setProperty("class", "subtext")
        self.subtitle_label.setAlignment(Qt.AlignCenter)

        brand_layout.addWidget(self.title_label)
        brand_layout.addWidget(self.subtitle_label)
        layout.addLayout(brand_layout)

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("dividerLine")
        layout.addWidget(line)

        # Inputs section
        input_layout = QVBoxLayout()
        input_layout.setSpacing(10)

        # Username Field
        self.un_label = QLabel("Username")
        self.un_label.setProperty("class", "heading-secondary")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setFixedHeight(38)
        self.username_input.returnPressed.connect(self._focus_password)
        input_layout.addWidget(self.un_label)
        input_layout.addWidget(self.username_input)

        # Password Field
        self.pw_label = QLabel("Password")
        self.pw_label.setProperty("class", "heading-secondary")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(38)
        self.password_input.returnPressed.connect(self._on_login_clicked)
        input_layout.addWidget(self.pw_label)
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

        # Default credentials reminder
        self.cred_hint = QLabel("Default: <b>admin</b> / <code>Admin@123</code> &nbsp;•&nbsp; <b>munshi</b> / <code>Munshi@123</code>")
        self.cred_hint.setStyleSheet("color: #64748B; font-size: 11.5px; margin: 4px 0;")
        self.cred_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.cred_hint)

        # Action Buttons (Login & Exit)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.login_btn = QPushButton("Login")
        self.login_btn.setProperty("class", "btn-primary")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.clicked.connect(self._on_login_clicked)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setMinimumHeight(40)
        self.exit_btn.clicked.connect(self._on_exit_clicked)

        btn_layout.addWidget(self.login_btn, stretch=2)
        btn_layout.addWidget(self.exit_btn, stretch=1)
        layout.addLayout(btn_layout)

        # Footer Date & Time display
        self.clock_label = QLabel()
        self.clock_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.clock_label)

        main_layout.addWidget(self.container)

        self._apply_theme()
        theme_mgr.theme_changed.connect(lambda _: self._apply_theme())

        # Start Clock Timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def _apply_theme(self):
        is_dark = theme_mgr.is_dark_mode()
        bg_col = "#0F172A" if is_dark else "#FFFFFF"
        border_col = "#334155" if is_dark else "#E2E8F0"
        self.container.setStyleSheet(
            f"QFrame#MainContainer {{ background-color: {bg_col}; border: 1px solid {border_col}; border-radius: 12px; }}"
        )

        title_col = "#FFFFFF" if is_dark else "#0F172A"
        sub_col = "#E2E8F0" if is_dark else "#64748B"
        lbl_col = "#FFFFFF" if is_dark else "#1E293B"
        hint_col = "#F1F5F9" if is_dark else "#475569"
        clock_col = "#E2E8F0" if is_dark else "#64748B"
        cb_col = "#FFFFFF" if is_dark else "#1E293B"

        self.title_label.setStyleSheet(f"font-size: 19px; font-weight: 800; color: {title_col}; border: none; background: transparent;")
        self.subtitle_label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {sub_col}; border: none; background: transparent;")
        self.un_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {lbl_col}; border: none; background: transparent;")
        self.pw_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {lbl_col}; border: none; background: transparent;")
        self.cred_hint.setStyleSheet(f"color: {hint_col}; font-size: 11.5px; margin: 4px 0; border: none; background: transparent;")
        self.clock_label.setStyleSheet(f"color: {clock_col}; font-size: 11px; margin-top: 10px; border: none; background: transparent;")
        self.show_password_cb.setStyleSheet(f"QCheckBox {{ color: {cb_col}; font-weight: 600; font-size: 12px; border: none; background: transparent; }}")
        self.remember_un_cb.setStyleSheet(f"QCheckBox {{ color: {cb_col}; font-weight: 600; font-size: 12px; border: none; background: transparent; }}")

        # Inputs
        inp_bg = "#1E293B" if is_dark else "#FFFFFF"
        inp_border = "#334155" if is_dark else "#CBD5E1"
        inp_fg = "#FFFFFF" if is_dark else "#0F172A"
        inp_style = f"QLineEdit {{ background-color: {inp_bg}; color: {inp_fg}; border: 1px solid {inp_border}; border-radius: 6px; padding: 0 10px; font-size: 13px; font-weight: 600; }}"
        self.username_input.setStyleSheet(inp_style)
        self.password_input.setStyleSheet(inp_style)

        # Theme toggle button
        theme_txt = "☼ Light" if is_dark else "☽ Dark"
        self.theme_btn.setText(theme_txt)
        btn_bg = "#1E293B" if is_dark else "#FFFFFF"
        btn_fg = "#FFFFFF" if is_dark else "#0F172A"
        self.theme_btn.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; color: {btn_fg}; font-size: 11.5px; font-weight: 700; "
            f"padding: 4px 10px; border-radius: 6px; border: 1px solid {border_col}; }} "
            f"QPushButton:hover {{ background-color: #2563EB; color: #FFFFFF; border-color: #2563EB; }}"
        )

        # Exit button
        self.exit_btn.setStyleSheet(
            f"QPushButton {{ background-color: {btn_bg}; color: {btn_fg}; font-weight: 700; font-size: 13px; "
            f"border-radius: 6px; border: 1px solid {border_col}; }} "
            f"QPushButton:hover {{ background-color: #EF4444; color: #FFFFFF; border-color: #DC2626; }}"
        )

    def _toggle_theme(self):
        theme_mgr.toggle_theme()
        self._apply_theme()

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
            self.username_input.setText("admin")
            self.password_input.setText("Admin@123")
            self.password_input.selectAll()
            self.password_input.setFocus()

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

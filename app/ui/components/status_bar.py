from datetime import datetime
from PySide6.QtWidgets import QStatusBar, QLabel, QFrame
from PySide6.QtCore import QTimer, Qt
from app.security.session import current_session
from app.config import DB_TYPE
from app.ui.theme_manager import theme_mgr


class AppStatusBar(QStatusBar):
    """
    Application Status Bar displaying:
    - Current Logged-in User & Role Badge
    - Connection Status Indicator
    - Current System Date & Live Clock
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # User info label
        self.user_label = QLabel("User: Not Logged In")
        self.user_label.setStyleSheet("font-weight: 600; margin-left: 8px;")

        # Role badge label
        self.role_label = QLabel("Role: Guest")

        # Connection status label
        self.conn_label = QLabel(f"DB: Connected ({DB_TYPE.upper()})")
        self.conn_label.setStyleSheet("color: #16A34A; font-weight: 600;")

        # Live Clock label
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("font-weight: 600; margin-right: 12px;")

        # Separator line
        sep1 = self._create_separator()
        sep2 = self._create_separator()
        sep3 = self._create_separator()

        # Add widgets to status bar
        self.addWidget(self.user_label)
        self.addWidget(sep1)
        self.addWidget(self.role_label)
        self.addWidget(sep2)
        self.addWidget(self.conn_label)

        self.addPermanentWidget(sep3)
        self.addPermanentWidget(self.clock_label)

        # Live timer for clock
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

        theme_mgr.theme_changed.connect(lambda _: self.refresh_user_status())

    def _create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setObjectName("statusSeparator")
        return line

    def _update_clock(self):
        now_str = datetime.now().strftime("%A, %b %d, %Y  %I:%M:%S %p")
        self.clock_label.setText(now_str)

    def refresh_user_status(self):
        is_dark = theme_mgr.is_dark_mode()
        if current_session.is_authenticated:
            user_str = f"User: {current_session.full_name} ({current_session.username})"
            role_str = f"Role: {current_session.role_name}"

            if current_session.is_admin:
                if is_dark:
                    badge_style = "background-color: #1E3A8A; color: #93C5FD; padding: 2px 8px; border-radius: 4px; font-weight: 700; border: 1px solid #2563EB;"
                else:
                    badge_style = "background-color: #DBEAFE; color: #1D4ED8; padding: 2px 8px; border-radius: 4px; font-weight: 700;"
            else:
                if is_dark:
                    badge_style = "background-color: #78350F; color: #FDE68A; padding: 2px 8px; border-radius: 4px; font-weight: 700; border: 1px solid #D97706;"
                else:
                    badge_style = "background-color: #FEF3C7; color: #D97706; padding: 2px 8px; border-radius: 4px; font-weight: 700;"

            self.user_label.setText(user_str)
            self.role_label.setText(role_str)
            self.role_label.setStyleSheet(badge_style)
        else:
            self.user_label.setText("User: Not Logged In")
            self.role_label.setText("Role: Guest")
            guest_style = "background-color: #334155; color: #E2E8F0; padding: 2px 8px; border-radius: 4px;" if is_dark else "background-color: #E2E8F0; color: #475569; padding: 2px 8px; border-radius: 4px;"
            self.role_label.setStyleSheet(guest_style)

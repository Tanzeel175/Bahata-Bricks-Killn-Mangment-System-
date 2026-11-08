import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.ui.components.wheel_filter import GlobalFocusWheelEventFilter
from app.database.init_db import init_db
from app.ui.views.login_window import LoginWindow
from app.ui.views.initial_setup import InitialSetupDialog
from app.ui.views.password_change import PasswordChangeDialog
from app.ui.views.main_window import MainWindow
from app.services.auth_service import AuthService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("BahtaApp")


def main():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Bahta Management System")
    app.setOrganizationName("Bahta Kiln Operations")

    # Install Global Focus Wheel Filter so mouse wheel scrolls the page unless the widget is clicked/focused
    wheel_filter = GlobalFocusWheelEventFilter(app)
    app.installEventFilter(wheel_filter)

    # Initialize and apply application-wide theme (Dark / Light / System auto-detect)
    from app.ui.theme_manager import theme_mgr
    theme_mgr.apply_theme()

    logger.info("Initializing database and seeding default datasets...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    if AuthService.needs_initial_setup():
        setup_dialog = InitialSetupDialog()
        if setup_dialog.exec() != InitialSetupDialog.Accepted:
            logger.info("Application exited before initial administrator setup.")
            return

    # Launch Login Screen
    login_dialog = LoginWindow()
    if login_dialog.exec() == LoginWindow.Accepted:
        if AuthService.requires_password_change():
            change_dialog = PasswordChangeDialog()
            if change_dialog.exec() != PasswordChangeDialog.Accepted:
                AuthService.logout()
                return
        logger.info("Authentication successful. Launching main workspace...")
        main_win = MainWindow()
        main_win.fit_screen_with_margins(5)
        main_win.show()
        sys.exit(app.exec())
    else:
        logger.info("Application exited from login window.")
        sys.exit(0)


if __name__ == "__main__":
    main()

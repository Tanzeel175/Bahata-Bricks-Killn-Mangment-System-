import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.ui.components.wheel_filter import GlobalFocusWheelEventFilter
from app.database.init_db import init_db
from app.ui.views.login_window import LoginWindow
from app.ui.views.main_window import MainWindow

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

    # Global Application Stylesheet — ensures table headers are tall without affecting QCalendarWidget popups
    app.setStyleSheet("""
        QTableWidget {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 4px;
            padding: 0px;
            margin: 0px;
            gridline-color: #E2E8F0;
            selection-background-color: #E0F2FE;
            selection-color: #0F172A;
            font-size: 13px;
        }
        QTableWidget::item {
            padding: 8px 10px;
            min-height: 36px;
        }
        QTableWidget QHeaderView {
            background-color: #F8FAFC;
            border: none;
            border-bottom: 2px solid #CBD5E1;
            padding: 0px;
            margin: 0px;
            min-height: 48px;
            border-radius: 0px;
        }
        QTableWidget QHeaderView::section {
            background-color: #F8FAFC;
            color: #0F172A;
            font-weight: 700;
            font-size: 12px;
            padding: 8px 10px;
            border: none;
            border-right: 1px solid #CBD5E1;
            border-bottom: 2px solid #CBD5E1;
            min-height: 48px;
            border-radius: 0px;
        }
        QTableCornerButton::section {
            background-color: #F8FAFC;
            border: none;
            border-bottom: 2px solid #CBD5E1;
            border-right: 1px solid #CBD5E1;
            border-radius: 0px;
            padding: 0px;
            margin: 0px;
        }
        QCalendarWidget QAbstractItemView {
            background-color: #FFFFFF;
            color: #1E293B;
            selection-background-color: #0284C7;
            selection-color: #FFFFFF;
            font-size: 13px;
            font-weight: 600;
            padding: 2px;
        }
        QCalendarWidget QWidget {
            color: #1E293B;
            font-size: 13px;
        }
        QCalendarWidget QToolButton {
            color: #1E293B;
            background-color: #F8FAFC;
            border-radius: 4px;
            padding: 4px;
            font-weight: bold;
        }
        QDateEdit {
            background-color: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 13px;
            color: #1E293B;
            min-height: 32px;
        }
    """)

    logger.info("Initializing database and seeding default datasets...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")

    # Launch Login Screen
    login_dialog = LoginWindow()
    if login_dialog.exec() == LoginWindow.Accepted:
        logger.info("Authentication successful. Launching main workspace...")
        main_win = MainWindow()
        main_win.showMaximized()
        sys.exit(app.exec())
    else:
        logger.info("Application exited from login window.")
        sys.exit(0)


if __name__ == "__main__":
    main()

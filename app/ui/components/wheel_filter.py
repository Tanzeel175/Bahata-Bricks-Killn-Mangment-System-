from PySide6.QtCore import QObject, QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDateTimeEdit, QTimeEdit,
    QSpinBox, QDoubleSpinBox, QAbstractSpinBox,
    QAbstractScrollArea, QApplication, QWidget, QLineEdit
)


class GlobalFocusWheelEventFilter(QObject):
    """
    Custom Global Event Filter for Date, Category, and Number Selection Boxes.

    Interactive Behavior:
    1. Left Click to Select: Boxes are only selected/activated when explicitly Left-Clicked.
    2. Mouse Leave Auto-Deselect: As soon as the mouse leaves the box (Mouse Leave),
       the box loses focus/selection automatically.
    3. Click-Only In-Box Scrolling: Mouse wheel scrolling only operates inside a box if
       the user explicitly Left-Clicked on that box AND the mouse is currently over it.
    4. Otherwise, mouse wheel scrolling cleanly scrolls the main page/window.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clicked_control = None

    def _find_input_control(self, obj: QObject):
        """Find if obj is, or is a child of, a DateEdit, ComboBox, or SpinBox."""
        curr = obj
        while curr is not None:
            if isinstance(curr, (QComboBox, QAbstractSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit, QSpinBox, QDoubleSpinBox)):
                return curr
            if hasattr(curr, "parent") and callable(curr.parent):
                curr = curr.parent()
            else:
                break
        return None

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        event_type = event.type()

        # 1. Track Left Click on Input Controls
        if event_type == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                control = self._find_input_control(obj)
                if control is not None:
                    self.clicked_control = control
                else:
                    self.clicked_control = None

        # 2. Track Mouse Leave to Auto-Deselect / Remove Focus
        elif event_type == QEvent.Leave:
            control = self._find_input_control(obj)
            if control is not None:
                # Clear active click tracking if mouse leaves control
                if self.clicked_control is control or self.clicked_control == control:
                    self.clicked_control = None

                # Remove focus and clear text selection on mouse leave
                control.clearFocus()
                if hasattr(control, "lineEdit") and control.lineEdit():
                    control.lineEdit().deselect()
                    control.lineEdit().clearFocus()

        # 3. Handle Mouse Wheel Events
        elif event_type == QEvent.Wheel:
            control = self._find_input_control(obj)
            if control is not None:
                # Allow wheel scrolling if a ComboBox popup dropdown is currently open and active
                if isinstance(control, QComboBox):
                    if hasattr(control, "view") and control.view() and control.view().isVisible():
                        if obj is control.view() or obj is control.view().viewport():
                            return super().eventFilter(obj, event)

                # Check if the user explicitly Left-Clicked on this box AND the mouse is inside it
                is_click_activated = (
                    self.clicked_control is control and
                    control.underMouse() and
                    control.hasFocus()
                )

                if is_click_activated:
                    # Allow in-box scrolling while mouse is inside the clicked box
                    return super().eventFilter(obj, event)

                # Otherwise, forward wheel event to parent scroll area to scroll the main window
                parent = control.parent()
                while parent is not None:
                    if isinstance(parent, QAbstractScrollArea):
                        QApplication.sendEvent(parent.viewport(), event)
                        return True
                    parent = parent.parent() if hasattr(parent, "parent") and callable(parent.parent) else None

                if control.window() and isinstance(control.window(), QWidget):
                    QApplication.sendEvent(control.window(), event)
                    return True

                return True

        return super().eventFilter(obj, event)

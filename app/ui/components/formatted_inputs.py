import re
from PySide6.QtWidgets import QLineEdit
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtCore import QRegularExpression


class CNICLineEdit(QLineEdit):
    """
    Custom QLineEdit for Pakistani CNIC auto-formatting.
    Auto inserts hyphens at positions: XXXXX-XXXXXXX-X.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxLength(15)  # 5 + 1 + 7 + 1 + 1
        self.setPlaceholderText("35202-1234567-1")
        self.textEdited.connect(self._on_text_edited)

    def _on_text_edited(self, text: str):
        # Extract digits only
        digits = re.sub(r"\D", "", text)
        if len(digits) > 13:
            digits = digits[:13]

        formatted = ""
        if len(digits) > 0:
            formatted += digits[:5]
        if len(digits) > 5:
            formatted += "-" + digits[5:12]
        if len(digits) > 12:
            formatted += "-" + digits[12]

        if formatted != text:
            cursor_pos = self.cursorPosition()
            self.setText(formatted)
            self.setCursorPosition(min(cursor_pos + 1, len(formatted)))


class PhoneLineEdit(QLineEdit):
    """
    Custom QLineEdit for Pakistani Mobile Numbers (03XX-XXXXXXX or +92...).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaxLength(15)
        self.setPlaceholderText("03001234567 or +923001234567")
        regex = QRegularExpression(r"^(\+92|0)?3\d{0,9}$")
        self.setValidator(QRegularExpressionValidator(regex, self))


class NumericLineEdit(QLineEdit):
    """
    Custom QLineEdit restricting input strictly to non-negative numbers.
    """

    def __init__(self, allow_decimal: bool = True, parent=None):
        super().__init__(parent)
        if allow_decimal:
            regex = QRegularExpression(r"^\d*\.?\d*$")
        else:
            regex = QRegularExpression(r"^\d*$")
        self.setValidator(QRegularExpressionValidator(regex, self))
        self.setText("0")


class CurrencyEdit(QLineEdit):
    """
    Custom QLineEdit for Currency / Amount input.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        regex = QRegularExpression(r"^\d*(\.\d{0,2})?$")
        self.setValidator(QRegularExpressionValidator(regex, self))
        self.setPlaceholderText("0.00")

    def get_value(self) -> float:
        text = self.text().strip()
        try:
            return float(text) if text else 0.0
        except ValueError:
            return 0.0

    def set_value(self, val: float):
        self.setText(f"{val:.2f}")

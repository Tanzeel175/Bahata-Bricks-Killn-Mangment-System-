from datetime import date
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QTextBrowser, QFileDialog
)
from PySide6.QtCore import Qt, QDate, QSizeF, QMarginsF
from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout, QFont
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

from app.config import COMPANY_NAME, APP_SUBTITLE
from app.ui.components.toast import ToastNotification


class VoucherWindow(QDialog):
    """
    Dedicated Popup Window for Cash Receipt (Amdan) and Payment (Akrajat) Vouchers.
    Provides a clean, scrollable, zoomable, printable, and PDF-exportable A4 document.
    """

    def __init__(self, txn_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.txn_data = txn_data
        t_type = txn_data.get("TransactionType", "RECEIPT")
        t_no = txn_data.get("TransactionNo", "TXN")
        t_title = "Cash Receipt (رسید وصولی)" if t_type == "RECEIPT" else "Cash Payment Voucher (واؤچر ادائیگی)"

        self.setWindowTitle(f"📄 {t_title} — {t_no}")
        self.resize(850, 720)
        self.setMinimumSize(700, 550)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")

        self.zoom_level = 100
        self._init_ui()
        self._render_voucher()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # 1. Top Action Toolbar
        tb_frame = QFrame()
        tb_frame.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 6px; }"
        )
        tb_layout = QHBoxLayout(tb_frame)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(10)

        lbl_doc = QLabel("📋 Printable A4 Voucher Preview")
        lbl_doc.setStyleSheet("font-size: 13px; font-weight: 800; color: #1E293B;")
        tb_layout.addWidget(lbl_doc)
        tb_layout.addStretch()

        # Zoom Controls
        self.btn_zoom_out = QPushButton("🔍 -")
        self.btn_zoom_out.setToolTip("Zoom Out")
        self.btn_zoom_out.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #334155; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 12px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.btn_zoom_out.clicked.connect(self._zoom_out)
        tb_layout.addWidget(self.btn_zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet("font-weight: 700; color: #64748B; min-width: 45px;")
        self.lbl_zoom.setAlignment(Qt.AlignCenter)
        tb_layout.addWidget(self.lbl_zoom)

        self.btn_zoom_in = QPushButton("🔍 +")
        self.btn_zoom_in.setToolTip("Zoom In")
        self.btn_zoom_in.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #334155; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 12px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        tb_layout.addWidget(self.btn_zoom_in)

        # Print Button
        self.btn_print = QPushButton("🖨️ Print Voucher")
        self.btn_print.setStyleSheet(
            "QPushButton { background-color: #0284C7; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 16px; border: none; } "
            "QPushButton:hover { background-color: #0369A1; }"
        )
        self.btn_print.clicked.connect(self._on_print)
        tb_layout.addWidget(self.btn_print)

        # PDF Export Button
        self.btn_pdf = QPushButton("📄 Save as PDF")
        self.btn_pdf.setStyleSheet(
            "QPushButton { background-color: #16A34A; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 16px; border: none; } "
            "QPushButton:hover { background-color: #15803D; }"
        )
        self.btn_pdf.clicked.connect(self._on_export_pdf)
        tb_layout.addWidget(self.btn_pdf)

        # Close Button
        self.btn_close = QPushButton("✖ Close")
        self.btn_close.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #475569; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 14px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.btn_close.clicked.connect(self.close)
        tb_layout.addWidget(self.btn_close)

        main_layout.addWidget(tb_frame)

        # 2. Text Browser Document Viewport
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(False)
        self.text_browser.setStyleSheet(
            "QTextBrowser { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 20px; }"
        )
        main_layout.addWidget(self.text_browser)

    def _render_voucher(self):
        txn = self.txn_data
        t_type = txn.get("TransactionType", "RECEIPT")
        t_no = txn.get("TransactionNo", "TXN-000000")
        t_date = txn.get("DateStr", "") or str(txn.get("TransactionDate", ""))
        acc_id = txn.get("AccountID", "")
        acc_name = txn.get("AccountName", "Account")
        urdu_name = txn.get("UrduName", "")
        category = txn.get("CategoryName", "General")
        amount = float(txn.get("Amount", 0.0) or 0.0)
        method = txn.get("PaymentMethod", "Cash")
        bank_acc = txn.get("BankAccount", "")
        cheque_no = txn.get("ChequeNumber", "")
        desc = txn.get("Description", "")
        ref_type = txn.get("ReferenceType", "")
        ref_id = txn.get("ReferenceID", "")
        entered_by = txn.get("CreatedBy", "Staff")

        is_receipt = (t_type == "RECEIPT")
        header_title = "CASH RECEIPT VOUCHER (رسید وصولی نقد)" if is_receipt else "CASH PAYMENT VOUCHER (واؤچر ادائیگی نقد)"
        accent_color = "#16A34A" if is_receipt else "#DC2626"
        badge_bg = "#DCFCE7" if is_receipt else "#FEE2E2"
        badge_border = "#86EFAC" if is_receipt else "#FCA5A5"
        movement_label = "MONEY RECEIVED FROM (وصول کنندہ سے رقم موصول ہوئی):" if is_receipt else "MONEY PAID TO (ادائیگی برائے):"

        method_details = method
        if bank_acc:
            method_details += f" &bull; Bank A/C: {bank_acc}"
        if cheque_no:
            method_details += f" &bull; Cheque #: {cheque_no}"

        urdu_display = f" / {urdu_name}" if urdu_name else ""

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                color: #0F172A;
                margin: 0;
                padding: 10px;
                background-color: #FFFFFF;
            }}
            .voucher-card {{
                border: 2px solid {accent_color};
                border-radius: 10px;
                padding: 24px;
                max-width: 760px;
                margin: auto;
            }}
            .company-header {{
                text-align: center;
                border-bottom: 2px solid #E2E8F0;
                padding-bottom: 14px;
                margin-bottom: 18px;
            }}
            .company-title {{
                font-size: 24px;
                font-weight: 900;
                color: #0F172A;
                margin: 0;
            }}
            .company-sub {{
                font-size: 13px;
                color: #64748B;
                margin-top: 4px;
                font-weight: 600;
            }}
            .voucher-badge-box {{
                text-align: center;
                margin-top: 10px;
            }}
            .voucher-badge {{
                display: inline-block;
                background-color: {badge_bg};
                color: {accent_color};
                border: 1px solid {badge_border};
                border-radius: 20px;
                padding: 6px 24px;
                font-size: 16px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}
            .meta-grid {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 16px;
                margin-bottom: 16px;
            }}
            .meta-grid td {{
                padding: 6px 8px;
                font-size: 13px;
            }}
            .meta-label {{
                font-weight: 700;
                color: #475569;
                width: 25%;
            }}
            .meta-val {{
                font-weight: 800;
                color: #0F172A;
                width: 25%;
            }}
            .party-box {{
                background-color: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 14px 18px;
                margin-top: 14px;
                margin-bottom: 16px;
            }}
            .party-title {{
                font-size: 12px;
                font-weight: 800;
                color: #64748B;
                text-transform: uppercase;
                margin-bottom: 6px;
            }}
            .party-name {{
                font-size: 18px;
                font-weight: 800;
                color: #0F172A;
            }}
            .party-sub {{
                font-size: 12px;
                color: #475569;
                margin-top: 4px;
            }}
            .amount-box {{
                background-color: {badge_bg};
                border: 2px dashed {accent_color};
                border-radius: 8px;
                padding: 16px 20px;
                text-align: center;
                margin-top: 16px;
                margin-bottom: 16px;
            }}
            .amount-title {{
                font-size: 13px;
                font-weight: 700;
                color: #334155;
            }}
            .amount-val {{
                font-size: 28px;
                font-weight: 900;
                color: {accent_color};
                margin-top: 4px;
            }}
            .narration-box {{
                border: 1px solid #E2E8F0;
                border-radius: 6px;
                padding: 12px 16px;
                background-color: #FFFFFF;
                font-size: 13px;
                color: #1E293B;
                line-height: 1.5;
                margin-bottom: 24px;
            }}
            .signatures-table {{
                width: 100%;
                margin-top: 36px;
                border-collapse: collapse;
            }}
            .signatures-table td {{
                width: 50%;
                text-align: center;
                padding: 10px;
            }}
            .sig-line {{
                border-top: 1px solid #94A3B8;
                width: 80%;
                margin: auto;
                padding-top: 6px;
                font-weight: 700;
                font-size: 12px;
                color: #334155;
            }}
            .footer-note {{
                font-size: 10px;
                color: #94A3B8;
                text-align: center;
                margin-top: 20px;
                border-top: 1px solid #F1F5F9;
                padding-top: 8px;
            }}
        </style>
        </head>
        <body>
            <div class="voucher-card">
                <div class="company-header">
                    <div class="company-title">{COMPANY_NAME}</div>
                    <div class="company-sub">{APP_SUBTITLE} &bull; Kiln Operations ERP</div>
                    <div class="voucher-badge-box">
                        <span class="voucher-badge">{header_title}</span>
                    </div>
                </div>

                <table class="meta-grid">
                    <tr>
                        <td class="meta-label">Voucher / Ref No:</td>
                        <td class="meta-val">{t_no}</td>
                        <td class="meta-label">Date (تاریخ):</td>
                        <td class="meta-val">{t_date}</td>
                    </tr>
                    <tr>
                        <td class="meta-label">Payment Method:</td>
                        <td class="meta-val">{method_details}</td>
                        <td class="meta-label">Category (کھاتہ قسم):</td>
                        <td class="meta-val">{category}</td>
                    </tr>
                    <tr>
                        <td class="meta-label">Ref Type / Batch:</td>
                        <td class="meta-val">{ref_type or "N/A"}</td>
                        <td class="meta-label">Entered By:</td>
                        <td class="meta-val">{entered_by}</td>
                    </tr>
                </table>

                <div class="party-box">
                    <div class="party-title">{movement_label}</div>
                    <div class="party-name">{acc_id} &mdash; {acc_name}{urdu_display}</div>
                    <div class="party-sub">Category: <b>{category}</b> &bull; Phone: {txn.get("Mobile") or "N/A"} &bull; CNIC: {txn.get("CNIC") or "N/A"}</div>
                </div>

                <div class="amount-box">
                    <div class="amount-title">Total Transaction Amount (کل رقم)</div>
                    <div class="amount-val">Rs. {amount:,.2f}</div>
                </div>

                <div style="font-weight: 700; font-size: 12px; color: #475569; margin-bottom: 4px;">Description / Narration (تفصیل):</div>
                <div class="narration-box">
                    {desc or "No additional description recorded."}
                </div>

                <table class="signatures-table">
                    <tr>
                        <td>
                            <div class="sig-line">Prepared / Approved by (دستخط منشی/کیشیئر)</div>
                        </td>
                        <td>
                            <div class="sig-line">Customer / Labour Signature (دستخط وصول کنندہ)</div>
                        </td>
                    </tr>
                </table>

                <div class="footer-note">
                    Official computerized voucher generated by Bahta ERP &bull; Verified against internal database ledger
                </div>
            </div>
        </body>
        </html>
        """
        self.html_content = html
        self.text_browser.setHtml(html)

    def _zoom_in(self):
        if self.zoom_level < 160:
            self.zoom_level += 10
            self.text_browser.zoomIn(1)
            self.lbl_zoom.setText(f"{self.zoom_level}%")

    def _zoom_out(self):
        if self.zoom_level > 60:
            self.zoom_level -= 10
            self.text_browser.zoomOut(1)
            self.lbl_zoom.setText(f"{self.zoom_level}%")

    def _on_print(self):
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Millimeter)

        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(self.html_content)
            doc.print_(printer)
            ToastNotification.show_success(self, "Printed", "Voucher sent to printer.")

    def _on_export_pdf(self):
        t_no = self.txn_data.get("TransactionNo", "Voucher")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Voucher as PDF",
            f"{t_no}.pdf",
            "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(file_path)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        printer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Millimeter)

        doc = QTextDocument()
        doc.setHtml(self.html_content)
        doc.print_(printer)

        ToastNotification.show_success(self, "PDF Exported", f"Saved successfully to:\n{file_path}")

from datetime import date
from typing import Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QTextBrowser, QFileDialog
)
from PySide6.QtCore import Qt, QDate, QSizeF, QMarginsF
from PySide6.QtGui import QTextDocument, QPageSize, QPageLayout, QFont
from PySide6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

from app.ui.components.toast import ToastNotification


class LedgerReportWindow(QDialog):
    """
    Dedicated Popup Report Window for Labour & Account Ledger.
    Provides a clean, scrollable, zoomable, printable, and PDF-exportable document.
    Outputs crystal-clear, full-sized A4 multi-page documents for print and PDF.
    """

    def __init__(self, ledger_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.ledger_data = ledger_data
        worker = ledger_data.get("worker", {})
        w_name = worker.get("english_name", "Labourer")
        w_id = worker.get("worker_id", "")

        self.setWindowTitle(f"📄 Labour Ledger Report — {w_name} ({w_id})")
        self.resize(1040, 850)
        self.setMinimumSize(880, 600)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")

        self.zoom_level = 100
        self._init_ui()
        self._render_report()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. Top Action Toolbar
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 6px; }"
        )
        tb_layout = QHBoxLayout(toolbar_frame)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(10)

        lbl_doc = QLabel("📋 Printable A4 Document Preview")
        lbl_doc.setStyleSheet("font-size: 14px; font-weight: 800; color: #1E293B;")
        tb_layout.addWidget(lbl_doc)
        tb_layout.addStretch()

        # Zoom Controls
        self.btn_zoom_out = QPushButton("🔍 -")
        self.btn_zoom_out.setToolTip("Zoom Out")
        self.btn_zoom_out.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #334155; font-weight: 700; font-size: 13px; border-radius: 6px; padding: 6px 12px; border: 1px solid #CBD5E1; } "
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
            "QPushButton { background-color: #F1F5F9; color: #334155; font-weight: 700; font-size: 13px; border-radius: 6px; padding: 6px 12px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.btn_zoom_in.clicked.connect(self._zoom_in)
        tb_layout.addWidget(self.btn_zoom_in)

        # Print Button
        self.btn_print = QPushButton("🖨️ Print Report")
        self.btn_print.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 16px; border: none; } "
            "QPushButton:hover { background-color: #1D4ED8; }"
        )
        self.btn_print.clicked.connect(self._on_print)
        tb_layout.addWidget(self.btn_print)

        # PDF Export Button
        self.btn_pdf = QPushButton("📄 Save as PDF")
        self.btn_pdf.setStyleSheet(
            "QPushButton { background-color: #D97706; color: #FFFFFF; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 16px; border: none; } "
            "QPushButton:hover { background-color: #B45309; }"
        )
        self.btn_pdf.clicked.connect(self._on_export_pdf)
        tb_layout.addWidget(self.btn_pdf)

        # Close Button
        self.btn_close = QPushButton("✖ Close")
        self.btn_close.setStyleSheet(
            "QPushButton { background-color: #E2E8F0; color: #334155; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 6px 14px; border: 1px solid #CBD5E1; } "
            "QPushButton:hover { background-color: #CBD5E1; }"
        )
        self.btn_close.clicked.connect(self.close)
        tb_layout.addWidget(self.btn_close)

        main_layout.addWidget(toolbar_frame)

        # 2. Report Document Viewer (QTextBrowser)
        self.browser = QTextBrowser()
        self.browser.setStyleSheet(
            "QTextBrowser { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 6px 10px; }"
        )
        self.browser.setOpenExternalLinks(False)
        main_layout.addWidget(self.browser)

    def _generate_html(self) -> str:
        d = self.ledger_data
        comp = d["company"]
        w = d["worker"]
        p = d["period"]

        rows_html = ""
        for t in d["transactions"]:
            c_str = f"Rs. {t['credit']:,.2f}" if t['credit'] > 0 else "—"
            d_str = f"Rs. {t['debit']:,.2f}" if t['debit'] > 0 else "—"
            r_val = t['running_balance']
            r_str = f"Rs. {r_val:,.2f}" if r_val >= 0 else f"-Rs. {abs(r_val):,.2f}"
            r_color = "#15803D" if r_val >= 0 else "#DC2626"

            rows_html += f"""
            <tr>
                <td width="11%" nowrap style="padding: 4px 5px; border: 1px solid #CBD5E1; font-size: 8.5pt; white-space: nowrap;">{t['date_str']}</td>
                <td width="9%" nowrap style="padding: 4px 5px; border: 1px solid #CBD5E1; font-size: 8.5pt; font-weight: bold; color: #334155; white-space: nowrap;">{t['ref']}</td>
                <td width="36%" style="padding: 4px 5px; border: 1px solid #CBD5E1; font-size: 8.5pt;">{t['description']}</td>
                <td width="14%" nowrap style="padding: 4px 5px; border: 1px solid #CBD5E1; font-size: 8.5pt; text-align: right; color: #16A34A; font-weight: bold; white-space: nowrap;">{c_str}</td>
                <td width="14%" nowrap style="padding: 4px 5px; border: 1px solid #CBD5E1; font-size: 8.5pt; text-align: right; color: #DC2626; font-weight: bold; white-space: nowrap;">{d_str}</td>
                <td width="16%" nowrap style="padding: 4px 5px; border: 1px solid #CBD5E1; font-size: 8.5pt; text-align: right; font-weight: bold; color: {r_color}; white-space: nowrap;">{r_str}</td>
            </tr>
            """

        if not d["transactions"]:
            rows_html = """
            <tr>
                <td colspan="6" style="padding: 12px; text-align: center; color: #64748B; font-style: italic; border: 1px solid #CBD5E1; font-size: 10pt;">
                    No financial transactions recorded for this account during the selected period.
                </td>
            </tr>
            """

        op_bal = d["opening_balance"]
        op_sign = f"Rs. {op_bal:,.2f}" if op_bal >= 0 else f"-Rs. {abs(op_bal):,.2f}"
        op_color = "#15803D" if op_bal >= 0 else "#DC2626"

        badge_color = "#15803D"
        badge_bg = "#F0FDF4"
        badge_border = "#22C55E"

        if d["statement_status"] == "RECEIVABLE":
            badge_color = "#DC2626"
            badge_bg = "#FEF2F2"
            badge_border = "#EF4444"
        elif d["statement_status"] == "ADVANCE":
            if w["category"] == "Customer":
                badge_color = "#15803D"
                badge_bg = "#F0FDF4"
                badge_border = "#22C55E"
            else:
                badge_color = "#DC2626"
                badge_bg = "#FEF2F2"
                badge_border = "#EF4444"
        elif d["statement_status"] == "BALANCED":
            badge_color = "#334155"
            badge_bg = "#F8FAFC"
            badge_border = "#94A3B8"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{
                    size: A4 portrait;
                    margin: 12mm;
                }}
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    margin: 0;
                    padding: 4px;
                    color: #0F172A;
                    background-color: #FFFFFF;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                tr {{
                    page-break-inside: avoid;
                }}
                .header-card {{
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    padding: 12px 18px;
                    border-radius: 6px;
                    text-align: center;
                    margin-bottom: 8px;
                    page-break-inside: avoid;
                }}
                .yellow-badge {{
                    background-color: #FDE047;
                    color: #000000;
                    font-size: 10pt;
                    font-weight: 800;
                    padding: 4px 18px;
                    border-radius: 4px;
                    text-align: center;
                    margin-bottom: 12px;
                    page-break-inside: avoid;
                }}
                .info-table {{
                    width: 100%;
                    border: 1px solid #E2E8F0;
                    background-color: #F8FAFC;
                    margin-bottom: 12px;
                    page-break-inside: avoid;
                }}
                .info-table td {{
                    padding: 6px 10px;
                    font-size: 10.5pt;
                    vertical-align: top;
                }}
                .table-main th {{
                    background-color: #F1F5F9;
                    color: #0F172A;
                    font-weight: bold;
                    font-size: 10.5pt;
                    padding: 7px 8px;
                    border: 1px solid #CBD5E1;
                    text-align: left;
                }}
                .totals-card {{
                    background-color: #F8FAFC;
                    border: 1px solid #CBD5E1;
                    border-radius: 6px;
                    padding: 8px 12px;
                    margin-top: 10px;
                    margin-bottom: 12px;
                    page-break-inside: avoid;
                }}
                .statement-badge {{
                    background-color: {badge_bg};
                    border: 2px solid {badge_border};
                    color: {badge_color};
                    border-radius: 6px;
                    padding: 10px;
                    text-align: center;
                    margin-top: 10px;
                    page-break-inside: avoid;
                }}
            </style>
        </head>
        <body>
            <div class="header-card">
                <div style="font-size: 17pt; font-weight: 900; letter-spacing: 1px;">{comp['name'].upper()}</div>
                <div style="font-size: 10pt; color: #93C5FD; margin-top: 2px;">
                    Owner: <strong>{comp['owner']}</strong> &nbsp;|&nbsp; Mobile: <strong>{comp['mobile']}</strong>
                </div>
            </div>

            <div class="yellow-badge">
                {'CUSTOMER KHATA LEDGER (گاہک کھاتہ رپورٹ)' if w['category'] == 'Customer' else 'LABOUR LEDGER (KHATA) REPORT (لیبر کھاتہ رپورٹ)'}
            </div>

            <table class="info-table">
                <tr>
                    <td style="width: 55%;">
                        <strong>Account Name:</strong> {w['english_name']}<br>
                        <strong>Account ID:</strong> {w['worker_id']}<br>
                        <strong>Category:</strong> {w['category']}
                    </td>
                    <td style="width: 45%; text-align: right;">
                        <strong>Ledger Period:</strong> {p['from_date']} to {p['to_date']}<br>
                        <span style="font-weight: bold; color: {op_color};">
                            Opening Balance: {op_sign}
                        </span>
                    </td>
                </tr>
            </table>

            <table width="100%" class="table-main" style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                <thead>
                    <tr>
                        <th width="11%" nowrap style="padding: 4px 5px; font-size: 9pt; white-space: nowrap;">Date</th>
                        <th width="9%" nowrap style="padding: 4px 5px; font-size: 9pt; white-space: nowrap;">Ref #</th>
                        <th width="36%" nowrap style="padding: 4px 5px; font-size: 9pt; white-space: nowrap;">Transaction Description</th>
                        <th width="14%" nowrap style="padding: 4px 5px; font-size: 9pt; text-align: right; white-space: nowrap;">{'Credit (Recv)' if w['category'] == 'Customer' else 'Credit (Earned)'}</th>
                        <th width="14%" nowrap style="padding: 4px 5px; font-size: 9pt; text-align: right; white-space: nowrap;">{'Debit (Sales)' if w['category'] == 'Customer' else 'Debit (Paid)'}</th>
                        <th width="16%" nowrap style="padding: 4px 5px; font-size: 9pt; text-align: right; white-space: nowrap;">Running Bal</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <table style="width: 100%; page-break-inside: avoid;">
                <tr>
                    <td style="width: 55%; vertical-align: top;">
                        <div class="totals-card" style="width: 95%;">
                            <table style="width: 100%; font-size: 10.5pt;">
                                <tr>
                                    <td style="color: #16A34A; font-weight: bold; padding: 2px 0;">{'Total Credit (Payments Received):' if w['category'] == 'Customer' else 'Total Credit (Earned):'}</td>
                                    <td style="text-align: right; color: #16A34A; font-weight: bold; padding: 2px 0;">Rs. {d['total_credit']:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="color: #DC2626; font-weight: bold; padding: 2px 0;">{'Total Debit (Sales Deliveries):' if w['category'] == 'Customer' else 'Total Debit (Paid):'}</td>
                                    <td style="text-align: right; color: #DC2626; font-weight: bold; padding: 2px 0;">Rs. {d['total_debit']:,.2f}</td>
                                </tr>
                                <tr style="border-top: 1px solid #CBD5E1;">
                                    <td style="padding-top: 4px; font-weight: 900; font-size: 11pt;">Closing Balance:</td>
                                    <td style="padding-top: 4px; text-align: right; font-weight: 900; font-size: 11pt; color: {'#16A34A' if d['closing_balance'] >= 0 else '#DC2626'};">
                                        {'Rs. ' + f"{d['closing_balance']:,.2f}" if d['closing_balance'] >= 0 else '-Rs. ' + f"{abs(d['closing_balance']):,.2f}"}
                                    </td>
                                </tr>
                            </table>
                        </div>
                    </td>
                    <td style="width: 45%;"></td>
                </tr>
            </table>

            <div class="statement-badge">
                <div style="font-size: 9pt; font-weight: 800; letter-spacing: 1px;">OUTSTANDING ACCOUNT STATEMENT</div>
                <div style="font-size: 13pt; font-weight: 900; margin-top: 2px;">{d['statement_label']}</div>
            </div>
        </body>
        </html>
        """
        return html

    def _render_report(self):
        self.browser.setHtml(self._generate_html())

    def _zoom_in(self):
        if self.zoom_level < 160:
            self.zoom_level += 15
            self.browser.zoomIn(1)
            self.lbl_zoom.setText(f"{self.zoom_level}%")

    def _zoom_out(self):
        if self.zoom_level > 60:
            self.zoom_level -= 15
            self.browser.zoomOut(1)
            self.lbl_zoom.setText(f"{self.zoom_level}%")

    def _print_to_printer(self, printer: QPrinter):
        """Render full-sized document in points matching the printer printable area."""
        doc = QTextDocument()
        doc.setDocumentMargin(12)
        # Use logical Point units so font sizes (10pt, 14pt, 17pt) fill the A4 page perfectly!
        page_size_pts = printer.pageLayout().paintRect(QPageLayout.Unit.Point).size()
        doc.setPageSize(QSizeF(page_size_pts.width(), page_size_pts.height()))
        doc.setHtml(self._generate_html())
        doc.print_(printer)

    def _on_print(self):
        printer = QPrinter(QPrinter.PrinterResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)

        dlg = QPrintDialog(printer, self)
        dlg.setWindowTitle("🖨️ Print A4 Labour Ledger Statement")
        if dlg.exec() == QPrintDialog.Accepted:
            self._print_to_printer(printer)

    def _on_export_pdf(self):
        w_id = self.ledger_data.get("worker", {}).get("worker_id", "Labour")
        default_file = f"Ledger_{w_id}_{date.today().strftime('%Y%m%d')}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Multi-Page A4 PDF", default_file, "PDF Files (*.pdf)")
        if file_path:
            printer = QPrinter(QPrinter.PrinterResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Unit.Millimeter)
            printer.setOutputFileName(file_path)

            self._print_to_printer(printer)
            ToastNotification.show_success(self, "PDF Exported", f"A4 PDF saved successfully to:\n{file_path}")

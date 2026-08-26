from datetime import date, datetime
from typing import Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextBrowser, QFileDialog, QFrame, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextDocument, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from app.config import COMPANY_NAME, APP_SUBTITLE
from app.ui.components.toast import ToastNotification


class SalesReceiptWindow(QDialog):
    """
    Print Preview & PDF Export Window for Brick Kiln Sales Receipts.
    Supports native Windows printing, A4 formatting, and PDF export.
    """

    def __init__(self, sale_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.sale_data = sale_data

        inv_no = sale_data.get("InvoiceNo", "")
        cust_name = sale_data.get("CustomerName", "")

        self.setWindowTitle(f"🧾 Sales Receipt — {inv_no} ({cust_name})")
        self.resize(1000, 800)
        self.setMinimumSize(850, 580)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")

        self.zoom_level = 100
        self._init_ui()
        self._render_receipt()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # 1. Action Toolbar
        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet(
            "QFrame { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 6px; }"
        )
        tb_layout = QHBoxLayout(toolbar_frame)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(8)

        def make_btn(text, bg_color, hover_color, text_color="#FFFFFF"):
            btn = QPushButton(text)
            btn.setMinimumHeight(34)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {bg_color}; color: {text_color}; font-weight: 700; font-size: 12px; border-radius: 6px; padding: 4px 14px; border: none; }} "
                f"QPushButton:hover {{ background-color: {hover_color}; }}"
            )
            return btn

        self.btn_print = make_btn("🖨️ Print Receipt", "#0284C7", "#0369A1")
        self.btn_print.clicked.connect(self._on_print)

        self.btn_pdf = make_btn("📄 Save as PDF", "#10B981", "#059669")
        self.btn_pdf.clicked.connect(self._on_save_pdf)

        self.btn_zoom_in = make_btn("🔍+ Zoom In", "#64748B", "#475569")
        self.btn_zoom_in.clicked.connect(self._zoom_in)

        self.btn_zoom_out = make_btn("🔍- Zoom Out", "#64748B", "#475569")
        self.btn_zoom_out.clicked.connect(self._zoom_out)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setStyleSheet("font-weight: bold; color: #475569; padding: 0 4px; font-size: 12px;")

        self.btn_close = make_btn("❌ Close", "#94A3B8", "#64748B")
        self.btn_close.clicked.connect(self.close)

        tb_layout.addWidget(self.btn_print)
        tb_layout.addWidget(self.btn_pdf)
        tb_layout.addSpacing(16)
        tb_layout.addWidget(self.btn_zoom_out)
        tb_layout.addWidget(self.lbl_zoom)
        tb_layout.addWidget(self.btn_zoom_in)
        tb_layout.addStretch()
        tb_layout.addWidget(self.btn_close)

        main_layout.addWidget(toolbar_frame)

        # 2. Report Document Viewer (QTextBrowser)
        self.browser = QTextBrowser()
        self.browser.setStyleSheet(
            "QTextBrowser { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 8px; padding: 8px 14px; }"
        )
        self.browser.setOpenExternalLinks(False)
        main_layout.addWidget(self.browser)

    def _generate_html(self) -> str:
        s = self.sale_data

        rows_html = ""
        total_qty = 0.0
        for idx, item in enumerate(s.get("Details", []), start=1):
            qty = item.get("Quantity", 0.0)
            rate = item.get("RatePer1000", 0.0)
            total = item.get("TotalAmount", 0.0)
            total_qty += qty

            rows_html += f"""
            <tr>
                <td width="8%" style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9pt; text-align: center;">{idx}</td>
                <td width="42%" style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9pt; font-weight: bold; color: #1E293B;">{item.get('ProductName', '')}</td>
                <td width="16%" style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9pt; text-align: right;">{qty:,.0f}</td>
                <td width="16%" style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9pt; text-align: right;">Rs. {rate:,.2f}</td>
                <td width="18%" style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9pt; text-align: right; font-weight: bold; color: #16A34A;">Rs. {total:,.2f}</td>
            </tr>
            """

        transport_str = s.get("TransportMode", "N/A") or "N/A"
        driver_str = s.get("DriverName", "N/A") or "N/A"
        vehicle_str = s.get("VehicleNumber", "")
        if vehicle_str:
            transport_str += f" ({vehicle_str})"

        remarks_str = s.get("Remarks", "") or "None"

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
                .header-card {{
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    padding: 12px 18px;
                    border-radius: 6px;
                    text-align: center;
                    margin-bottom: 6px;
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
                }}
                .info-table {{
                    width: 100%;
                    border: 1px solid #CBD5E1;
                    background-color: #F8FAFC;
                    margin-bottom: 12px;
                }}
                .info-table td {{
                    padding: 6px 10px;
                    font-size: 9.5pt;
                    vertical-align: top;
                }}
                .table-main th {{
                    background-color: #F1F5F9;
                    color: #0F172A;
                    font-weight: bold;
                    font-size: 9.5pt;
                    padding: 6px 8px;
                    border: 1px solid #CBD5E1;
                }}
                .total-box {{
                    background-color: #F0FDF4;
                    border: 2px solid #22C55E;
                    border-radius: 6px;
                    padding: 10px 14px;
                    text-align: right;
                    margin-top: 12px;
                }}
                .sig-box {{
                    margin-top: 36px;
                    width: 100%;
                }}
                .sig-box td {{
                    padding-top: 30px;
                    border-top: 1px dashed #94A3B8;
                    text-align: center;
                    font-weight: bold;
                    font-size: 9.5pt;
                    color: #475569;
                }}
            </style>
        </head>
        <body>
            <div class="header-card">
                <div style="font-size: 16pt; font-weight: 900; letter-spacing: 1px;">{COMPANY_NAME.upper()}</div>
                <div style="font-size: 9.5pt; color: #93C5FD; margin-top: 2px;">
                    {APP_SUBTITLE} &nbsp;|&nbsp; Owner Contact: <strong>0300-1234567</strong>
                </div>
            </div>

            <div class="yellow-badge">
                BRICK DELIVERY RECEIPT & SALES INVOICE (سیلز رسید)
            </div>

            <table class="info-table">
                <tr>
                    <td style="width: 50%;">
                        <strong>Invoice / Receipt #:</strong> <span style="font-weight: 900; color: #0284C7;">{s.get('InvoiceNo', '')}</span><br>
                        <strong>Sale Date:</strong> {s.get('SaleDate', '')}<br>
                        <strong>Customer Name:</strong> {s.get('CustomerName', '')} {f"({s.get('CustomerUrdu', '')})" if s.get('CustomerUrdu') else ""}<br>
                        <strong>Customer ID:</strong> {s.get('CustomerID', '')} &nbsp;|&nbsp; <strong>Mobile:</strong> {s.get('CustomerMobile', 'N/A')}
                    </td>
                    <td style="width: 50%;">
                        <strong>Transport Mode:</strong> {transport_str}<br>
                        <strong>Delivery Person / Driver:</strong> {driver_str}<br>
                        <strong>Remarks / Site:</strong> {remarks_str}<br>
                        <strong>Issued By:</strong> {s.get('CreatedBy', 'System')}
                    </td>
                </tr>
            </table>

            <table width="100%" class="table-main" style="border-collapse: collapse; margin-bottom: 8px;">
                <thead>
                    <tr>
                        <th width="8%">#</th>
                        <th width="42%" style="text-align: left;">Product Description</th>
                        <th width="16%" style="text-align: right;">Quantity</th>
                        <th width="16%" style="text-align: right;">Rate (/1000)</th>
                        <th width="18%" style="text-align: right;">Total Amount</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
                <tfoot>
                    <tr style="background-color: #F8FAFC; font-weight: bold;">
                        <td colspan="2" style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9.5pt; text-align: right;">Total Items & Quantity:</td>
                        <td style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9.5pt; text-align: right; color: #0F172A;">{total_qty:,.0f}</td>
                        <td style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 9.5pt; text-align: right;">Grand Total:</td>
                        <td style="padding: 6px 8px; border: 1px solid #CBD5E1; font-size: 10.5pt; text-align: right; color: #15803D; font-weight: 900;">Rs. {s.get('TotalAmount', 0.0):,.2f}</td>
                    </tr>
                </tfoot>
            </table>

            <div class="total-box">
                <span style="font-size: 11pt; font-weight: 800; color: #166534;">
                    NET PAYABLE AMOUNT: Rs. {s.get('TotalAmount', 0.0):,.2f}
                </span>
            </div>

            <table class="sig-box" style="margin-top: 40px;">
                <tr>
                    <td style="width: 40%;">Customer / Receiver Signature</td>
                    <td style="width: 20%;"></td>
                    <td style="width: 40%;">Munshi / Authorized Signature</td>
                </tr>
            </table>
        </body>
        </html>
        """
        return html

    def _render_receipt(self):
        html_content = self._generate_html()
        self.browser.setHtml(html_content)

    def _zoom_in(self):
        if self.zoom_level < 200:
            self.zoom_level += 15
            self.browser.zoomIn(1)
            self.lbl_zoom.setText(f"{self.zoom_level}%")

    def _zoom_out(self):
        if self.zoom_level > 60:
            self.zoom_level -= 15
            self.browser.zoomOut(1)
            self.lbl_zoom.setText(f"{self.zoom_level}%")

    def _on_print(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        page_layout = QPageLayout(
            QPageSize(QPageSize.PageSizeId.A4),
            QPageLayout.Orientation.Portrait,
            QPageLayout.Unit.Point
        )
        printer.setPageLayout(page_layout)

        print_dialog = QPrintDialog(printer, self)
        print_dialog.setWindowTitle("Print Sales Receipt")
        if print_dialog.exec() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setDefaultFont(QFont("Segoe UI", 9))
            doc.setPageSize(page_layout.paintRect(QPageLayout.Unit.Point).size())
            doc.setHtml(self._generate_html())
            doc.print_(printer)
            ToastNotification.success(self, "Sales receipt sent to printer successfully!")

    def _on_save_pdf(self):
        inv = self.sale_data.get("InvoiceNo", "Receipt")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sales Receipt as PDF",
            f"Sales_Receipt_{inv}.pdf",
            "PDF Files (*.pdf)"
        )
        if not path:
            return

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)

            page_layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                QPageLayout.Unit.Point
            )
            printer.setPageLayout(page_layout)

            doc = QTextDocument()
            doc.setDefaultFont(QFont("Segoe UI", 9))
            doc.setPageSize(page_layout.paintRect(QPageLayout.Unit.Point).size())
            doc.setHtml(self._generate_html())
            doc.print_(printer)

            ToastNotification.success(self, f"Sales Receipt PDF saved successfully:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error Saving PDF", f"Failed to generate PDF file:\n{str(e)}")

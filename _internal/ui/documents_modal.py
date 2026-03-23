# -*- coding: utf-8 -*-
"""
Documents Modal — A sleek dialog to generate and print documents for a specific employee.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QMessageBox, QTextEdit,
)
from PyQt5.QtCore import Qt, QSizeF
from PyQt5.QtGui import QTextDocument, QTextOption
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog

from ui.widgets import (
    ArabicLineEdit, ArabicDateEdit, ActionButton, ArabicFormLayout,
    PageHeader, Separator
)
from ui.print_header import get_document_header
import database as db

class PrintDocumentDialog(QDialog):
    """Dialog to configure and print a specific document for an employee."""

    def __init__(self, employee, doc_type, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.doc_type = doc_type
        
        self.setWindowTitle("طباعة الوثيقة: " + doc_type)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)

        emp_name = db.get_employee_full_name(self.employee)
        header = PageHeader(
            "إعداد وطباعة وثيقة", 
            f"الوثيقة: {self.doc_type} | الموظف: {emp_name}"
        )
        layout.addWidget(header)
        layout.addWidget(Separator())

        form = ArabicFormLayout()

        self.doc_number_input = ArabicLineEdit("رقم الوثيقة (اختياري)")
        form.addRow("الرقم:", self.doc_number_input)

        self.doc_date = ArabicDateEdit()
        form.addRow("تاريخ التحرير:", self.doc_date)

        self.reason_input = QTextEdit()
        self.reason_input.setLayoutDirection(Qt.RightToLeft)
        self.reason_input.setMaximumHeight(80)
        
        if self.doc_type in ["تنبيه", "استئناف عمل"]:
            self.reason_input.setPlaceholderText("سبب إضافي (مثال: انتهاء العطلة المرضية / سبب التنبيه)...")
            form.addRow("السبب / الملاحظة:", self.reason_input)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        preview_btn = ActionButton("معاينة وطباعة", "⎙", "primary")
        preview_btn.clicked.connect(self._preview_print)
        
        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)

    def _generate_html(self):
        emp = self.employee
        settings = db.get_all_settings()
        
        doc_number = self.doc_number_input.text().strip() or "........"
        doc_date = self.doc_date.date().toString("yyyy/MM/dd")
        reason = self.reason_input.toPlainText().strip()

        school = settings.get("school_name", "المؤسسة التعليمية")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")

        emp_dict = dict(emp)
        emp_name = db.get_employee_full_name(emp)
        emp_grade = emp_dict["grade"] or "ــــــ"
        emp_subject = emp_dict["subject"] or ""
        emp_degree = emp_dict["degree"] or ""
        effective_date = emp_dict.get("effective_date", "ــــ/ــ/ــ") or "ــــ/ــ/ــ"
        effective_date = effective_date.replace("-", "/")
        emp_fn = emp_dict.get("first_name", "") or ""
        emp_ln = emp_dict.get("last_name", "") or ""
        emp_bd = (emp_dict.get("birth_date", "") or "ــــ/ــ/ــ").replace("-", "/")
        emp_bp = ""

        subject_line = ""
        if emp_subject:
            subject_line = f"، مادة\u200f: <b>{emp_subject}</b>"

        # Header with institution logo
        header_html = get_document_header(settings, doc_number)

        # Body by type
        if self.doc_type == "شهادة عمل":
            body = f"""
            <h2 style="text-align:center; margin:10px 0; font-size:36px; font-weight:bold;">شـهـادة عمـل</h2>
            <br/><br/>
            <p style="font-size:18px; line-height:1.5; font-weight:bold;">
                يشهد السيد مدير {school} بأن السيد(ة) المذكور(ة) أسفله:
            </p>
            <table dir="rtl" style="font-size:18px; font-weight:bold; line-height:1.5; border: none; width: 100%;">
                <tr><td style="width: 150px; border: none;">الإسم</td><td style="width: 20px; border: none; text-align: center;">:</td><td style="border: none;">{emp_fn}</td></tr>
                <tr><td style="border: none;">اللقب</td><td style="border: none; text-align: center;">:</td><td style="border: none;">{emp_ln}</td></tr>
                <tr><td style="border: none;">تاريخ ومكان الميلاد</td><td style="border: none; text-align: center;">:</td><td style="border: none;">{emp_bd} {emp_bp}</td></tr>
                <tr><td style="border: none;">الوظيفة</td><td style="border: none; text-align: center;">:</td><td style="border: none;">{emp_grade} {emp_subject}</td></tr>
            </table>
            <br/>
            <p style="font-size:18px; line-height:1.5; font-weight:bold;">
                أنه يزاول عمله منذ {effective_date} إلى يومنا هذا.
            </p>
            <br/><br/>
            <p style="font-size:18px; line-height:1.5; font-weight:bold; text-align: center; margin-top: 30px;">
                سُلمت هذه الشهادة للعمل بها في حدود ما يقتضيه القانون.
            </p>
            """
        elif self.doc_type == "محضر تنصيب":
            body = f"""
            <h2 style="text-align:center; margin:20px 0;">محضر تنصيب</h2>
            <p style="font-size:14px; line-height:2;">
                نحن الممضون أسفله، مدير {school}، نشهد أن السيد(ة) المذكور(ة) أعلاه،
                <b>{emp_name}</b>، بصفته(ها) <b>{emp_grade}</b>{subject_line}،
                درجة <b>{emp_degree}</b>،
                قد التحق(ت) بمنصب عمله(ها) بمؤسستنا بتاريخ <b>{doc_date}</b>.<br/><br/>
                وقد حُرّر هذا المحضر لتقديمه للجهة المعنية.
            </p>
            """
        elif self.doc_type == "مقرر تعيين":
            body = f"""
            <h2 style="text-align:center; margin:20px 0;">مقرر تعيين</h2>
            <p style="font-size:14px; line-height:2;">
                بناءً على المرسوم التنفيذي المتعلق بتنظيم المؤسسات التعليمية،
                وبناءً على مقتضيات المصلحة،<br/>
                <b>يُعَيَّن</b> السيد(ة) <b>{emp_name}</b><br/>
                بصفة <b>{emp_grade}</b>{subject_line}<br/>
                درجة <b>{emp_degree}</b><br/>
                ابتداءً من تاريخ <b>{doc_date}</b>.
            </p>
            """
        elif self.doc_type == "استئناف عمل":
            reason_text = reason if reason else "/"
            body = f"""
            <h2 style="text-align:center; font-size: 45px; font-weight: bold; margin: 40px 0;">بـيـان اسـتـئـنـاف عـمـل</h2>
            <p style="font-size: 16px; font-weight: bold; text-align: right; margin-bottom: 20px;">
                إن مدير المؤسسة المذكور أسفله يفيد المعني (ة) والسلطات المختصة<br/>
                باستئناف العمل الوارد أدناه:
            </p>
            <table style="width: 100%; border-collapse: collapse; margin: 30px 0; border: 1px solid black;" dir="rtl">
                <tr>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold; width: 25%;">اللقب و الاسم</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold; width: 35%;">التخصص</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold; width: 40%;" colspan="2">مؤسسة العمل</th>
                </tr>
                <tr>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">{emp_name}</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">{emp_subject}</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;" colspan="2">{school}</td>
                </tr>
                <tr>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">الجنسية</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">الصفة</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">تاريخ الاستئناف</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">الملاحظة</th>
                </tr>
                <tr>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">جزائرية</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">{emp_grade}</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">{doc_date}</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">{reason_text}</td>
                </tr>
            </table>
            """
        elif self.doc_type == "تنبيه":
            reason_line = f"<br/><b>السبب:</b> {reason}" if reason else ""
            body = f"""
            <h2 style="text-align:center; margin:20px 0;">تنبيـــه</h2>
            <p style="font-size:14px; line-height:2;">
                إلى السيد(ة) <b>{emp_name}</b>، {emp_grade} بـ {school}.<br/><br/>
                يُنبه عليكم بضرورة الالتزام بالقوانين والتنظيمات المعمول بها.{reason_line}
            </p>
            <p style="font-size:14px; line-height:2;">
                وفي حالة تكرار المخالفة، سيتم اتخاذ الإجراءات القانونية اللازمة.
            </p>
            """
        else:
            body = f"<p>وثيقة غير معروفة: {self.doc_type}</p>"

        # Footer
        if self.doc_type == "استئناف عمل":
            footer = f"""
            <br/><br/>
            <table width="100%" dir="rtl" style="margin-top: 30px;">
                <tr>
                    <td style="text-align:right; width:50%;">
                        <div style="font-size:16px; font-weight: bold;">
                            إمضاء المعني (ة) بالأمر<br/><br/>
                            <span style="color:transparent;">إمضاء</span>
                        </div>
                    </td>
                    <td style="text-align:left; width:50%;">
                        <div style="font-size:16px; font-weight: bold;">
                            حرر بـ {wilaya} في {doc_date}<br/>
                            مدير المؤسسة<br/><br/><br/>
                        </div>
                    </td>
                </tr>
            </table>
            """
        else:
            footer = f"""
            <br/><br/>
            <table width="100%" dir="rtl" style="margin-top: 30px;">
                <tr>
                    <td style="text-align:left; width:50%;">
                        <div style="font-size:16px; font-weight:bold;">
                            {wilaya} في {doc_date}<br/>
                            المدير(ة)<br/><br/><br/>
                        </div>
                    </td>
                    <td style="text-align:right; width:50%;">
                        <div style="font-size:16px; font-weight:bold;">
                            إمضاء المعني(ة)<br/><br/><br/>
                        </div>
                    </td>
                </tr>
            </table>
            """

        body_margin = "0px"
        return f"""
        <html dir="rtl">
        <head><style>
            body {{ font-family: 'Amiri', 'Traditional Arabic', serif; direction: rtl; text-align: right; margin: {body_margin}; line-height: 1.8; }}
            h2 {{ color: #1a1a1a; }}
        </style></head>
        <body dir="rtl">{header_html} {body} {footer}</body></html>
        """

    def _preview_print(self):
        html = self._generate_html()
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self)
        dialog.exec_()

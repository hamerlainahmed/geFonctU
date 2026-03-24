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
from ui.print_header import get_document_header, get_document_footer
import database as db

class PrintDocumentDialog(QDialog):
    """Dialog to configure and print a specific document for an employee."""

    def __init__(self, employee, doc_type, parent=None, custom_settings=None):
        super().__init__(parent)
        self.employee = employee
        self.doc_type = doc_type
        self.custom_settings = custom_settings
        
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

        from PyQt5.QtGui import QIntValidator
        self.doc_number_input = ArabicLineEdit("رقم الوثيقة (أرقام فقط)")
        self.doc_number_input.setValidator(QIntValidator(1, 999999, self))
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
        settings = self.custom_settings if self.custom_settings else db.get_all_settings()
        doc_input = self.doc_number_input.text().strip()
        if doc_input.isdigit():
            doc_number = doc_input.zfill(3)
        else:
            doc_number = doc_input or "........"
            
        doc_date = self.doc_date.date().toString("yyyy/MM/dd")
        reason = self.reason_input.toPlainText().strip()

        school = settings.get("school_name", "المؤسسة التعليمية")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        school_address = settings.get("school_address", "......................")

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
        emp_end_date = (emp_dict.get("end_date", "") or "").replace("-", "/")

        subject_line = ""
        if emp_subject:
            subject_line = f"، مادة\u200f: <b>{emp_subject}</b>"

        # By default, use generic headers
        header_html = get_document_header(settings, doc_number)
        footer_html = get_document_footer(wilaya, doc_date, show_employee_signature=False)

        # Body by type
        if self.doc_type == "شهادة عمل":
            from ui.print_header import _get_school_initials
            from datetime import datetime
            school_initials = _get_school_initials(school)
            year = datetime.now().year
            doc_num_str = doc_number if doc_number else "............."

            school_display = school + " - " + school_address
            school_code = settings.get("school_code", "")
            if school_code:
                school_display += f"<br/>رمز المؤسسة: {school_code}"

            if "مستخلف" in emp_grade and emp_end_date:
                work_period_sentence = f"أنه زاول عمله من {effective_date} إلى {emp_end_date}."
            else:
                work_period_sentence = f"أنه يزاول عمله منذ {effective_date} إلى يومنا هذا."
            
            # COMPLETELY BYPASS DEFAULT HEADERS/FOOTERS/CSS for exact matching dimensions
            header_html = ""
            footer_html = ""
            
            body = f"""
            <style>
                body {{ margin: 2px !important; line-height: 0.9 !important; }}
                table {{ border-collapse: separate !important; width: 100% !important; }}
                td, th {{ border: none !important; padding: 0px !important; text-align: right; }}
            </style>
            
            <table width="100%" dir="rtl" style="font-size:18px; font-weight:bold; margin-top: 0px; margin-bottom: 2px;line-height: 0.8;">
                <tr >
                    <td align="center" width="100%" style="padding:0px; font-size: 18px; font-weight: bold; line-height: 0.8; text-align: center;">الجمهورية الجزائرية الديمقراطية الشعبية</td>
                </tr>
                 <tr >
                    <td align="center" width="100%" style="padding:0px; font-size: 16px; font-weight: bold; line-height: 0.8; text-align: center;">وزارة التربية الوطنية</td>
                </tr>
                 <tr>
                    <td align="right" width="100%" style="padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">مديرية التربية لولاية {wilaya}</td>
                </tr>
                 <tr>
                    <td align="right" width="100%" style="padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">{school_display}</td>
                </tr>
                  <tr style="line-height: 0.8;">
                    <td dir="rtl" style="line-height: 0.8;font-size: 14px;direction:rtl;text-align: left;">
                     <span style="unicode-bidi: bidi-override; direction: rtl;">الرقم: {doc_num_str}&rlm;/&rlm; {school_initials}&rlm;/&rlm; {year}</span>
                    </td>
                    </tr>
                <tr>
                <td style="font-size: 24px;font-weight: bold; text-align: center;" align="center" width="100%">شهادة عمــــل</td>
                </tr>
            </table>
          
            <table dir="rtl" width="100%" border="0" style="font-size:14px; font-weight:bold; line-height:0.9; margin-top: 2px;">
                <tr>
                <td align="right" colspan="3" style="font-size:16px;">يشهد السيد مدير {school} أن السيد(ة) المذكور(ة) أسفله:</td>
                </tr>
                <tr>
                <td align="right" width="75%" style="border: none;">{emp_fn}</td>
                <td align="right" width="20%" style="border: none;">الإسم:</td>
                <td width="5%" style="border: none;"> </td>
                </tr>
               <tr>
                <td align="right" width="75%" style="border: none;">{emp_ln}</td>
                <td align="right" width="20%" style="border: none;">اللقب:</td>
                <td width="5%" style="border: none;"> </td>
                </tr>
                <tr>
                <td align="right" width="75%" style="border: none;">{emp_bd} {emp_bp}</td>
                <td align="right" width="20%" style="border: none;">تاريخ ومكان الميلاد:</td>
                <td width="5%" style="border: none;"> </td>
                </tr>
                <tr>
                <td align="right" width="75%" style="border: none;">{emp_grade} مادة: {emp_subject}</td>
                <td align="right" width="20%" style="border: none;">الوظيفة:</td>
                <td width="5%" style="border: none;"> </td>
                </tr>
                <tr>
                <td align="center" colspan="3" style="font-size:18px;border: none;">{work_period_sentence}</td>
                </tr>
                 <tr>
                <td align="center" style="text-align: center; font-size:16px; line-height:1.0; font-weight:bold; margin-top: 5px;" colspan="3">سُلمت هذه الشهادة للعمل بها في حدود ما يقتضيه القانون.</td>
                </tr>
            </table>
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
                            حرر بـ {school_address} في {doc_date}<br/>
                            مدير المؤسسة<br/><br/><br/>
                        </div>
                    </td>
                </tr>
            </table>
            """
        else:
            footer = f"""
         
            <table width="100%" dir="rtl" style="margin-top: 1px;">
                <tr>
                    <td width="50%%" style="text-align:left; width:50%;">
                        <div align="center" style="font-size:16px; font-weight:bold;">
                            {school_address} في {doc_date}<br/>
                            المدير(ة)
                        </div>
                    </td>
                    <td width="50%%"></td>
                </tr>
            </table>
            """

        body_margin = "0px"
        return f"""
        <html dir="rtl">
        <head><style>
            body {{ font-family: 'Amiri', 'Traditional Arabic', serif; direction: rtl; text-align: right; margin: {body_margin}; line-height: 0.9; }}
            h2 {{ color: #1a1a1a; }}
        </style></head>
        <body dir="rtl">{header_html} {body} {footer}</body></html>
        """

    def _preview_print(self):
        html = self._generate_html()
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self)
        dialog.exec_()

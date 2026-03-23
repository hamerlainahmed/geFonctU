# -*- coding: utf-8 -*-
"""
Documents Page — Generate and print official Arabic administrative documents.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QDialog, QMessageBox, QLabel, QTextEdit, QSizePolicy,
    QGroupBox,
)
from PyQt5.QtCore import Qt, QDate, QSizeF
from PyQt5.QtGui import QFont, QTextDocument, QTextOption
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog

from ui.widgets import (
    ArabicLabel, ArabicComboBox, ArabicDateEdit, ArabicLineEdit,
    Card, ActionButton, ArabicFormLayout, Separator, PageHeader,
)
from ui.print_header import get_document_header
import database as db

DOC_TYPES = [
    "شهادة عمل",
    "محضر تنصيب",
    "مقرر تعيين",
    "استئناف عمل",
    "تنبيه",
]


class DocumentsPage(QWidget):
    """Page for generating official Arabic administrative documents."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        header = PageHeader("إنشاء الوثائق الإدارية", "اختيار الموظف ونوع الوثيقة ثم معاينة وطباعة")
        layout.addWidget(header)

        # Split: Controls on the right, Preview on the left
        split = QHBoxLayout()
        split.setSpacing(20)

        # Controls
        controls_card = Card()
        controls_layout = QVBoxLayout(controls_card)
        controls_layout.setSpacing(12)

        form = ArabicFormLayout()

        self.employee_combo = ArabicComboBox()
        self.employee_combo.currentIndexChanged.connect(self._update_preview)
        form.addRow("الموظف:", self.employee_combo)

        self.doc_type_combo = ArabicComboBox()
        self.doc_type_combo.addItems(DOC_TYPES)
        self.doc_type_combo.currentTextChanged.connect(self._update_preview)
        form.addRow("نوع الوثيقة:", self.doc_type_combo)

        self.doc_number_input = ArabicLineEdit("رقم الوثيقة")
        self.doc_number_input.textChanged.connect(self._update_preview)
        form.addRow("رقم الوثيقة:", self.doc_number_input)

        self.doc_date = ArabicDateEdit()
        self.doc_date.dateChanged.connect(self._update_preview)
        form.addRow("التاريخ:", self.doc_date)

        self.reason_input = QTextEdit()
        self.reason_input.setLayoutDirection(Qt.RightToLeft)
        self.reason_input.setMaximumHeight(80)
        self.reason_input.setPlaceholderText("سبب إضافي أو ملاحظات...")
        self.reason_input.textChanged.connect(self._update_preview)
        form.addRow("ملاحظات:", self.reason_input)

        controls_layout.addLayout(form)

        # Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        preview_btn = ActionButton("معاينة وطباعة", "⎙", "primary")
        preview_btn.clicked.connect(self._preview_print)
        btn_layout.addWidget(preview_btn)

        save_btn = ActionButton("حفظ في السجل", "✔", "success")
        save_btn.clicked.connect(self._save_document)
        btn_layout.addWidget(save_btn)

        controls_layout.addLayout(btn_layout)

        split.addWidget(controls_card, stretch=1)

        # Preview area
        preview_panel = QVBoxLayout()
        preview_title = ArabicLabel("معاينة الوثيقة", object_name="section_title")
        preview_panel.addWidget(preview_title)

        self.preview_area = QTextEdit()
        self.preview_area.setLayoutDirection(Qt.RightToLeft)
        self.preview_area.setReadOnly(True)
        self.preview_area.setMinimumHeight(400)
        self.preview_area.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #1a1a1a;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
                padding: 24px;
                font-family: 'Amiri', 'Traditional Arabic';
                font-size: 14px;
            }
        """)
        preview_panel.addWidget(self.preview_area)
        split.addLayout(preview_panel, stretch=2)

        layout.addLayout(split, stretch=1)

        self._load_employees()
        self._update_preview()

    def _load_employees(self):
        self.employee_combo.clear()
        self.employees = db.get_all_employees()
        for emp in self.employees:
            full_name = db.get_employee_full_name(emp)
            grade = emp["grade"] or ""
            self.employee_combo.addItem("%s — %s" % (full_name, grade), emp["id"])

    def _get_selected_employee(self):
        idx = self.employee_combo.currentIndex()
        if idx < 0 or idx >= len(self.employees):
            return None
        emp_id = self.employee_combo.currentData()
        return db.get_employee(emp_id)

    def _get_settings(self):
        return db.get_all_settings()

    def _update_preview(self, *args):
        html = self._generate_html()
        self.preview_area.setHtml(html)

    def _generate_html(self):
        emp = self._get_selected_employee()
        settings = self._get_settings()
        doc_type = self.doc_type_combo.currentText()
        doc_number = self.doc_number_input.text().strip() or "........"
        doc_date = self.doc_date.date().toString("yyyy/MM/dd")
        reason = self.reason_input.toPlainText().strip()

        school = settings.get("school_name", "المؤسسة التعليمية")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")

        if emp:
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
        else:
            emp_name = "ــــــــــــــ"
            emp_grade = "ــــــ"
            emp_subject = ""
            emp_degree = ""
            effective_date = "ــــ/ــ/ــ"
            emp_fn = ""
            emp_ln = ""
            emp_bd = "ــــ/ــ/ــ"
            emp_bp = ""

        subject_line = ""
        if emp_subject:
            subject_line = "، مادة: <b>%s</b>" % emp_subject

        # Header with institution logo
        header_html = get_document_header(settings, doc_number)

        # Body by type
        if doc_type == "شهادة عمل":
            body = """
            <h2 style="text-align:center; margin:10px 0; font-size:36px; font-weight:bold;">شـهـادة عمـل</h2>
            <br/><br/>
            <p style="font-size:18px; line-height:1.5; font-weight:bold;">
                يشهد السيد مدير %(school)s بأن السيد(ة) المذكور(ة) أسفله:
            </p>
            <table dir="rtl" style="font-size:18px; font-weight:bold; line-height:1.5; border: none; width: 100%%;">
                <tr><td style="width: 150px; border: none;">الإسم</td><td style="width: 20px; border: none; text-align: center;">:</td><td style="border: none;">%(first_name)s</td></tr>
                <tr><td style="border: none;">اللقب</td><td style="border: none; text-align: center;">:</td><td style="border: none;">%(last_name)s</td></tr>
                <tr><td style="border: none;">تاريخ ومكان الميلاد</td><td style="border: none; text-align: center;">:</td><td style="border: none;">%(birth_date)s %(birth_place)s</td></tr>
                <tr><td style="border: none;">الوظيفة</td><td style="border: none; text-align: center;">:</td><td style="border: none;">%(grade)s %(subject)s</td></tr>
            </table>
            <br/>
            <p style="font-size:18px; line-height:1.5; font-weight:bold;">
                أنه يزاول عمله منذ %(effective_date)s إلى يومنا هذا.
            </p>
            <br/><br/>
            <p style="font-size:18px; line-height:1.5; font-weight:bold; text-align: center; margin-top: 30px;">
                سُلمت هذه الشهادة للعمل بها في حدود ما يقتضيه القانون.
            </p>
            """ % {"school": school, "first_name": emp_fn, "last_name": emp_ln,
                   "birth_date": emp_bd, "birth_place": emp_bp, "grade": emp_grade,
                   "subject": emp_subject, "effective_date": effective_date}

        elif doc_type == "محضر تنصيب":
            body = """
            <h2 style="text-align:center; margin:20px 0;">محضر تنصيب</h2>
            <p style="font-size:14px; line-height:2;">
                نحن الممضون أسفله، مدير %(school)s، نشهد أن السيد(ة) المذكور(ة) أعلاه،
                <b>%(name)s</b>، بصفته(ها) <b>%(grade)s</b>%(subject)s،
                درجة <b>%(degree)s</b>،
                قد التحق(ت) بمنصب عمله(ها) بمؤسستنا بتاريخ <b>%(date)s</b>.<br/><br/>
                وقد حُرّر هذا المحضر لتقديمه للجهة المعنية.
            </p>
            """ % {"school": school, "name": emp_name, "grade": emp_grade,
                   "subject": subject_line, "degree": emp_degree, "date": doc_date}

        elif doc_type == "مقرر تعيين":
            body = """
            <h2 style="text-align:center; margin:20px 0;">مقرر تعيين</h2>
            <p style="font-size:14px; line-height:2;">
                بناءً على المرسوم التنفيذي المتعلق بتنظيم المؤسسات التعليمية،
                وبناءً على مقتضيات المصلحة،<br/>
                <b>يُعيَّن</b> السيد(ة) <b>%(name)s</b><br/>
                بصفة <b>%(grade)s</b>%(subject)s<br/>
                درجة <b>%(degree)s</b><br/>
                ابتداءً من تاريخ <b>%(date)s</b>.
            </p>
            """ % {"name": emp_name, "grade": emp_grade,
                   "subject": subject_line, "degree": emp_degree, "date": doc_date}

        elif doc_type == "استئناف عمل":
            reason_text = reason if reason else "/"
            body = """
            <h2 style="text-align:center; font-size: 45px; font-weight: bold; margin: 40px 0;">بـيـان اسـتـئـنـاف عـمـل</h2>
            <p style="font-size: 16px; font-weight: bold; text-align: right; margin-bottom: 20px;">
                إن مدير المؤسسة المذكور أسفله يفيد المعني (ة) والسلطات المختصة<br/>
                باستئناف العمل الوارد أدناه:
            </p>
            <table style="width: 100%%; border-collapse: collapse; margin: 30px 0; border: 1px solid black;" dir="rtl">
                <tr>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold; width: 25%%;">اللقب و الاسم</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold; width: 35%%;">التخصص</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold; width: 40%%;" colspan="2">مؤسسة العمل</th>
                </tr>
                <tr>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">%(name)s</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">%(subject_line)s</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;" colspan="2">%(school)s</td>
                </tr>
                <tr>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">الجنسية</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">الصفة</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">تاريخ الاستئناف</th>
                    <th style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">الملاحظة</th>
                </tr>
                <tr>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">جزائرية</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">%(grade)s</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">%(date)s</td>
                    <td style="border: 1px solid black; padding: 12px; text-align: center; font-size: 16px; font-weight: bold;">%(reason)s</td>
                </tr>
            </table>
            """ % {"school": school, "name": emp_name, "grade": emp_grade,
                   "subject_line": emp_subject, "date": doc_date, "reason": reason_text}

        elif doc_type == "تنبيه":
            reason_line = ""
            if reason:
                reason_line = "<br/><b>السبب:</b> %s" % reason
            body = """
            <h2 style="text-align:center; margin:20px 0;">تنبيـــه</h2>
            <p style="font-size:14px; line-height:2;">
                إلى السيد(ة) <b>%(name)s</b>، %(grade)s بـ %(school)s.<br/><br/>
                يُنبه عليكم بضرورة الالتزام بالقوانين والتنظيمات المعمول بها.%(reason)s
            </p>
            <p style="font-size:14px; line-height:2;">
                وفي حالة تكرار المخالفة، سيتم اتخاذ الإجراءات القانونية اللازمة.
            </p>
            """ % {"name": emp_name, "grade": emp_grade, "school": school, "reason": reason_line}
        else:
            body = "<p>يرجى اختيار نوع الوثيقة.</p>"

        # Footer
        from datetime import datetime
        if doc_type == "استئناف عمل":
            footer = """
            <br/><br/>
            <table width="100%%" dir="rtl" style="margin-top: 30px;">
                <tr>
                    <td style="text-align:right; width:50%%;">
                        <div style="font-size:16px; font-weight: bold;">
                            إمضاء المعني (ة) بالأمر<br/><br/>
                            <span style="color:transparent;">إمضاء</span>
                        </div>
                    </td>
                    <td style="text-align:left; width:50%%;">
                        <div style="font-size:16px; font-weight: bold;">
                            حرر بـ %(wilaya)s في %(date)s<br/>
                            مدير المؤسسة<br/><br/><br/>
                        </div>
                    </td>
                </tr>
            </table>
            """ % {"date": doc_date, "wilaya": wilaya}
        else:
            footer = """
            <br/><br/>
            <table width="100%%" dir="rtl" style="margin-top: 30px;">
                <tr>
                    <td style="text-align:left; width:50%%;">
                        <div style="font-size:16px; font-weight:bold;">
                            %(wilaya)s في %(date)s<br/>
                            المدير(ة)<br/><br/><br/>
                        </div>
                    </td>
                    <td style="text-align:right; width:50%%;">
                        <div style="font-size:16px; font-weight:bold;">
                            إمضاء المعني(ة)<br/><br/><br/>
                        </div>
                    </td>
                </tr>
            </table>
            """ % {"date": doc_date, "wilaya": wilaya}

        body_margin = "0px"
        return """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right;
                   margin: %s; line-height: 1.8; }
            h2 { color: #1a1a1a; }
        </style></head>
        <body dir="rtl">%s %s %s</body></html>
        """ % (body_margin, header_html, body, footer)

    def _preview_print(self):
        emp = self._get_selected_employee()
        if not emp:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف أولاً")
            return

        html = self._generate_html()
        
        # استدعاء نظام المعاينة والطباعة الجديد (RTL)
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self)
        dialog.exec_()

    def _save_document(self):
        emp = self._get_selected_employee()
        if not emp:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف أولاً")
            return

        data = {
            "employee_id": emp["id"],
            "doc_type": self.doc_type_combo.currentText(),
            "doc_number": self.doc_number_input.text().strip(),
            "doc_date": self.doc_date.date().toString("yyyy-MM-dd"),
            "content": self._generate_html(),
        }
        db.add_document(data)
        QMessageBox.information(self, "نجاح", "✅ تم حفظ الوثيقة بنجاح")

    def refresh(self):
        self._load_employees()
        self._update_preview()

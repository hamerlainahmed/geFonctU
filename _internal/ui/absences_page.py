# -*- coding: utf-8 -*-
"""
Absence & Delay Management Page — Record, track, and report.
Stats moved to sidebar. This page focuses on the table and tabs.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QLabel, QGroupBox, QSpacerItem, QSizePolicy, QTextEdit, QTabWidget,
    QComboBox, QSpinBox, QMenu, QPushButton
)
from PyQt5.QtCore import Qt, QDate, QSizeF
from PyQt5.QtGui import QFont, QTextDocument, QTextOption
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog

from ui.widgets import (
    ArabicLineEdit, ArabicLabel, ArabicComboBox, ArabicDateEdit,
    Card, SearchBar, ActionButton, ArabicFormLayout, Separator,
    PageHeader,
)
import database as db
from datetime import datetime


class RecordAbsenceDialog(QDialog):
    """Dialog for recording an absence or delay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تسجيل غياب / تأخر")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QLabel("تسجيل غياب أو تأخر ⏰")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(header)

        form = ArabicFormLayout()

        self.employee_combo = ArabicComboBox()
        self._load_employees()
        form.addRow("الموظف:", self.employee_combo)

        self.type_combo = ArabicComboBox()
        self.type_combo.addItems(["غياب", "تأخر"])
        form.addRow("النوع:", self.type_combo)

        self.date_input = ArabicDateEdit()
        form.addRow("التاريخ:", self.date_input)

        self.time_input = ArabicLineEdit("مثال: 08:30")
        form.addRow("الوقت (اختياري):", self.time_input)

        self.duration_input = ArabicLineEdit("مثال: يوم كامل، ساعتان")
        form.addRow("المدة:", self.duration_input)

        self.notes_input = QTextEdit()
        self.notes_input.setLayoutDirection(Qt.RightToLeft)
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("ملاحظات إضافية...")
        form.addRow("ملاحظات:", self.notes_input)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        save_btn = ActionButton("تسجيل", "✔", "success")
        save_btn.clicked.connect(self._save)
        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _load_employees(self):
        self.employees = db.get_all_employees()
        for emp in self.employees:
            full_name = db.get_employee_full_name(emp)
            grade = emp["grade"] or ""
            self.employee_combo.addItem("%s — %s" % (full_name, grade), emp["id"])

    def _save(self):
        if self.employee_combo.currentIndex() < 0:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف")
            return
        self.accept()

    def get_data(self):
        return {
            "employee_id": self.employee_combo.currentData(),
            "absence_type": self.type_combo.currentText(),
            "absence_date": self.date_input.date().toString("yyyy-MM-dd"),
            "absence_time": self.time_input.text().strip(),
            "duration": self.duration_input.text().strip(),
            "is_justified": 0,
            "justification": "",
            "director_decision": "",
            "salary_deduction": "",
            "performance_deduction": "",
            "notes": self.notes_input.toPlainText().strip(),
        }



class AbsencesPage(QWidget):
    """Absence & delay management page — table-focused, stats in sidebar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 12)

        # Header row
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        
        header = QLabel("الغيابات والتأخرات 📋")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        header_row.addWidget(header)
        header_row.addStretch()

        new_btn = ActionButton("تسجيل غياب / تأخر", "📝", "primary")
        new_btn.setMinimumHeight(40)
        new_btn.clicked.connect(self._record_absence)
        header_row.addWidget(new_btn, alignment=Qt.AlignTop)
        layout.addLayout(header_row)

        # Tabs — take all remaining space
        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.RightToLeft)

        # Tab 1: All absences
        self.all_tab = QWidget()
        all_layout = QVBoxLayout(self.all_tab)
        all_layout.setContentsMargins(8, 10, 8, 8)
        all_layout.setSpacing(8)

        # Filters row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.filter_employee = ArabicComboBox()
        self.filter_employee.addItem("جميع الموظفين", None)
        employees = db.get_all_employees()
        for emp in employees:
            self.filter_employee.addItem(
                db.get_employee_full_name(emp), emp["id"]
            )
        self.filter_employee.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(QLabel("الموظف:"))
        filter_row.addWidget(self.filter_employee)

        self.filter_start = ArabicDateEdit()
        self.filter_start.setDate(QDate.currentDate().addMonths(-1))
        self.filter_start.dateChanged.connect(self._apply_filter)
        filter_row.addWidget(QLabel("من:"))
        filter_row.addWidget(self.filter_start)

        self.filter_end = ArabicDateEdit()
        self.filter_end.dateChanged.connect(self._apply_filter)
        filter_row.addWidget(QLabel("إلى:"))
        filter_row.addWidget(self.filter_end)

        filter_row.addStretch()
        all_layout.addLayout(filter_row)

        self.absences_table = QTableWidget()
        self.absences_table.setLayoutDirection(Qt.RightToLeft)
        self.absences_table.setColumnCount(8)
        self.absences_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "النوع", "التاريخ",
            "المدة", "الحالة", "القرار", "إجراءات"
        ])
        self.absences_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.absences_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.absences_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.absences_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.absences_table.setAlternatingRowColors(True)
        self.absences_table.verticalHeader().setVisible(False)
        self.absences_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.absences_table.setShowGrid(False)
        self.absences_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        all_layout.addWidget(self.absences_table, stretch=1)

        self.tabs.addTab(self.all_tab, "📋  سجل الغيابات")

        # Tab 2: Monthly statistics
        self.stats_tab = QWidget()
        stats_tab_layout = QVBoxLayout(self.stats_tab)
        stats_tab_layout.setContentsMargins(8, 10, 8, 8)
        stats_tab_layout.setSpacing(8)

        month_row = QHBoxLayout()
        month_row.setSpacing(8)

        self.month_combo = ArabicComboBox()
        months = ["جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
                   "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]
        for i, m in enumerate(months):
            self.month_combo.addItem(m, i + 1)
        current_month = QDate.currentDate().month()
        self.month_combo.setCurrentIndex(current_month - 1)
        self.month_combo.currentIndexChanged.connect(self._refresh_monthly_stats)
        month_row.addWidget(QLabel("الشهر:"))
        month_row.addWidget(self.month_combo)

        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2040)
        self.year_spin.setValue(QDate.currentDate().year())
        self.year_spin.valueChanged.connect(self._refresh_monthly_stats)
        month_row.addWidget(QLabel("السنة:"))
        month_row.addWidget(self.year_spin)

        month_row.addStretch()
        
        print_stats_btn = ActionButton("طباعة الإحصائيات", "🖨️", "primary")
        print_stats_btn.clicked.connect(self._print_monthly_stats)
        month_row.addWidget(print_stats_btn)

        stats_tab_layout.addLayout(month_row)

        self.monthly_table = QTableWidget()
        self.monthly_table.setLayoutDirection(Qt.RightToLeft)
        self.monthly_table.setColumnCount(6)
        self.monthly_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "عدد الغيابات", "عدد التأخرات",
            "المبررة", "غير المبررة"
        ])
        self.monthly_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.monthly_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.monthly_table.setAlternatingRowColors(True)
        self.monthly_table.verticalHeader().setVisible(False)
        self.monthly_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.monthly_table.setShowGrid(False)
        self.monthly_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        stats_tab_layout.addWidget(self.monthly_table, stretch=1)

        self.tabs.addTab(self.stats_tab, "📊  الإحصائيات الشهرية")

        layout.addWidget(self.tabs, stretch=1)

    def _record_absence(self):
        dialog = RecordAbsenceDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            abs_id = db.add_absence(data)

            # Automatically insert a corresponding inquiry
            reason = data["absence_type"]
            date_str = data["absence_date"]
            time_str = data["absence_time"]
            duration = data["duration"] or "غير محدد"
            if reason == "غياب":
                details = "غياب بتاريخ: %s، المدة: %s" % (date_str, duration)
            else:
                if time_str:
                    details = "تأخر بتاريخ: %s، الوقت: %s، المدة: %s" % (date_str, time_str, duration)
                else:
                    details = "تأخر بتاريخ: %s، المدة: %s" % (date_str, duration)

            inquiry_data = {
                "employee_id": data["employee_id"],
                "inquiry_type": reason,
                "inquiry_date": datetime.now().strftime("%Y-%m-%d"),
                "inquiry_time": datetime.now().strftime("%H:%M"),
                "details": details,
                "additional_notes": data["notes"],
                "status": "معلّق",
            }
            inq_id = db.add_inquiry(inquiry_data)

            QMessageBox.information(self, "نجاح", "✅ تم تسجيل %s وإنشاء استفسار بنجاح" % data["absence_type"])
            self.refresh()
            self._print_inquiry(inq_id)

    def _apply_filter(self):
        self._refresh_absences()



    def _print_inquiry(self, inq_id):
        """Print inquiry using the official shared template (2×A5 on A4 landscape)."""
        inquiry = db.get_inquiry(inq_id)
        if not inquiry:
            return
        emp = db.get_employee(inquiry["employee_id"])
        if not emp:
            return

        settings = db.get_all_settings()
        from ui.inquiries_page import InquiriesPage
        html = InquiriesPage._generate_inquiry_html(None, inquiry, emp, settings)

        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=True)
        dialog.exec_()



    def _print_salary_deduction(self, abs_id):
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code

        subject_line = ""
        if "subject" in emp.keys() and emp["subject"]:
            subject_line = "، مادة: <b>%s</b>" % emp["subject"]

        reason = absence["absence_type"]
        date_str = absence["absence_date"]
        duration = absence["duration"] or "غير محدد"
        time_str = absence["absence_time"]
        
        if reason == "غياب":
            reason_details = "غياب بتاريخ: %s، المدة: %s" % (date_str, duration)
            reason_paragraph = """
                <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right; text-indent: 40px;">
                    نعلمكم أنه بناء على سجل الحضور بالمؤسسة الأستاذ(ة) : <b>%(en)s</b>، 
                    بصفته(ها): <b>%(eg)s</b>%(sl)s،
                    تغيب(ت) عن منصب عمله(ها) <b>%(rd)s</b>
                    بدون مبرر مقبول ولا إذن مسبق.
                </p>
            """ % {"en": emp_name, "eg": emp["grade"] or "", "sl": subject_line, "rd": reason_details}
        else: # تأخر
            if time_str:
                reason_details = "تأخر بتاريخ: %s، الوقت: %s، المدة: %s" % (date_str, time_str, duration)
            else:
                reason_details = "تأخر بتاريخ: %s، المدة: %s" % (date_str, duration)
            
            reason_paragraph = """
                <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right; text-indent: 40px;">
                    نعلمكم أنه بناء على سجل الحضور بالمؤسسة الأستاذ(ة) : <b>%(en)s</b>، 
                    بصفته(ها): <b>%(eg)s</b>%(sl)s،
                    المعني(ة) بالأمر قد تأخر(ت) عن الالتحاق بمنصب عمله(ها)، <b>%(rd)s</b>.
                </p>
            """ % {"en": emp_name, "eg": emp["grade"] or "", "sl": subject_line, "rd": reason_details}

        notes = absence["notes"]
        additional_line = ("<br/>ملاحظة: <b>%s</b>" % notes) if notes else ""

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px; line-height: 1.8; }
            h2 { text-align: center; color: #000; margin: 20px 0; font-weight: bold; }
        </style></head>
        <body dir="rtl">
            <div style="text-align:center; margin-bottom: 8px; font-weight: bold;">
                <div style="font-size:16px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="font-size:14px;">وزارة التربية الوطنية</div>
            </div>
            <table dir="rtl" width="100%%%%" style="font-weight: bold; font-size: 14px; margin-bottom: 10px;">
                <tr>
                    <td style="text-align:right; width:50%%%%;">
                        مديرية التربية لولاية %(wilaya)s<br/>%(school_display)s
                    </td>
                    <td style="text-align:left; width:50%%%%;">
                        السنة الدراسية: %(school_year)s
                    </td>
                </tr>
            </table>
            <hr style="border:1px solid #333;"/>
            <h2 style="font-size: 28px; text-decoration: underline;">اسـتـفـسـار</h2>
            <table dir="rtl" width="100%%%%" style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">
                <tr>
                    <td style="text-align:right; width:100%%%%;">
                        إلى السيد(ة): <b>%(emp_name)s</b><br/>
                        الرتبة: <b>%(emp_grade)s</b>%(subject_line)s<br/>
                        بمؤسسة: <b>%(school)s</b>
                    </td>
                </tr>
            </table>
            <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right;">
                <u>الموضوع:</u> استفسار بسبب <b>%(reason)s</b>
            </p>
            %(reason_paragraph)s
            <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right; text-indent: 40px;">
                لذلك نطلب منكم تقديم تبريراتكم وتوضيحاتكم كتابياً
                في أجل أقصاه <b>48 ساعة</b> من تاريخ استلام هذا الاستفسار.%(additional_line)s
            </p>
            <p style="font-size:14px; line-height:2; font-weight:bold; text-align: right; margin-top: 20px;">
                ⚠️ نذكركم بأن عدم الرد في الآجال المحددة يعتبر قبولاً للمخالفة المنسوبة إليكم.
            </p>
            <br/><br/>
            <table width="100%%%%" dir="rtl" style="margin-top: 20px;">
                <tr>
                    <td style="text-align:left; width:50%%%%;">
                        <div style="font-size:16px; font-weight:bold;">
                            %(wilaya)s في: %(today)s<br/>المدير(ة)<br/><br/><br/><b>%(director)s</b>
                        </div>
                    </td>
                    <td style="text-align:right; width:50%%%%;">
                        <div style="font-size:16px; font-weight:bold;">
                            إمضاء المعني(ة) بالأمر<br/><br/><br/>
                        </div>
                    </td>
                </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "school_year": school_year,
            "emp_name": emp_name, "emp_grade": emp["grade"] or "", "subject_line": subject_line,
            "reason": reason, "reason_paragraph": reason_paragraph,
            "additional_line": additional_line, "today": today, "director": director,
        }
        self._show_print_preview(html)


    def _print_salary_deduction(self, abs_id):
        absence = db.get_absence(abs_id)
        if not absence:
            return
        emp = db.get_employee(absence["employee_id"])
        if not emp:
            return

        if not absence["salary_deduction"] and not absence["performance_deduction"]:
            QMessageBox.warning(self, "تنبيه", "لا يوجد قرار خصم. يرجى إدخال قرار المدير أولاً.")
            return

        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        emp_name = db.get_employee_full_name(emp)
        today = datetime.now().strftime("%Y/%m/%d")

        school_display = school
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code

        deduction_lines = ""
        if absence["salary_deduction"]:
            deduction_lines += "<b>خصم من الراتب:</b> %s<br/>" % absence["salary_deduction"]
        if absence["performance_deduction"]:
            deduction_lines += "<b>خصم من المردودية:</b> %s<br/>" % absence["performance_deduction"]

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px; line-height: 2; }
            h2 { text-align: center; color: #1a1a1a; margin: 24px 0; }
        </style></head>
        <body dir="rtl">
            <div style="text-align:center; margin-bottom: 8px;">
                <div style="font-size:13px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="font-size:12px;">وزارة التربية الوطنية</div>
            </div>
            <table width="100%%" dir="rtl"><tr>
                <td style="text-align:right; width:50%%; font-size:12px;">
                    مديرية التربية لولاية: %(wilaya)s<br/>%(school_display)s
                </td>
                <td style="text-align:left; width:50%%; font-size:12px;">
                    السنة الدراسية: %(school_year)s
                </td>
            </tr></table>
            <hr style="border:1px solid #333;"/>

            <h2>قرار خصم من الراتب / المردودية</h2>

            <p style="font-size:14px;">
                بناءً على القوانين والتنظيمات المعمول بها،<br/>
                وبناءً على %(absence_type)s السيد(ة): <b>%(emp_name)s</b>،
                <b>%(emp_grade)s</b>، بتاريخ: <b>%(absence_date)s</b><br/><br/>

                <b>قرار المدير:</b> %(decision)s<br/><br/>

                %(deduction_lines)s
            </p>

            <br/><br/>
            <table width="100%%" dir="rtl"><tr>
                <td style="text-align:left; width:50%%;">
                    <div style="font-size:12px;">
                        حُرّر بتاريخ: %(today)s<br/>
                        المدير(ة)<br/><br/><br/><b>%(director)s</b>
                    </div>
                </td>
            </tr></table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "school_year": school_year,
            "emp_name": emp_name, "emp_grade": emp["grade"] or "",
            "absence_type": absence["absence_type"],
            "absence_date": absence["absence_date"],
            "decision": absence["director_decision"] or "—",
            "deduction_lines": deduction_lines,
            "today": today, "director": director,
        }
        self._show_print_preview(html)

    def _print_warning(self, abs_id):
        absence = db.get_absence(abs_id)
        if not absence:
            return
        emp = db.get_employee(absence["employee_id"])
        if not emp:
            return

        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        emp_name = db.get_employee_full_name(emp)
        today = datetime.now().strftime("%Y/%m/%d")

        school_display = school
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code

        reason = ""
        if absence["director_decision"]:
            reason = "<br/><b>السبب:</b> %s" % absence["director_decision"]

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px; line-height: 2; }
            h2 { text-align: center; color: #1a1a1a; margin: 24px 0; }
        </style></head>
        <body dir="rtl">
            <div style="text-align:center; margin-bottom: 8px;">
                <div style="font-size:13px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="font-size:12px;">وزارة التربية الوطنية</div>
            </div>
            <table width="100%%" dir="rtl"><tr>
                <td style="text-align:right; width:50%%; font-size:12px;">
                    مديرية التربية لولاية: %(wilaya)s<br/>%(school_display)s
                </td>
                <td style="text-align:left; width:50%%; font-size:12px;">
                    السنة الدراسية: %(school_year)s
                </td>
            </tr></table>
            <hr style="border:1px solid #333;"/>

            <h2>تنبيـــه</h2>

            <p style="font-size:14px;">
                إلى السيد(ة): <b>%(emp_name)s</b><br/>
                <b>%(emp_grade)s</b> بـ %(school)s<br/><br/>

                يُنبه عليكم بضرورة الالتزام بالقوانين والتنظيمات المعمول بها
                والقيام بواجباتكم المهنية على أكمل وجه.%(reason)s<br/><br/>

                وفي حالة تكرار المخالفة، سيتم اتخاذ الإجراءات القانونية والتأديبية اللازمة
                طبقا للتنظيم المعمول به.
            </p>

            <br/><br/>
            <table width="100%%" dir="rtl"><tr>
                <td style="text-align:left; width:50%%;">
                    <div style="font-size:12px;">
                        حُرّر بتاريخ: %(today)s<br/>
                        المدير(ة)<br/><br/><br/><b>%(director)s</b>
                    </div>
                </td>
                <td style="text-align:right; width:50%%;">
                    <div style="font-size:12px;">
                        إمضاء المعني(ة)<br/><br/><br/><b>%(emp_name)s</b>
                    </div>
                </td>
            </tr></table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "school_year": school_year,
            "emp_name": emp_name, "emp_grade": emp["grade"] or "",
            "reason": reason,
            "today": today, "director": director,
        }
        self._show_print_preview(html)

    def _show_print_preview(self, html):
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self)
        dialog.exec_()

    def _delete_absence(self, abs_id):
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            "هل أنت متأكد من حذف هذا السجل نهائياً؟\nسيتم حذفه من سجل الغيابات.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_absence(abs_id)
            QMessageBox.information(self, "نجاح", "تم حذف السجل بنجاح.")
            self.refresh()

    def refresh(self):
        self._refresh_absences()
        self._refresh_monthly_stats()

    def get_stats(self):
        """Return stats dict for sidebar display."""
        stats = db.get_absence_stats()
        return {
            "total": stats.get("total", 0),
            "absences": stats.get("absences", 0),
            "delays": stats.get("delays", 0),
            "unjustified": stats.get("unjustified", 0),
        }

    def _refresh_absences(self):
        emp_id = self.filter_employee.currentData()
        start = self.filter_start.date().toString("yyyy-MM-dd")
        end = self.filter_end.date().toString("yyyy-MM-dd")

        if emp_id:
            absences = db.get_absences_for_employee(emp_id, start, end)
            emp = db.get_employee(emp_id)
            for_table = []
            for a in absences:
                row_data = dict(a)
                row_data["employee_name"] = db.get_employee_full_name(emp) if emp else ""
                row_data["employee_grade"] = emp["grade"] if emp else ""
                for_table.append(row_data)
        else:
            absences = db.get_all_absences(start, end)
            for_table = absences

        self.absences_table.setRowCount(0)
        self.absences_table.setRowCount(len(for_table))

        for row, a in enumerate(for_table):
            emp_name = a.get("employee_name", "") if hasattr(a, "get") else (a["employee_name"] if "employee_name" in a.keys() else "")
            emp_grade = a.get("employee_grade", "") if hasattr(a, "get") else (a["employee_grade"] if "employee_grade" in a.keys() else "")

            self.absences_table.setItem(row, 0, self._item(emp_name))
            self.absences_table.setItem(row, 1, self._item(emp_grade))

            # Type badge
            abs_type = a["absence_type"]
            type_label = QLabel(abs_type)
            type_label.setAlignment(Qt.AlignCenter)
            if abs_type == "غياب":
                type_label.setObjectName("badge_danger")
            else:
                type_label.setObjectName("badge_warning")
            self.absences_table.setCellWidget(row, 2, type_label)

            self.absences_table.setItem(row, 3, self._item(a["absence_date"]))
            self.absences_table.setItem(row, 4, self._item(a["duration"] or "—"))

            # Justified badge
            justified = a["is_justified"]
            j_label = QLabel("مبرر" if justified else "غير مبرر")
            j_label.setAlignment(Qt.AlignCenter)
            j_label.setObjectName("badge_success" if justified else "badge_danger")
            self.absences_table.setCellWidget(row, 5, j_label)

            self.absences_table.setItem(row, 6, self._item(a["director_decision"] or "—"))

            # Actions
            abs_id = a["id"]
            actions = QWidget()
            actions.setLayoutDirection(Qt.RightToLeft)
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)

            options_btn = QPushButton(" خيارات")
            from ui.icons import get_icon
            options_btn.setIcon(get_icon("settings", color="#475569"))
            options_btn.setCursor(Qt.PointingHandCursor)
            options_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    color: #475569;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                    color: #1e293b;
                }
            """)
            
            menu = QMenu(options_btn)
            menu.setLayoutDirection(Qt.RightToLeft)
            menu.setStyleSheet("""
                QMenu {
                    background-color: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px;
                }
                QMenu::item {
                    padding: 6px 24px; border-radius: 4px; color: #1e293b; font-size: 13px;
                }
                QMenu::item:selected {
                    background-color: #f1f5f9; color: #2563eb;
                }
            """)
            

            delete_action = menu.addAction(get_icon("delete", color="#ef4444"), "حذف")
            delete_action.triggered.connect(lambda checked, aid=abs_id: self._delete_absence(aid))
            
            options_btn.setMenu(menu)
            al.addWidget(options_btn)
            al.addStretch()
            self.absences_table.setCellWidget(row, 7, actions)
            self.absences_table.setRowHeight(row, 42)

    def _refresh_monthly_stats(self):
        month = self.month_combo.currentData()
        year = self.year_spin.value()
        if not month:
            return

        rows = db.get_monthly_absence_summary(year, month)
        self.monthly_table.setRowCount(0)
        self.monthly_table.setRowCount(len(rows))

        for row, r in enumerate(rows):
            self.monthly_table.setItem(row, 0, self._item(
                "%s %s" % (r["last_name"], r["first_name"])
            ))
            self.monthly_table.setItem(row, 1, self._item(r["grade"] or ""))
            self.monthly_table.setItem(row, 2, self._item(str(r["absences_count"])))
            self.monthly_table.setItem(row, 3, self._item(str(r["delays_count"])))
            self.monthly_table.setItem(row, 4, self._item(str(r["justified_count"])))
            self.monthly_table.setItem(row, 5, self._item(str(r["unjustified_count"])))
            self.monthly_table.setRowHeight(row, 42)

    def _item(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    def _print_monthly_stats(self):
        month_idx = self.month_combo.currentData()
        month_name = self.month_combo.currentText()
        year = self.year_spin.value()
        
        if not month_idx:
            return
            
        rows = db.get_monthly_absence_summary(year, month_idx)
        
        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        
        table_html = ""
        for i, r in enumerate(rows):
            emp_name = "%s %s" % (r["last_name"], r["first_name"])
            table_html += f"""
            <tr>
                <td>{r["unjustified_count"]}</td>
                <td>{r["justified_count"]}</td>
                <td>{r["delays_count"]}</td>
                <td>{r["absences_count"]}</td>
                <td>{r["grade"] or ""}</td>
                <td>{emp_name}</td>
                <td>{i + 1}</td>
            </tr>
            """
            
        html = f"""
        <html dir="rtl">
        <head>
            <style>
                body {{ font-family: 'Amiri', 'Traditional Arabic', serif; direction: rtl; padding: 5px; }}
                h2 {{ text-align: center; margin-bottom: 20px; font-weight: bold; border-bottom: 2px solid #ccc; padding-bottom: 2px; }}
                table.header-table {{line-height: 0.9; width: 100%; margin-bottom: 0px; font-weight: bold; font-size: 14px; }}
                table.data-table {{line-height: 0.9; width: 100%;border-collapse: collapse;border: 1px solid #000; margin-bottom: 2px; }}
                table.data-table th, table.data-table td {{border: 1px solid #000;padding: 1px; font-size: 12px; text-align: right; }}
                table.data-table th {{font-weight: bold; text-align: center; }}
                table.data-table td {{text-align: left; }}
                .footer {{ text-align: left; margin-top: 4px; font-weight: bold; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div style="text-align:center; font-weight: bold; margin-bottom: 15px;">
                <div style="font-size:16px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="font-size:14px;">وزارة التربية الوطنية</div>
            </div>
            
            <table width="100%" align="right" class="header-table">
                <tr>
                    <td colspan="2" style="width: 100%;">
                        مديرية التربية لولاية: {wilaya}
                      
                    </td>
                    </tr>
                    <tr>
                       
                    <td style="text-align: right; width: 20%;">
                        السنة الدراسية: {school_year}
                    </td>
                    <td style="text-align: left; width: 80%;">
                         المؤسسة: {school}
                    </td>
                </tr>
            </table>
            
            <h2>إحصائيات الغيابات والتأخرات لشهر {month_name} {year}</h2>
            
            <table width="100%" align="right" style="width: 100%;line-height: 0.9;" class="data-table">
                <thead>
                    <tr>
                        <th>غير مبررة</th>
                        <th>تأخرات</th>
                        <th>غيابات</th>
                        <th>الرتبة</th>
                        <th>مبررة</th>
                        <th>اسم ولقب الموظف</th>
                        <th>الرقم</th>
                    </tr>
                </thead>
                <tbody>
                    {table_html}
                </tbody>
            </table>
            
            <div class="footer">
                حُرّر في: {datetime.now().strftime('%Y/%m/%d')}<br/><br/>
                المدير(ة)<br/><br/><br/>
                {director}
            </div>
        </body>
        </html>
        """
        self._show_print_preview(html)

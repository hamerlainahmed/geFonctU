# -*- coding: utf-8 -*-
"""
Deductions Page — View and print all deduction decisions:
 • Deduction notices (إشعار بالخصم) for director salary deduction decisions
 • Total deductions report per employee (sick leaves + director decisions)
 • Separate views: justified (sick leaves) vs unjustified (director deductions)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QLabel, QFrame, QSizePolicy, QTabWidget, QGraphicsDropShadowEffect,
    QPushButton, QGridLayout,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont

from ui.widgets import (
    ArabicLabel, ArabicComboBox, StatCard, ActionButton, Separator,
)
import database as db
from datetime import datetime

MONTHS_AR = [
    "جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
    "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

class DeductionsPage(QWidget):
    """Deductions management page — print notices and total reports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 16)

        # Header
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header = QLabel("الاقتطاعات 💰")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        header_row.addWidget(header)
        header_row.addStretch()

        # Month Filter
        filter_label = QLabel("تصفية بشهر الاقتطاع:")
        filter_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_row.addWidget(filter_label, alignment=Qt.AlignVCenter)
        
        self.filter_month = ArabicComboBox()
        self.filter_month.addItem("الكل", "الكل")
        for m in MONTHS_AR:
            self.filter_month.addItem(m, m)
        self.filter_month.setMinimumWidth(150)
        self.filter_month.currentIndexChanged.connect(self.refresh)
        header_row.addWidget(self.filter_month, alignment=Qt.AlignVCenter)
        header_row.addSpacing(20)

        # Print monthly deductions button
        print_monthly_btn = ActionButton("طباعة اقتطاعات الشهر", "🖨️", "primary")
        print_monthly_btn.setMinimumHeight(42)
        print_monthly_btn.clicked.connect(self._print_monthly_deductions)
        header_row.addWidget(print_monthly_btn, alignment=Qt.AlignVCenter)

        layout.addLayout(header_row)

        # Stats Cards removed

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.RightToLeft)

        # ═══ Tab 1: Unjustified Deductions (Director Decisions) ═══
        self.unjustified_tab = QWidget()
        unj_layout = QVBoxLayout(self.unjustified_tab)
        unj_layout.setContentsMargins(8, 10, 8, 8)
        unj_layout.setSpacing(8)

        unj_info = QLabel("🚫 اقتطاعات غير مبررة — قرارات المدير بالخصم (غياب غير مبرر / تأخر / عدم تأدية مهام)")
        unj_info.setStyleSheet("font-size: 13px; color: #b91c1c; font-weight: bold; padding: 8px; "
                                "background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;")
        unj_info.setWordWrap(True)
        unj_layout.addWidget(unj_info)

        self.unjustified_table = QTableWidget()
        self.unjustified_table.setLayoutDirection(Qt.RightToLeft)
        self.unjustified_table.setColumnCount(8)
        self.unjustified_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "نوع القرار", "عدد أيام الخصم",
            "الشهر / الثلاثي", "سبب الاستفسار", "تاريخ القرار", "إجراءات"
        ])
        self.unjustified_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.unjustified_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.unjustified_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.unjustified_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.unjustified_table.setAlternatingRowColors(True)
        self.unjustified_table.verticalHeader().setVisible(False)
        self.unjustified_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.unjustified_table.setShowGrid(False)
        self.unjustified_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        unj_layout.addWidget(self.unjustified_table, stretch=1)

        self.tabs.addTab(self.unjustified_tab, "🚫  اقتطاعات غير مبررة")

        # ═══ Tab 2: Justified Deductions (Sick Leaves) ═══
        self.justified_tab = QWidget()
        jst_layout = QVBoxLayout(self.justified_tab)
        jst_layout.setContentsMargins(8, 10, 8, 8)
        jst_layout.setSpacing(8)

        jst_info = QLabel("🏥 اقتطاعات مبررة — العطل المرضية (عدد الأيام المقتطعة من الراتب)")
        jst_info.setStyleSheet("font-size: 13px; color: #1e40af; font-weight: bold; padding: 8px; "
                                "background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;")
        jst_info.setWordWrap(True)
        jst_layout.addWidget(jst_info)

        self.justified_table = QTableWidget()
        self.justified_table.setLayoutDirection(Qt.RightToLeft)
        self.justified_table.setColumnCount(6)
        self.justified_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "فترة العطلة المرضية", "أيام الخصم",
            "شهر الاقتطاع", "الحالة"
        ])
        self.justified_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.justified_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.justified_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.justified_table.setAlternatingRowColors(True)
        self.justified_table.verticalHeader().setVisible(False)
        self.justified_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.justified_table.setShowGrid(False)
        self.justified_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        jst_layout.addWidget(self.justified_table, stretch=1)

        self.tabs.addTab(self.justified_tab, "🏥  اقتطاعات مبررة")

        layout.addWidget(self.tabs, stretch=1)

    # ──────────────────────────────────────────────
    # Print: Deduction Notice (إشعار بالخصم)
    # ──────────────────────────────────────────────
    def _print_deduction_notice(self, inq_id):
        inquiry = db.get_inquiry(inq_id)
        if not inquiry:
            return
        emp = db.get_employee(inquiry["employee_id"])
        if not emp:
            return

        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        school_address = settings.get("school_address", "........................")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        emp_name = db.get_employee_full_name(emp)
        today = datetime.now().strftime("%Y/%m/%d")

        school_display = school
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code

        subject_line = ""
        if emp["subject"]:
            subject_line = "، مادة: <b>%s</b>" % emp["subject"]

        decision = inquiry["director_decision"]
        inq_dict = dict(inquiry)
        inq_type = inq_dict.get("inquiry_type", "") or ""
        inq_details = inq_dict.get("details", "") or ""

        if decision == "خصم من الراتب":
            days = inq_dict.get("deduction_days", "")
            month = inq_dict.get("deduction_month", "")
            if month:
                proposed = "خصم ما يعادل %s يوم من راتب شهر %s" % (days, month)
            else:
                proposed = "خصم ما يعادل %s يوم" % days
        elif decision == "خصم من المردودية":
            if "غياب" in inq_type:
                m_reason = "غيابكم"
            elif "تأخر" in inq_type:
                m_reason = "تأخركم"
            else:
                m_reason = "جدول تقييم المردودية"
            quarter = inq_dict.get("deduction_quarter", "")
            proposed = "خصم من المردودية بما يتناسب مع %s في الثلاثي %s" % (m_reason, quarter)
        else:
            proposed = str(decision)

        if inq_details:
            reason_text = inq_details
        else:
            if "غياب" in inq_type:
                reason_text = "غيابكم"
            elif "تأخر" in inq_type:
                reason_text = "تأخركم"
            else:
                reason_text = "عدم تأدية مهامكم"

        deduction_details = (
            "<p style=\"font-size: 16px; font-weight: bold; line-height: 1.0; text-align: left;\">"
            "نحيطكم علما أننا اقترحنا: %s<br/>"
            "وذلك للأسباب التالية : %s"
            "</p>"
        ) % (proposed, reason_text)

        core_content = """
            <div style="line-height: 0.7;text-align:center; font-weight: bold;">
                <div style="line-height: 0.7;text-align:center;font-size:18px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="line-height: 0.7;text-align:center;font-size:18px;">وزارة التربية الوطنية</div>
            </div>
            <table width="100%%" style="line-height: 0.7;font-weight: bold; font-size: 16px;">
                <tr style="line-height: 0.7;">
                    <td style="text-align:right; width:50%%;">
                        السنة الدراسية: %(school_year)s
                    </td>
                    <td style="text-align:left; width:50%%;">
                      
                      مديرية التربية لولاية %(wilaya)s
                    </td>
                </tr>
                <tr style="line-height: 0.7;">
                    
                     <td style="text-align:center; width:50%%;">
                       إلى
                    </td>
                    <td style="text-align:left; width:50%%;">
                        %(school)s - %(school_addr)s
                    </td>
                </tr>
                <tr style="line-height: 0.7;">
                    
                    <td style="text-align:center; width:50%%;">
                     السيد(ة): <b>%(emp_name)s</b>
                    </td>
                    <td style="text-align:left; width:50%%;">
                        رمز المؤسسة: %(school_code)s
                    </td>
                </tr>
                <tr style="line-height: 0.7;">
                    
                    <td style="text-align:center; width:50%%;">
                     الرتبة: <b>%(emp_grade)s</b>
                    </td>
                     <td style="text-align:left; width:50%%;">
                     
                    </td>
                </tr>
            </table>
           <table width="100%%" style="line-height: 0.7;font-weight: bold; font-size: 16px;">
            <tr style="line-height: 0.7;">
                <td colspan="2" style="font-size: 18px; text-align:left; width:100%%;">
                    الموضوع: إشعار بالخصم
                </td>
               
            </tr>
            <tr style="line-height: 0.7;">
                <td colspan="2" style="font-size: 16px; text-align:left; width:100%%;">
                    عطفا على الاستفسار المؤرخ في: <b>%(inquiry_date)s</b>، 
              
                </td>
              
            </tr>
            <tr style="line-height: 0.7;">
                <td colspan="2" style="font-size: 16px; text-align:left; width:100%%;">
                  %(deduction_details)s
                </td>
              
            </tr>
            <tr style="line-height: 0.7;">
                <td colspan="2" style="font-size: 14px; text-align:left; width:100%%;">
                  %(notes_section)s
                </td>
              
            </tr>
            <tr style="line-height: 0.7;">
                <td style="text-align:center; width:30%%;">
حرر بـ%(school_address)s في: %(today)s
                </td>
                <td style="font-size: 13px; text-align:left; width:70%%;">
                نسخة موجهة إلى:
                </td>
              
            </tr>
            <tr style="line-height: 0.7;">
                <td style="font-size: 16px; text-align:center; width:30%%;">
   المدير(ة)
                </td>
                <td style="font-size: 13px; text-align:left; width:70%%;">
- ملف المعني بالأمر
                </td>
              
            </tr>
            <tr style="line-height: 0.7;">
                <td style="font-size: 16px; text-align:center; width:30%%;">
                <b>%(director)s</b>   
             </td>
                <td style="font-size: 13px; text-align:left; width:70%%;">
- م.ت.ن. المستخدمين
                </td>
              
            </tr>
       
            
           </table>
        """ % {
            "wilaya": wilaya, "school": school, "school_code": school_code,
            "school_address": school_address, "school_addr": school_address,
            "school_display": school_display, "school_year": school_year,
            "emp_name": emp_name, "emp_grade": emp["grade"] or "",
            "subject_line": subject_line,
            "inquiry_date": inquiry["inquiry_date"],
            "inquiry_type": inquiry["inquiry_type"],
            "decision": decision,
            "deduction_details": deduction_details,
            "notes_section": (
                '<p style="line-height: 0.7;font-size:13px; font-weight:bold; color: #666;">ملاحظات: %s</p>'
                % inquiry["decision_notes"]
            ) if inquiry["decision_notes"] else "",
            "today": today, "director": director,
        }

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; }
            
        </style></head>
        <body style="margin: 0; padding: 0;" dir="rtl">
            <table height="100%%" width="100%%" cellspacing="0" cellpadding="0"
         style="border-collapse: collapse; margin: 0; padding: 0;">
                <tr style="height: 100%%;">
                    <td width="49%%" style="padding: 3px; border: 1px dashed #999; direction: rtl;">
                        %s
                    </td>
                    <td width="1%%" style="border: none;"></td>
                    <td width="49%%" style=" padding: 3px; border: 1px dashed #999; direction: rtl;">
                        %s
                    </td>
                </tr>
            </table>
        </body></html>
        """ % (core_content, core_content)

        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=True)
        dialog.exec_()

    # ──────────────────────────────────────────────
    # Print: Monthly Deductions (up to 4 documents)
    # ──────────────────────────────────────────────
    def _is_teacher(self, grade):
        """Check if this grade is a teacher grade."""
        if not grade:
            return False
        return "أستاذ" in grade

    def _print_monthly_deductions(self):
        """Print monthly deduction tables split by category:
        - Unjustified (301) × teachers / admin
        - Justified (302)   × teachers / admin
        """
        month_filter = self.filter_month.currentData()
        if month_filter == "الكل":
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار شهر محدد لطباعة الاقتطاعات.")
            return

        month_index = MONTHS_AR.index(month_filter) + 1
        current_year = QDate.currentDate().year()

        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        school_address = settings.get("school_address", "........................")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        today = datetime.now().strftime("%d-%m-%Y")

        # ── Gather unjustified deductions (director salary deductions) ──
        all_inquiries = db.get_decided_inquiries()
        unjustified_rows = []
        for inq in all_inquiries:
            decision = inq["director_decision"]
            if decision == "خصم من الراتب" and inq["deduction_month"] == month_filter:
                emp = db.get_employee(inq["employee_id"])
                if emp:
                    unjustified_rows.append({
                        "name": db.get_employee_full_name(emp),
                        "grade": emp["grade"] or "",
                        "code": emp["account_number"] or "",
                        "days": "%02d يوم" % inq["deduction_days"],
                        "date": inq["inquiry_date"] or "",
                    })

        # ── Gather justified deductions (sick leaves) ──
        all_sick_leaves = db.get_all_sick_leaves()
        justified_rows = []
        for sl in all_sick_leaves:
            chunks = self._calc_sick_leave_chunks(sl["start_date"], sl["duration_days"])
            for chunk in chunks:
                if chunk["month_name"] == month_filter:
                    emp = db.get_employee(sl["employee_id"])
                    if emp:
                        justified_rows.append({
                            "name": db.get_employee_full_name(emp),
                            "grade": emp["grade"] or "",
                            "code": emp["account_number"] or "",
                            "days": "%02d يوم" % chunk["days"],
                            "date": sl["start_date"] or "",
                            "doctor": sl["doctor_name"] or "",
                        })

        # ── Split by category ──
        unjustified_teachers = [r for r in unjustified_rows if self._is_teacher(r["grade"])]
        unjustified_admin = [r for r in unjustified_rows if not self._is_teacher(r["grade"])]
        justified_teachers = [r for r in justified_rows if self._is_teacher(r["grade"])]
        justified_admin = [r for r in justified_rows if not self._is_teacher(r["grade"])]

        # ── Generate pages ──
        pages = []

        if unjustified_admin:
            pages.append(self._generate_deduction_page(
                title="جدول الاقتطاعات غير المبررة",
                month_name=month_filter,
                code="301",
                admin_label="تسيير نفقات الموظفين الإداريين",
                rows=unjustified_admin,
                settings=settings,
                today=today,
                is_justified=False,
            ))

        if unjustified_teachers:
            pages.append(self._generate_deduction_page(
                title="جدول الاقتطاعات غير المبررة",
                month_name=month_filter,
                code="301",
                admin_label="تسيير نفقات الأساتذة",
                rows=unjustified_teachers,
                settings=settings,
                today=today,
                is_justified=False,
            ))

        if justified_admin:
            pages.append(self._generate_deduction_page(
                title="جدول الاقتطاعات المبررة",
                month_name=month_filter,
                code="302",
                admin_label="تسيير نفقات الموظفين الإداريين",
                rows=justified_admin,
                settings=settings,
                today=today,
                is_justified=True,
            ))

        if justified_teachers:
            pages.append(self._generate_deduction_page(
                title="جدول الاقتطاعات المبررة",
                month_name=month_filter,
                code="302",
                admin_label="تسيير نفقات الأساتذة",
                rows=justified_teachers,
                settings=settings,
                today=today,
                is_justified=True,
            ))

        if not pages:
            QMessageBox.information(self, "تنبيه", "لا توجد اقتطاعات مسجلة لشهر %s." % month_filter)
            return

        # Combine all pages with explicit page breaks between them
        page_break = '<p style="page-break-before: always;"></p>'
        combined_body = page_break.join(pages)

        html = """
        <html dir="rtl">
        <head><style>
            @page { margin: 15mm; }
            body {
                font-family: 'Amiri', 'Traditional Arabic', serif;
                direction: rtl;
                margin: 0;
                padding: 0;
            }
            table { border-collapse: collapse; width: 100%%; }
        </style></head>
        <body dir="rtl">
            %s
        </body></html>
        """ % combined_body

        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self)
        dialog.exec_()

    def _generate_deduction_page(self, title, month_name, code, admin_label, rows, settings, today, is_justified=False):
        """Generate a single deduction page HTML."""
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        school_address = settings.get("school_address", "........................")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        current_year = QDate.currentDate().year()

        # Generate school initials for ref number
        school_initials = self._get_school_initials(school)

        # Build table rows
        table_rows = ""
        for idx, r in enumerate(rows):
            
            if is_justified:
                table_rows += (
                    '<tr style="line-height: 1.0;">'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;font-weight:bold;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%02d</td>'
                    '</tr>'
                ) % (r.get("doctor", ""), r["date"], r["days"], r["code"], r["grade"], r["name"], idx + 1)
            else:
                table_rows += (
                    '<tr style="line-height: 1.0;">'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;font-weight:bold;">%s</td>'
                    '<td style="padding:1px;border:1px solid #333;text-align:center;">%02d</td>'
                    '</tr>'
                ) % (r["date"], r["days"], r["code"], r["grade"], r["name"], idx + 1)

        # Build header columns based on type
        header_cols = (
                '<th style="padding:1px;border:1px solid #333;">الفترة</th>'
                '<th style="padding:1px;border:1px solid #333;">عدد الأيام</th>'
                '<th style="padding:1px;border:1px solid #333;">رمز الموظف</th>'
                '<th style="padding:1px;border:1px solid #333;">الرتبة</th>'
                '<th style="padding:1px;border:1px solid #333;">اسم ولقب الموظف (ة)</th>'
                '<th style="padding:1px;border:1px solid #333;">الرقم</th>'
            )
        if is_justified:
            header_cols = (
                '<th style="padding:1px;border:1px solid #333;">اسم الطبيب</th>'
            ) + header_cols
        
        page_html = """
            <div style="line-height: 1.0; text-align: left; font-weight: bold; font-size: 14px;">
                <div style="text-align: center; font-size: 18px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="text-align: center; font-size: 18px;">وزارة التربية الوطنية</div>
            </div>

            <table width="100%%" style="line-height: 1.0; font-weight: bold; font-size: 16px;">
                <tr style="line-height: 1.0;">
                   
                    <td style="text-align: left; width: auto;">مديرية التربية لولاية %(wilaya)s</td>
                </tr>
                <tr style="line-height: 1.0;">
                  
                    <td  style="text-align: left; width: auto;">%(school)s - %(school_address)s</td>
                </tr>
                <tr style="line-height: 1.0;">
                   
                    <td style="text-align: left; width: auto;">رمز المؤسسة : %(school_code)s</td>
                </tr>
                <tr style="line-height: 1.0;">
                    
                  
               
                    <td dir="rtl" style="direction:rtl;text-align: left;">
                     <span style="unicode-bidi: bidi-override; direction: rtl;">الرقم:.............&rlm;/&rlm; %(school_initials)s&rlm;/&rlm; %(year)s</span>
                    </td>
                    </tr>
            </table>

            <div style="line-height: 0.9; text-align: center;">
                <div style=" font-size: 18px; font-weight: bold;">%(title)s</div>
                <div style="font-size: 18px; font-weight: bold;">لشهر: %(month_name)s %(year)s</div>
                <div style=" font-size: 16px; font-weight: bold;">الرمز %(code)s</div>
            </div>

            <div align="right" style="line-height: 1.0; font-size: 18px; font-weight: bold;">
                الإدارة : %(admin_label)s .
            </div>

            <table width="100%%" dir="rtl" style="font-size: 16px; border: 1px solid #333; margin-bottom: 2px;">
                <tr style="font-weight: bold;">
                    %(header_cols)s
                </tr>
                %(table_rows)s
            </table>

            <table width="100%%" style="line-height: 1.0; font-size: 16px; font-weight: bold; margin-top: 2px;">
                <tr style="line-height: 1.0;">
                    <td style="text-align: center; width: 40%%;">%(school_address)s في %(today)s</td>
                     <td style="text-align: left; width: 40%%;"></td>
                    <td style="text-align: center; width: 20%%;">تاريخ استلام:</td>
                </tr>
                <tr style="line-height: 1.0;">
                    <td style="text-align: center; width: 40%%;">المدير</td>
                     <td style="text-align: left; width: 40%%;"></td>
                    <td style="text-align: center; width: 20%%;">.............................</td>
                </tr>
                <tr style="line-height: 1.0;">
                    <td style="text-align: center; width: 40%%;"></td>
                     <td style="text-align: left; width: 40%%;"></td>
                    <td style="text-align: center; width: 20%%;">.............................</td>
                </tr>
            </table>
        """ % {
            "wilaya": wilaya,
            "school": school,
            "school_code": school_code,
            "school_address": school_address,
            "school_initials": school_initials,
            "year": current_year,
            "title": title,
            "month_name": month_name,
            "code": code,
            "admin_label": admin_label,
            "header_cols": header_cols,
            "table_rows": table_rows,
            "today": today,
            "director": director,
        }
        return page_html

    def _get_school_initials(self, school_name):
        """Extract initials from school name, ignoring honorary/type prefixes.
        E.g. 'متوسطة الشهيد نذار قدور' → 'م.ن.ق'
        The first letter of the school type (متوسطة/ثانوية/ابتدائية) is kept,
        then honorary words are skipped, and initials of remaining words are taken.
        """
        if not school_name:
            return ""

        # Words to skip entirely (honorary titles)
        skip_words = {
            "الشهيد", "الشهيدة", "المجاهد", "المجاهدة", "العلامة",
            "القائد", "الأمير", "الشيخ", "الإمام", "الرئيس",
            "البطل", "العقيد", "الرائد", "المقاوم", "المناضل",
            "شهيد", "مجاهد", "علامة", "قائد", "أمير", "شيخ",
        }

        # School type words — take first letter then skip
        type_words = {
            "متوسطة", "ثانوية", "ابتدائية", "مدرسة", "ليسي",
            "إكمالية", "تقنية",
        }

        words = school_name.strip().split()
        initials = []

        for word in words:
            clean = word.strip()
            if not clean:
                continue
            # Remove leading ال for comparison (but keep original for initial)
            bare = clean.lstrip("ال") if clean.startswith("ال") else clean
            if clean in skip_words or bare in skip_words:
                continue
            if clean in type_words:
                initials.append(clean[0])
                continue
            # Take the first character
            initials.append(clean[0])

        return ".".join(initials)

    # ──────────────────────────────────────────────
    # Refresh
    # ──────────────────────────────────────────────
    def refresh(self):
        self._refresh_unjustified()
        self._refresh_justified()

    def _refresh_stats(self):
        pass

    def _calc_sick_leave_chunks(self, start_date_str, duration_days):
        chunks = []
        try:
            date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            try:
                date_obj = datetime.strptime(start_date_str, "%Y/%m/%d")
            except:
                # fallback if parsing fails: just assign entire duration to current month
                return [{"month_name": MONTHS_AR[datetime.now().month - 1], "days": duration_days}]
                
        month = date_obj.month
        # The deduction month is the month AFTER the sick leave starts
        if month == 12:
            month = 1
        else:
            month += 1
            
        rem_days = duration_days
        while rem_days > 0:
            chunk_days = min(rem_days, 30)
            chunks.append({
                "month_name": MONTHS_AR[month - 1],
                "days": chunk_days
            })
            rem_days -= chunk_days
            if month == 12:
                month = 1
            else:
                month += 1
        return chunks

    def _refresh_unjustified(self):
        inquiries = db.get_decided_inquiries()
        month_filter = self.filter_month.currentData()
        
        # Apply filter
        if month_filter != "الكل":
            filtered = []
            for inq in inquiries:
                decision = inq["director_decision"]
                if decision == "خصم من الراتب" and inq["deduction_month"] == month_filter:
                    filtered.append(inq)
                elif decision == "خصم من المردودية":
                    # Productivity deduction isn't strictly this month
                    filtered.append(inq)
            inquiries = filtered

        self.unjustified_table.setRowCount(0)
        self.unjustified_table.setRowCount(len(inquiries))

        for row, inq in enumerate(inquiries):
            emp_name = inq["employee_name"]
            emp_grade = inq["employee_grade"] or ""
            decision = inq["director_decision"]

            self.unjustified_table.setItem(row, 0, self._item(emp_name))
            self.unjustified_table.setItem(row, 1, self._item(emp_grade))

            # Decision type badge
            if decision == "خصم من الراتب":
                dec_label = QLabel("💰 خصم من الراتب")
                dec_label.setObjectName("badge_danger")
            else:
                dec_label = QLabel("📉 خصم من المردودية")
                dec_label.setObjectName("badge_warning")
            dec_label.setAlignment(Qt.AlignCenter)
            self.unjustified_table.setCellWidget(row, 2, dec_label)

            # Deduction days
            if decision == "خصم من الراتب":
                self.unjustified_table.setItem(row, 3, self._item("%d يوم" % inq["deduction_days"]))
            else:
                self.unjustified_table.setItem(row, 3, self._item("—"))

            # Month/Quarter
            if decision == "خصم من الراتب":
                self.unjustified_table.setItem(row, 4, self._item(inq["deduction_month"]))
            else:
                quarter = inq["deduction_quarter"] or ""
                # Shorten the quarter text
                if quarter:
                    short_quarter = quarter.split("(")[0].strip() if "(" in quarter else quarter
                else:
                    short_quarter = "—"
                self.unjustified_table.setItem(row, 4, self._item(short_quarter))

            self.unjustified_table.setItem(row, 5, self._item(inq["inquiry_type"]))
            self.unjustified_table.setItem(row, 6, self._item(inq["decided_at"] or "—"))

            # Actions
            inq_id = inq["id"]
            actions = QWidget()
            actions.setLayoutDirection(Qt.RightToLeft)
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)

            print_btn = ActionButton("", "🖨", "icon")
            print_btn.setToolTip("طباعة إشعار بالخصم")
            print_btn.clicked.connect(
                lambda checked, aid=inq_id: self._print_deduction_notice(aid)
            )
            al.addWidget(print_btn)
            al.addStretch()

            self.unjustified_table.setCellWidget(row, 7, actions)
            self.unjustified_table.setRowHeight(row, 44)

    def _refresh_justified(self):
        sick_leaves = db.get_all_sick_leaves()
        month_filter = self.filter_month.currentData()
        
        display_rows = []
        for sl in sick_leaves:
            chunks = self._calc_sick_leave_chunks(sl["start_date"], sl["duration_days"])
            for chunk in chunks:
                if month_filter == "الكل" or chunk["month_name"] == month_filter:
                    sl_row = dict(sl)
                    sl_row["chunk_month"] = chunk["month_name"]
                    sl_row["chunk_days"] = chunk["days"]
                    display_rows.append(sl_row)

        self.justified_table.setRowCount(0)
        self.justified_table.setRowCount(len(display_rows))

        for row, sl in enumerate(display_rows):
            self.justified_table.setItem(row, 0, self._item(sl["employee_name"]))
            self.justified_table.setItem(row, 1, self._item(sl["employee_grade"] or ""))
            self.justified_table.setItem(row, 2, self._item("%s إلى %s" % (sl["start_date"], sl["end_date"])))
            
            days_item = self._item("%d يوم" % sl["chunk_days"])
            days_item.setFont(QFont("Amiri", 11, QFont.Bold))
            self.justified_table.setItem(row, 3, days_item)
            
            month_item = self._item(sl["chunk_month"])
            month_item.setFont(QFont("Amiri", 11, QFont.Bold))
            month_item.setForeground(QColor("#2563eb"))
            self.justified_table.setItem(row, 4, month_item)

            status = sl["status"]
            if status == "جارية":
                status_lbl = QLabel("🏥 جارية")
                status_lbl.setObjectName("badge_warning")
            else:
                status_lbl = QLabel("✅ منتهية")
                status_lbl.setObjectName("badge_success")
            status_lbl.setAlignment(Qt.AlignCenter)
            self.justified_table.setCellWidget(row, 5, status_lbl)
            self.justified_table.setRowHeight(row, 44)


    def _item(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

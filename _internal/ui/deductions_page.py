# -*- coding: utf-8 -*-
"""
Deductions Page — View and print all deduction decisions:
 • Deduction notices (إشعار بالخصم) for director salary deduction decisions
 • Total deductions report per employee (all types in one unified document)
 • Manual deduction entry (sick leave, maternity, unjustified, settlement)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QLabel, QFrame, QSizePolicy, QTabWidget, QGraphicsDropShadowEffect,
    QPushButton, QGridLayout, QSpinBox,
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont

from ui.widgets import (
    ArabicLabel, ArabicComboBox, ArabicLineEdit, ArabicDateEdit,
    StatCard, ActionButton, Separator, ArabicFormLayout,
)
import database as db
from datetime import datetime

MONTHS_AR = [
    "جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
    "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

DEDUCTION_TYPES = ["عطلة مرضية", "عطلة أمومة", "غير مبرر", "تسوية"]


class ManualDeductionDialog(QDialog):
    """Dialog for adding a manual deduction entry."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة اقتطاع يدوي")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(480)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("إضافة اقتطاع يدوي ✍️")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title)

        form = ArabicFormLayout()

        # Employee selector
        self.employee_combo = ArabicComboBox()
        self._load_employees()
        form.addRow("الموظف *:", self.employee_combo)

        # Deduction type
        self.type_combo = ArabicComboBox()
        self.type_combo.addItems(DEDUCTION_TYPES)
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("نوع الاقتطاع *:", self.type_combo)

        # Duration in days
        self.days_spin = QSpinBox()
        self.days_spin.setLayoutDirection(Qt.RightToLeft)
        self.days_spin.setMinimum(1)
        self.days_spin.setMaximum(365)
        self.days_spin.setValue(1)
        self.days_spin.setSuffix(" يوم")
        self.days_spin.setStyleSheet("""
            QSpinBox {
                padding: 6px 12px; font-size: 14px;
                border: 2px solid #e5e7eb; border-radius: 8px;
                background: #ffffff; min-height: 32px;
            }
            QSpinBox:focus { border-color: #3b82f6; }
            QSpinBox::up-button, QSpinBox::down-button { width: 24px; border: none; }
        """)
        form.addRow("عدد الأيام *:", self.days_spin)

        # Medical certificate date
        self.cert_date = ArabicDateEdit()
        self.cert_date_label = QLabel("تاريخ الشهادة الطبية:")
        form.addRow(self.cert_date_label, self.cert_date)

        # Deduction month
        self.month_combo = ArabicComboBox()
        for m in MONTHS_AR:
            self.month_combo.addItem(m, m)
        # default to current month
        current_month_idx = datetime.now().month - 1
        self.month_combo.setCurrentIndex(current_month_idx)
        form.addRow("شهر الاقتطاع *:", self.month_combo)

        # Notes
        self.notes_input = ArabicLineEdit("ملاحظات (اختياري)")
        form.addRow("ملاحظات:", self.notes_input)

        layout.addLayout(form)
        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = ActionButton("حفظ الاقتطاع", "✔", "success")
        save_btn.clicked.connect(self._save)
        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._on_type_changed(self.type_combo.currentText())

    def _load_employees(self):
        employees = db.get_all_employees()
        for emp in employees:
            full_name = db.get_employee_full_name(emp)
            grade = emp["grade"] or ""
            self.employee_combo.addItem("%s — %s" % (full_name, grade), emp["id"])

    def _on_type_changed(self, text):
        """Show/hide certificate date based on deduction type."""
        # Certificate date only relevant for medical/maternity leave
        show_cert = text in ("عطلة مرضية", "عطلة أمومة")
        self.cert_date.setVisible(show_cert)
        self.cert_date_label.setVisible(show_cert)

    def _save(self):
        idx = self.employee_combo.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف")
            return
        self.accept()

    def get_data(self):
        deduction_type = self.type_combo.currentText()
        show_cert = deduction_type in ("عطلة مرضية", "عطلة أمومة")
        return {
            "employee_id": self.employee_combo.currentData(),
            "deduction_type": deduction_type,
            "duration_days": self.days_spin.value(),
            "cert_date": self.cert_date.date().toString("yyyy-MM-dd") if show_cert else "",
            "deduction_month": self.month_combo.currentText(),
            "notes": self.notes_input.text().strip(),
        }


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
        header_row.addSpacing(12)

        # Add manual deduction button
        add_btn = ActionButton("إضافة اقتطاع يدوي", "✍️", "success")
        add_btn.setMinimumHeight(42)
        add_btn.clicked.connect(self._add_manual_deduction)
        header_row.addWidget(add_btn, alignment=Qt.AlignVCenter)

        # Print monthly deductions button
        print_monthly_btn = ActionButton("طباعة اقتطاعات الشهر", "🖨️", "primary")
        print_monthly_btn.setMinimumHeight(42)
        print_monthly_btn.clicked.connect(self._print_monthly_deductions)
        header_row.addWidget(print_monthly_btn, alignment=Qt.AlignVCenter)

        layout.addLayout(header_row)

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

        # ═══ Tab 2: All Deductions (Sick Leaves + Manual) ═══
        self.all_deductions_tab = QWidget()
        all_layout = QVBoxLayout(self.all_deductions_tab)
        all_layout.setContentsMargins(8, 10, 8, 8)
        all_layout.setSpacing(8)

        all_info = QLabel("📋 جميع الاقتطاعات — عطل مرضية + عطل أمومة + غير مبرر + تسوية + يدوي")
        all_info.setStyleSheet("font-size: 13px; color: #1e40af; font-weight: bold; padding: 8px; "
                                "background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;")
        all_info.setWordWrap(True)
        all_layout.addWidget(all_info)

        self.all_deductions_table = QTableWidget()
        self.all_deductions_table.setLayoutDirection(Qt.RightToLeft)
        self.all_deductions_table.setColumnCount(7)
        self.all_deductions_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "نوع الغياب", "عدد الأيام",
            "شهر الاقتطاع", "تاريخ الشهادة الطبية", "إجراءات"
        ])
        self.all_deductions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.all_deductions_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.all_deductions_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.all_deductions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.all_deductions_table.setAlternatingRowColors(True)
        self.all_deductions_table.verticalHeader().setVisible(False)
        self.all_deductions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.all_deductions_table.setShowGrid(False)
        self.all_deductions_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        all_layout.addWidget(self.all_deductions_table, stretch=1)

        self.tabs.addTab(self.all_deductions_tab, "📋  جميع الاقتطاعات")

        layout.addWidget(self.tabs, stretch=1)

    # ──────────────────────────────────────────────
    # Add Manual Deduction
    # ──────────────────────────────────────────────
    def _add_manual_deduction(self):
        dialog = ManualDeductionDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            db.add_manual_deduction(data)
            QMessageBox.information(self, "نجاح", "✅ تم إضافة الاقتطاع بنجاح.")
            self.refresh()

    def _delete_manual_deduction(self, md_id):
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            "هل تريد حذف هذا الاقتطاع اليدوي؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_manual_deduction(md_id)
            self.refresh()

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
            "<p style=\"font-size: 18px; font-weight: bold;  text-align: right;\">"
            "نحيطكم علما أننا اقترحنا: %s<br/>"
            "وذلك للأسباب التالية : %s"
            "</p>"
        ) % (proposed, reason_text)

        core_content = """
            <div style="margin-top: 0px; text-align:center; font-weight: bold;">
                <div style="text-align:center;font-size:20px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="text-align:center;font-size:20px;">وزارة التربية الوطنية</div>
            </div>
            <table width="100%%" style="font-weight: bold; font-size: 18px;">
                <tr style="">
                <td style="font-size:18px;text-align:right; width:50%%;">
                      
                      مديرية التربية لولاية %(wilaya)s
                    </td>
                    <td style="font-size:18px;text-align:left; width:50%%;">
                        السنة الدراسية: %(school_year)s
                    </td>
                    
                </tr>
                <tr style="">
                     <td colspan="2" style="font-size:18px;text-align:right; width:50%%;">
                        %(school)s - %(school_addr)s
                    </td>
                 
                   
                </tr>
                <tr style="">
                     <td colspan="2" style="font-size:18px;text-align:right; width:50%%;">
                        رمز المؤسسة: %(school_code)s
                    </td>
                  
                   
                </tr>
                <tr style="">
                     <td style="font-size:18px;text-align:right; width:50%%;">
                      
                    </td>
                       <td style="font-size:16px;text-align:center; width:50%%;">
                       إلى
                    </td>
                   
                </tr>
                <tr style="">
                     <td style="font-size:18px;text-align:right; width:50%%;">
                    
                    </td>
                    <td style="font-size:16px;text-align:center; width:50%%;">
                     السيد(ة): <b>%(emp_name)s</b>
                    </td>
                   
                </tr>
                <tr style="">
                    <td style="font-size:16px;text-align:right; width:50%%;">
                     
                    </td>
                    <td style="font-size:16px;text-align:center; width:50%%;">
                     الرتبة: <b>%(emp_grade)s</b>
                    </td>
                     
                </tr>
            
            </table>
           <table width="100%%" style="font-weight: bold; font-size: 16px;">
            <tr style="">
                <td colspan="2" style="font-size: 18px; text-align:right; width:100%%;">
                    الموضوع: إشعار بالخصم
                </td>
               
            </tr>
            <tr style="">
                <td colspan="2" style="font-size: 16px; text-align:right; width:100%%;">
                    عطفا على الاستفسار المؤرخ في: <b>%(inquiry_date)s</b>، 
              
                </td>
              
            </tr>
            <tr style="">
                <td colspan="2" style="font-size: 18px; text-align:right; width:100%%;">
                  %(deduction_details)s
                </td>
              
            </tr>
            <tr style="">
                <td colspan="2" style="font-size: 14px; text-align:right; width:100%%;">
                  %(notes_section)s
                </td>
              
            </tr>
            <tr style="">
             
                <td style="font-size: 13px; text-align:right; width:60%%;">
                نسخة موجهة إلى:
                </td>
                 <td style="text-align:center; width:40%%;">
حرر بـ%(school_address)s في: %(today)s
                </td>
            </tr>
            <tr style="">
                 <td style="font-size: 13px; text-align:right; width:60%%;">
- ملف المعني بالأمر
                </td>
                <td style="font-size: 16px; text-align:center; width:40%%;">
   المدير(ة)
                </td>
           
              
            </tr>
            <tr style="">
              
                <td style="font-size: 13px; text-align:right; width:60%%;">
- م.ت.ن. المستخدمين
                </td>
                <td style="font-size: 16px; text-align:center; width:40%%;">
                <b>%(director)s</b>   
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
                '<p style="font-size:14px; font-weight:bold; color: #666;">ملاحظات: %s</p>'
                % inquiry["decision_notes"]
            ) if inquiry["decision_notes"] else "",
            "today": today, "director": director,
        }

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                    }
            
        </style></head>
        <body style="margin: 0; padding: 0;" dir="rtl">
            <table height="100%%" width="100%%" cellspacing="0" cellpadding="0"
         style="border-collapse: collapse; margin: 0; padding: 0;">
                <tr>
                    <td width="49%%" style="padding: 3px;">
                        %s
                    </td>
                    <td width="1%%" style="border: none;"></td>
                    <td width="49%%" style=" padding: 3px; border-right: 1px dashed #999;">
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
    # Print: Monthly Deductions (Unified per category)
    # ──────────────────────────────────────────────
    def _is_teacher(self, grade):
        """Check if this grade is a teacher grade."""
        if not grade:
            return False
        return "أستاذ" in grade

    def _print_monthly_deductions(self):
        """Print monthly deduction tables split by category:
        - One document for teachers with ALL deduction types
        - One document for admin/workers with ALL deduction types
        """
        month_filter = self.filter_month.currentData()
        if month_filter == "الكل":
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار شهر محدد لطباعة الاقتطاعات.")
            return

        month_index = MONTHS_AR.index(month_filter) + 1
        current_year = QDate.currentDate().year()

        settings = db.get_all_settings()

        # ── Gather ALL deduction rows ──
        all_rows = []

        # 1. Unjustified deductions from inquiries (director salary deductions)
        all_inquiries = db.get_decided_inquiries()
        for inq in all_inquiries:
            decision = inq["director_decision"]
            if decision == "خصم من الراتب" and inq["deduction_month"] == month_filter:
                emp = db.get_employee(inq["employee_id"])
                if emp:
                    all_rows.append({
                        "name": db.get_employee_full_name(emp),
                        "grade": emp["grade"] or "",
                        "code": emp["account_number"] or "",
                        "days": inq["deduction_days"],
                        "type": "غير مبرر",
                        "cert_date": "",
                    })

        # 2. Sick leaves
        all_sick_leaves = db.get_all_sick_leaves()
        for sl in all_sick_leaves:
            sl_d = dict(sl)
            chunks = self._calc_sick_leave_chunks(sl_d["start_date"], sl_d["duration_days"])
            for chunk in chunks:
                if chunk["month_name"] == month_filter:
                    emp = db.get_employee(sl_d["employee_id"])
                    if emp:
                        all_rows.append({
                            "name": db.get_employee_full_name(emp),
                            "grade": emp["grade"] or "",
                            "code": emp["account_number"] or "",
                            "days": chunk["days"],
                            "type": "عطلة مرضية",
                            "cert_date": sl_d.get("medical_cert_date", "") or "",
                        })

        # 3. Manual deductions
        all_manual = db.get_all_manual_deductions()
        for md in all_manual:
            md_d = dict(md)
            if md_d["deduction_month"] == month_filter:
                all_rows.append({
                    "name": md_d["employee_name"],
                    "grade": md_d["employee_grade"] or "",
                    "code": md_d.get("employee_code", "") or "",
                    "days": md_d["duration_days"],
                    "type": md_d["deduction_type"],
                    "cert_date": md_d.get("cert_date", "") or "",
                })

        # ── Split by category ──
        teacher_rows = [r for r in all_rows if self._is_teacher(r["grade"])]
        admin_rows = [r for r in all_rows if not self._is_teacher(r["grade"])]

        # Sort by type within each category
        type_order = {"عطلة مرضية": 0, "عطلة أمومة": 1, "غير مبرر": 2, "تسوية": 3}
        teacher_rows.sort(key=lambda r: type_order.get(r["type"], 99))
        admin_rows.sort(key=lambda r: type_order.get(r["type"], 99))

        # ── Generate pages ──
        pages = []
        today = datetime.now().strftime("%d-%m-%Y")

        if admin_rows:
            pages.append(self._generate_unified_deduction_page(
                month_name=month_filter,
                admin_label="تسيير نفقات الموظفين الإداريين والعمال المهنيين",
                rows=admin_rows,
                settings=settings,
                today=today,
            ))

        if teacher_rows:
            pages.append(self._generate_unified_deduction_page(
                month_name=month_filter,
                admin_label="تسيير نفقات الأساتذة",
                rows=teacher_rows,
                settings=settings,
                today=today,
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
          
            body {
                font-family: 'Amiri', 'Traditional Arabic', serif;
               
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

    def _generate_unified_deduction_page(self, month_name, admin_label, rows, settings, today):
        """Generate a single unified deduction page HTML with all types."""
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
            cert_display = r["cert_date"].replace("-", "/") if r["cert_date"] else ""
            table_rows += (
                '<tr style="">'
                '<td style="padding:1px;border:1px solid #333;text-align:center;">%02d</td>'
                '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                '<td style="padding:1px;border:1px solid #333;text-align:center;">%s</td>'
                '<td style="padding:1px;border:1px solid #333;text-align:center;font-weight:bold;">%s</td>'
                '</tr>'
            ) % ( idx + 1, r["code"],r["name"],r["grade"], r["type"], "%02d يوم" % r["days"], cert_display )

        header_cols = (
            '<th style="padding:1px;border:1px solid #333;">الرقم</th>'
            '<th style="padding:1px;border:1px solid #333;">رمز الموظف</th>'
            '<th style="padding:1px;border:1px solid #333;">اسم ولقب الموظف (ة)</th>'
            '<th style="padding:1px;border:1px solid #333;">الرتبة</th>'
            '<th style="padding:1px;border:1px solid #333;">نوع الغياب</th>'
            '<th style="padding:1px;border:1px solid #333;">عدد الأيام</th>'
            '<th style="padding:1px;border:1px solid #333;">تاريخ الشهادة الطبية</th>'
        )
        
        page_html = """
            <div style=" text-align: center; font-weight: bold; font-size: 20px;">
                <div style="text-align: center; font-size: 20px;">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                <div style="text-align: center; font-size: 20px;">وزارة التربية الوطنية</div>
            </div>

            <table width="100%%" style=" font-weight: bold; font-size: 18px;">
                <tr style="">
                   
                    <td style="text-align: right; width: auto;">مديرية التربية لولاية %(wilaya)s</td>
                </tr>
                <tr style="">
                  
                    <td  style="text-align: right; width: auto;">%(school)s - %(school_address)s</td>
                </tr>
                <tr style="">
                   
                    <td style="text-align: right; width: auto;">رمز المؤسسة : %(school_code)s</td>
                </tr>
                <tr style="">
                    
                  
               
                    <td dir="rtl" style=text-align: right;">
                     <span>الرقم:.............&rlm;/&rlm; %(school_initials)s&rlm;/&rlm; %(year)s</span>
                    </td>
                    </tr>
            </table>

            <div style="margin-top: 10px;margin-bottom: 10px;text-align: center;">
                <div style=" font-size: 20px; font-weight: bold;">جدول الاقتطاعات المبررة و غير المبررة</div>
                <div style="font-size: 18px; font-weight: bold;">لشهر: %(month_name)s %(year)s</div>
            </div>

            <div align="right" style=" font-size: 18px; font-weight: bold;">
                الإدارة : %(admin_label)s .
            </div>

            <table width="100%%" style="margin-top: 5px;margin-bottom: 10px;font-size: 16px; border: 1px solid #333; margin-bottom: 2px;">
                <tr style="font-weight: bold;">
                    %(header_cols)s
                </tr>
                %(table_rows)s
            </table>

            <table width="100%%" style="margin-top: 5px;margin-bottom: 10px;font-size: 16px; font-weight: bold; margin-top: 2px;">
                <tr style="">
                    <td style="text-align: center; width: 20%%;">تاريخ استلام:</td>
                     <td style="text-align: left; width: 40%%;"></td>
                    <td style="text-align: center; width: 40%%;">%(school_address)s في %(today)s</td>
                </tr>
                <tr style="">
                    <td style="text-align: center; width: 20%%;">.............................</td>
                     <td style="text-align: left; width: 40%%;"></td>
                    <td style="text-align: center; width: 40%%;">المدير</td>
                </tr>
                <tr style="">
                    <td style="text-align: center; width: 20%%;">.............................</td>
                     <td style="text-align: left; width: 40%%;"></td>
                    <td style="text-align: center; width: 40%%;">%(director)s</td>
                </tr>
            </table>
        """ % {
            "wilaya": wilaya,
            "school": school,
            "school_code": school_code,
            "school_address": school_address,
            "school_initials": school_initials,
            "year": current_year,
            "month_name": month_name,
            "admin_label": admin_label,
            "header_cols": header_cols,
            "table_rows": table_rows,
            "today": today,
            "director": director,
        }
        return page_html

    def _get_school_initials(self, school_name):
        """Extract initials from school name, ignoring honorary/type prefixes."""
        if not school_name:
            return ""

        skip_words = {
            "الشهيد", "الشهيدة", "المجاهد", "المجاهدة", "العلامة",
            "القائد", "الأمير", "الشيخ", "الإمام", "الرئيس",
            "البطل", "العقيد", "الرائد", "المقاوم", "المناضل",
            "شهيد", "مجاهد", "علامة", "قائد", "أمير", "شيخ",
        }

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
            bare = clean.lstrip("ال") if clean.startswith("ال") else clean
            if clean in skip_words or bare in skip_words:
                continue
            if clean in type_words:
                initials.append(clean[0])
                continue
            initials.append(clean[0])

        return ".".join(initials)

    # ──────────────────────────────────────────────
    # Refresh
    # ──────────────────────────────────────────────
    def refresh(self):
        self._refresh_unjustified()
        self._refresh_all_deductions()

    def _refresh_stats(self):
        pass

    def _calc_sick_leave_chunks(self, start_date_str, duration_days):
        """Calculate deduction: entire duration in a single month (month after sick leave start)."""
        try:
            date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
        except ValueError:
            try:
                date_obj = datetime.strptime(start_date_str, "%Y/%m/%d")
            except:
                return [{"month_name": MONTHS_AR[datetime.now().month - 1], "days": duration_days}]
                
        month = date_obj.month
        # The deduction month is the month AFTER the sick leave starts
        if month == 12:
            month = 1
        else:
            month += 1
            
        # All deduction in a single month
        return [{"month_name": MONTHS_AR[month - 1], "days": duration_days}]

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

    def _refresh_all_deductions(self):
        """Refresh the unified 'all deductions' tab with all types combined."""
        month_filter = self.filter_month.currentData()
        
        display_rows = []
        
        # 1. Sick leaves
        sick_leaves = db.get_all_sick_leaves()
        for sl in sick_leaves:
            sl_d = dict(sl)
            chunks = self._calc_sick_leave_chunks(sl_d["start_date"], sl_d["duration_days"])
            for chunk in chunks:
                if month_filter == "الكل" or chunk["month_name"] == month_filter:
                    display_rows.append({
                        "employee_name": sl_d["employee_name"],
                        "employee_grade": sl_d["employee_grade"] or "",
                        "type": "عطلة مرضية",
                        "days": chunk["days"],
                        "month": chunk["month_name"],
                        "cert_date": (sl_d.get("medical_cert_date", "") or "").replace("-", "/"),
                        "source": "sick_leave",
                        "source_id": sl_d["id"],
                    })
        
        # 2. Manual deductions
        all_manual = db.get_all_manual_deductions()
        for md in all_manual:
            md_d = dict(md)
            ded_month = md_d["deduction_month"]
            if month_filter == "الكل" or ded_month == month_filter:
                display_rows.append({
                    "employee_name": md_d["employee_name"],
                    "employee_grade": md_d["employee_grade"] or "",
                    "type": md_d["deduction_type"],
                    "days": md_d["duration_days"],
                    "month": ded_month,
                    "cert_date": (md_d.get("cert_date", "") or "").replace("-", "/"),
                    "source": "manual",
                    "source_id": md_d["id"],
                })

        # 3. Unjustified deductions from inquiries
        all_inquiries = db.get_decided_inquiries()
        for inq in all_inquiries:
            decision = inq["director_decision"]
            if decision == "خصم من الراتب":
                ded_month = inq["deduction_month"]
                if month_filter == "الكل" or ded_month == month_filter:
                    display_rows.append({
                        "employee_name": inq["employee_name"],
                        "employee_grade": inq["employee_grade"] or "",
                        "type": "غير مبرر",
                        "days": inq["deduction_days"],
                        "month": ded_month,
                        "cert_date": "",
                        "source": "inquiry",
                        "source_id": inq["id"],
                    })

        # Sort by type
        type_order = {"عطلة مرضية": 0, "عطلة أمومة": 1, "غير مبرر": 2, "تسوية": 3}
        display_rows.sort(key=lambda r: type_order.get(r["type"], 99))

        self.all_deductions_table.setRowCount(0)
        self.all_deductions_table.setRowCount(len(display_rows))

        type_colors = {
            "عطلة مرضية": ("#1e40af", "#eff6ff", "🏥"),
            "عطلة أمومة": ("#7c3aed", "#f5f3ff", "👶"),
            "غير مبرر": ("#b91c1c", "#fef2f2", "🚫"),
            "تسوية": ("#0d9488", "#f0fdfa", "⚖️"),
        }

        for row, item in enumerate(display_rows):
            self.all_deductions_table.setItem(row, 0, self._item(item["employee_name"]))
            self.all_deductions_table.setItem(row, 1, self._item(item["employee_grade"]))

            # Type badge
            fg, bg, emoji = type_colors.get(item["type"], ("#334155", "#f1f5f9", "📌"))
            type_lbl = QLabel("%s %s" % (emoji, item["type"]))
            type_lbl.setAlignment(Qt.AlignCenter)
            type_lbl.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: %s; background: %s; "
                "border-radius: 6px; padding: 3px 8px;" % (fg, bg)
            )
            self.all_deductions_table.setCellWidget(row, 2, type_lbl)

            days_item = self._item("%d يوم" % item["days"])
            days_item.setFont(QFont("Amiri", 11, QFont.Bold))
            self.all_deductions_table.setItem(row, 3, days_item)

            month_item = self._item(item["month"])
            month_item.setFont(QFont("Amiri", 11, QFont.Bold))
            month_item.setForeground(QColor("#2563eb"))
            self.all_deductions_table.setItem(row, 4, month_item)

            self.all_deductions_table.setItem(row, 5, self._item(item["cert_date"] or "—"))

            # Actions — delete button for manual deductions only
            actions = QWidget()
            actions.setLayoutDirection(Qt.RightToLeft)
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)

            if item["source"] == "manual":
                del_btn = ActionButton("", "🗑", "icon")
                del_btn.setToolTip("حذف الاقتطاع اليدوي")
                md_id = item["source_id"]
                del_btn.clicked.connect(
                    lambda checked, mid=md_id: self._delete_manual_deduction(mid)
                )
                al.addWidget(del_btn)
            
            al.addStretch()
            self.all_deductions_table.setCellWidget(row, 6, actions)
            self.all_deductions_table.setRowHeight(row, 44)


    def _item(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

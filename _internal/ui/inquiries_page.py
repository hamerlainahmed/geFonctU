# -*- coding: utf-8 -*-
"""
Inquiries Management Page — Full inquiry lifecycle:
 • View all inquiries with status filters
 • Director decisions: salary deduction, productivity deduction, postpone, cancel
 • Animated decision dialog with dynamic form
 • Delete / cancel inquiries
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QLabel, QFrame, QSizePolicy, QTextEdit, QTabWidget,
    QComboBox, QSpinBox, QGraphicsDropShadowEffect, QGridLayout,
    QPushButton, QMenu,
)
from PyQt5.QtCore import Qt, QDate, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor, QFont

from ui.widgets import (
    ArabicLineEdit, ArabicLabel, ArabicComboBox, ArabicDateEdit,
    Card, StatCard, ActionButton, ArabicFormLayout, Separator,
)
import database as db
from datetime import datetime


MONTHS_AR = [
    "جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
    "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

QUARTERS_AR = [
    "الثلاثي الأول (جانفي - مارس)",
    "الثلاثي الثاني (أفريل - جوان)",
    "الثلاثي الثالث (جويلية - سبتمبر)",
    "الثلاثي الرابع (أكتوبر - ديسمبر)",
]

DECISION_TYPES = [
    ("خصم من الراتب", "💰", "#dc2626", "#fef2f2", "#fecaca"),
    ("خصم من المردودية", "📉", "#d97706", "#fffbeb", "#fde68a"),
    ("إرجاء", "⏳", "#2563eb", "#eff6ff", "#bfdbfe"),
    ("بدون إجراء", "✅", "#059669", "#ecfdf5", "#a7f3d0"),
]

STATUS_BADGES = {
    "معلّق": ("badge_warning", "⏳ معلّق"),
    "تم البت": ("badge_success", "✅ تم البت"),
    "مُرجأ": ("badge_info", "⏳ مُرجأ"),
    "ملغى": ("badge_danger", "🚫 ملغى"),
}


class DecisionCard(QFrame):
    """A clickable card for selecting a director decision type."""

    def __init__(self, text, icon, color, bg, border_color, parent=None):
        super().__init__(parent)
        self.decision_text = text
        self._color = color
        self._bg = bg
        self._border = border_color
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(60)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(28)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 20px; background: transparent;")
        layout.addWidget(icon_lbl)

        text_lbl = QLabel(text)
        text_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: %s; background: transparent;" % color
        )
        layout.addWidget(text_lbl, stretch=1)

        self._icon_lbl = icon_lbl
        self._text_lbl = text_lbl
        self._set_default_style()

    def _set_default_style(self):
        self.setStyleSheet("""
            QFrame { background-color: #f8fafc; border: 2px solid #e5e7eb; border-radius: 12px; }
            QFrame:hover { border-color: %s; background-color: %s; }
        """ % (self._border, self._bg))

    def set_selected(self, selected):
        if selected:
            self.setStyleSheet(
                "QFrame { background-color: %s; border: 2px solid %s; border-radius: 12px; }"
                % (self._bg, self._color)
            )
            self._text_lbl.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: %s; background: transparent;" % self._color
            )
        else:
            self._set_default_style()
            self._text_lbl.setStyleSheet(
                "font-size: 13px; font-weight: bold; color: %s; background: transparent;" % self._color
            )


class DirectorDecisionDialog(QDialog):
    """Premium dialog for the director to make a decision on an inquiry."""

    def __init__(self, inquiry, employee, parent=None):
        super().__init__(parent)
        self.inquiry = inquiry
        self.employee = employee
        emp_name = db.get_employee_full_name(employee)
        self.setWindowTitle("قرار المدير — %s" % emp_name)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(600)
        self._selected_decision = None
        self._build_ui()

    def _build_ui(self):
        from PyQt5.QtWidgets import QScrollArea

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 8)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setLayoutDirection(Qt.RightToLeft)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(content)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 14, 20, 8)

        # Header
        header = QLabel("⚖️ قرار المدير")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        layout.addWidget(header)

        # Inquiry Info Card — compact
        emp_name = db.get_employee_full_name(self.employee)
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                     stop:0 #eff6ff, stop:1 #dbeafe);
                     border: 1px solid #bfdbfe; border-radius: 10px; }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 8, 12, 8)
        info_layout.setSpacing(2)

        info_lbl1 = QLabel("👤 %s  |  %s" % (emp_name, self.employee["grade"] or ""))
        info_lbl1.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e40af; background: transparent;")
        info_layout.addWidget(info_lbl1)

        info_lbl2 = QLabel("📝 %s  |  %s %s" % (
            self.inquiry["inquiry_type"],
            self.inquiry["inquiry_date"],
            self.inquiry["inquiry_time"] or "",
        ))
        info_lbl2.setStyleSheet("font-size: 12px; color: #1e40af; background: transparent;")
        info_layout.addWidget(info_lbl2)

        layout.addWidget(info_frame)

        # Decision Type Selection
        decision_header = QLabel("⚡ اختر نوع القرار:")
        decision_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #374151; margin-top: 4px;")
        layout.addWidget(decision_header)

        decision_grid = QGridLayout()
        decision_grid.setSpacing(6)
        self.decision_cards = []
        for idx, (text, icon, color, bg, border) in enumerate(DECISION_TYPES):
            card = DecisionCard(text, icon, color, bg, border)
            card.setFixedHeight(46)
            card.mousePressEvent = lambda event, t=text: self._select_decision(t)
            decision_grid.addWidget(card, idx // 2, idx % 2)
            self.decision_cards.append(card)
        layout.addLayout(decision_grid)

        # Dynamic decision details container
        self.details_frame = QFrame()
        self.details_frame.setStyleSheet("""
            QFrame { background-color: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; }
        """)
        details_layout = QVBoxLayout(self.details_frame)
        details_layout.setContentsMargins(12, 8, 12, 8)
        details_layout.setSpacing(6)

        # Salary deduction fields
        self.salary_frame = QWidget()
        salary_layout = QHBoxLayout(self.salary_frame)
        salary_layout.setContentsMargins(0, 0, 0, 0)
        salary_layout.setSpacing(8)

        salary_layout.addWidget(QLabel("عدد أيام الخصم:"))
        self.deduction_days_spin = QSpinBox()
        self.deduction_days_spin.setRange(1, 30)
        self.deduction_days_spin.setValue(1)
        self.deduction_days_spin.setLayoutDirection(Qt.RightToLeft)
        salary_layout.addWidget(self.deduction_days_spin)

        salary_layout.addWidget(QLabel("شهر الخصم:"))
        self.deduction_month_combo = ArabicComboBox()
        for m in MONTHS_AR:
            self.deduction_month_combo.addItem(m)
        current_month = datetime.now().month
        self.deduction_month_combo.setCurrentIndex(current_month - 1)
        salary_layout.addWidget(self.deduction_month_combo)
        salary_layout.addStretch()

        self.salary_frame.hide()
        details_layout.addWidget(self.salary_frame)

        # Performance deduction fields
        self.perf_frame = QWidget()
        perf_layout = QHBoxLayout(self.perf_frame)
        perf_layout.setContentsMargins(0, 0, 0, 0)
        perf_layout.setSpacing(8)

        perf_layout.addWidget(QLabel("الثلاثي:"))
        self.deduction_quarter_combo = ArabicComboBox()
        for q in QUARTERS_AR:
            self.deduction_quarter_combo.addItem(q)
        current_quarter = (datetime.now().month - 1) // 3
        self.deduction_quarter_combo.setCurrentIndex(current_quarter)
        perf_layout.addWidget(self.deduction_quarter_combo)
        perf_layout.addStretch()

        self.perf_frame.hide()
        details_layout.addWidget(self.perf_frame)

        # Notes
        notes_lbl = QLabel("ملاحظات (اختياري):")
        notes_lbl.setStyleSheet("font-size: 11px; color: #64748b;")
        details_layout.addWidget(notes_lbl)

        self.decision_notes = QTextEdit()
        self.decision_notes.setLayoutDirection(Qt.RightToLeft)
        self.decision_notes.setPlaceholderText("ملاحظات إضافية...")
        self.decision_notes.setMaximumHeight(50)
        details_layout.addWidget(self.decision_notes)

        self.details_frame.hide()
        layout.addWidget(self.details_frame)

        scroll.setWidget(content)
        main_layout.addWidget(scroll, stretch=1)

        # Buttons — OUTSIDE scroll area so they're always visible
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 6, 20, 0)
        btn_layout.setSpacing(10)

        save_btn = ActionButton("حفظ القرار", "✔", "success")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self._save)

        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # Limit height
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            self.setMaximumHeight(int(screen.availableGeometry().height() * 0.7))

    def _select_decision(self, decision_type):
        self._selected_decision = decision_type
        for card in self.decision_cards:
            card.set_selected(card.decision_text == decision_type)

        self.details_frame.show()

        if decision_type == "خصم من الراتب":
            self.salary_frame.show()
            self.perf_frame.hide()
        elif decision_type == "خصم من المردودية":
            self.salary_frame.hide()
            self.perf_frame.show()
        else:
            self.salary_frame.hide()
            self.perf_frame.hide()

    def _save(self):
        if not self._selected_decision:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار نوع القرار")
            return
        self.accept()

    def get_data(self):
        decision = self._selected_decision
        status = "تم البت"
        if decision == "إرجاء":
            status = "مُرجأ"

        return {
            "director_decision": decision,
            "deduction_days": self.deduction_days_spin.value() if decision == "خصم من الراتب" else 0,
            "deduction_month": self.deduction_month_combo.currentText() if decision == "خصم من الراتب" else "",
            "deduction_quarter": self.deduction_quarter_combo.currentText() if decision == "خصم من المردودية" else "",
            "decision_notes": self.decision_notes.toPlainText().strip(),
            "status": status,
        }


class InquiriesPage(QWidget):
    """Inquiry management page — track, decide, and manage employee inquiries."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 16)

        # Header row
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header = QLabel("الاستفسارات وقرارات المدير 📝")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        header_row.addWidget(header)
        header_row.addStretch()
        layout.addLayout(header_row)

        # Stats removed to save space

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.RightToLeft)

        # Tab 1: All inquiries
        self.all_tab = QWidget()
        all_layout = QVBoxLayout(self.all_tab)
        all_layout.setContentsMargins(8, 10, 8, 8)
        all_layout.setSpacing(8)

        # Filter row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.filter_status = ArabicComboBox()
        self.filter_status.addItem("جميع الحالات", None)
        self.filter_status.addItem("⏳ معلّقة", "معلّق")
        self.filter_status.addItem("✅ تم البت", "تم البت")
        self.filter_status.addItem("⏳ مُرجأة", "مُرجأ")
        self.filter_status.addItem("🚫 ملغاة", "ملغى")
        self.filter_status.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(QLabel("الحالة:"))
        filter_row.addWidget(self.filter_status)
        filter_row.addStretch()

        all_layout.addLayout(filter_row)

        self.inquiries_table = QTableWidget()
        self.inquiries_table.setLayoutDirection(Qt.RightToLeft)
        self.inquiries_table.setColumnCount(8)
        self.inquiries_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "نوع الاستفسار", "التاريخ والتوقيت",
            "التفاصيل", "الحالة", "القرار", "إجراءات"
        ])
        self.inquiries_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.inquiries_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.inquiries_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.inquiries_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.inquiries_table.setAlternatingRowColors(True)
        self.inquiries_table.verticalHeader().setVisible(False)
        self.inquiries_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.inquiries_table.setShowGrid(False)
        self.inquiries_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        all_layout.addWidget(self.inquiries_table, stretch=1)

        self.tabs.addTab(self.all_tab, "📋  جميع الاستفسارات")

        # Tab 2: Pending inquiries (quick view)
        self.pending_tab = QWidget()
        pending_layout = QVBoxLayout(self.pending_tab)
        pending_layout.setContentsMargins(8, 10, 8, 8)
        pending_layout.setSpacing(8)

        pending_info = QLabel("⏳ الاستفسارات المعلّقة التي تحتاج لقرار المدير")
        pending_info.setStyleSheet("font-size: 14px; color: #92400e; font-weight: bold; padding: 8px; "
                                    "background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;")
        pending_layout.addWidget(pending_info)

        self.pending_table = QTableWidget()
        self.pending_table.setLayoutDirection(Qt.RightToLeft)
        self.pending_table.setColumnCount(7)
        self.pending_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "نوع الاستفسار", "التاريخ والتوقيت",
            "التفاصيل", "الحالة", "إجراءات"
        ])
        self.pending_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pending_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.pending_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pending_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pending_table.setAlternatingRowColors(True)
        self.pending_table.verticalHeader().setVisible(False)
        self.pending_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pending_table.setShowGrid(False)
        self.pending_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pending_layout.addWidget(self.pending_table, stretch=1)

        self.tabs.addTab(self.pending_tab, "⏳  في انتظار القرار")

        layout.addWidget(self.tabs, stretch=1)

    def _apply_filter(self):
        self._refresh_all_table()

    def _open_decision(self, inq_id):
        inquiry = db.get_inquiry(inq_id)
        if not inquiry:
            return
        emp = db.get_employee(inquiry["employee_id"])
        if not emp:
            return

        dialog = DirectorDecisionDialog(inquiry, emp, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            db.update_inquiry_decision(inq_id, data)

            decision = data["director_decision"]
            if decision == "خصم من الراتب":
                msg = "✅ تم تسجيل قرار الخصم من الراتب (%d يوم) — شهر %s" % (
                    data["deduction_days"], data["deduction_month"])
            elif decision == "خصم من المردودية":
                msg = "✅ تم تسجيل قرار الخصم من المردودية — %s" % data["deduction_quarter"]
            elif decision == "إرجاء":
                msg = "⏳ تم إرجاء الاستفسار — سيُنظر فيه لاحقاً"
            else:
                msg = "✅ تم تسجيل القرار: بدون إجراء"

            QMessageBox.information(self, "نجاح", msg)
            self.refresh()

    def _cancel_inquiry(self, inq_id):
        reply = QMessageBox.question(
            self, "تأكيد الإلغاء",
            "هل أنت متأكد من إلغاء هذا الاستفسار؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.update_inquiry_status(inq_id, "ملغى")
            QMessageBox.information(self, "نجاح", "✅ تم إلغاء الاستفسار")
            self.refresh()

    def _delete_inquiry(self, inq_id):
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            "⚠️ هل أنت متأكد من حذف هذا الاستفسار نهائياً؟\nلا يمكن التراجع عن هذا الإجراء.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_inquiry(inq_id)
            QMessageBox.information(self, "نجاح", "✅ تم حذف الاستفسار نهائياً")
            self.refresh()

    def _reprint_inquiry(self, inq_id):
        """Reprint the original inquiry document."""
        inquiry = db.get_inquiry(inq_id)
        if not inquiry:
            return
        emp = db.get_employee(inquiry["employee_id"])
        if not emp:
            return

        from ui.inquiry_dialog import InquiryDialog
        # Generate HTML using the inquiry data
        settings = db.get_all_settings()
        html = self._generate_inquiry_html(inquiry, emp, settings)
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=True)
        dialog.exec_()

    def _generate_inquiry_html(self, inquiry, emp, settings):
        """Generate inquiry HTML matching the official template — 2×A5 on A4 landscape."""
        from datetime import datetime
        import database as db

        school      = db.get_formatted_school_name()
        school_type = settings.get("school_type", "المدرسة")
        wilaya      = settings.get("wilaya", "")
        school_addr = settings.get("school_address", school)
        
        emp_dict = dict(emp) if emp else {}
        inq_dict = dict(inquiry) if inquiry else {}
        
        emp_name    = db.get_employee_full_name(emp) if emp else ""
        emp_grade   = emp_dict.get("grade") or ""
        subject     = emp_dict.get("subject") or ""
        subject_part = " ، مادة: %s" % subject if subject else ""
        today       = datetime.now().strftime("%Y/%m/%d")

        inquiry_type = inq_dict.get("inquiry_type", "غياب")
        details = inq_dict.get("details") or ""
        
        reason_line = ""
        if inquiry_type == "غياب":
            reason_line = "<b>%s</b>" % details
        elif inquiry_type == "تأخر":
            reason_line = "<b>%s</b>" % details
        else:
            reason_line = "<b>%s</b>" % details

        school_stage = settings.get("school_stage", "متوسط")
        if school_stage == "إبتدائي":
            decree_text = "* بناءً على القرار رقم: 839 مؤرخ في 13 فبرير 1991 ،يحدد مهام مديري المدارس الأساسية للطورين الأول والثاني الابتدائيات."
        elif school_stage == "ثانوي":
            decree_text = "* بناءً على القرار رقم: 297 مؤرخ في 17 جوان 2006 يعدل و يتمم القرار 176 المؤرخ في 02 مارس 1991 المحدد لمهام مدير مؤسسة التعليم الثانوي."
        else:
            decree_text = "* بناءً على القرار رقم: 175 المؤرخ في 1991/03/02 المحدد لمهام مدير المدرسة الأساسية"

        # Build the reference line for the printed document
        inq_ref = inq_dict.get("inquiry_reference") or ""
        if inq_ref == "ملاحظات المدير":
            reference_text = "ملاحظات المدير"
        elif inq_ref == "المصلحة البيداغوجية":
            reference_text = "تقرير المصلحة البيداغوجية"
        elif inq_ref == "المصلحة الاقتصادية":
            reference_text = "تقرير المصلحة الاقتصادية"
        else:
            reference_text = "تقرير المصلحة"

        # ── CSS shared by both copies ─────────────────────────────────────
        css = """
        <style>
          body {
            font-family: 'Amiri', 'Traditional Arabic', serif;
            direction: rtl;
            margin: 0; padding: 0;
            color: #000;
            line-height: 1.5;
          }
          .copy {
            width: 100%;
            direction: rtl;
            line-height: 1.5;
          }
          .republic {
            text-align: center;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 5px;
          }
          table.top-table {
            width: 100%;
            margin-bottom: 5px;
            font-size: 13px;
            font-weight: bold;
          }
          .ref-box {
            border: 1px solid #000;
            padding: 1px;
            font-size: 11px;
            
          }
          .title {
            text-align: center;
            font-size: 22px;
            font-weight: bold;
            text-decoration: underline;
            letter-spacing: 2px;
           
          }
          .body-text {
            font-size: 11px;
            font-weight: bold;
            
           
          }
          .dir-block {
            text-align: center;
            font-size: 12px;
            font-weight: bold;
            
          }
         
          .section-title {
            font-weight: bold;
            font-size: 11px;
            margin-top: 0px;
            
          }
          .dots {
            font-size: 16px;
            line-height: 2;
            color: #333;
          }
          table.sig-table {
            width: 100%;
            margin-top: 0px;
            font-weight: bold;
            font-size: 11px;
            text-align: center;
          }
        </style>
        """

        def one_copy():
            return """
            <div class="copy">
          

              <table style=" font-size: 11px;" cellspacing="0" cellpadding="0" dir="rtl">
            
                 <tr>
               <td colspan="2" style=" font-size: 18px;" align="center" colspan="2">
                    
                الجمهورية الجزائرية الديمقراطية الشعبية              
                </td>
               </tr>
                  <tr>
               <td colspan="2" style=" font-size: 18px;" align="center" colspan="2">

              
                وزارة التربية الوطنية
                </td>
               </tr>
                <tr>
                
                   <td style="width: 45%%;  font-size: 16px;">
                   
                    مديرية التربية لولاية : %(wilaya)s
                 
                  
                  </td>
                    <td rowspan="2"  style="border-radius: 10px; font-size: 11px; border: 1px solid #888; width: 55%%; text-align: center;">
                      * طبقا للقرار الوزاري رقم: 65 المؤرخ في 2018/07/12 المتعلق بتنظيم الجماعة التربوية في المؤسسات التعليمية (أحكام خاصة بالموظفين)<br/>
                      %(decree_text)s
                  </td>
                </tr>
               
                   <tr>
                  <td style="width: 45%%;  font-size: 16px;">
                   
                  
                     %(school)s - %(school_addr)s
                  
                  </td>
                 
                
                </tr>
               
              
                
                <tr>
                  <td align="center" colspan="2" style=" font-size: 22px;padding:5px">
                    إسـتـفـسـار
                  </td>
                </tr>
              </table>

             <table width="100%%" border="0" padding="0px" style="margin-top: 10px;margin-bottom: 10px;font-size: 16px;">
                <tr>
                <td colspan="3">
                <u>الـمـرجـع:</u> بناء على %(reference_text)s بتاريخ : <b>%(today)s</b>
                </td>
                </tr>
                <tr>
              
                     <td >
                السيد (ة) : <b>%(emp_name)s</b>
                </td>
                <td colspan="2">
                الوظيفة : <b>%(emp_grade)s</b> %(subject_part)s
                </td>
                
                
            
                </tr>
                <tr>
                 
                
           
                 <td colspan="2" style="" align="right" font-size="14px" font-weight="bold" >
                يطلب منكم تبرير ما يأتي :

           
                </tr>
                <tr>
                <td colspan="2" style="" align="right" font-size="14px" font-weight="bold">
                %(reason_line)s

                </td>
             
              
                </tr>
                <tr>
                    <td style="width: 65%%;"></td>
                  <td align="center" width="35%%">
                بـ: %(school_addr)s في: %(today)s
                
                </td>
                </tr>
                <tr>
                    <td style="width: 65%%;"></td>
                  <td align="center" width="35%%">
                المديـر
                
                </td>
                </tr>
              </table>

            

            
              <div style="line-height: 2; font-size: 16px;" class="dots">
                * جواب المعني (ة) :..........................................................................
                ..................................................................................................
                ..................................................................................................
              </div>

              <table style="margin-top: 10px;margin-bottom: 10px; font-size: 18px;" width="100%%"  cellspacing="0" cellpadding="0" dir="rtl">
                <tr>
                    <td style="width: 50%%;"></td>
                  <td align="center" style="width: 50%%;">بـ: %(school_addr)s في: ....................</td>
              
                </tr>
                 <tr>
                 <td align="right" style="width: 50%%;"></td>
                 
                  <td align="center" style="font-size: 16px;width: 35%%;">إمضاء المعني (ة)</td>
                  
                </tr>
              </table>
         
              <div style="line-height: 2; font-size: 16px;" class="dots">
                * قرار مدير المؤسسة :.........................................................................
                ..................................................................................................
                ..................................................................................................
              </div>
              <table style=" font-size: 18px;" width="100%%"  cellspacing="0" cellpadding="0" dir="rtl">
                <tr>
                  <td style="width: 50%%;"></td>
                  <td align="center" style="width: 50%%;">بـ: %(school_addr)s في: ....................</td>
                </tr>
                 <tr>
                  <td style="width: 50%%;"></td>
                  <td align="center" style="width: 50%%;"> المديـر</td>
                </tr>
              </table>
            
            </div>
            """ % {
                "wilaya": wilaya, "school_type": school_type, "school": school,
                "school_addr": school_addr, "emp_name": emp_name,
                "emp_grade": emp_grade, "subject_part": subject_part,
                "today": today, "reason_line": reason_line,
                "decree_text": decree_text,
                "reference_text": reference_text,
            }

        copy_html = one_copy()

        # Two A5 copies side by side in one A4 landscape page
        html = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8"/>
%(css)s
</head>
<body style="margin: 0; padding: 0;">
  <table width="100%%" cellspacing="0" cellpadding="0"
         style="border-collapse: collapse; table-layout: fixed; margin: 0; padding: 0;">
    <tr>
    
     
      <td style="width:49%%;padding:5px; vertical-align:top;">
      
        %(copy)s
      </td>
 <td style="width:2%%; "></td>
        <td style="width:49%%; padding:5px;border-right: 1px dashed #888; vertical-align:top; ">
        %(copy)s
      </td>
    </tr>
  </table>
</body>
</html>""" % {"css": css, "copy": copy_html}

        return html


    def refresh(self):
        self._refresh_all_table()
        self._refresh_pending_table()

    def _refresh_stats(self):
        all_inq = db.get_all_inquiries()
        pending = sum(1 for i in all_inq if i["status"] == "معلّق")
        decided = sum(1 for i in all_inq if i["status"] == "تم البت")
        postponed = sum(1 for i in all_inq if i["status"] == "مُرجأ")
        total = len(all_inq)
        self.stat_pending.set_value(pending)
        self.stat_decided.set_value(decided)
        self.stat_postponed.set_value(postponed)
        self.stat_total.set_value(total)

    def _refresh_all_table(self):
        status_filter = self.filter_status.currentData()
        inquiries = db.get_all_inquiries(status_filter)
        self._populate_table(self.inquiries_table, inquiries, show_decision_col=True)

    def _refresh_pending_table(self):
        pending = db.get_all_inquiries("معلّق")
        postponed = db.get_all_inquiries("مُرجأ")
        all_pending = list(pending) + list(postponed)
        self._populate_table(self.pending_table, all_pending, show_decision_col=False)

    def _populate_table(self, table, inquiries, show_decision_col=True):
        table.setRowCount(0)
        table.setRowCount(len(inquiries))

        for row, inq in enumerate(inquiries):
            emp_name = inq.get("employee_name", "") if hasattr(inq, "get") else (
                inq["employee_name"] if "employee_name" in inq.keys() else ""
            )
            emp_grade = inq.get("employee_grade", "") if hasattr(inq, "get") else (
                inq["employee_grade"] if "employee_grade" in inq.keys() else ""
            )

            col = 0
            table.setItem(row, col, self._item(emp_name)); col += 1
            table.setItem(row, col, self._item(emp_grade)); col += 1

            # Type badge
            inq_type = inq["inquiry_type"]
            type_colors = {
                "غياب": "badge_danger",
                "تأخر": "badge_warning",
                "عدم تأدية مهام موكلة للموظف": "badge_info",
            }
            type_label = QLabel(inq_type)
            type_label.setAlignment(Qt.AlignCenter)
            type_label.setObjectName(type_colors.get(inq_type, "badge_info"))
            table.setCellWidget(row, col, type_label); col += 1

            # Date/Time
            date_time = inq["inquiry_date"]
            if inq["inquiry_time"]:
                date_time += "  %s" % inq["inquiry_time"]
            table.setItem(row, col, self._item(date_time)); col += 1

            # Details (truncated)
            details = inq["details"] or "—"
            if len(details) > 50:
                details = details[:50] + "..."
            table.setItem(row, col, self._item(details)); col += 1

            # Status badge
            status = inq["status"]
            badge_name, badge_text = STATUS_BADGES.get(status, ("badge_info", status))
            status_label = QLabel(badge_text)
            status_label.setAlignment(Qt.AlignCenter)
            status_label.setObjectName(badge_name)
            table.setCellWidget(row, col, status_label); col += 1

            if show_decision_col:
                decision = inq["director_decision"] or "—"
                if decision == "خصم من الراتب" and inq["deduction_days"]:
                    decision += " (%d يوم)" % inq["deduction_days"]
                table.setItem(row, col, self._item(decision)); col += 1

            # Actions
            inq_id = inq["id"]
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
            
            if status in ("معلّق", "مُرجأ"):
                decision_action = menu.addAction(get_icon("decision", color="#475569"), "قرار المدير")
                decision_action.triggered.connect(lambda checked, aid=inq_id: self._open_decision(aid))
            
            reprint_action = menu.addAction(get_icon("print", color="#475569"), "إعادة طباعة الاستفسار")
            reprint_action.triggered.connect(lambda checked, aid=inq_id: self._reprint_inquiry(aid))

            if status in ("معلّق", "مُرجأ"):
                cancel_action = menu.addAction(get_icon("cancel", color="#475569"), "إلغاء الاستفسار")
                cancel_action.triggered.connect(lambda checked, aid=inq_id: self._cancel_inquiry(aid))

            delete_action = menu.addAction(get_icon("delete", color="#ef4444"), "حذف الاستفسار")
            delete_action.triggered.connect(lambda checked, aid=inq_id: self._delete_inquiry(aid))

            options_btn.setMenu(menu)
            al.addWidget(options_btn)

            al.addStretch()
            table.setCellWidget(row, col, actions)
            table.setRowHeight(row, 44)

    def _item(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

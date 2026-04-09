# -*- coding: utf-8 -*-
"""
Sick Leave Management Page — Full workflow:
1. Request sick leave (with doctor name)
2. If teacher + >7 days → substitution with full details
3. End of sick leave → resume work document
4. End of substitution → end substitution document + info card
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QMessageBox, QHeaderView, QAbstractItemView,
    QLabel, QGroupBox, QSpacerItem, QSizePolicy, QTextEdit, QTabWidget,
    QFrame, QGridLayout, QPushButton, QMenu, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QScrollArea, QApplication, QSpinBox,
)
from PyQt5.QtCore import Qt, QDate, QMarginsF, QSizeF, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QTextDocument, QTextOption, QColor
from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog

from ui.widgets import (
    ArabicLineEdit, ArabicLabel, ArabicComboBox, ArabicDateEdit,
    Card, StatCard, SearchBar, ActionButton, ArabicFormLayout, Separator,
    PageHeader,
)
from ui.icons import get_icon
import database as db
from datetime import datetime, timedelta


DEGREE_TYPES = ["ليسانس", "ماستر", "مهندس دولة", "ماجيستر", "دكتوراه"]

MONTHS_AR = [
    "جانفي", "فيفري", "مارس", "أفريل", "ماي", "جوان",
    "جويلية", "أوت", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر",
]

LEAVE_TYPES = ["عطلة مرضية", "عطلة أمومة"]


class ToastNotification(QFrame):
    """A modern animated toast notification for sick leave expiry alerts."""

    def __init__(self, message, parent=None, duration=8000, toast_type="warning"):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._duration = duration

        # Style based on type
        styles = {
            "warning": {
                "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fef3c7, stop:1 #fde68a)",
                "border": "#f59e0b",
                "text": "#92400e",
                "icon": "⚠️",
                "title": "تنبيه — عطل مرضية منتهية",
            },
            "info": {
                "bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dbeafe, stop:1 #bfdbfe)",
                "border": "#3b82f6",
                "text": "#1e40af",
                "icon": "ℹ️",
                "title": "معلومة",
            },
        }
        s = styles.get(toast_type, styles["warning"])

        self.setStyleSheet("""
            ToastNotification {
                background: %s;
                border: 2px solid %s;
                border-radius: 12px;
                margin: 4px;
            }
        """ % (s["bg"], s["border"]))

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 50))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Icon
        icon_lbl = QLabel(s["icon"])
        icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        icon_lbl.setFixedWidth(36)
        icon_lbl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.addWidget(icon_lbl)

        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(4)

        title_lbl = QLabel(s["title"])
        title_lbl.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: %s; background: transparent;" % s["text"]
        )
        content_layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            "font-size: 13px; color: %s; background: transparent; line-height: 1.2.5;" % s["text"]
        )
        content_layout.addWidget(msg_lbl)

        layout.addLayout(content_layout, stretch=1)

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setMinimumSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 0, 0, 0.08);
                border: 1px solid rgba(0, 0, 0, 0.12);
                font-size: 20px;
                font-weight: bold;
                color: %s;
                border-radius: 16px;
                padding: 0px;
                margin: 0px;
                min-width: 32px;
                min-height: 32px;
                max-width: 32px;
                max-height: 32px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.18);
                border: 1px solid rgba(0, 0, 0, 0.2);
            }
        """ % s["text"])
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn, alignment=Qt.AlignTop)

        self.setFixedHeight(0)
        self.setMaximumHeight(0)

    def show_toast(self):
        """Animate the toast into view."""
        self.show()
        self.setFixedHeight(self.sizeHint().height())
        self.setMaximumHeight(self.sizeHint().height())

        # Opacity animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        # Keep existing shadow — apply opacity to content instead
        # Actually we need to be careful with stacking effects.
        # Instead, just use the height animation approach.

        # Auto-dismiss timer
        QTimer.singleShot(self._duration, self._dismiss)

    def _dismiss(self):
        """Animate out and remove."""
        self.setFixedHeight(0)
        self.setMaximumHeight(0)
        self.hide()
        self.deleteLater()


class SickLeaveRequestDialog(QDialog):
    """Multi-step wizard dialog for requesting a sick leave.
    
    Step 1: Employee + Leave type + Duration
    Step 2: Medical certificate + Deduction + Confirmation
    
    If `employee` is provided, the employee selector is hidden and
    that employee is used directly (useful when called from EmployeesPage).
    """

    def __init__(self, parent=None, employee=None):
        super().__init__(parent)
        self._preset_employee = employee
        self._current_step = 0
        self.setWindowTitle("طلب عطلة مرضية")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedWidth(440)
        self._build_ui()
        if employee:
            self._apply_preset_employee()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Compact widget stylesheet override (reduce internal padding)
        compact_combo = """
            QComboBox {
                padding: 4px 8px; font-size: 13px;
                border: 1.5px solid #d1d5db; border-radius: 6px;
                background: #fff; max-height: 28px; min-height: 28px;
            }
            QComboBox:focus { border-color: #3b82f6; }
            QComboBox::drop-down { width: 22px; border: none; }
        """
        compact_date = """
            QDateEdit {
                padding: 4px 8px; font-size: 13px;
                border: 1.5px solid #d1d5db; border-radius: 6px;
                background: #fff; max-height: 28px; min-height: 28px;
            }
            QDateEdit:focus { border-color: #3b82f6; }
            QDateEdit::drop-down { width: 22px; border: none; }
        """
        compact_spin = """
            QSpinBox {
                padding: 4px 8px; font-size: 13px;
                border: 1.5px solid #d1d5db; border-radius: 6px;
                background: #fff; max-height: 28px; min-height: 28px;
            }
            QSpinBox:focus { border-color: #3b82f6; }
            QSpinBox::up-button, QSpinBox::down-button { width: 20px; border: none; }
        """
        compact_input = """
            QLineEdit {
                padding: 4px 8px; font-size: 13px;
                border: 1.5px solid #d1d5db; border-radius: 6px;
                background: #fff; max-height: 28px; min-height: 28px;
            }
            QLineEdit:focus { border-color: #3b82f6; }
        """
        lbl_s = "font-size: 12px; color: #475569; background: transparent;"
        lbl_bold = "font-size: 12px; font-weight: bold; color: #334155; background: transparent;"

        # ── Slim header ──
        header_frame = QFrame()
        header_frame.setFixedHeight(56)
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1);
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)

        title_lbl = QLabel("🏥 طلب عطلة مرضية")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: white; background: transparent;")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        # Step pills in header
        self._step_labels = []
        step_names = ["① الموظف والمدة", "② الشهادة والاقتطاع"]
        for i, name in enumerate(step_names):
            pill = QLabel(name)
            pill.setFixedHeight(26)
            pill.setAlignment(Qt.AlignCenter)
            pill.setContentsMargins(8, 0, 8, 0)
            self._step_labels.append(pill)
            header_layout.addWidget(pill)

        main_layout.addWidget(header_frame)

        # ── Content area ──
        self._stacked = QTabWidget()
        self._stacked.setStyleSheet("""
            QTabWidget::pane { border: none; background: white; }
            QTabBar { height: 0px; }
            QTabBar::tab { height: 0px; width: 0px; }
        """)
        self._stacked.tabBar().hide()

        # ═══════ Step 1: Employee + Leave Type + Duration ═══════
        step1 = QWidget()
        step1.setStyleSheet("background: white;")
        s1 = QVBoxLayout(step1)
        s1.setSpacing(6)
        s1.setContentsMargins(16, 12, 16, 8)

        # Employee row
        self.employee_combo = ArabicComboBox()
        self.employee_combo.setStyleSheet(compact_combo)
        self._load_employees()
        self._employee_combo_row_label = QLabel("الموظف:")
        self._employee_combo_row_label.setStyleSheet(lbl_bold)

        self._preset_emp_label = ArabicLabel("")
        self._preset_emp_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #1e293b;"
            " padding: 4px 8px; background: #f1f5f9;"
            " border: 1px solid #e2e8f0; border-radius: 6px;"
        )
        self._preset_emp_row_label = QLabel("الموظف:")
        self._preset_emp_row_label.setStyleSheet(lbl_bold)
        self._preset_emp_label.hide()
        self._preset_emp_row_label.hide()

        s1.addWidget(self._employee_combo_row_label)
        s1.addWidget(self.employee_combo)
        s1.addWidget(self._preset_emp_row_label)
        s1.addWidget(self._preset_emp_label)

        # Leave type row
        lbl_type = QLabel("نوع العطلة:")
        lbl_type.setStyleSheet(lbl_bold)
        self.leave_type_combo = ArabicComboBox()
        self.leave_type_combo.setStyleSheet(compact_combo)
        self.leave_type_combo.addItems(LEAVE_TYPES)
        self.leave_type_combo.currentTextChanged.connect(self._on_leave_type_changed)
        s1.addWidget(lbl_type)
        s1.addWidget(self.leave_type_combo)

        # Duration section title
        dur_title = QLabel("📅 فترة العطلة")
        dur_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 4px; background: transparent;")
        s1.addWidget(dur_title)

        # Duration grid — 3 rows, compact
        dur_grid = QGridLayout()
        dur_grid.setSpacing(6)
        dur_grid.setContentsMargins(0, 0, 0, 0)

        lbl_start = QLabel("تاريخ أول يوم:")
        lbl_start.setStyleSheet(lbl_s)
        self.start_date = ArabicDateEdit()
        self.start_date.setStyleSheet(compact_date)
        dur_grid.addWidget(lbl_start, 0, 0)
        dur_grid.addWidget(self.start_date, 0, 1)

        lbl_days = QLabel("عدد الأيام:")
        lbl_days.setStyleSheet(lbl_s)
        self.days_spin = QSpinBox()
        self.days_spin.setLayoutDirection(Qt.RightToLeft)
        self.days_spin.setMinimum(1)
        self.days_spin.setMaximum(365)
        self.days_spin.setValue(1)
        self.days_spin.setSuffix(" يوم")
        self.days_spin.setStyleSheet(compact_spin)
        dur_grid.addWidget(lbl_days, 1, 0)
        dur_grid.addWidget(self.days_spin, 1, 1)

        lbl_end = QLabel("آخر يوم عطلة:")
        lbl_end.setStyleSheet(lbl_s)
        self.end_date_label = ArabicLabel("")
        self.end_date_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #1d4ed8;"
            " padding: 4px 8px; background: #eff6ff;"
            " border: 1px solid #bfdbfe; border-radius: 6px;"
            " max-height: 26px;"
        )
        dur_grid.addWidget(lbl_end, 2, 0)
        dur_grid.addWidget(self.end_date_label, 2, 1)

        s1.addLayout(dur_grid)

        self.start_date.dateChanged.connect(self._update_duration)
        self.days_spin.valueChanged.connect(self._update_duration)

        # Substitution info (compact)
        self.subst_info = QFrame()
        self.subst_info.setStyleSheet("""
            QFrame {
                background: #fefce8; border: 1px solid #fde68a;
                border-radius: 6px;
            }
        """)
        info_layout = QVBoxLayout(self.subst_info)
        info_layout.setContentsMargins(8, 4, 8, 4)
        self.subst_info_label = QLabel("")
        self.subst_info_label.setWordWrap(True)
        self.subst_info_label.setStyleSheet("font-size: 11px; background: transparent;")
        info_layout.addWidget(self.subst_info_label)
        s1.addWidget(self.subst_info)
        self.subst_info.hide()

        self._stacked.addTab(step1, "")

        # ═══════ Step 2: Certificate + Deduction ═══════
        step2 = QWidget()
        step2.setStyleSheet("background: white;")
        s2 = QVBoxLayout(step2)
        s2.setSpacing(6)
        s2.setContentsMargins(16, 12, 16, 8)

        cert_title = QLabel("📋 الشهادة الطبية")
        cert_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b; background: transparent;")
        s2.addWidget(cert_title)

        cert_grid = QGridLayout()
        cert_grid.setSpacing(6)
        cert_grid.setContentsMargins(0, 0, 0, 0)

        lbl_cert = QLabel("تاريخ الشهادة:")
        lbl_cert.setStyleSheet(lbl_s)
        self.cert_date = ArabicDateEdit()
        self.cert_date.setStyleSheet(compact_date)
        self.cert_date.dateChanged.connect(self._update_deduction_month)
        cert_grid.addWidget(lbl_cert, 0, 0)
        cert_grid.addWidget(self.cert_date, 0, 1)

        lbl_doctor = QLabel("اسم الطبيب *:")
        lbl_doctor.setStyleSheet(lbl_s)
        self.doctor_input = ArabicLineEdit("اسم الطبيب الذي حرر الشهادة")
        self.doctor_input.setStyleSheet(compact_input)
        cert_grid.addWidget(lbl_doctor, 1, 0)
        cert_grid.addWidget(self.doctor_input, 1, 1)

        s2.addLayout(cert_grid)

        # Deduction section
        ded_title = QLabel("💰 الاقتطاع")
        ded_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b; margin-top: 4px; background: transparent;")
        s2.addWidget(ded_title)

        ded_grid = QGridLayout()
        ded_grid.setSpacing(6)
        ded_grid.setContentsMargins(0, 0, 0, 0)

        lbl_month = QLabel("شهر الاقتطاع:")
        lbl_month.setStyleSheet(lbl_s)
        self.deduction_month_combo = ArabicComboBox()
        self.deduction_month_combo.setStyleSheet(compact_combo)
        for m in MONTHS_AR:
            self.deduction_month_combo.addItem(m)
        ded_grid.addWidget(lbl_month, 0, 0)
        ded_grid.addWidget(self.deduction_month_combo, 0, 1)

        s2.addLayout(ded_grid)
        self._update_deduction_month()

        # Summary card (compact)
        self._summary_frame = QFrame()
        self._summary_frame.setStyleSheet("""
            QFrame {
                background: #f0fdf4; border: 1px solid #bbf7d0;
                border-radius: 8px;
            }
        """)
        summary_layout = QVBoxLayout(self._summary_frame)
        summary_layout.setContentsMargins(10, 6, 10, 6)
        summary_layout.setSpacing(2)
        summary_lbl = QLabel("✅ ملخص الطلب")
        summary_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #166534; background: transparent;")
        summary_layout.addWidget(summary_lbl)
        self._summary_text = QLabel("")
        self._summary_text.setWordWrap(True)
        self._summary_text.setStyleSheet("font-size: 12px; color: #15803d; background: transparent;")
        summary_layout.addWidget(self._summary_text)
        s2.addWidget(self._summary_frame)

        self._stacked.addTab(step2, "")

        main_layout.addWidget(self._stacked, stretch=1)

        # ── Footer buttons (compact) ──
        footer = QFrame()
        footer.setStyleSheet("QFrame { background: #f8fafc; border-top: 1px solid #e2e8f0; }")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(16, 8, 16, 8)
        footer_layout.setSpacing(6)

        self.back_btn = ActionButton("السابق", "←", "outline")
        self.back_btn.clicked.connect(self._go_back)
        self.back_btn.hide()

        self.next_btn = ActionButton("التالي", "→", "primary")
        self.next_btn.clicked.connect(self._go_next)

        self.save_btn = ActionButton("تأكيد الطلب", "✔", "success")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.hide()

        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(self.reject)

        footer_layout.addWidget(self.save_btn)
        footer_layout.addWidget(self.next_btn)
        footer_layout.addWidget(self.back_btn)
        footer_layout.addStretch()
        footer_layout.addWidget(cancel_btn)

        main_layout.addWidget(footer)

        self._update_duration()
        self._update_step_ui()

    def _update_step_ui(self):
        """Update visual state of step indicators and buttons."""
        self._stacked.setCurrentIndex(self._current_step)

        for i, pill in enumerate(self._step_labels):
            if i == self._current_step:
                pill.setStyleSheet(
                    "font-size: 11px; font-weight: bold; color: white;"
                    " background: rgba(255,255,255,0.25); border-radius: 4px;"
                    " padding: 2px 8px;"
                )
            elif i < self._current_step:
                pill.setStyleSheet(
                    "font-size: 11px; color: rgba(255,255,255,0.7);"
                    " background: rgba(255,255,255,0.1); border-radius: 4px;"
                    " padding: 2px 8px;"
                )
            else:
                pill.setStyleSheet(
                    "font-size: 11px; color: rgba(255,255,255,0.4);"
                    " background: transparent; border-radius: 4px;"
                    " padding: 2px 8px;"
                )

        # Buttons
        self.back_btn.setVisible(self._current_step > 0)
        self.next_btn.setVisible(self._current_step < 1)
        self.save_btn.setVisible(self._current_step == 1)

        # Update summary on step 2
        if self._current_step == 1:
            self._update_summary()

    def _go_next(self):
        """Validate current step and move to next."""
        if self._current_step == 0:
            emp = self._get_selected_employee()
            if not emp:
                QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف")
                return
            self._current_step = 1
            self._update_step_ui()

    def _go_back(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._update_step_ui()

    def _update_summary(self):
        """Build summary text for step 2."""
        emp = self._get_selected_employee()
        emp_name = db.get_employee_full_name(emp) if emp else "—"
        leave_type = self.leave_type_combo.currentText()
        start = self.start_date.date().toPyDate()
        days = self.days_spin.value()
        end = start + timedelta(days=days - 1)
        
        lines = [
            "الموظف: <b>%s</b>" % emp_name,
            "النوع: <b>%s</b>" % leave_type,
            "الفترة: <b>%s</b> ← <b>%s</b> (%d يوم)" % (
                self.start_date.date().toString("yyyy/MM/dd"),
                "%04d/%02d/%02d" % (end.year, end.month, end.day),
                days
            ),
        ]
        self._summary_text.setText("<br/>".join(lines))

        # Update save button text based on substitution
        if self.needs_substitution():
            self.save_btn.setText(" ✔ حفظ العطلة المرضية")
        else:
            self.save_btn.setText(" ✔ تأكيد الطلب")

    def _load_employees(self):
        self.employees = db.get_all_employees()
        for emp in self.employees:
            full_name = db.get_employee_full_name(emp)
            grade = emp["grade"] or ""
            self.employee_combo.addItem("%s — %s" % (full_name, grade), emp["id"])

    def _apply_preset_employee(self):
        """Hide combo, show preset employee label."""
        emp = self._preset_employee
        full_name = db.get_employee_full_name(emp)
        grade = emp["grade"] or ""
        self._preset_emp_label.setText("%s — %s" % (full_name, grade))
        self._preset_emp_label.show()
        self._preset_emp_row_label.show()
        self.employee_combo.hide()
        self._employee_combo_row_label.hide()
        self._update_duration()

    def _get_selected_employee(self):
        if self._preset_employee:
            return self._preset_employee
        idx = self.employee_combo.currentIndex()
        if idx < 0:
            return None
        emp_id = self.employee_combo.currentData()
        return db.get_employee(emp_id)

    def _on_leave_type_changed(self, text):
        if text == "عطلة أمومة":
            self.days_spin.setValue(150)

    def _update_duration(self):
        start = self.start_date.date().toPyDate()
        days = self.days_spin.value()
        end = start + timedelta(days=days - 1)

        self.end_date_label.setText("%04d/%02d/%02d" % (end.year, end.month, end.day))

        emp = self._get_selected_employee()
        if emp and "أستاذ" in (emp["grade"] or ""):
            if days > 7:
                self.subst_info.show()
                self.subst_info_label.setText(
                    "⚠️ مدة العطلة تتجاوز 7 أيام — سيتم طلب معلومات الاستخلاف."
                )
                self.subst_info_label.setStyleSheet(
                    "color: #b45309; font-size: 13px; background: transparent; font-weight: bold;"
                )
            else:
                self.subst_info.show()
                self.subst_info_label.setText(
                    "✅ لا يتطلب استخلاف."
                )
                self.subst_info_label.setStyleSheet(
                    "color: #059669; font-size: 13px; background: transparent;"
                )
        else:
            self.subst_info.hide()

    def _save(self):
        doctor = self.doctor_input.text().strip()
        if not doctor:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الطبيب")
            return
        self.accept()

    def _update_deduction_month(self):
        """Set deduction month to the month after the medical certificate date."""
        cert_date = self.cert_date.date().toPyDate()
        next_month = cert_date.month
        if next_month == 12:
            next_month = 0
        self.deduction_month_combo.setCurrentIndex(next_month)

    def get_data(self):
        start = self.start_date.date().toPyDate()
        days = self.days_spin.value()
        end = start + timedelta(days=days - 1)
        emp = self._get_selected_employee()

        return {
            "employee_id": emp["id"],
            "start_date": self.start_date.date().toString("yyyy-MM-dd"),
            "end_date": "%04d-%02d-%02d" % (end.year, end.month, end.day),
            "doctor_name": self.doctor_input.text().strip(),
            "medical_cert_date": self.cert_date.date().toString("yyyy-MM-dd"),
            "duration_days": days,
            "status": "جارية",
            "leave_type": self.leave_type_combo.currentText(),
            "deduction_month": self.deduction_month_combo.currentText(),
        }

    def needs_substitution(self):
        emp = self._get_selected_employee()
        if not emp:
            return False
        days = self.days_spin.value()
        return "أستاذ" in (emp["grade"] or "") and days > 7



class SubstitutionDetailsDialog(QDialog):
    """Dialog for entering full substitute teacher information."""

    def __init__(self, teacher, sick_leave_id, start_date, end_date, parent=None, substitute=None):
        super().__init__(parent)
        self.teacher = teacher
        self.sick_leave_id = sick_leave_id
        self.start_date_str = start_date
        # Cap end_date to June 30 of the current school year
        self.end_date_str = self._cap_end_date(start_date, end_date)
        self.substitute_data = substitute
        teacher_name = db.get_employee_full_name(teacher) if teacher else (substitute.get("teacher_name", "") if substitute else "")
        self.setWindowTitle("تعديل معلومات المستخلف" if substitute else ("استخلاف الأستاذ(ة): %s" % teacher_name))
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(680)
        self._build_ui()
        if substitute:
            self._populate(substitute)

    @staticmethod
    def _cap_end_date(start_date_str, end_date_str):
        """Cap the substitution end date to June 30 of the current school year.
        
        In Algeria, the school year ends on June 30. Substitution contracts
        cannot extend beyond this date regardless of sick leave duration.
        """
        try:
            start_date = datetime.strptime(start_date_str.replace("/", "-"), "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str.replace("/", "-"), "%Y-%m-%d")
        except (ValueError, AttributeError):
            return end_date_str
        
        # Determine the school year's June 30 based on the contract start date
        if start_date.month <= 6:
            june_30 = datetime(start_date.year, 6, 30)
        else:
            june_30 = datetime(start_date.year + 1, 6, 30)
        
        if end_date > june_30:
            return june_30.strftime("%Y-%m-%d")
        return end_date_str

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 12)

        # Scroll area to prevent dialog from overflowing the screen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setLayoutDirection(Qt.RightToLeft)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content_widget = QWidget()
        content_widget.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 8)

        teacher_name = db.get_employee_full_name(self.teacher) if self.teacher else (self.substitute_data.get("teacher_name", "") if self.substitute_data else "")
        header_text = "تعديل معلومات المستخلف(ة) 🔄" if self.substitute_data else "معلومات الأستاذ(ة) المستخلف(ة) 🔄"
        header = QLabel(header_text)
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        layout.addWidget(header)

        # Period info
        period_label = ArabicLabel(
            "تاريخ العطلة: من %s إلى %s  — استخلاف: %s" % (self.start_date_str, self.end_date_str, teacher_name)
        )
        period_label.setObjectName("badge_info")
        layout.addWidget(period_label)

        grid = QGridLayout()
        grid.setSpacing(12)

        # In RTL: col 0 = rightmost. So: label col 0, input col 1 (right pair), label col 2, input col 3 (left pair)
        # Row 0: اللقب (right) + الاسم (left)
        self.last_name_input = ArabicLineEdit("اللقب")
        grid.addWidget(QLabel("اللقب *:"), 0, 0)
        grid.addWidget(self.last_name_input, 0, 1)

        self.first_name_input = ArabicLineEdit("الاسم")
        grid.addWidget(QLabel("الاسم *:"), 0, 2)
        grid.addWidget(self.first_name_input, 0, 3)

        # Row 1: تاريخ الميلاد (right) + مكان الميلاد (left)
        self.birth_date_input = ArabicDateEdit()
        grid.addWidget(QLabel("تاريخ الميلاد *:"), 1, 0)
        grid.addWidget(self.birth_date_input, 1, 1)

        self.birth_place_input = ArabicLineEdit("مكان الميلاد")
        grid.addWidget(QLabel("مكان الميلاد *:"), 1, 2)
        grid.addWidget(self.birth_place_input, 1, 3)

        # Row 2: اللقب بالفرنسية (right) + الاسم بالفرنسية (left)
        self.last_name_fr_input = ArabicLineEdit("NOM (اللقب بالفرنسية)")
        self.last_name_fr_input.setLayoutDirection(Qt.LeftToRight)
        self.last_name_fr_input.setAlignment(Qt.AlignLeft)
        grid.addWidget(QLabel("اللقب بالفرنسية:"), 2, 0)
        grid.addWidget(self.last_name_fr_input, 2, 1)

        self.first_name_fr_input = ArabicLineEdit("Prénom (الاسم بالفرنسية)")
        self.first_name_fr_input.setLayoutDirection(Qt.LeftToRight)
        self.first_name_fr_input.setAlignment(Qt.AlignLeft)
        grid.addWidget(QLabel("الاسم بالفرنسية:"), 2, 2)
        grid.addWidget(self.first_name_fr_input, 2, 3)

        # Row 3: رقم التعريف (right) + الحساب البريدي (left)
        self.national_id_input = ArabicLineEdit("البطاقة الوطنية")
        grid.addWidget(QLabel("رقم التعريف *:"), 3, 0)
        grid.addWidget(self.national_id_input, 3, 1)

        self.postal_account_input = ArabicLineEdit("رقم الحساب البريدي")
        grid.addWidget(QLabel("الحساب البريدي *:"), 3, 2)
        grid.addWidget(self.postal_account_input, 3, 3)

        # Row 4: الضمان الاجتماعي (right) + نوع الشهادة (left)
        self.social_security_input = ArabicLineEdit("الضمان الاجتماعي")
        grid.addWidget(QLabel("الضمان *:"), 4, 0)
        grid.addWidget(self.social_security_input, 4, 1)

        self.degree_type_combo = ArabicComboBox()
        self.degree_type_combo.addItems(DEGREE_TYPES)
        grid.addWidget(QLabel("نوع الشهادة *:"), 4, 2)
        grid.addWidget(self.degree_type_combo, 4, 3)

        # Row 5: التخصص (right) + تاريخ الشهادة (left)
        self.degree_speciality_input = ArabicLineEdit("تخصص الشهادة")
        grid.addWidget(QLabel("التخصص *:"), 5, 0)
        grid.addWidget(self.degree_speciality_input, 5, 1)

        self.degree_date_input = ArabicDateEdit()
        grid.addWidget(QLabel("تاريخ الشهادة *:"), 5, 2)
        grid.addWidget(self.degree_date_input, 5, 3)

        # Row 6: العنوان (right) + مصدر الشهادة (left)
        self.address_input = ArabicLineEdit("العنوان الكامل")
        grid.addWidget(QLabel("العنوان:"), 6, 0)
        grid.addWidget(self.address_input, 6, 1)

        self.degree_source_input = ArabicLineEdit("الجامعة / المعهد")
        grid.addWidget(QLabel("مصدر الشهادة *:"), 6, 2)
        grid.addWidget(self.degree_source_input, 6, 3)

        layout.addLayout(grid)

        # Note about required fields
        note = ArabicLabel("* جميع الحقول المشار إليها بنجمة إلزامية")
        note.setStyleSheet("color: #dc2626; font-size: 12px; font-style: italic;")
        layout.addWidget(note)

        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll, stretch=1)

        # Buttons — OUTSIDE scroll area so they're always visible
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(16, 0, 16, 0)
        btn_text = "حفظ التعديلات" if self.substitute_data else "تأكيد وطباعة محضر التنصيب"
        save_btn = ActionButton(btn_text, "⎙" if not self.substitute_data else "💾", "success")
        save_btn.clicked.connect(self._save)
        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # Limit dialog height to 85% of available screen height
        screen = QApplication.primaryScreen()
        if screen:
            available_height = screen.availableGeometry().height()
            self.setMaximumHeight(int(available_height * 0.85))

    def _populate(self, sub):
        # Use separate fields if available, otherwise fallback to split from substitute_name
        sub_first = sub.get("substitute_first_name", "") or ""
        sub_last = sub.get("substitute_last_name", "") or ""
        if not sub_first and not sub_last:
            # Backward compatibility: split substitute_name
            full = sub.get("substitute_name", "")
            parts = full.split(" ", 1) if full else [""]
            sub_last = parts[0]
            sub_first = parts[1] if len(parts) > 1 else ""
        self.last_name_input.setText(sub_last)
        self.first_name_input.setText(sub_first)
        self.birth_place_input.setText(sub.get("substitute_birth_place", ""))
        self.first_name_fr_input.setText(sub.get("substitute_first_name_fr", ""))
        self.last_name_fr_input.setText(sub.get("substitute_last_name_fr", ""))
        self.national_id_input.setText(sub.get("substitute_national_id", ""))
        self.postal_account_input.setText(sub.get("substitute_postal_account", ""))
        self.social_security_input.setText(sub.get("substitute_social_security", ""))
        self.degree_speciality_input.setText(sub.get("substitute_degree_speciality", ""))
        self.address_input.setText(sub.get("substitute_address", ""))
        self.degree_source_input.setText(sub.get("substitute_degree_source", ""))
        
        idx = self.degree_type_combo.findText(sub.get("substitute_degree_type", ""))
        if idx >= 0:
            self.degree_type_combo.setCurrentIndex(idx)
            
        bd = sub.get("substitute_birth_date", "")
        if bd:
            self.birth_date_input.setDate(QDate.fromString(bd, "yyyy-MM-dd"))
            
        dd = sub.get("substitute_degree_date", "")
        if dd:
            self.degree_date_input.setDate(QDate.fromString(dd, "yyyy-MM-dd"))

    def _save(self):
        # Validate all fields
        fields = [
            (self.last_name_input, "اللقب"),
            (self.first_name_input, "الاسم"),
            (self.birth_place_input, "مكان الميلاد"),
            (self.national_id_input, "رقم بطاقة التعريف"),
            (self.postal_account_input, "رقم الحساب البريدي"),
            (self.social_security_input, "رقم الضمان الاجتماعي"),
            (self.degree_speciality_input, "تخصص الشهادة"),
            (self.degree_source_input, "مصدر الشهادة"),
        ]
        for field, name in fields:
            if not field.text().strip():
                QMessageBox.warning(self, "حقل إلزامي", "يرجى إدخال: %s" % name)
                field.setFocus()
                return
        self.accept()

    def get_data(self):
        last_name = self.last_name_input.text().strip()
        first_name = self.first_name_input.text().strip()
        full_name = "%s %s" % (last_name, first_name)
        return {
            "sick_leave_id": self.sick_leave_id,
            "teacher_id": self.teacher["id"],
            "substitute_name": full_name,
            "substitute_first_name": first_name,
            "substitute_last_name": last_name,
            "substitute_birth_place": self.birth_place_input.text().strip(),
            "substitute_birth_date": self.birth_date_input.date().toString("yyyy-MM-dd"),
            "substitute_national_id": self.national_id_input.text().strip(),
            "substitute_postal_account": self.postal_account_input.text().strip(),
            "substitute_social_security": self.social_security_input.text().strip(),
            "substitute_degree_type": self.degree_type_combo.currentText(),
            "substitute_degree_speciality": self.degree_speciality_input.text().strip(),
            "substitute_degree_date": self.degree_date_input.date().toString("yyyy-MM-dd"),
            "substitute_degree_source": self.degree_source_input.text().strip(),
            "substitute_first_name_fr": self.first_name_fr_input.text().strip(),
            "substitute_last_name_fr": self.last_name_fr_input.text().strip(),
            "substitute_address": self.address_input.text().strip(),
            "start_date": self.start_date_str,
            "end_date": self.end_date_str,
            "status": self.substitute_data.get("status", "جارية") if self.substitute_data else "جارية",
        }


class SickLeavePage(QWidget):
    """Sick leave management page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._active_toasts = []
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 28, 28, 28)

        # Header
        header_row = QHBoxLayout()
        header = QLabel("العطل المرضية والاستخلاف 🏥")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        header_row.addWidget(header)
        header_row.addStretch()

        add_subst_btn = ActionButton("إضافة استخلاف", "🔄", "success")
        add_subst_btn.setMinimumHeight(44)
        add_subst_btn.clicked.connect(self._add_substitution)
        header_row.addWidget(add_subst_btn, alignment=Qt.AlignTop)

        new_btn = ActionButton("طلب عطلة مرضية", "🏥", "primary")
        new_btn.setMinimumHeight(44)
        new_btn.clicked.connect(self._new_sick_leave)
        header_row.addWidget(new_btn, alignment=Qt.AlignTop)

        layout.addLayout(header_row)

        # Toast container for notifications
        self._toast_container = QVBoxLayout()
        self._toast_container.setSpacing(8)
        layout.addLayout(self._toast_container)

        # Stats removed

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.RightToLeft)

        # Tab 1: Sick leaves
        self.leaves_tab = QWidget()
        leaves_layout = QVBoxLayout(self.leaves_tab)
        leaves_layout.setContentsMargins(0, 12, 0, 0)

        self.leaves_table = QTableWidget()
        self.leaves_table.setLayoutDirection(Qt.RightToLeft)
        self.leaves_table.setColumnCount(7)
        self.leaves_table.setHorizontalHeaderLabels([
            "الموظف", "الرتبة", "تاريخ البداية", "تاريخ النهاية",
            "المدة", "الحالة", "إجراءات"
        ])
        self.leaves_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.leaves_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.leaves_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.leaves_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.leaves_table.setAlternatingRowColors(True)
        self.leaves_table.verticalHeader().setVisible(False)
        self.leaves_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.leaves_table.setShowGrid(False)
        leaves_layout.addWidget(self.leaves_table)

        self.tabs.addTab(self.leaves_tab, "🏥  العطل المرضية")

        # Tab 2: Substitutions
        self.subst_tab = QWidget()
        subst_layout = QVBoxLayout(self.subst_tab)
        subst_layout.setContentsMargins(0, 12, 0, 0)

        self.subst_table = QTableWidget()
        self.subst_table.setLayoutDirection(Qt.RightToLeft)
        self.subst_table.setColumnCount(7)
        self.subst_table.setHorizontalHeaderLabels([
            "الأستاذ(ة)", "المستخلف(ة)", "تاريخ البداية", "تاريخ النهاية",
            "المادة", "الحالة", "إجراءات"
        ])
        self.subst_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.subst_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.subst_table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.subst_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.subst_table.setAlternatingRowColors(True)
        self.subst_table.verticalHeader().setVisible(False)
        self.subst_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.subst_table.setShowGrid(False)
        subst_layout.addWidget(self.subst_table)

        self.tabs.addTab(self.subst_tab, "🔄  الاستخلافات")

        layout.addWidget(self.tabs, stretch=1)

    def _add_substitution(self):
        """Add substitution for a teacher already on sick leave."""
        available_leaves = db.get_active_sick_leaves_for_substitution()
        if not available_leaves:
            QMessageBox.information(
                self, "تنبيه",
                "لا توجد عطل مرضية جارية تحتاج استخلاف.\n"
                "يجب أن تكون مدة العطلة أكثر من 7 أيام ولم يتم تسجيل استخلاف لها بعد."
            )
            return

        # Show selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة استخلاف — اختيار الأستاذ(ة)")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.setMinimumWidth(520)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setSpacing(12)
        dlg_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("اختيار الأستاذ(ة) في عطلة مرضية 🔄")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 8px;")
        dlg_layout.addWidget(header)

        info_lbl = QLabel("اختر الأستاذ(ة) الذي تريد إضافة مستخلف(ة) له(ها):")
        info_lbl.setStyleSheet("font-size: 13px; color: #64748b;")
        dlg_layout.addWidget(info_lbl)

        teacher_combo = ArabicComboBox()
        for sl in available_leaves:
            label = "%s — %s (من %s إلى %s)" % (
                sl["employee_name"], sl["employee_grade"] or "",
                sl["start_date"], sl["end_date"]
            )
            teacher_combo.addItem(label, sl["id"])
        dlg_layout.addWidget(teacher_combo)

        dlg_layout.addStretch()

        btn_layout = QHBoxLayout()
        confirm_btn = ActionButton("متابعة", "→", "success")
        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        dlg_layout.addLayout(btn_layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        # Get selected sick leave
        sl_id = teacher_combo.currentData()
        sl = db.get_sick_leave(sl_id)
        if not sl:
            return
        emp = db.get_employee(sl["employee_id"])
        if not emp:
            return

        # Show substitute details dialog
        subst_dialog = SubstitutionDetailsDialog(
            emp, sl_id, sl["start_date"], sl["end_date"], self
        )
        if subst_dialog.exec_() == QDialog.Accepted:
            subst_data = subst_dialog.get_data()
            db.add_substitution(subst_data)
            self.refresh()  # Immediate synchronous refresh
            QMessageBox.information(
                self, "نجاح",
                "✅ تم تسجيل الاستخلاف بنجاح.\n"
                "يمكنك الآن طباعة محضر التنصيب ومقرر التعيين من قائمة الإجراءات."
            )

    def _new_sick_leave(self):
        dialog = SickLeaveRequestDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            # Extract leave_type and deduction_month (keep in data for DB storage)
            leave_type = data.get("leave_type", "عطلة مرضية")
            deduction_month = data.get("deduction_month", "")
            sl_id = db.add_sick_leave(data)

            # Auto-create a manual deduction entry for this sick leave
            emp = db.get_employee(data["employee_id"])
            if deduction_month and emp:
                deduction_data = {
                    "employee_id": data["employee_id"],
                    "deduction_type": leave_type,
                    "duration_days": data["duration_days"],
                    "cert_date": data["medical_cert_date"],
                    "deduction_month": deduction_month,
                    "notes": "اقتطاع تلقائي — %s" % leave_type,
                }
                db.add_manual_deduction(deduction_data)

            self.refresh()  # Immediate refresh before modals

            if dialog.needs_substitution():
                reply = QMessageBox.question(
                    self, "حجز الاستخلاف",
                    "تم حفظ العطلة المرضية بنجاح.\nهل تريد حجز معلومات المستخلف الآن؟",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    # Show substitution details dialog
                    subst_dialog = SubstitutionDetailsDialog(
                        emp, sl_id, data["start_date"], data["end_date"], self
                    )
                    if subst_dialog.exec_() == QDialog.Accepted:
                        subst_data = subst_dialog.get_data()
                        db.add_substitution(subst_data)
                        self.refresh()  # Immediate refresh for substitution
                        QMessageBox.information(
                            self, "نجاح",
                            "✅ تم تسجيل العطلة المرضية والاستخلاف بنجاح.\n"
                            "يمكنك الآن طباعة محضر التنصيب ومقرر التعيين من قائمة الإجراءات."
                        )
                    else:
                        QMessageBox.information(
                            self, "تنبيه",
                            "تم تسجيل العطلة المرضية بدون استخلاف.\n"
                            "يمكنك إضافة الاستخلاف لاحقاً."
                        )
                else:
                    QMessageBox.information(
                        self, "تنبيه",
                        "تم تسجيل العطلة المرضية بدون استخلاف.\n"
                        "يمكنك إضافة الاستخلاف لاحقاً."
                    )
            else:
                QMessageBox.information(
                    self, "نجاح",
                    "✅ تم تسجيل طلب العطلة المرضية بنجاح."
                )
                self._print_sick_leave_request(sl_id, emp)

    def _print_sick_leave_request(self, sl_id, emp):
        sl = db.get_sick_leave(sl_id)
        if not sl:
            return
        settings = db.get_all_settings()
        html = self._generate_sick_leave_html(sl, emp, settings)
        self._show_print_preview(html, landscape=False)

    def _generate_sick_leave_html(self, sl, emp, settings):
        school = db.get_formatted_school_name()
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        school_address = settings.get("school_address", "........................")
        
        emp_last_name = emp["last_name"]
        emp_first_name = emp["first_name"]
        emp_grade = emp["grade"] or ""
        subject_line = ""
        if dict(emp).get("subject") and "أستاذ" in (dict(emp).get("grade", "") or ""):
            subject_line = " مادة %s" % emp["subject"]

        school_display = school + " - " + school_address
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code

        today = datetime.now().strftime("%Y/%m/%d")

        # Get past 12 months leaves
        all_leaves = db.get_sick_leaves_for_employee(emp["id"])
        past_leaves = []
        try:
            sl_date = datetime.strptime(sl["start_date"].replace("/", "-"), "%Y-%m-%d")
        except Exception:
            sl_date = datetime.now()
        
        twelve_months_ago = sl_date - timedelta(days=365)
        
        for l in all_leaves:
            if l["id"] == sl["id"]:
                continue
            try:
                l_start = datetime.strptime(l["start_date"].replace("/", "-"), "%Y-%m-%d")
                if twelve_months_ago <= l_start <= sl_date:
                    past_leaves.append(l)
            except Exception:
                pass
                
        past_leaves.sort(key=lambda x: x["start_date"])
        
        history_slots = []
        num_slots = max(4, len(past_leaves) + (len(past_leaves) % 2))
        for i in range(num_slots):
            if i < len(past_leaves):
                p = past_leaves[i]
                s_str = p["start_date"].replace("-", "/")
                e_str = p["end_date"].replace("-", "/")
                history_slots.append(f"{i+1}- من: <b>{s_str}</b> الى: <b>{e_str}</b>")
            else:
                history_slots.append(f"{i+1}-من................الى................")

        history_html = ""
        for r in range(num_slots // 2):
            history_html += "<tr align='right'><td style='width: 50%%;'>%s</td><td style='width: 50%%;'>%s</td></tr>" % (
                history_slots[r*2], history_slots[r*2+1]
            )

        html = """
        <html >
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 40px; font-size: 16px; }
            .header-text { font-size: 22px; font-weight: bold; text-decoration: underline; text-align: center; }
            .right-header { font-size: 22px; font-weight: bold; text-align: right; margin-top: 50px; margin-bottom: 60px; line-height: 1.2.5; }
            .title { font-size: 48px; font-weight: bold; text-align: center; margin-bottom: 60px; }
            .content { font-size: 18px; font-weight: bold; width: 100%%; border-collapse: separate; border-spacing: 0 15px; }
            .content td { padding: 5px; }
            .flex-row { display: flex; width: 60%%; justify-content: space-between; }
            .table-history { width: 85%%; border: none; font-size: 12px; font-weight: bold; margin-top: 5px; }
            .table-history td { padding: 1px 0; }
            .footer-table { width: 100%%; font-size: 24px; font-weight: bold; margin-top: 80px; }
        </style></head>
        <body >
         <table width="100%%"  style="margin-bottom: 5px;">
                <tr>
                    <td style="text-align:center;padding:0px; font-size: 22px; font-weight: bold; ">
                       الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:center;padding:0px; font-size: 22px; font-weight: bold; ">
                     وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:right;padding:0px; font-size: 18px; font-weight: bold; ">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:right;padding:0px; font-size: 18px; font-weight: bold; ">
                       
                        %(school_display)s
                    </td>
                </tr>
                <tr>
                <td width="100%%" style="text-align:center; font-size: 24px; font-weight: bold; padding-top: 20px;">
                  طلب عطلة مرضية
                </td>
                </tr>
           
            </table>
            <table class="content" >
            <tr>
            <td>الاسم : %(first_name)s</td>
            <td>اللقب : %(last_name)s</td>
            </tr>
            <tr>
            <td colspan="2">الرتبة : %(emp_grade)s%(subject_line)s</td>
            </tr>
            <tr>
            <td colspan="2">يطلب رخصة: %(leave_type)s لمدة %(duration)s يوم من: %(start_date)s الى: %(end_date)s</td>
            </tr>
            <tr>
            <td colspan="2">للسبب التالي : %(leave_type)s</td>
            </tr>
            <tr>
            <td colspan="2">الوثائق المرفقة : شهادة طبية</td>
            </tr>
            </table>
           <div width="100%%"  style="margin: 20px 0px 20px 0px;">
                <div  style="font-size: 18px; font-weight: bold; ">العطل المحصل عليها خلال الاثني عشر شهر التي سبقت هذا الطلب</div>
                <table width="100%%"   style="" class="table-history">
                    %(history_html)s
                </table>
            </div>

        <table width="100%%" >
               <tr>
               
              
                  <td style="text-align:center; width:30%%;">إمضاء المعني(ة) بالأمر</td>
             <td style="text-align:center; width:30%%;"></td>
            <td style="font-size:22px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في : %(today)s
                </td>
            </tr>
            <tr>
                
                
                <td style="text-align:center; width:30%%;">%(emp_name)s</td>
                <td style="text-align:center; width:30%%;"></td>
                <td style="font-size:22px; font-weight: bold; text-align:center; width:40%%;">
                        المدير
                </td>
            </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display,
            "school_address": school_address,
            "last_name": emp_last_name, "first_name": emp_first_name,
            "emp_name": "%s %s" % (emp_last_name, emp_first_name),
            "emp_grade": emp_grade, "subject_line": subject_line,
            "start_date": sl["start_date"].replace("-", "/"),
            "end_date": sl["end_date"].replace("-", "/"), "duration": sl["duration_days"],
            "today": today, "history_html": history_html,
            "leave_type": dict(sl).get("leave_type", "عطلة مرضية") or "عطلة مرضية",
        }

        return html

    def _show_print_preview(self, html, landscape=False):
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=landscape)
        dialog.exec_()

    def _delete_sick_leave(self, sl_id):
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            "هل أنت متأكد من حذف هذه العطلة المرضية؟\nسيتم حذف الاستخلاف المرتبط بها (إن وجد).",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_sick_leave(sl_id)
            self.refresh()
            QMessageBox.information(self, "نجاح", "تم حذف العطلة المرضية بنجاح.")

    def _end_sick_leave(self, sl_id):
        """End a sick leave and generate resume work document."""
        sl = db.get_sick_leave(sl_id)
        if not sl:
            return
        emp = db.get_employee(sl["employee_id"])
        if not emp:
            return

        # Show dialog to pick resume date
        dialog = QDialog(self)
        dialog.setWindowTitle("إنهاء العطلة المرضية")
        dialog.setLayoutDirection(Qt.RightToLeft)
        dialog.setMinimumWidth(420)

        dlg_layout = QVBoxLayout(dialog)
        dlg_layout.setSpacing(12)
        dlg_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("إنهاء العطلة المرضية واستئناف العمل")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; margin-bottom: 4px;")
        dlg_layout.addWidget(header)

        emp_name = db.get_employee_full_name(emp)
        info_lbl = QLabel("الموظف(ة): %s\nفترة العطلة: %s ← %s" % (
            emp_name, sl["start_date"], sl["end_date"]
        ))
        info_lbl.setStyleSheet("font-size: 13px; color: #64748b; margin-bottom: 8px;")
        dlg_layout.addWidget(info_lbl)

        form = ArabicFormLayout()
        resume_date_edit = ArabicDateEdit()
        # Default: day after end_date
        end_date = datetime.strptime(sl["end_date"], "%Y-%m-%d")
        default_resume = end_date + timedelta(days=1)
        resume_date_edit.setDate(QDate(default_resume.year, default_resume.month, default_resume.day))
        form.addRow("تاريخ استئناف العمل:", resume_date_edit)
        dlg_layout.addLayout(form)

        note_lbl = QLabel("⚡ يمكنك تعديل التاريخ إذا كان الاستئناف قد تم في تاريخ سابق.")
        note_lbl.setStyleSheet("font-size: 12px; color: #b45309; font-style: italic;")
        note_lbl.setWordWrap(True)
        dlg_layout.addWidget(note_lbl)

        dlg_layout.addStretch()

        btn_layout = QHBoxLayout()
        confirm_btn = ActionButton("تأكيد الاستئناف", "✔", "success")
        confirm_btn.clicked.connect(dialog.accept)
        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(confirm_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        dlg_layout.addLayout(btn_layout)

        if dialog.exec_() != QDialog.Accepted:
            return

        resume_str = resume_date_edit.date().toString("yyyy-MM-dd")

        db.update_sick_leave_status(sl_id, "منتهية", resume_str)

        # End any active substitution
        subst = db.get_substitution_by_sick_leave(sl_id)
        if subst and subst["status"] == "جارية":
            db.update_substitution_status(subst["id"], "منتهية")

        QMessageBox.information(
            self, "نجاح",
            "✅ تم إنهاء العطلة المرضية بنجاح.\n"
            "تاريخ استئناف العمل: %s" % resume_str
        )

        self.refresh()
        
        # Print resume work document
        self._print_resume_work(emp, sl, resume_str)

        # If there was a substitution, print end of substitution
        if subst:
            self._print_end_substitution(emp, subst)

    def _print_resume_work(self, emp, sl, resume_str):
        settings = db.get_all_settings()
        school = db.get_formatted_school_name()
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        school_address = settings.get("school_address", "......................")
        emp_name = db.get_employee_full_name(emp)

        subject_html = ""
        if dict(emp).get("subject") and "أستاذ" in (dict(emp).get("grade", "") or ""):
            subject_html = """
                <tr>
                <td style="width: 10%%; padding: 2px; text-align: right; font-size: 16px;"></td>
                <td  style="width: 30%%; padding: 2px; text-align: right; font-size: 16px;">التخصص:</td>
                <td style="width: 60%%; padding: 2px; text-align: right; font-size: 16px;">%s</td>
                </tr>""" % emp["subject"]
            
        school_display = school + " - " + school_address
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code
        today = datetime.now().strftime("%Y/%m/%d")

        html = """
        <html dir="rtl" >
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   margin: 30px;  }
            .header-text { font-size: 16px; font-weight: bold; text-align: center; margin: 2px 0; }
            .header-right { font-size: 14px; font-weight: bold; text-align: right; margin-top: 2px; margin-bottom: 5px;  }
            .doc-title { text-align: center; font-size: 45px; font-weight: bold; margin: 10; font-family: 'Arial', 'Amiri', sans-serif; text-shadow: 2px 2px #ccc; }
            .intro-text { font-size: 18px; font-weight: bold; margin-bottom: 15px; margin-top: 15px; text-align: right; }
            .info-table { border-collapse: collapse; width: 100%%; margin: 10px; border: 1px solid black!important; }
            .info-table th, .info-table td { border: 1px solid black!important; padding: 2px; text-align: center; font-size: 14px;  }
        </style></head>
        <body >
          <table width="100%%"  style="margin-bottom: 15px;">
                <tr>
                    <td style="text-align:center;padding:0px; font-size: 24px; font-weight: bold; ">
                       الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:center;padding:0px; font-size: 24px; font-weight: bold; ">
                     وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:right;padding:0px; font-size: 22px; font-weight: bold; ">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:right;padding:0px; font-size: 22px; font-weight: bold; ">
                       
                        %(school_display)s
                    </td>
                </tr>
                <tr>
                    <td >
                  
                    </td>
                </tr>
                <tr>
                <td width="100%%" style="padding:5px; text-align:center; font-size: 24px; font-weight: bold; padding:10px;">
                  بيان استئناف عمل
                </td>
                </tr>
           
            </table>

          

            <div class="intro-text">
             يشهد مدير المؤسسة أن السيد(ة):
            </div>
            <table style="font-size: 18px; width: 100%%; border-collapse: collapse; margin: 20px;line-height: 2.5;">
                <tr>
                <td style="width: 10%%; padding: 2px; text-align: right;"></td>
                <td  style="width: 20%%; padding: 2px; text-align: right;">اللقب و الاسم:</td>
                <td style="width: 70%%; padding: 2px; text-align: right;">%(emp_name)s</td>
                    
                </tr>
                <tr>
                <td style="width: 10%%; padding: 2px; text-align: right;"></td>
                <td  style="width: 20%%; padding: 2px; text-align: right;">الرتبة:</td>
                <td style="width: 70%%; padding: 2px; text-align: right;">%(emp_grade)s</td>
                    
                </tr>
                %(subject_html)s
                <tr>
                <td style="width: 10%%; padding: 2px; text-align: right;"></td>
                <td  style="width: 20%%; padding: 2px; text-align: right;">الوضعية الإدارية:</td>
                <td style="width: 70%%; padding: 2px; text-align: right;">%(employee_status)s</td>
                    
                </tr>
                <tr>
                <td style="width: 10%%; padding: 2px; text-align: right;"></td>
                <td  style="width: 20%%; padding: 2px; text-align: right;">مؤسسة العمل:</td>
                <td style="width: 70%%; padding: 2px; text-align: right;">%(school)s</td>
                    
                </tr>
            
                <tr>
                <td style="width: 10%%; padding: 2px; text-align: right;"></td>
                <td  style="width: 20%%; padding: 2px; text-align: right;">استأنف عمله بتاريخ:</td>
                <td style="width: 70%%; padding: 2px; text-align: right;">%(resume_date)s</td>
                    
                </tr>
                  <tr>
                <td style="width: 10%%; padding: 2px; text-align: right;"></td>
                <td  style="width: 20%%; padding: 2px; text-align: right;">الملاحظة:</td>
                <td style="width: 70%%; padding: 2px; text-align: right;"></td>   
                </tr>
            </table>
            
            <table width="100%%"  style="margin-top: 25px;">
               <tr>
             
                  <td style="text-align:center; width:30%%;">إمضاء الموظف</td>
             <td style="text-align:center; width:30%%;"></td>
                <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في : %(today)s
                </td>
                
            </tr>
            <tr>
             <td style="text-align:center; width:30%%;">%(emp_name)s</td>
                 <td style="text-align:center; width:30%%;"></td>
            <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;">
                        المدير
                </td>
        
               
                
               
            </tr>
            </table>
             
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "school_year": school_year,
            "school_address": school_address,
            "emp_name": emp_name, "emp_grade": emp["grade"] or "",
            "subject_html": subject_html,
            "employee_status": dict(emp).get("employee_status") or "مرسم",
            "start_date": sl["start_date"], "end_date": sl["end_date"],
            "resume_date": resume_str,
            "today": today, "director": director,
        }
        self._show_print_preview(html)

    def _print_end_substitution(self, teacher, subst):
        settings = db.get_all_settings()
        school = db.get_formatted_school_name()
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        school_address = settings.get("school_address", "......................")
        teacher_name = db.get_employee_full_name(teacher)
        today_str = datetime.now().strftime("%Y/%m/%d")

        school_display = school + " - " + school_address
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code

        html = """
        <html dir='rtl'>
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif; text-align: right;  }
            .header-text { font-size: 24px; font-weight: bold; text-align: center; margin: 2px 0; }
            .header-right { font-size: 18px; font-weight: bold; text-align: right; margin-top: 10px; margin-bottom: 30px;  }
            .recipient-block { font-size: 20px; font-weight: bold; text-align: right; margin-right: 20px; margin-bottom: 40px; ; }
            .subject-title { font-size: 22px; font-weight: bold; margin: 30px 40px; text-align: right; }
            .content-p { font-size: 20px; margin:5px;  text-align: right; text-indent: 40px; }
            h2 { text-align: center; color: #1a1a1a; margin: 24px 0; font-weight: bold; font-size: 24px; text-decoration: underline; }
            .info-table {margin:auto; border-collapse: collapse; width: 95%%; margin: 5px; }
            .info-table th, .info-table td { border: 1px solid black !important; padding: 2px; font-size: 14px; font-weight: bold; text-align: right;  }
            .info-table td.label { width: 40%%; }
        </style></head>
        <body >
            <div class="header-text">الجمهورية الجزائرية الديمقراطية الشعبية</div>
            <div class="header-text">وزارة التربية الوطنية</div>
            <div style="font-size: 22px;  text-align: right;">
                مديرية التربية لولاية %(wilaya)s<br/>
                %(school_display)s
            </div>
            
            <div class="recipient-block">
            <table width="100%%">
                <tr>
                    <td width="60%%"></td>
                    <td width="40%%" style="text-align:center;">إلى السيد : مدير التربية</td>
                </tr>
                <tr>
                    <td width="60%%"></td>
                    <td width="40%%" style="text-align:center;">مصلحة المستخدمين</td>
                </tr>
                <tr>
                    <td width="60%%"></td>
                    <td width="40%%" style="text-align:center;">%(desk_label)s</td>
                </tr>
            </table>
            </div>

            <div class="subject-title">الموضوع: نهاية الإستخلاف</div>

            <p class="content-p">
                نعلم سيادتكم أن الأستـــاذ(ة) : %(sub_name)s مستخلفــ(ة) علــى منصــب عطلــة مرضيــة (مادة %(teacher_subject)s) أنهــــت إستخلافهـــا بتاريــــخ %(end_date)s.
            </p>

             <table width="100%%" style="margin-top: 15px; margin-bottom: 5px;">
<tr>
</tr>
               <tr>
                <td style="text-align:center; width:60%%;"></td>
                <td style="font-size:20px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في %(today)s
                </td>
            </tr>
            <tr>
                <td style="text-align:center; width:60%%;"></td>
                <td style="font-size:22px; font-weight: bold; text-align:center; width:40%%; padding-top: 10px;">
                        المدير
                </td>
            </tr>
            </table>

            <!-- Page Break for Information Card -->
            <div style="page-break-before: always;"></div>
            <table width="100%%"  style="margin-top: 5px; margin-bottom: 5px;">
                <tr>
                    <td style="text-align:center; font-size: 22px; font-weight: bold; ">
                       الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:center; font-size: 22px; font-weight: bold; ">
                     وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:right; font-size: 20px; font-weight: bold; ">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:right; font-size: 20px; font-weight: bold; ">
                       
                        %(school_display)s
                    </td>
                </tr>
              
                <tr>
                <td style="text-align:center; font-size: 24px; font-weight: bold; ">
                  <h2>بطاقة معلومات الخاصة بالأساتذة المتعاقدين</h2>
                </td>
                </tr>
                <tr>
                 <td style="text-align:center; font-size: 20px; font-weight: bold; ">
                 السنة الدراسية %(school_year)s
                 </td>
                </tr>
            </table>
         
            <table width="90%%" align="center" class="info-table" border="1" cellspacing="0" cellpadding="1" style="font-size: 16px; line-height: 2.5;border-collapse: collapse; margin: 5px;">
                <tr>
                <td style="text-align: right; width: 50%%; border: 1px solid black; padding: 1px;  font-weight: bold;" >
                        اللقب: %(sub_last_name)s<br/>الإسم: %(sub_first_name)s<br/>رقم الحساب البريدي: %(sub_postal)s<br/>رقم الضمان الاجتماعي: %(sub_ss)s
                    </td>
                    <td style="text-align: left; width: 50%%; border: 1px solid black; padding: 1px; line-height: 2.5;" dir="ltr">
                        <span style="font-family: Arial;">NOM du CCP: <b>%(sub_last_name_fr)s</b><br/>
                        Prénom du CCP: <b>%(sub_first_name_fr)s</b><br/>
                        N CCP:</span> %(sub_postal)s
                    </td>
                    
                </tr>
                <tr>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >تاريخ ومكان الازدياد: %(sub_birth_date)s %(sub_birth_place)s</td>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >عنوان المتعاقد(ة): <b>%(sub_address)s</b></td>
                </tr>
                <tr>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >الوظيفــة: أستاذ(ة) مستخلف(ة)</td>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >التخصص: %(sub_degree_spec)s</td>
                </tr>
                <tr>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >تاريخ التنصيب: %(start_date)s</td>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >تاريخ نهاية التعاقد: %(end_date)s</td>
                </tr>
                 <tr>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >عدد الغيابات الإجمالية للفترة:...........</td>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >تحديد الفترة من : ........... إلى ...........</td>
                </tr>
                 <tr>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >معدل منحة تحسين الآداء التربوية:...../40</td>
                    <td style="text-align: right; border: 1px solid black; padding: 1px; font-weight: bold; " >تحديد الفترة من : %(start_date)s إلى %(end_date)s</td>
                </tr>
            </table>

            <table width="100%%"  style="margin-top: 15px;">
                <tr>
                    <td style="text-align:center; width:60%%;"></td>
                    <td style="font-size:20px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في %(today)s
                    </td>
                </tr>
                <tr>
                    <td style="text-align:center; width:60%%;"></td>
                    <td style="font-size:22px; font-weight: bold; text-align:center; width:40%%; padding-top: 10px;">
                        المدير
                    </td>
                </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "school_year": school_year,
            "school_address": school_address, "teacher_name": teacher_name,
            "teacher_subject": teacher["subject"] or "................",
            "desk_label": self._get_desk_label(settings),
            "sub_name": subst["substitute_name"],
            "sub_last_name": dict(subst).get("substitute_last_name", "") or "................",
            "sub_first_name": dict(subst).get("substitute_first_name", "") or "................",
            "sub_birth_place": subst["substitute_birth_place"],
            "sub_birth_date": subst["substitute_birth_date"],
            "sub_nid": subst["substitute_national_id"],
            "sub_postal": subst["substitute_postal_account"],
            "sub_ss": subst["substitute_social_security"],
            "sub_first_name_fr": dict(subst).get("substitute_first_name_fr") or "................",
            "sub_last_name_fr": dict(subst).get("substitute_last_name_fr") or "................",
            "sub_address": dict(subst).get("substitute_address") or ".................................",
            "sub_degree_type": subst["substitute_degree_type"],
            "sub_degree_spec": subst["substitute_degree_speciality"],
            "sub_degree_date": subst["substitute_degree_date"],
            "start_date": subst["start_date"].replace("-", "/"), "end_date": subst["end_date"].replace("-", "/"),
            "today": today_str, "director": director,
        }
        self._show_print_preview(html)

    def _print_installation_report(self, subst):
        """Print محضر التنصيب for a substitute."""
        teacher = db.get_employee(subst["teacher_id"])
        settings = db.get_all_settings()
        school = db.get_formatted_school_name()
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_address = settings.get("school_address", "......................")
        current_year = datetime.now().strftime("%Y")
        today_str = datetime.now().strftime("%Y/%m/%d")
        start_date = dict(subst).get("start_date", "").replace("-", "/")

        school_display = school + " - " + school_address
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code

        subst_dict = dict(subst)
        sub_last_name = subst_dict.get("substitute_last_name", "") or ""
        sub_first_name = subst_dict.get("substitute_first_name", "") or ""
        
        if not sub_last_name and not sub_first_name:
            sub_name = subst["substitute_name"]
            parts = sub_name.split(" ", 1)
            sub_last_name = parts[0]
            sub_first_name = parts[1] if len(parts) > 1 else ""
        
        teacher_subject = teacher["subject"] if teacher else "............"
        settings = db.get_all_settings()
        sub_grade_info = self._get_sub_grade_info(settings, dict(subst).get("substitute_degree_type", ""))

        html = """
        <html >
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px 40px;  }
            .header-text { font-size: 22px; font-weight: bold; text-align: center; }
            .header-info { width: 100%%; font-size: 18px; font-weight: bold; margin-top: 5px; }
            .title-box { border: 2px solid black; padding: 10px; width: fit-content; margin: 10px auto;margin-bottom: 30px; text-align: center; font-size: 28px; font-weight: bold; }
            .content-p { font-size: 18px; font-weight: bold; margin-top: 10px; text-align: right; }
            .info-line { font-size: 18px; font-weight: bold; margin-top: 15px;  }
            .signatures { width: 100%%; margin-top: 60px; font-size: 18px; font-weight: bold; text-align: center;  }
        </style></head>
        <body >
              <div class="header-text">الجمهورية الجزائرية الديمقراطية الشعبية</div>
            <div class="header-text">وزارة التربية الوطنية</div>
            <div style="font-size:18px; font-weight: bold; text-align: right;">
                مديرية التربية لولاية %(wilaya)s<br/>
                %(school_display)s
            </div>
            
         

            <div class="title-box">محـــــــــضر تنصيـــــــــب</div>

                    
            
            <table style="width: 100%%; font-size: 18px; margin: 5px auto; line-height: 2.5;">
                <tr> <td class="content-p">
                بنـــاء على مقرر التوظيف في إطـــار التعاقد على منصب مالي شاغـــر مؤقت عطلـــة مرضية
               
               
                </td></tr>
                     <tr> <td class="content-p">
               
               
                رقم: ........... /م.ت/م.ت.م/ %(current_year)s بتاريخ: %(today_str)s.
                </td></tr>
                <tr>
                 <td class="content-p">قمنا نحن السيد : مدير %(school)s   يوم: %(start_date)s بتنصيب السيد(ة):
                </td></tr>
                <tr><td style="width: 100%%;"></td></tr>
                <tr style="line-height: 2.5;">
                    <td style="width: 100%%;">اللقب : %(sub_last_name)s</td>
                </tr>
                <tr style="line-height: 2.5;">
                    <td style="width: 100%%;">الاسم : %(sub_first_name)s</td>
                </tr>   
                <tr style="line-height: 2.5;">
                    <td style="width: 100%%;">تاريخ الميلاد : %(sub_birth_date)s بـ %(sub_birth_place)s</td>
                </tr>
                <tr style="line-height: 2.5;">
                    <td style="width: 100%%;">الوظيفة : %(sub_prof_title)s - مادة %(teacher_subject)s</td>
                </tr>
                <tr style="line-height: 2.5;">
                    <td style="width: 100%%;">الوضعية الإدارية : مستخلف(ة) عطلة مرضية</td>
                </tr>
            </table>

          
            
       
         <table width="100%%"  style="margin-top: 15px;">
                <tr>
                <td style="text-align:center; width:60%%;"></td>
                    <td style="font-size:18px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في %(today)s
                    </td>
                    
                </tr>
                <tr>
                    
                    <td style="font-size:18px; font-weight: bold; text-align:center; width:60%%;">امضاء المعني</td>
               <td style="font-size:18px; font-weight: bold; text-align:center; width:40%%; padding-top: 10px;">
                        المدير
                    </td>
                </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "current_year": current_year,
            "school_address": school_address,
            "today_str": today_str, "start_date": start_date,
            "sub_last_name": sub_last_name, "sub_first_name": sub_first_name,
            "sub_birth_date": subst["substitute_birth_date"].replace("-", "/"),
            "sub_birth_place": subst["substitute_birth_place"],
            "teacher_subject": teacher_subject,
            "sub_prof_title": sub_grade_info["title"],
            "today": today_str
        }
        self._show_print_preview(html)

    def _print_appointment_decision(self, subst):
        """Print مقرر التعيين (مقرر تعاقد) for a substitute."""
        teacher = db.get_employee(subst["teacher_id"])
        sick_leave = db.get_sick_leave(subst["sick_leave_id"])
        settings = db.get_all_settings()
        school = db.get_formatted_school_name()
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "......................")
        teacher_name = db.get_employee_full_name(teacher) if teacher else "......................"
        subject = teacher["subject"] if teacher and teacher["subject"] else "......................"
        current_year = datetime.now().strftime("%Y")
        
        school_display = school
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code
        
        cert_date = dict(sick_leave).get("medical_cert_date", "").replace("-", "/") if sick_leave else ""
        if not cert_date:
            cert_date = "....................."

        start_date = dict(subst).get("start_date", "").replace("-", "/")
        end_date = dict(subst).get("end_date", "").replace("-", "/")

        degree_type = dict(subst).get("substitute_degree_type", "") or ""
        grade_info = self._get_sub_grade_info(settings, degree_type)
        class_grade = grade_info["class"]
        index_points = grade_info["index"]
        prof_title = grade_info["title"]

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Traditional Arabic', 'Amiri', serif;
                   text-align: right; margin: 0px; padding: 0px; font-size: 18px; }
            .header-text { line-height: 0.9; font-size: 24px; font-weight: bold; text-align: center; }
            .entete { line-height: 0.9; font-size: 22px; font-weight: bold; text-align: right; margin-bottom: 1px; }
            .considerations { font-size: 12px; text-align: right; }
            .article { text-align: right; font-size: 14px; margin-top: 3px; }
            .article-title { font-weight: bold; text-decoration: underline; }
            .footer-table td { font-weight: bold; padding: 0; margin: 0; font-size: 14px; }
        </style></head>
        <body >
            <div class="header-text" align="center">
                الجمهورية الجزائرية الديمقراطية الشعبية<br/>
                وزارة التربية الوطنية
            </div>
            
            <div class="entete" >
            مديرية التربية لولاية: %(wilaya)s<br/>
            مـصـلــــــحــــــــة الـمـستخدمين<br/>
            مكتـــب التعليـــــم الثـــــــانـــوي والمتوسط<br/>

             <span>الرقم:.............&rlm;/&rlm;م.ت &rlm;/&rlm;م.ت.م&rlm;/&rlm; %(current_year)s</span>
            
            </div>

            <div align="center" style="width:fit-content;margin:auto;border: 2px solid black;border-radius: 10px;padding: 5px;text-align: center;">
                <h2 style="font-size: 22px;font-weight: bold;text-align: center;margin:0px">مقرر توظـيف في اطار التعاقد</h2>
                <h3 style="font-size: 20px;font-weight: bold;text-align: center;margin:0px">عطلة مرضية / عطلة أمومة</h3>
            </div>

            <table width="100%%" cellspacing="0" cellpadding="0"  style="text-align: right;font-size: 16px;">
                <tr><td style="font-size: 20px;font-weight: bold;"><b>إن السيد(ة) مديـــر التربيـــة لولايـــة %(wilaya)s .</b></td></tr>
                <tr>
                    <td >- بمقتضى الأمر رقم : 06-03 المؤرخ في : 19 جمادى الثانية عام 1427 الموافق 15 يوليو سنة 2006 المتضمن القانون الأساسي العام للوظيفة العمومية المتمم.</td>
                  
                </tr>
                <tr>
                    <td >- بمقتضى المرسوم الرئاسي رقم :07-304 المؤرخ في 17 رمضان 1428 الموافق ل 29/سبتمبر 2007 الذي يحدد الشبكة الإستدلالية لمرتبات الموظفين ونظام دفع رواتبهم المعدل والمتمم.</td>
                  
                </tr>
                <tr>
                    <td >- بمقتضى المرسوم التنفيذي رقم 90/99 المؤرخ في :اول رمضان عام 1410 الموافق ل27مارس سنة1990 المتعلق بسلطة التعيين و التسيير الإداري بالنسبة للموظفين و أعوان الإدارة الـمركزية و الـولايات و البلديـات و المؤسسـات الـعمومية ذات الطـابع الإداري .</td>
                  
                </tr>
                <tr>
                    <td >- بمقتضى المرسوم التنفيذي رقم :90/174 المؤرخ في 09جوان 1990 المعدل بالمرسوم رقم:02-71 المؤرخ في:19 فيفري 2002 الذي يحدد كيفية تنظيم مديرية التربية على مستوى الولاية وسيرها.</td>
                  
                </tr>
                <tr>
                    <td >- بمقتضى المرسوم التنفيدي رقم :25/54 المؤرخ في:23جمادى التانية عام1444 الموافق ل21جانفي2025 المتضمن القانون الاساسي الخاص بالموظفين المنتمين للاسلاك الخاصة بالتربية الوطنية.</td>
                  
                </tr>
                <tr>
                    <td >- بناء على التعليمة الوزارية رقم : 05 المؤرخ في 2025/07/24 التي تحدد كيفيات توظيف أساتذة بصفة متعاقدين في مؤسسات التعليم التابعة لوزارة التربية الوطنية ودفع رواتبهم.</td>
                  
                </tr>
                <tr>
                    <td  style="font-size: 18px;">- بناء على الشهادة الطبية المؤرخة في <b>%(cert_date)s</b> المقدمة من طرف الأستاذ(ة): <b>%(teacher_name)s</b> .</td>
                    
                </tr>
                <tr>
                    <td  style="font-size: 18px;">- بناء على طلب التوظيف المقدم من طرف السيد(ة): <b>%(sub_name)s</b> المؤرخ في : <b>%(sub_start_date)s</b> .</td>
                    
                </tr>
                <tr>
                    <td  style="font-size: 18px;"> الحاصل(ة) على شهادة: <b>%(sub_degree_type)s تخصص %(sub_degree_spec)s</b> الصادرة عن : <b>%(sub_degree_source)s</b> .</td>
                   
                </tr>
                <tr>
                    <td  style="font-size: 18px;">- باقتراح من السيـــد(ة) مديـر(ة): <b>%(school)s</b> .</td>
                    
                </tr>
            </table>

            <div align="center" style="font-size: 24px; font-weight: bold; margin: 5px;">يــــــــقــــــــــــرر</div>

            <table width="100%%" cellspacing="0" cellpadding="0"  style="text-align: right;font-size: 20px;">
                <tr>
                    <td colspan="2" >
                        <span style="font-weight: bold; text-decoration: underline;">المـادة الأولــى :</span> يوظف السيــد (ة) : <b>%(sub_name)s</b>، 
                    </td>
                </tr>
                <tr><td colspan="2" > في إطار التعاقد على منصب شاغر مؤقت (عطلة مرضية) من: <b>%(start_date)s</b> إلى: <b>%(end_date)s</b>،</td></tr>
                <tr><td colspan="2" > في رتبة : <b>%(prof_title)s</b>، المادة : <b>%(subject)s</b>،</td></tr>
                <tr><td colspan="2" > خلفــا للأستاذ(ة) : <b>%(teacher_name)s</b> بالمؤسسة : <b>%(school)s</b>.</td></tr>
                <tr>
                    <td colspan="2" >
                        <span style="font-weight: bold; text-decoration: underline;">المادة الثانية :</span> يتقاضى المعني(ة) بالأمر مرتبه(ها) على أساس الصنف <b>%(class_grade)s</b> الرقم الاستدلالي <b>%(index_points)s</b>.
                    </td>
                </tr>
               <tr>
                    <td colspan="2" >
                        <span style="font-weight: bold; text-decoration: underline;">المـادة الثالثة :</span> يكلف السادة رئيس مصلحة المستخدمين و رئيس مصلحة تسيير نفقات المستخدمين و مدير(ة) المؤسسة بتنفيذ هذا القرار كل في مجال اختصاصه .
                    </td>
                </tr>
                <tr>
                    <td style="font-weight: bold;text-align:right; width:50%%;"></td>
                    <td align="center" style="text-align:center; width:50%%;" >
                        %(wilaya)s في <b>%(start_date)s</b>
                    </td>
                </tr>
                <tr>
                    <td style="text-align:right; width:50%%;"></td>
                    <td align="center" style="font-weight: bold;text-align:center; width:50%%;" >
                        مدير التربية
                    </td>
                </tr>
            </table>

        </body></html>
        """ % {
            "wilaya": wilaya,
            "school": school,
            "current_year": current_year,
            "sub_name": subst["substitute_name"],
            "sub_start_date": dict(subst).get("start_date", "").replace("-", "/"),
            "sub_degree_type": degree_type,
            "sub_degree_spec": subst["substitute_degree_speciality"],
            "sub_degree_source": dict(subst).get("substitute_degree_source", "") or ".....................",
            "cert_date": cert_date,
            "teacher_name": teacher_name,
            "start_date": start_date,
            "end_date": end_date,
            "prof_title": prof_title,
            "subject": subject,
            "class_grade": class_grade,
            "index_points": index_points,
        }
        self._show_print_preview(html)

    def _print_sub_work_cert(self, subst):
        settings = db.get_all_settings()
        school = db.get_formatted_school_name()
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        school_address = settings.get("school_address", "......................")
        year = datetime.now().year
        school_initials = self._get_school_initials(school)
        director = settings.get("director_name", "")
        
        school_display = school + " - " + school_address
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code
        
        subst_dict = dict(subst)
        emp_fn = subst_dict.get("substitute_first_name", "") or ""
        emp_ln = subst_dict.get("substitute_last_name", "") or ""
        
        if not emp_fn and not emp_ln:
            emp_fn = subst_dict.get("substitute_name", "") or ""
            emp_ln = "" # Could split, but typically substitute_name contains both
            if " " in emp_fn:
                parts = emp_fn.split(" ", 1)
                emp_fn = parts[1]
                emp_ln = parts[0]
            
        emp_bd = (subst_dict.get("substitute_birth_date", "") or "ــــ/ــ/ــ").replace("-", "/")
        emp_bp = subst_dict.get("substitute_birth_place", "") or ""
        
        emp_grade = "أستاذ(ة) مستخلف(ة)"
        emp_subject = ""
        # Could resolve subject via teacher ID if needed, or leave blank/generic.
        # Let's see if we can get it from teacher since we usually have teacher_subject in subst dict (it's actually in UI only).
        # We will retrieve teacher to get subject
        teacher = db.get_employee(subst["teacher_id"])
        if teacher:
            teacher_dict = dict(teacher)
            if teacher_dict.get("subject"):
                emp_subject = teacher_dict["subject"]
            
        effective_date = subst_dict.get("start_date", "ــــ/ــ/ــ").replace("-", "/")
        end_date = subst_dict.get("end_date", "").replace("-", "/")
        status = subst_dict.get("status", "جارية")
        if status == "جارية":
            work_status_text = "يزاول عمله منذ %s إلى يومنا هذا." % effective_date
        else:
            if not end_date:
                work_status_text = "زاول عمله منذ %s." % effective_date
            else:
                work_status_text = "زاول عمله منذ %s إلى %s." % (effective_date, end_date)

        html = """
        <html >
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px;  }
            .header-text { font-size: 18px; font-weight: bold; text-align: center; margin: 2px 0; }
            .header-right { font-size: 14px; font-weight: bold; text-align: right; margin-top: 10px; margin-bottom: 20px;  }
        </style></head>
        <body >
             <table width="100%%"  style="font-size:22px; font-weight:bold; margin-top: 0px; margin-bottom: 5px;">
                <tr >
                    <td align="center" width="100%%" style="padding:0px; font-size: 22px; font-weight: bold; ">
                    الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr >
                    <td align="center" width="100%%" style="padding:0px; font-size: 22px; font-weight: bold; ">
                    وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td  width="100%%" style="padding:0px; font-size: 20px; font-weight: bold; ">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td  width="100%%" style="padding:0px; font-size: 20px; font-weight: bold; ">
                       
                        %(school_display)s
                    </td>
                </tr>
                  <tr style="">
                    
                  
               
                    <td  style="font-size: 18px;text-align: right;">
                     <span>الرقم:.............&rlm;/&rlm; %(school_initials)s&rlm;/&rlm; %(year)s</span>
                    </td>
                    </tr>
                      <tr>
 <td>
                       </td>
                       </tr>
                <tr>
                <td style="padding:10px;font-size: 28px;font-weight: bold;" align="center" width="100%%">
                   
                    شهادة عمــــل
                  
                </td>
                </tr>
           
            </table>
          
            <table  width="100%%" border="0" style="font-size:18px;  line-height:2; margin-top: 15px;">
                <tr>
                <td colspan="3" style="font-size:18px;font-weight:bold;">يشهد السيد مدير %(school)s أن السيد(ة) المذكور(ة) أسفله:</td>
                </tr>
                <tr>
                <td width="5%%" style="border: none;"> </td>
                <td width="20%%" style="border: none;">الإسم:</td>
                <td width="75%%" style="border: none;">%(first_name)s</td>
                </tr>
               <tr>
                <td width="5%%" style="border: none;"> </td>
                <td width="20%%" style="border: none;">اللقب:</td>
                <td width="75%%" style="border: none;">%(last_name)s</td>
                </tr>

                <tr>
                <td width="5%%" style="border: none;"> </td>
                <td width="20%%" style="border: none;">تاريخ ومكان الميلاد:</td>
                <td width="75%%" style="border: none;">%(birth_date)s %(birth_place)s</td>
                </tr>
                <tr>
                <td width="5%%" style="border: none;"> </td>
                <td width="20%%" style="border: none;">الوظيفة:</td>
                <td width="75%%" style="border: none;">%(grade)s مادة: %(subject)s</td>
                </tr>
                <tr>
               
                <td colspan="3" style="font-weight:bold;font-size:18px;border: none;">      %(work_status_text)s </td>
                </tr>
                 <tr>
               
                <td align="center" style="font-size:20px; font-weight:bold; margin-top: 5px;" colspan="3">  سُلمت هذه الشهادة للعمل بها في حدود ما يقتضيه القانون. </td>
                </tr>
            </table>
           
            
             <table width="100%%"  style="margin-top: 15px;font-size: 18px;">
             <tr>
                    <td>
                </td>
                </tr>
                <tr>
                    <td style="text-align:right; width:50%%;"></td>
                    <td align="center" style="font-size:18px;text-align:center; width:50%%;" >
                        حرر بـ %(school_address)s في: %(date)s
                    </td>
                </tr>
                <tr>
                    <td style="text-align:right; width:50%%;"></td>
                    <td align="center" style="font-size:18px;font-weight:bold;text-align:center; width:50%%;" >
                     مدير المؤسسة
                    </td>
                </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display,
            "school_address": school_address,
            "first_name": emp_fn, "last_name": emp_ln,
            "birth_date": emp_bd, "birth_place": emp_bp,
            "grade": emp_grade, "subject": emp_subject,
            "effective_date": effective_date,
            "work_status_text": work_status_text,
            "start_date": effective_date,
            "year": year, "school_initials": school_initials,
            "date": datetime.now().strftime("%Y/%m/%d")
        }
        self._show_print_preview(html)

    def refresh(self):
        self._refresh_leaves()
        self._refresh_substitutions()
        self._check_expired_leaves()

    def _update_stats(self):
        pass

    def _refresh_leaves(self):
        leaves = db.get_all_sick_leaves()
        self.leaves_table.setRowCount(0)
        self.leaves_table.setRowCount(len(leaves))

        for row, sl in enumerate(leaves):
            self.leaves_table.setItem(row, 0, self._item(sl["employee_name"]))
            self.leaves_table.setItem(row, 1, self._item(sl["employee_grade"] or ""))
            self.leaves_table.setItem(row, 2, self._item(sl["start_date"]))
            self.leaves_table.setItem(row, 3, self._item(sl["end_date"]))
            self.leaves_table.setItem(row, 4, self._item("%s يوم" % sl["duration_days"]))

            # Status badge
            status = sl["status"]
            status_label = QLabel(status)
            status_label.setAlignment(Qt.AlignCenter)
            if status == "جارية":
                status_label.setObjectName("badge_warning")
            else:
                status_label.setObjectName("badge_success")
            self.leaves_table.setCellWidget(row, 5, status_label)

            # Actions
            actions = QWidget()
            actions.setLayoutDirection(Qt.RightToLeft)
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)
            options_btn = QPushButton(" خيارات")
            options_btn.setIcon(get_icon("settings", color="#475569"))
            options_btn.setCursor(Qt.PointingHandCursor)
            options_btn.setStyleSheet("""
                QPushButton { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 12px; font-weight: bold; }
                QPushButton:hover { background-color: #e2e8f0; color: #1e293b; }
            """)
            menu = QMenu(options_btn)
            menu.setLayoutDirection(Qt.RightToLeft)
            menu.setStyleSheet("""
                QMenu { background-color: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; }
                QMenu::item { padding: 6px 24px; border-radius: 4px; color: #1e293b; font-size: 13px; }
                QMenu::item:selected { background-color: #f1f5f9; color: #2563eb; }
            """)

            if status == "جارية":
                end_action = menu.addAction(get_icon("check", color="#10b981"), "إنهاء العطلة واستئناف العمل")
                end_action.triggered.connect(lambda checked, sid=sl["id"]: self._end_sick_leave(sid))
                menu.addSeparator()

            print_action = menu.addAction(get_icon("print", color="#475569"), "طباعة طلب العطلة المرضية")
            print_action.triggered.connect(lambda checked, sid=sl["id"], eid=sl["employee_id"]: self._print_sick_leave_request(sid, db.get_employee(eid)))

            if status == "منتهية":
                reprint_action = menu.addAction(get_icon("document", color="#475569"), "إعادة طباعة بيان استئناف العمل")
                reprint_action.triggered.connect(
                    lambda checked, sid=sl["id"]: self._reprint_resume_work(sid)
                )

            menu.addSeparator()
            delete_action = menu.addAction(get_icon("delete", color="#ef4444"), "حذف العطلة المرضية")
            delete_action.triggered.connect(lambda checked, sid=sl["id"]: self._delete_sick_leave(sid))

            options_btn.setMenu(menu)
            al.addWidget(options_btn)
            al.addStretch()
            self.leaves_table.setCellWidget(row, 6, actions)
            self.leaves_table.setRowHeight(row, 42)

    def _refresh_substitutions(self):
        substs = db.get_all_substitutions()
        self.subst_table.setRowCount(0)
        self.subst_table.setRowCount(len(substs))

        for row, s in enumerate(substs):
            self.subst_table.setItem(row, 0, self._item(s["teacher_name"]))
            self.subst_table.setItem(row, 1, self._item(s["substitute_name"]))
            self.subst_table.setItem(row, 2, self._item(s["start_date"]))
            self.subst_table.setItem(row, 3, self._item(s["end_date"]))
            self.subst_table.setItem(row, 4, self._item(s["teacher_subject"] or ""))

            status = s["status"]
            status_label = QLabel(status)
            status_label.setAlignment(Qt.AlignCenter)
            if status == "جارية":
                status_label.setObjectName("badge_warning")
            else:
                status_label.setObjectName("badge_success")
            self.subst_table.setCellWidget(row, 5, status_label)

            # Actions
            actions = QWidget()
            actions.setLayoutDirection(Qt.RightToLeft)
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)
            options_btn = QPushButton(" خيارات")
            options_btn.setIcon(get_icon("settings", color="#475569"))
            options_btn.setCursor(Qt.PointingHandCursor)
            options_btn.setStyleSheet("""
                QPushButton { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 12px; font-weight: bold; }
                QPushButton:hover { background-color: #e2e8f0; color: #1e293b; }
            """)
            menu = QMenu(options_btn)
            menu.setLayoutDirection(Qt.RightToLeft)
            menu.setStyleSheet("""
                QMenu { background-color: white; border: 1px solid #cbd5e1; border-radius: 4px; padding: 4px; }
                QMenu::item { padding: 6px 24px; border-radius: 4px; color: #1e293b; font-size: 13px; }
                QMenu::item:selected { background-color: #f1f5f9; color: #2563eb; }
            """)
            edit_action = menu.addAction(get_icon("edit", color="#475569"), "تعديل معلومات الاستخلاف")
            edit_action.triggered.connect(lambda checked, sid=s["id"]: self._edit_substitution(sid))
            menu.addSeparator()
            
            print_menu = menu.addMenu(get_icon("print", color="#475569"), "طباعة وثيقة...")
            print_menu.setLayoutDirection(Qt.RightToLeft)
            
            act1 = print_menu.addAction("محضر التنصيب")
            act1.triggered.connect(lambda checked, sid=s["id"]: self._print_installation_report(db.get_substitution(sid)))
            
            act2 = print_menu.addAction("مقرر التعيين")
            act2.triggered.connect(lambda checked, sid=s["id"]: self._print_appointment_decision(db.get_substitution(sid)))
            
            act3 = print_menu.addAction("شهادة عمل")
            act3.triggered.connect(lambda checked, sid=s["id"]: self._print_sub_work_cert(db.get_substitution(sid)))
            
            if status == "جارية":
                menu.addSeparator()
                end_action = menu.addAction(get_icon("flag", color="#f59e0b"), "طباعة نهاية الاستخلاف وبطاقة المعلومات")
                end_action.triggered.connect(lambda checked, sid=s["id"], tid=s["teacher_id"]: self._print_end_substitution(db.get_employee(tid), db.get_substitution(sid)))

            # Cancel substitution option (always available)
            menu.addSeparator()
            cancel_action = menu.addAction(get_icon("delete", color="#ef4444"), "إلغاء الاستخلاف")
            cancel_action.triggered.connect(lambda checked, sid=s["id"], sname=s["substitute_name"]: self._cancel_substitution(sid, sname))

            options_btn.setMenu(menu)
            al.addWidget(options_btn)

            al.addStretch()
            self.subst_table.setCellWidget(row, 6, actions)
            self.subst_table.setRowHeight(row, 48)

    def _edit_substitution(self, sid):
        subst = db.get_substitution(sid)
        if not subst: return
        teacher = db.get_employee(subst["teacher_id"])
        dialog = SubstitutionDetailsDialog(
            teacher=teacher,
            sick_leave_id=subst["sick_leave_id"],
            start_date=subst["start_date"],
            end_date=subst["end_date"],
            parent=self,
            substitute=dict(subst)
        )
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            db.update_substitution(sid, data)
            self.refresh()
            QMessageBox.information(self, "نجاح", "تم تحديث بيانات الاستخلاف بنجاح.")

    def _cancel_substitution(self, sub_id, substitute_name):
        """Cancel/delete a substitution after confirmation."""
        reply = QMessageBox.warning(
            self, "تأكيد إلغاء الاستخلاف",
            "هل أنت متأكد من إلغاء استخلاف:\n\n"
            "المستخلف(ة): %s\n\n"
            "⚠️ سيتم حذف جميع معلومات الاستخلاف نهائياً.\n"
            "هذا الإجراء لا يمكن التراجع عنه." % substitute_name,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db.delete_substitution(sub_id)
            self.refresh()
            QMessageBox.information(
                self, "تم الإلغاء",
                "✅ تم إلغاء الاستخلاف بنجاح.\n"
                "يمكنك إضافة مستخلف(ة) جديد(ة) إذا لزم الأمر."
            )

    def _reprint_resume_work(self, sl_id):
        """Reprint the resume work document for a completed sick leave."""
        sl = db.get_sick_leave(sl_id)
        if not sl:
            return
        emp = db.get_employee(sl["employee_id"])
        if not emp:
            return

        resume_str = sl["resume_date"]
        if not resume_str:
            # Fallback: calculate from end_date
            end_date = datetime.strptime(sl["end_date"], "%Y-%m-%d")
            resume_date = end_date + timedelta(days=1)
            resume_str = resume_date.strftime("%Y-%m-%d")

        self._print_resume_work(emp, sl, resume_str)

    def _check_expired_leaves(self):
        """Check for active sick leaves that have expired and show toast."""
        # Clear existing toasts
        for toast in self._active_toasts:
            try:
                toast._dismiss()
            except RuntimeError:
                pass
        self._active_toasts.clear()

        expired = db.get_expired_sick_leaves()
        if not expired:
            return

        # Build notification message
        lines = []
        for sl in expired:
            emp_name = sl["employee_name"]
            end_date = sl["end_date"]
            days_past = (datetime.now() - datetime.strptime(end_date, "%Y-%m-%d")).days
            lines.append(
                "• %s — انتهت بتاريخ %s (منذ %d يوم)" % (emp_name, end_date, days_past)
            )

        msg = "يوجد %d عطلة مرضية منتهية لم يتم تأكيد استئناف العمل:\n%s" % (
            len(expired), "\n".join(lines)
        )

        toast = ToastNotification(msg, self, duration=12000, toast_type="warning")
        self._toast_container.addWidget(toast)
        self._active_toasts.append(toast)
        toast.show_toast()

    def _get_sub_grade_info(self, settings, degree_type):
        """Determine substitute grade title, classification, and index based on school stage and diploma."""
        stage = settings.get("school_stage", "متوسط")
        degree = (degree_type or "").strip()
        
        if stage == "إبتدائي" or stage == "ابتدائي":
            stage_label = "الابتدائي"
            if "ماستر" in degree or "مهندس" in degree:
                return {"title": "أستاذ التعليم %s قسم أول" % stage_label, "class": "13", "index": "778"}
            elif "ليسانس" in degree:
                return {"title": "أستاذ التعليم %s" % stage_label, "class": "12", "index": "737"}
            else:
                return {"title": "أستاذ التعليم %s" % stage_label, "class": "____", "index": "____"}
        elif stage == "ثانوي":
            stage_label = "الثانوي"
            if "ماجستير" in degree or "دكتوراه" in degree:
                return {"title": "أستاذ التعليم %s قسم أول" % stage_label, "class": "14", "index": "821"}
            elif "ماستر" in degree or "مهندس" in degree:
                return {"title": "أستاذ التعليم %s" % stage_label, "class": "12", "index": "737"}
            elif "ليسانس" in degree:
                return {"title": "أستاذ التعليم %s" % stage_label, "class": "12", "index": "737"}
            else:
                return {"title": "أستاذ التعليم %s" % stage_label, "class": "____", "index": "____"}
        else:  # متوسط (default)
            stage_label = "المتوسط"
            if "ماستر" in degree or "مهندس" in degree:
                return {"title": "أستاذ التعليم %s قسم أول" % stage_label, "class": "13", "index": "778"}
            elif "ليسانس" in degree:
                return {"title": "أستاذ التعليم %s" % stage_label, "class": "12", "index": "737"}
            else:
                return {"title": "أستاذ التعليم %s" % stage_label, "class": "____", "index": "____"}

    def _get_desk_label(self, settings):
        """Return the correct office name based on school stage."""
        stage = settings.get("school_stage", "متوسط")
        if stage == "إبتدائي":
            return "مكتب التعليم الابتدائي"
        elif stage == "ثانوي":
            return "مكتب التعليم الثانوي"
        else:
            return "مكتب التعليم المتوسط"

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

    def _item(self, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

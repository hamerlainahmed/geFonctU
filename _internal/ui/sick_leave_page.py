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
            "font-size: 13px; color: %s; background: transparent; line-height: 1.5;" % s["text"]
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
    """Dialog for requesting a sick leave.
    
    If `employee` is provided, the employee selector is hidden and
    that employee is used directly (useful when called from EmployeesPage).
    """

    def __init__(self, parent=None, employee=None):
        super().__init__(parent)
        self._preset_employee = employee  # pre-selected employee (optional)
        self.setWindowTitle("طلب عطلة مرضية")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(520)
        self._build_ui()
        if employee:
            self._apply_preset_employee()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        title_lbl = QLabel("طلب عطلة مرضية 🏥")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(title_lbl)

        form = ArabicFormLayout()

        # Employee selector — shown only if no preset employee
        self.employee_combo = ArabicComboBox()
        self._load_employees()
        self._employee_combo_row_label = QLabel("الموظف:")
        form.addRow(self._employee_combo_row_label, self.employee_combo)

        # Static employee label — shown when employee is preset
        self._preset_emp_label = ArabicLabel("")
        self._preset_emp_label.setStyleSheet(
            "font-weight: bold; font-size: 15px; color: #1e293b;"
            " padding: 6px 12px; background: #f1f5f9;"
            " border: 1px solid #e2e8f0; border-radius: 8px;"
        )
        self._preset_emp_row_label = QLabel("الموظف:")
        form.addRow(self._preset_emp_row_label, self._preset_emp_label)
        self._preset_emp_label.hide()
        self._preset_emp_row_label.hide()

        # Start date
        self.start_date = ArabicDateEdit()
        form.addRow("تاريخ أول يوم:", self.start_date)

        # Number of days
        self.days_spin = QSpinBox()
        self.days_spin.setLayoutDirection(Qt.RightToLeft)
        self.days_spin.setMinimum(1)
        self.days_spin.setMaximum(365)
        self.days_spin.setValue(1)
        self.days_spin.setSuffix(" يوم")
        self.days_spin.setStyleSheet("""
            QSpinBox {
                padding: 6px 12px;
                font-size: 14px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                background: #ffffff;
                min-height: 32px;
            }
            QSpinBox:focus {
                border-color: #3b82f6;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 24px;
                border: none;
            }
        """)
        form.addRow("عدد الأيام:", self.days_spin)

        # Calculated end date (read-only)
        self.end_date_label = ArabicLabel("")
        self.end_date_label.setStyleSheet("""
            font-weight: bold;
            font-size: 15px;
            color: #1d4ed8;
            padding: 6px 12px;
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
        """)
        form.addRow("📅 آخر يوم عطلة:", self.end_date_label)

        self.start_date.dateChanged.connect(self._update_duration)
        self.days_spin.valueChanged.connect(self._update_duration)

        # Medical Certificate Date
        self.cert_date = ArabicDateEdit()
        form.addRow("تاريخ الشهادة الطبية:", self.cert_date)

        # Doctor name
        self.doctor_input = ArabicLineEdit("اسم الطبيب الذي حرر الشهادة")
        form.addRow("اسم الطبيب:", self.doctor_input)

        layout.addLayout(form)

        # Info about substitution
        self.subst_info = QFrame()
        self.subst_info.setObjectName("dashboard_panel")
        info_layout = QVBoxLayout(self.subst_info)
        info_layout.setContentsMargins(12, 12, 12, 12)
        self.subst_info_label = QLabel("")
        self.subst_info_label.setWordWrap(True)
        self.subst_info_label.setStyleSheet("font-size: 13px; background: transparent;")
        info_layout.addWidget(self.subst_info_label)
        layout.addWidget(self.subst_info)
        self.subst_info.hide()

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = ActionButton("تأكيد الطلب", "✔", "success")
        self.save_btn.clicked.connect(self._save)
        cancel_btn = ActionButton("إلغاء", "✖", "outline")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._update_duration()

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
        # trigger substitution info update
        self._update_duration()

    def _get_selected_employee(self):
        if self._preset_employee:
            return self._preset_employee
        idx = self.employee_combo.currentIndex()
        if idx < 0:
            return None
        emp_id = self.employee_combo.currentData()
        return db.get_employee(emp_id)

    def _update_duration(self):
        start = self.start_date.date().toPyDate()
        days = self.days_spin.value()
        end = start + timedelta(days=days - 1)

        # Update the calculated end date label
        self.end_date_label.setText("%04d/%02d/%02d" % (end.year, end.month, end.day))

        emp = self._get_selected_employee()
        if emp and "أستاذ" in (emp["grade"] or ""):
            if days > 7:
                self.subst_info.show()
                self.subst_info_label.setText(
                    "⚠️ مدة العطلة المرضية تتجاوز 7 أيام.\n"
                    "بعد تأكيد الطلب، ستنتقل لإدخال معلومات الأستاذ(ة) المستخلف(ة)."
                )
                self.subst_info_label.setStyleSheet(
                    "color: #b45309; font-size: 13px; background: transparent; font-weight: bold;"
                )
                self.save_btn.setText(" 📝 إدخال معلومات الاستخلاف")
            else:
                self.subst_info.show()
                self.subst_info_label.setText(
                    "لا يتطلب استخلاف. سيتم طباعة طلب العطلة المرضية مباشرة."
                )
                self.subst_info_label.setStyleSheet(
                    "color: #059669; font-size: 13px; background: transparent;"
                )
                self.save_btn.setText(" ✔ تأكيد وطباعة الطلب")
        else:
            self.subst_info.hide()
            self.save_btn.setText(" ✔ تأكيد الطلب")

    def _save(self):
        emp = self._get_selected_employee()
        if not emp:
            QMessageBox.warning(self, "تنبيه", "يرجى اختيار موظف")
            return

        doctor = self.doctor_input.text().strip()
        if not doctor:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الطبيب")
            return

        self.accept()

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
        self.end_date_str = end_date
        self.substitute_data = substitute
        teacher_name = db.get_employee_full_name(teacher) if teacher else (substitute.get("teacher_name", "") if substitute else "")
        self.setWindowTitle("تعديل معلومات المستخلف" if substitute else ("استخلاف الأستاذ(ة): %s" % teacher_name))
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(680)
        self._build_ui()
        if substitute:
            self._populate(substitute)

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
            QMessageBox.information(
                self, "نجاح",
                "✅ تم تسجيل الاستخلاف بنجاح.\n"
                "يمكنك الآن طباعة محضر التنصيب ومقرر التعيين من قائمة الإجراءات."
            )
            self.refresh()

    def _new_sick_leave(self):
        dialog = SickLeaveRequestDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            sl_id = db.add_sick_leave(data)

            emp = db.get_employee(data["employee_id"])

            if dialog.needs_substitution():
                # Show substitution details dialog
                subst_dialog = SubstitutionDetailsDialog(
                    emp, sl_id, data["start_date"], data["end_date"], self
                )
                if subst_dialog.exec_() == QDialog.Accepted:
                    subst_data = subst_dialog.get_data()
                    db.add_substitution(subst_data)
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
                    self, "نجاح",
                    "✅ تم تسجيل طلب العطلة المرضية بنجاح."
                )
                self._print_sick_leave_request(sl_id, emp)

            self.refresh()

    def _print_sick_leave_request(self, sl_id, emp):
        sl = db.get_sick_leave(sl_id)
        if not sl:
            return
        settings = db.get_all_settings()
        html = self._generate_sick_leave_html(sl, emp, settings)
        self._show_print_preview(html, landscape=False)

    def _generate_sick_leave_html(self, sl, emp, settings):
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        school_address = settings.get("school_address", "........................")
        
        emp_last_name = emp["last_name"]
        emp_first_name = emp["first_name"]
        emp_grade = emp["grade"] or ""
        subject_line = ""
        if emp["subject"]:
            subject_line = " مادة %s" % emp["subject"]

        school_display = school
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
            history_html += "<tr style='line-height: 0.8;' align='right'><td style='width: 50%%;'>%s</td><td style='width: 50%%;'>%s</td></tr>" % (
                history_slots[r*2+1], history_slots[r*2]
            )

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 40px; }
            .header-text { font-size: 22px; font-weight: bold; text-decoration: underline; text-align: center; }
            .right-header { font-size: 22px; font-weight: bold; text-align: right; margin-top: 50px; margin-bottom: 60px; line-height: 1.5; }
            .title { font-size: 48px; font-weight: bold; text-align: center; margin-bottom: 60px; }
            .content { font-size: 16px; font-weight: bold; line-height: 0.9; }
            .flex-row { display: flex; width: 60%%; justify-content: space-between; }
            .table-history { width: 85%%; border: none; font-size: 12px; font-weight: bold; margin-top: 5px; }
            .table-history td { padding: 1px 0; }
            .footer-table { width: 100%%; font-size: 24px; font-weight: bold; margin-top: 80px; }
        </style></head>
        <body dir="rtl">
         <table width="100%%" dir="rtl" style="margin-top: -2x; margin-bottom: 5px;line-height: 0.8;">
                <tr>
                    <td style="text-align:center;padding:0px; font-size: 16px; font-weight: bold; line-height: 0.8;">
                       الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:center;padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                     وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:left;padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:left;padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                       
                        %(school_display)s
                    </td>
                </tr>
                <tr>
                <td width="100%%" style="text-align:center; font-size: 22px; font-weight: bold; line-height: 0.8;">
                  طلب عطلة مرضية
                </td>
                </tr>
           
            </table>
            <table width="100%%" class="content" align="right" style="line-height: 0.9;">
            <tr style="line-height: 0.9;">
            <td>اللقب : %(last_name)s</td>
            <td>الاسم : %(first_name)s</td>
            </tr>
            <tr style="line-height: 0.9;">
            <td colspan="2">الرتبة : %(emp_grade)s%(subject_line)s</td>
            </tr>
            <tr style="line-height: 0.9;">
            <td colspan="2">يطلب رخصة: عطلة مرضية %(duration)s يوم من: %(start_date)s الى: %(end_date)s</td>
            </tr>
            <tr style="line-height: 0.9;">
            <td colspan="2">للسبب التالي : عطلة مرضية</td>
            </tr>
            <tr style="line-height: 0.9;">
            <td colspan="2">الوثائق المرفقة : شهادة طبية</td>
            </tr>
            </table>
           <div width="100%%"  style="margin-top: 5px;">
                <div align="right" style="font-size: 16px; font-weight: bold; line-height: 0.9;">العطل المحصل عليها خلال الاثني عشر شهر التي سبقت هذا الطلب</div>
                <table width="100%%" align="right" dir="rtl" style="line-height: 0.8;" class="table-history">
                    %(history_html)s
                </table>
            </div>

        <table width="100%%" dir="rtl" style="margin-top: 2px;line-height: 0.9;">
               <tr>
                <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;line-height: 0.9;">
                        %(school_address)s في : %(today)s
                </td>
                <td style="text-align:center; width:30%%;"></td>
                  <td style="text-align:center; width:30%%;">إمضاء المعني(ة) بالأمر</td>
           
            </tr>
            <tr>
                <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;line-height: 0.9;">
                        المدير
                </td>
                <td style="text-align:center; width:30%%;"></td>
                <td style="text-align:center; width:30%%;">%(emp_name)s</td>
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
        }

        return html

    def _show_print_preview(self, html, landscape=False):
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=landscape)
        dialog.exec_()

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

        # Print resume work document
        self._print_resume_work(emp, sl, resume_str)

        # If there was a substitution, print end of substitution
        if subst:
            self._print_end_substitution(emp, subst)

        self.refresh()

    def _print_resume_work(self, emp, sl, resume_str):
        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")
        school_address = settings.get("school_address", "......................")
        emp_name = db.get_employee_full_name(emp)

        subject_line = ""
        if emp["subject"]:
            subject_line = "، مادة: <b>%s</b>" % emp["subject"]
            
        school_display = school
        if school_code:
            school_display += "<br/>رمز المؤسسة: %s" % school_code
        today = datetime.now().strftime("%Y/%m/%d")

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px; line-height: 0.9; }
            .header-text { font-size: 16px; font-weight: bold; text-align: center; margin: 2px 0; }
            .header-right { font-size: 14px; font-weight: bold; text-align: left; margin-top: 2px; margin-bottom: 5px; line-height: 0.9; }
            .doc-title { text-align: center; font-size: 45px; font-weight: bold; margin: 10; font-family: 'Arial', 'Amiri', sans-serif; text-shadow: 2px 2px #ccc; }
            .intro-text { font-size: 16px; font-weight: bold; margin-bottom: 2px; text-align: left; }
            .info-table { border-collapse: collapse; width: 100%%; margin: 10px; border: 1px solid black!important;line-height: 0.9; }
            .info-table th, .info-table td { border: 1px solid black!important; padding: 2px; text-align: center; font-size: 14px;  }
        </style></head>
        <body dir="rtl">
          <table width="100%%" dir="rtl" style="margin-top: -2x; margin-bottom: 5px;line-height: 0.8;">
                <tr>
                    <td style="text-align:center;padding:0px; font-size: 16px; font-weight: bold; line-height: 0.8;">
                       الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:center;padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                     وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:left;padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:left;padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                       
                        %(school_display)s
                    </td>
                </tr>
                <tr>
                <td width="100%%" style="text-align:center; font-size: 18px; font-weight: bold; line-height: 0.8;">
                  بيان استئناف عمل
                </td>
                </tr>
           
            </table>

          

            <div class="intro-text">
                إن مدير المؤسسة المذكور أسفله يفيد المعني (ة) و السلطات المختصة باستئناف العمل الوارد أدناه:
            </div>
            <table style="width: 100%%; border-collapse: collapse; margin: 5px;line-height: 0.9;">
                <tr>
                <td style="width: 70%%; padding: 2px; text-align: left; font-size: 14px;">%(emp_name)s</td>
                <td dir="rtl" style="width: 30%%; padding: 2px; text-align: left; font-size: 14px;">اللقب و الاسم:</td>
                    
                </tr>
                <tr>
                <td style="width: 70%%; padding: 2px; text-align: left; font-size: 14px;">%(subject_line)s</td>
                <td dir="rtl" style="width: 30%%; padding: 2px; text-align: left; font-size: 14px;">التخصص:</td>
                    
                </tr>
                <tr>
                <td style="width: 70%%; padding: 2px; text-align: left; font-size: 14px;">%(school)s</td>
                <td dir="rtl" style="width: 30%%; padding: 2px; text-align: left; font-size: 14px;">مؤسسة العمل:</td>
                    
                </tr>
                <tr>
                <td style="width: 70%%; padding: 2px; text-align: left; font-size: 14px;">%(emp_grade)s</td>
                <td dir="rtl" style="width: 30%%; padding: 2px; text-align: left; font-size: 14px;">الصفة:</td>
                    
                </tr>
                <tr>
                <td style="width: 70%%; padding: 2px; text-align: left; font-size: 14px;">%(resume_date)s</td>
                <td dir="rtl" style="width: 30%%; padding: 2px; text-align: left; font-size: 14px;">تاريخ الاستئناف:</td>
                    
                </tr>
                <tr>
                <td style="width: 70%%; padding: 2px; text-align: left; font-size: 14px;">جزائرية</td>   
                <td dir="rtl" style="width: 30%%; padding: 2px; text-align: left; font-size: 14px;">الجنسية:</td>
                </tr>
                  <tr>
                <td style="width: 70%%; padding: 2px; text-align: left; font-size: 14px;"></td>   
                <td dir="rtl" style="width: 30%%; padding: 2px; text-align: left; font-size: 14px;">الملاحظة:</td>
                </tr>
            </table>
            
            <table width="100%%" dir="rtl" style="margin-top: 2px;line-height: 0.9;">
               <tr>
                <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;line-height: 0.9;">
                        %(school_address)s في : %(today)s
                </td>
                <td style="text-align:center; width:30%%;"></td>
                  <td style="text-align:center; width:30%%;">إمضاء المعني(ة) بالأمر</td>
           
            </tr>
            <tr>
                <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;line-height: 0.9;">
                        المدير
                </td>
                <td style="text-align:center; width:30%%;"></td>
                <td style="text-align:center; width:30%%;">%(emp_name)s</td>
            </tr>
            </table>
             
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "school_year": school_year,
            "school_address": school_address,
            "emp_name": emp_name, "emp_grade": emp["grade"] or "",
            "subject_line": emp["subject"] or "",
            "start_date": sl["start_date"], "end_date": sl["end_date"],
            "resume_date": resume_str,
            "today": today, "director": director,
        }
        self._show_print_preview(html)

    def _print_end_substitution(self, teacher, subst):
        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
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
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 20px; line-height: 0.9; }
            .header-text { font-size: 16px; font-weight: bold; text-align: center; margin: 2px 0; }
            .header-right { font-size: 14px; font-weight: bold; text-align: right; margin-top: 10px; margin-bottom: 30px; line-height: 0.9; }
            .recipient-block { font-size: 16px; font-weight: bold; text-align: right; margin-right: 20px; margin-bottom: 40px; line-height: 0.9; }
            .subject-title { font-size: 20px; font-weight: bold; margin: 30px 40px; text-align: left; }
            .content-p { font-size: 18px; font-weight: bold; margin: 10px 20px; line-height: 0.9; text-align: left; text-indent: 40px; }
            h2 { text-align: center; color: #1a1a1a; margin: 24px 0; font-weight: bold; font-size: 24px; text-decoration: underline; }
            .info-table { border-collapse: collapse; width: 100%%; margin: 5px; }
            .info-table th, .info-table td { border: 1px solid black !important; padding: 2px; font-size: 14px; font-weight: bold; text-align: right; line-height: 0.9; }
            .info-table td.label { width: 40%%; }
        </style></head>
        <body dir="rtl">
            <div class="header-text">الجمهورية الجزائرية الديمقراطية الشعبية</div>
            <div class="header-text">وزارة التربية الوطنية</div>
            <div style="text-align: left;">
                مديرية التربية لولاية %(wilaya)s<br/>
                %(school_display)s
            </div>
            
            <div class="recipient-block">
            <table>
                <tr>
                    <td width="40%%" style="text-align:center;">إلى السيد : مدير التربية</td>
                    <td width="60%%"></td>
                </tr>
                <tr>
                    <td width="40%%" style="text-align:center;">مصلحة المستخدمين</td>
                    <td width="60%%"></td>
                </tr>
                <tr>
                    <td width="40%%" style="text-align:center;">مكتب التعليم المتوسط</td>
                    <td width="60%%"></td>
                </tr>
            </table>
            </div>

            <div class="subject-title">الموضوع: نهاية الإستخلاف</div>

            <p class="content-p">
                نعلم سيادتكم أن الأستـــاذ(ة) : %(sub_name)s مستخلفــ(ة) علــى منصــب عطلــة مرضيــة (مادة %(teacher_subject)s) أنهــــت إستخلافهـــا بتاريــــخ %(end_date)s.
            </p>

               <tr>
                <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في %(today)s
                </td>
                <td style="text-align:center; width:60%%;"></td>
            </tr>
            <tr>
                <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%; padding-top: 10px;">
                        المدير
                </td>
                <td style="text-align:center; width:60%%;"></td>
            </tr>
            </table>

            <!-- Page Break for Information Card -->
            <div style="page-break-before: always;"></div>
            <table width="100%%" dir="rtl" style="margin-top: 15px; margin-bottom: 5px;">
                <tr>
                    <td style="text-align:center; font-size: 14px; font-weight: bold; line-height: 0.9;">
                       الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:center; font-size: 14px; font-weight: bold; line-height: 0.9;">
                     وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:left; font-size: 14px; font-weight: bold; line-height: 0.9;">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td style="text-align:left; font-size: 14px; font-weight: bold; line-height: 0.9;">
                       
                        %(school_display)s
                    </td>
                </tr>
                <tr>
                <td style="text-align:center; font-size: 14px; font-weight: bold; line-height: 0.9;">
                  <h2>بطاقة معلومات الخاصة بالأساتذة المتعاقدين</h2>
                </td>
                </tr>
                <tr>
                 <td style="text-align:center; font-size: 14px; font-weight: bold; line-height: 0.9;">
                 السنة الدراسية %(school_year)s
                 </td>
                </tr>
            </table>
         
            <table class="info-table" border="1" cellspacing="0" cellpadding="1" style="font-size: 12px; line-height: 0.8;border-collapse: collapse; width: 100%%; margin: 5px;">
                <tr>
                    <td style="text-align: left; width: 50%%; border: 1px solid black; padding: 1px; line-height: 0.8;" dir="ltr">
                        <span style="font-family: Arial;">NOM du CCP: <b>%(sub_last_name_fr)s</b><br/>
                        Prénom du CCP: <b>%(sub_first_name_fr)s</b><br/>
                        N CCP:</span> %(sub_postal)s
                    </td>
                    <td style="text-align: left; width: 50%%; border: 1px solid black; padding: 1px; line-height: 0.8; font-weight: bold;" dir="rtl">
                        اللقب: %(sub_last_name)s<br/>الإسم: %(sub_first_name)s<br/>رقم الحساب البريدي: %(sub_postal)s<br/>رقم الضمان الاجتماعي: %(sub_ss)s
                    </td>
                </tr>
                <tr>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">عنوان المتعاقد(ة): <b>%(sub_address)s</b></td>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">تاريخ ومكان الازدياد: %(sub_birth_date)s %(sub_birth_place)s</td>
                </tr>
                <tr>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">التخصص: %(sub_degree_spec)s</td>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">الوظيفــة: أستاذ(ة) مستخلف(ة)</td>
                </tr>
                <tr>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">تاريخ نهاية التعاقد: %(end_date)s</td>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">تاريخ التنصيب: %(start_date)s</td>
                </tr>
                 <tr>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">تحديد الفترة من : ........... إلى ...........</td>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">عدد الغيابات الإجمالية للفترة:...........</td>
                </tr>
                 <tr>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">تحديد الفترة من : %(start_date)s إلى %(end_date)s</td>
                    <td style="text-align: left; border: 1px solid black; padding: 1px; font-weight: bold; line-height: 0.8;" dir="rtl">معدل منحة تحسين الآداء التربوية:...../40</td>
                </tr>
            </table>

            <table width="100%%" dir="rtl" style="line-height: 0.9;margin-top: 5px;">
                <tr>
                    <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في %(today)s
                    </td>
                    <td style="text-align:center; width:60%%;"></td>
                </tr>
                <tr>
                    <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%; padding-top: 10px;">
                        المدير
                    </td>
                    <td style="text-align:center; width:60%%;"></td>
                </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display, "school_year": school_year,
            "school_address": school_address, "teacher_name": teacher_name,
            "teacher_subject": teacher["subject"] or "................",
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
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_address = settings.get("school_address", "......................")
        current_year = datetime.now().strftime("%Y")
        today_str = datetime.now().strftime("%Y/%m/%d")
        start_date = dict(subst).get("start_date", "").replace("-", "/")

        school_display = school
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

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px 40px; line-height: 0.9; }
            .header-text { font-size: 16px; font-weight: bold; text-align: center; }
            .header-info { width: 100%%; font-size: 16px; font-weight: bold; margin-top: 5px; }
            .title-box { border: 2px solid black; padding: 10px; width: fit-content; margin: 10px auto; text-align: center; font-size: 26px; font-weight: bold; }
            .content-p { font-size: 14px; font-weight: bold; margin-top: 10px; line-height: 0.9;text-align: left; }
            .info-line { font-size: 18px; font-weight: bold; margin-top: 15px; line-height: 0.9; }
            .signatures { width: 100%%; margin-top: 60px; font-size: 18px; font-weight: bold; text-align: center; line-height: 0.9; }
        </style></head>
        <body dir="rtl">
              <div class="header-text">الجمهورية الجزائرية الديمقراطية الشعبية</div>
            <div class="header-text">وزارة التربية الوطنية</div>
            <div style="text-align: left;">
                مديرية التربية لولاية %(wilaya)s<br/>
                %(school_display)s
            </div>
            
         

            <div class="title-box">محـــــــــضر تنصيـــــــــب</div>

            <div class="content-p">
                بناء على قرار التوظيف في إطار التعاقد على منصب مالي شاغر مؤقت عطلة مرضية<br/>
                رقم: ........ /م.ت/م.ت.م/ %(current_year)s بتاريخ: %(today_str)s.<br/>
                قمنا نحن السيد : مدير %(school)s   يوم: %(start_date)s بتنصيب السيد(ة):
            </div>

           
            
            <table style="width: 100%%; font-size: 14px; font-weight: bold; margin: 5px auto;line-height: 0.9;" dir="rtl">
                <tr>
                    <td style="width: 100%%;">اللقب : %(sub_last_name)s</td>
                </tr>
                <tr>
                    <td style="width: 100%%;">الاسم : %(sub_first_name)s</td>
                </tr>   
                <tr>
                    <td style="width: 100%%;">تاريخ الميلاد : %(sub_birth_date)s بـ %(sub_birth_place)s</td>
                </tr>
                <tr>
                    <td style="width: 100%%;">الوظيفة : أستاذ(ة) مادة %(teacher_subject)s</td>
                </tr>
                <tr>
                    <td style="width: 100%%;">الصفة : مستخلف(ة) عطلة مرضية</td>
                </tr>
            </table>

          
            
       
         <table width="100%%" dir="rtl" style="line-height: 0.9;margin-top: 5px;">
                <tr>
                    <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%;">
                        %(school_address)s في %(today)s
                    </td>
                    <td style="text-align:center; width:60%%;"></td>
                </tr>
                <tr>
                    <td style="font-size:16px; font-weight: bold; text-align:center; width:40%%; padding-top: 10px;">
                        المدير
                    </td>
                    <td style="text-align:center; width:60%%;">امضاء المعني</td>
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
            "today": today_str
        }
        self._show_print_preview(html)

    def _print_appointment_decision(self, subst):
        """Print مقرر التعيين (مقرر تعاقد) for a substitute."""
        teacher = db.get_employee(subst["teacher_id"])
        sick_leave = db.get_sick_leave(subst["sick_leave_id"])
        settings = db.get_all_settings()
        school = settings.get("school_name", "المؤسسة التعليمية")
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
        if "ليسانس" in degree_type:
            class_grade, index_points = "12", "737"
            prof_title = "أستاذ التعليم المتوسط"
        elif "ماستر" in degree_type or "مهندس" in degree_type:
            class_grade, index_points = "13", "778"
            prof_title = "أستاذ التعليم الثانوي"
        else:
            class_grade, index_points = "____", "____"
            prof_title = "أستاذ"

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Traditional Arabic', 'Amiri', serif;
                   direction: rtl; text-align: right; margin: 0px; padding: 0px; font-size: 13px; font-weight: bold; }
            .header-text { font-size: 16px; font-weight: bold; text-align: center; }
            .entete { font-size: 13px; font-weight: bold; text-align: right; margin-bottom: 2px; }
            .considerations { font-size: 12px; text-align: right; }
            .article { text-align: right; font-size: 14px; margin-top: 5px; }
            .article-title { font-weight: bold; text-decoration: underline; }
            .footer-table td { font-weight: bold; padding: 0; margin: 0; font-size: 14px; }
        </style></head>
        <body dir="rtl" align="right">
            <div class="header-text" dir="rtl" align="center">
                الجمهورية الجزائرية الديمقراطية الشعبية<br/>
                وزارة التربية الوطنية
            </div>
            
            <div class="entete" dir="rtl" align="right">
            مديرية التربية لولاية: %(wilaya)s<br/>
            مـصـلــــــحــــــــة الـمـستخدمين<br/>
            مكتـــب التعليـــــم الثـــــــانـــوي والمتوسط<br/>
            /رقـم :......./م.ت /م.ت.م
            %(current_year)s
            </div>

            <div style="line-height: 0.9;text-align: center;">
                <h2 style="line-height: 0.9;text-align: center;margin:0px">مقرر توظـيف في اطار التعاقد</h2>
                <h3 style="line-height: 0.9;text-align: center;margin:0px">عطلة مرضية / عطلة أمومة</h3>
            </div>

            <table width="100%%" cellspacing="0" cellpadding="0" dir="rtl" style="font-size: 12px;line-height: 0.9;">
                <tr><td colspan="2" align="right"><b>إن السيد(ة) مديـــر التربيـــة لولايـــة %(wilaya)s .</b></td></tr>
                <tr>
                    <td align="right">بمقتضى الأمر رقم : 06-03 المؤرخ في : 19 جمادى الثانية عام 1427 الموافق 15 يوليو سنة 2006 المتضمن القانون الأساسي العام للوظيفة العمومية المتمم.</td>
                    <td width="15" align="center" valign="top">-</td>
                </tr>
                <tr>
                    <td align="right">بمقتضى المرسوم الرئاسي رقم :07-304 المؤرخ في 17 رمضان 1428 الموافق ل 29/سبتمبر 2007 الذي يحدد الشبكة الإستدلالية لمرتبات الموظفين ونظام دفع رواتبهم المعدل والمتمم.</td>
                    <td width="15" align="center" valign="top">-</td>
                </tr>
                <tr>
                    <td align="right">بمقتضى المرسوم التنفيذي رقم 90/99 المؤرخ في :اول رمضان عام 1410 الموافق ل27مارس سنة1990 المتعلق بسلطة التعيين و التسيير الإداري بالنسبة للموظفين و أعوان الإدارة الـمركزية و الـولايات و البلديـات و المؤسسـات الـعمومية ذات الطـابع الإداري .</td>
                    <td width="15" align="center" valign="top">-</td>
                </tr>
                <tr>
                    <td align="right">بمقتضى المرسوم التنفيذي رقم :90/174 المؤرخ في 09جوان 1990 المعدل بالمرسوم رقم:02-71 المؤرخ في:19 فيفري 2002 الذي يحدد كيفية تنظيم مديرية التربية على مستوى الولاية وسيرها.</td>
                    <td width="15" align="center" valign="top">-</td>
                </tr>
                <tr>
                    <td align="right">بمقتضى المرسوم التنفيدي رقم :25/54 المؤرخ في:23جمادى التانية عام1444 الموافق ل21جانفي2025 المتضمن القانون الاساسي الخاص بالموظفين المنتمين للاسلاك الخاصة بالتربية الوطنية.</td>
                    <td width="15" align="center" valign="top">-</td>
                </tr>
                <tr>
                    <td align="right">بناء على التعليمة الوزارية رقم : 05 المؤرخ في 2025/07/24 التي تحدد كيفيات توظيف أساتذة بصفة متعاقدين في مؤسسات التعليم التابعة لوزارة التربية الوطنية ودفع رواتبهم.</td>
                    <td width="15" align="center" valign="top">-</td>
                </tr>
                <tr>
                    <td align="right" style="font-size: 13px;">بناء على الشهادة الطبية المؤرخة في <b>%(cert_date)s</b> المقدمة من طرف الأستاذ(ة): <b>%(teacher_name)s</b> .</td>
                    <td width="15" align="center" valign="top" style="font-size: 13px;">-</td>
                </tr>
                <tr>
                    <td align="right" style="font-size: 13px;">بناء على طلب التوظيف المقدم من طرف السيد(ة): <b>%(sub_name)s</b> المؤرخ في : <b>%(sub_start_date)s</b> .</td>
                    <td width="15" align="center" valign="top" style="font-size: 13px;">-</td>
                </tr>
                <tr>
                    <td colspan="2" align="right" style="font-size: 13px;">الحاصل(ة) على شهادة: <b>%(sub_degree_type)s تخصص %(sub_degree_spec)s</b> الصادرة عن : <b>%(sub_degree_source)s</b> .</td>
                   
                </tr>
                <tr>
                    <td align="right" style="font-size: 13px;">باقتراح من السيـــد(ة) مديـر(ة): <b>%(school)s</b> .</td>
                    <td width="15" align="center" valign="top" style="font-size: 13px;">-</td>
                </tr>
            </table>

            <div align="center" style="font-size: 20px; font-weight: bold; margin-top: 2px; margin-bottom: 2px;">يــــــــقــــــــــــرر</div>

            <table width="100%%" cellspacing="0" cellpadding="0" dir="rtl" style="font-size: 14px;">
                <tr>
                    <td align="right">
                        <span style="font-weight: bold; text-decoration: underline;">المـادة الأولــى :</span> يوظف السيــد (ة) : <b>%(sub_name)s</b>، 
                    </td>
                </tr>
                <tr><td align="right"> في إطار التعاقد على منصب شاغر مؤقت (عطلة مرضية) من: <b>%(start_date)s</b> إلى: <b>%(end_date)s</b>،</td></tr>
                <tr><td align="right"> في رتبة : <b>%(prof_title)s</b>، المادة : <b>%(subject)s</b>،</td></tr>
                <tr><td align="right"> خلفــا للأستاذ(ة) : <b>%(teacher_name)s</b> بالمؤسسة : <b>%(school)s</b>.</td></tr>
            </table>

            <table width="100%%" cellspacing="0" cellpadding="0" dir="rtl" style="font-size: 14px; margin-top: 3px;">
                <tr>
                    <td align="right">
                        <span style="font-weight: bold; text-decoration: underline;">المادة الثانية :</span> يتقاضى المعني(ة) بالأمر مرتبه(ها) على أساس الصنف <b>%(class_grade)s</b> الرقم الاستدلالي <b>%(index_points)s</b>.
                    </td>
                </tr>
            </table>

             <table width="100%%" cellspacing="0" cellpadding="0" dir="rtl" style="font-size: 14px; margin-top: 3px;">
                <tr>
                    <td align="right">
                        <span style="font-weight: bold; text-decoration: underline;">المـادة الثالثة :</span> يكلف السادة رئيس مصلحة المستخدمين و رئيس مصلحة تسيير نفقات المستخدمين و مدير(ة) المؤسسة بتنفيذ هذا القرار كل في مجال اختصاصه .
                    </td>
                </tr>
            </table>

            <table width="100%%" class="footer-table" dir="rtl" align="right" style="margin-top: 15px;">
                <tr>
                    <td align="center" style="text-align:center; width:50%%;" dir="rtl">
                        %(wilaya)s في <b>%(start_date)s</b>
                    </td>
                    <td style="text-align:right; width:50%%;"></td>
                </tr>
                <tr>
                    <td align="center" style="text-align:center; width:50%%;" dir="rtl">
                        مدير التربية
                    </td>
                    <td style="text-align:right; width:50%%;"></td>
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
        school = settings.get("school_name", "المؤسسة التعليمية")
        school_code = settings.get("school_code", "")
        wilaya = settings.get("wilaya", "")
        year = datetime.now().year
        school_initials = self._get_school_initials(school)
        director = settings.get("director_name", "")
        
        school_display = school
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
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px; line-height: 0.9; }
            .header-text { font-size: 16px; font-weight: bold; text-align: center; margin: 2px 0; }
            .header-right { font-size: 14px; font-weight: bold; text-align: right; margin-top: 10px; margin-bottom: 20px; line-height: 0.9; }
        </style></head>
        <body dir="rtl">
             <table width="100%%" dir="rtl" style="font-size:18px; font-weight:bold; margin-top: 0px; margin-bottom: 5px;line-height: 0.8;">
                <tr >
                    <td align="center" width="100%%" style="padding:0px; font-size: 18px; font-weight: bold; line-height: 0.8;">
                    الجمهورية الجزائرية الديمقراطية الشعبية
                    </td>
                </tr>
                 <tr >
                    <td align="center" width="100%%" style="padding:0px; font-size: 16px; font-weight: bold; line-height: 0.8;">
                    وزارة التربية الوطنية
                    </td>
                </tr>
                 <tr>
                    <td align="right" width="100%%" style="padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                        مديرية التربية لولاية %(wilaya)s
                      
                    </td>
                </tr>
                 <tr>
                    <td align="right" width="100%%" style="padding:0px; font-size: 14px; font-weight: bold; line-height: 0.8;">
                       
                        %(school_display)s
                    </td>
                </tr>
                  <tr style="line-height: 0.8;">
                    
                  
               
                    <td dir="rtl" style="line-height: 0.8;font-size: 14px;direction:rtl;text-align: left;">
                     <span style="unicode-bidi: bidi-override; direction: rtl;">الرقم:.............&rlm;/&rlm; %(school_initials)s&rlm;/&rlm; %(year)s</span>
                    </td>
                    </tr>
                <tr>
                <td style="font-size: 24px;font-weight: bold;" align="center" width="100%%">
                   
                    شهادة عمــــل
                  
                </td>
                </tr>
           
            </table>
          
            <table dir="rtl" width="100%%" border="0" style="font-size:14px; font-weight:bold; line-height:0.9; margin-top: 10px;">
                <tr>
                <td colspan="3" style="font-size:16px;">يشهد السيد مدير %(school)s أن السيد(ة) المذكور(ة) أسفله:</td>
                </tr>
                <tr>
                <td width="75%%" style="border: none;">%(first_name)s</td>
                <td width="20%%" style="border: none;">الإسم:</td>
                <td width="5%%" style="border: none;"> </td>
                </tr>
               <tr>
                <td width="75%%" style="border: none;">%(last_name)s</td>
                <td width="20%%" style="border: none;">اللقب:</td>
                <td width="5%%" style="border: none;"> </td>
                </tr>

                <tr>
                <td width="75%%" style="border: none;">%(birth_date)s %(birth_place)s</td>
                <td width="20%%" style="border: none;">تاريخ ومكان الميلاد:</td>
                <td width="5%%" style="border: none;"> </td>
                </tr>
                <tr>
                <td width="75%%" style="border: none;">%(grade)s مادة: %(subject)s</td>
                <td width="20%%" style="border: none;">الوظيفة:</td>
                <td width="5%%" style="border: none;"> </td>
                </tr>
                <tr>
               
                <td colspan="3" style="font-size:16px;border: none;">      %(work_status_text)s </td>
                </tr>
                 <tr>
               
                <td align="center" style="font-size:16px; line-height:1.0; font-weight:bold; margin-top: 5px;" colspan="3">  سُلمت هذه الشهادة للعمل بها في حدود ما يقتضيه القانون. </td>
                </tr>
            </table>
           
            
             <table width="100%%" class="footer-table" dir="rtl" align="right" style="margin-top: 5px;font-size: 16px;">
                <tr>
                    <td align="center" style="text-align:center; width:50%%;" dir="rtl">
                        حرر بـ %(wilaya)s في: %(date)s
                    </td>
                    <td style="text-align:right; width:50%%;"></td>
                </tr>
                <tr>
                    <td align="center" style="text-align:center; width:50%%;" dir="rtl">
                     مدير المؤسسة
                    </td>
                    <td style="text-align:right; width:50%%;"></td>
                </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_display": school_display,
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

# -*- coding: utf-8 -*-
"""
Employee Management Page — Tab-based employee dialog + batch evaluation printing.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QMessageBox, QHeaderView, QAbstractItemView, QSizePolicy,
    QFormLayout, QTextEdit, QSpacerItem, QLabel, QMenu, QPushButton,
    QFrame, QTabWidget, QDoubleSpinBox, QGridLayout, QScrollArea,
    QGroupBox, QDateEdit, QProgressDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QFont, QCursor, QColor

from ui.widgets import (
    ArabicLineEdit, ArabicLabel, ArabicComboBox, ArabicDateEdit,
    Card, SearchBar, ActionButton, ArabicFormLayout, Separator,
    PageHeader,
)
from ui.documents_modal import PrintDocumentDialog
from ui.inquiry_dialog import InquiryDialog
from ui.icons import get_icon
from ui.evaluation_dialog import (
    compute_score_limits, get_remark, score_to_arabic_words,
    get_previous_years, is_eligible_for_evaluation, get_eligible_employees,
    EvaluationPrinter,
)
import database as db

GRADES = [
    "أستاذ التعليم المتوسط", "أستاذ التعليم الابتدائي", "أستاذ التعليم الثانوي",
    "أستاذ رئيسي", "أستاذ مكوّن", "مساعد تربوي", "مستشار التربية",
    "مستشار التوجيه", "مقتصد", "نائب مقتصد", "مدير", "نائب مدير",
    "عامل مهني", "عون وقاية", "عون خدمة", "سائق", "طباخ", "مخزني", "حاجب",
    "حارس", "كاتب", "محاسب", "إداري",
]

# الرتب المعفاة من الدرجات (ليس لهم درجة ولا تاريخ سريان)
WORKER_GRADES = ["عامل مهني", "عون وقاية", "عون خدمة", "سائق", "طباخ", "مخزني", "حاجب"]

FAMILY_STATUS = ["أعزب(ة)", "متزوج(ة)", "مطلق(ة)", "أرمل(ة)"]


class _NullableDateEdit(QDateEdit):
    """
    QDateEdit with calendar popup that supports an empty '/' state.
    - When value = minimum date (2000/01/01), displays '/' (empty).
    - Calendar always opens at current month even when empty.
    - .text() returns '' when empty, 'yyyy/MM/dd' otherwise.
    - .setText() parses date strings or clears if empty.
    """

    _NULL = QDate(1900, 1, 1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy/MM/dd")
        self.setMinimumDate(self._NULL)
        self.setSpecialValueText("/")
        self.setDate(self._NULL)   # starts empty
        self.setFixedHeight(28)
        self.setStyleSheet("""
            QDateEdit {
                font-size: 12px; font-weight: bold;
                border: 1px solid #94a3b8; border-radius: 6px;
                padding: 2px 4px; background: #fff;
            }
            QDateEdit:focus { border-color: #3b82f6; background: #eff6ff; }
        """)

    def showPopup(self):
        """Navigate calendar to current month when date is empty."""
        if self.date() <= self._NULL:
            cal = self.calendarWidget()
            if cal:
                today = QDate.currentDate()
                if today > cal.maximumDate():
                    today = cal.maximumDate()
                elif today < cal.minimumDate():
                    today = cal.minimumDate()
                cal.setCurrentPage(today.year(), today.month())
        super().showPopup()

    def keyPressEvent(self, event):
        """Delete / Backspace clears the date back to '/'."""
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.clear_date()
        else:
            super().keyPressEvent(event)

    def is_null(self):
        return self.date() <= self._NULL

    def clear_date(self):
        self.setDate(self._NULL)

    def text(self) -> str:
        if self.is_null():
            return ""
        return self.date().toString("yyyy/MM/dd")

    def setText(self, value: str):
        if not value or value.strip() in ("", "/"):
            self.clear_date()
            return
        clean = value.strip().replace("-", "/")
        d = QDate.fromString(clean, "yyyy/MM/dd")
        if not d.isValid():
            d = QDate.fromString(value.strip(), "yyyy-MM-dd")
        if d.isValid():
            self.setDate(d)
        else:
            self.clear_date()


class EmployeeDialog(QDialog):
    """Dialog for adding / editing an employee — organised in tabs."""

    def __init__(self, parent=None, employee=None, initial_tab=0):
        super().__init__(parent)
        self.employee = employee
        self.setWindowTitle("تعديل موظف" if employee else "إضافة موظف جديد")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(680)
        self.setMinimumHeight(580)
        self._eval_widgets = []   # (year_str, edu_spin, edu_date, adm_spin, adm_date, remark_lbl)
        self._build_ui()

        if employee:
            self._populate(employee)
            self._load_evaluations()

        self.tabs.setCurrentIndex(initial_tab)

    # ══════════════════════════════════════════════════════════════════════
    #  BUILD UI
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        header_txt = "تعديل بيانات الموظف ✏️" if self.employee else "إضافة موظف جديد ➕"
        header = QLabel(header_txt)
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 4px;")
        main_layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.RightToLeft)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                background: #ffffff;
                padding: 4px;
            }
            QTabBar::tab {
                background: #f1f5f9;
                border: 1px solid #cbd5e1;
                border-bottom: none;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
                margin-left: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                color: #1d4ed8;
                border-bottom: 2px solid #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background: #e2e8f0;
            }
        """)

        self.tabs.addTab(self._build_personal_tab(), "👤 المعلومات الشخصية")
        self.tabs.addTab(self._build_career_tab(), "💼 المسار المهني")
        self.tabs.addTab(self._build_evaluation_tab(), "📊 التقييم")

        main_layout.addWidget(self.tabs, 1)

        # ─ Buttons ─
        btn_layout = QHBoxLayout()
        save_btn = ActionButton("حفظ", "\U0001F4BE", "success")
        save_btn.clicked.connect(self._save)
        cancel_btn = ActionButton("إلغاء", "\u274C", "outline")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    # ─── Tab 1: المعلومات الشخصية ─────────────────────────────────────────

    def _build_personal_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_w = QWidget()
        layout = QVBoxLayout(scroll_w)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        form = ArabicFormLayout()

        self.last_name_input = ArabicLineEdit("اللقب بالعربية")
        form.addRow("اللقب *:", self.last_name_input)

        self.first_name_input = ArabicLineEdit("الاسم بالعربية")
        form.addRow("الاسم *:", self.first_name_input)

        self.maiden_name_input = ArabicLineEdit("اللقب الأصلي للمتزوجات")
        form.addRow("اللقب الأصلي:", self.maiden_name_input)

        self.birth_date = _NullableDateEdit()
        self.birth_date.setToolTip("اضغط Delete لمسح التاريخ")
        form.addRow("تاريخ الميلاد:", self.birth_date)

        self.birth_place_input = ArabicLineEdit("مكان الميلاد")
        form.addRow("مكان الميلاد:", self.birth_place_input)

        self.family_status_combo = ArabicComboBox()
        self.family_status_combo.addItem("")   # فارغ
        self.family_status_combo.addItems(FAMILY_STATUS)
        self.family_status_combo.setEditable(True)
        form.addRow("الحالة العائلية:", self.family_status_combo)

        self.national_id_input = ArabicLineEdit("رقم البطاقة الوطنية")
        form.addRow("رقم التعريف:", self.national_id_input)
        
        self.social_security_input = ArabicLineEdit("رقم الضمان الاجتماعي")
        form.addRow("رقم الضمان الاجتماعي:", self.social_security_input)

        self.phone_input = ArabicLineEdit("رقم الهاتف")
        form.addRow("الهاتف:", self.phone_input)

        self.address_input = ArabicLineEdit("العنوان الكامل")
        form.addRow("العنوان:", self.address_input)

        layout.addLayout(form)
        layout.addStretch()
        scroll.setWidget(scroll_w)

        wrapper = QVBoxLayout(tab)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)
        return tab

    # ─── Tab 2: المسار المهني ──────────────────────────────────────────────

    def _build_career_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_w = QWidget()
        layout = QVBoxLayout(scroll_w)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        form = ArabicFormLayout()

        self.code_input = ArabicLineEdit("الرمز الوظيفي")
        form.addRow("الرمز الوظيفي:", self.code_input)

        self.grade_combo = ArabicComboBox()
        self.grade_combo.setEditable(True)
        all_grades = list(GRADES)
        try:
            custom_grades = db.get_all_grades()
            for cg in custom_grades:
                if cg not in all_grades:
                    all_grades.append(cg)
        except Exception:
            pass
        self.grade_combo.addItems(all_grades)
        self.grade_combo.currentTextChanged.connect(self._on_grade_changed)
        form.addRow("الرتبة:", self.grade_combo)

        self.subject_input = ArabicLineEdit("المادة (للأساتذة فقط)")
        self.subject_label = QLabel("مادة التخصص:")
        form.addRow(self.subject_label, self.subject_input)

        self.category_input = ArabicLineEdit("الصنف (مثال: 11)")
        form.addRow("الصنف:", self.category_input)

        self.degree_input = ArabicLineEdit("الدرجة (رقم)")
        self.degree_input.textChanged.connect(self._on_degree_changed)
        self.degree_label = QLabel("الدرجة:")
        form.addRow(self.degree_label, self.degree_input)

        self.effective_date = _NullableDateEdit()
        self.effective_date.setToolTip("اضغط Delete لمسح التاريخ")
        self.effective_date_label = QLabel("تاريخ سريان الدرجة:")
        form.addRow(self.effective_date_label, self.effective_date)

        sep = Separator()
        form.addRow(sep)

        self.diploma_input = ArabicLineEdit("الشهادة المحصل عليها")
        form.addRow("الشهادة:", self.diploma_input)

        self.diploma_date_input = ArabicLineEdit("تاريخ الحصول عليها (مثال: 2015)")
        form.addRow("تاريخ الشهادة:", self.diploma_date_input)

        sep2 = Separator()
        form.addRow(sep2)

        self.account_number_input = ArabicLineEdit("رقم الحساب الجاري البريدي")
        form.addRow("رقم الحساب:", self.account_number_input)

        self.account_key_input = ArabicLineEdit("المفتاح")
        form.addRow("المفتاح:", self.account_key_input)

        layout.addLayout(form)
        layout.addStretch()

        # Show/hide subject based on grade
        self._on_grade_changed(self.grade_combo.currentText())

        scroll.setWidget(scroll_w)
        wrapper = QVBoxLayout(tab)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)
        return tab

    # ─── Tab 3: التقييم ────────────────────────────────────────────────────

    def _build_evaluation_tab(self):
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_w = QWidget()
        layout = QVBoxLayout(scroll_w)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        # ─ رسالة الإعفاء ─
        self.exempt_label = QLabel(
            "⚠️ هذا الموظف معفى من التقييم (عامل مهني أو درجة 0)."
        )
        self.exempt_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #b45309; "
            "background: #fffbeb; border: 1px solid #fde68a; "
            "border-radius: 8px; padding: 12px;"
        )
        self.exempt_label.setWordWrap(True)
        self.exempt_label.setVisible(False)
        layout.addWidget(self.exempt_label)

        # ─ حاوية الإدخال ─
        self.eval_container = QWidget()
        eval_layout = QVBoxLayout(self.eval_container)
        eval_layout.setSpacing(12)
        eval_layout.setContentsMargins(0, 0, 0, 0)

        # معلومات المجال
        self.range_label = QLabel()
        self.range_label.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #1d4ed8; "
            "background: #eff6ff; border: 1px solid #bfdbfe; "
            "border-radius: 8px; padding: 10px;"
        )
        self.range_label.setWordWrap(True)
        eval_layout.addWidget(self.range_label)

        # ─ جدول السنوات الثلاث السابقة + السنة الحالية ─
        grid_title = QLabel("النقاط المتحصل عليها خلال السنوات الثلاث السابقة + السنة الحالية:")
        grid_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #334155;")
        eval_layout.addWidget(grid_title)

        # Get years
        settings = db.get_all_settings()
        current_year = settings.get("school_year", "2025/2026")
        prev_years = get_previous_years(current_year, 3)
        all_years = prev_years + [current_year]  # 3 سنوات سابقة + السنة الحالية

        # Build a grid for 4 years (3 previous + current)
        grid_frame = QFrame()
        grid_frame.setStyleSheet("""
            QFrame { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px; }
        """)
        grid = QGridLayout(grid_frame)
        grid.setSpacing(8)

        # Headers
        headers = ["السنة الدراسية", "النقطة التربوية", "تاريخها", "النقطة الإدارية", "تاريخها", "الملاحظة"]
        for c, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "font-size: 12px; font-weight: bold; color: #475569; "
                "background: #e2e8f0; padding: 4px; border-radius: 4px;"
            )
            grid.addWidget(lbl, 0, c)

        self._eval_widgets = []
        for r, yr in enumerate(all_years):
            row = r + 1
            is_current = (yr == current_year)

            # السنة
            yr_lbl = QLabel(yr)
            yr_lbl.setAlignment(Qt.AlignCenter)
            if is_current:
                yr_lbl.setStyleSheet(
                    "font-weight: bold; font-size: 13px; color: #fff; "
                    "background: #3b82f6; border-radius: 4px; padding: 2px 6px;"
                )
            else:
                yr_lbl.setStyleSheet("font-weight: bold; font-size: 13px; color: #1e293b;")
            grid.addWidget(yr_lbl, row, 0)

            # النقطة التربوية — min=-0.5 (empty), max=20, step=0.5
            edu_spin = QDoubleSpinBox()
            edu_spin.setDecimals(1)
            edu_spin.setSingleStep(0.5)
            edu_spin.setMinimum(-0.5)
            edu_spin.setMaximum(20.0)
            edu_spin.setValue(-0.5)  # empty by default
            edu_spin.setSpecialValueText("/")
            edu_spin.setFixedWidth(90)
            edu_spin.setStyleSheet(self._spin_style())
            grid.addWidget(edu_spin, row, 1)

            # تاريخ النقطة التربوية
            edu_date = _NullableDateEdit()
            edu_date.setToolTip("اضغط Delete لمسح التاريخ")
            grid.addWidget(edu_date, row, 2)

            # النقطة الإدارية
            adm_spin = QDoubleSpinBox()
            adm_spin.setDecimals(1)
            adm_spin.setSingleStep(0.5)
            # المجال يُضبط ديناميكياً حسب الدرجة
            adm_spin.setMinimum(-0.5)
            adm_spin.setMaximum(20.0)
            adm_spin.setValue(-0.5)
            adm_spin.setSpecialValueText("/")
            adm_spin.setFixedWidth(90)
            adm_spin.setStyleSheet(self._spin_style())
            grid.addWidget(adm_spin, row, 3)

            # تاريخ النقطة الإدارية
            adm_date = _NullableDateEdit()
            adm_date.setToolTip("اضغط Delete لمسح التاريخ")
            
            # تقييد تاريخ النقطة الإدارية ضمن السنة الدراسية
            try:
                y1 = int(yr.split("/")[0])
                y2 = y1 + 1
                min_d = QDate(y1, 1, 1)
                max_d = QDate(y2, 8, 31)
                
                cal = adm_date.calendarWidget()
                if cal:
                    cal.setMinimumDate(min_d)
                    cal.setMaximumDate(max_d)
                    
                adm_date._min_valid = min_d
                adm_date._max_valid = max_d
                
                def validate_date(target=adm_date):
                    if not target.is_null():
                        d = target.date()
                        if d < target._min_valid:
                            target.setDate(target._min_valid)
                        elif d > target._max_valid:
                            target.setDate(target._max_valid)
                            
                adm_date.editingFinished.connect(validate_date)
            except Exception:
                pass

            grid.addWidget(adm_date, row, 4)

            # الملاحظة — تتحدث تلقائياً
            remark_lbl = QLabel("/")
            remark_lbl.setAlignment(Qt.AlignCenter)
            remark_lbl.setFixedWidth(90)
            remark_lbl.setStyleSheet(
                "font-size: 11px; font-weight: bold; border-radius: 6px; "
                "padding: 3px 6px; background: #f1f5f9; color: #64748b;"
            )
            grid.addWidget(remark_lbl, row, 5)

            # ربط تغيير القيمة بتحديث الملاحظة
            adm_spin.valueChanged.connect(
                lambda val, lbl=remark_lbl: self._on_admin_score_changed(val, lbl)
            )

            self._eval_widgets.append((yr, edu_spin, edu_date, adm_spin, adm_date, remark_lbl))

        eval_layout.addWidget(grid_frame)

        # ─ ملاحظة المدير ─
        note_title = QLabel("ملاحظة المدير:")
        note_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #334155; margin-top: 8px;")
        eval_layout.addWidget(note_title)

        from PyQt5.QtWidgets import QTextEdit
        self.director_note_input = QTextEdit()
        self.director_note_input.setLayoutDirection(Qt.RightToLeft)
        self.director_note_input.setPlaceholderText("ملاحظة المدير حول أداء الموظف (اختياري)...")
        self.director_note_input.setMaximumHeight(80)
        self.director_note_input.setStyleSheet("""
            QTextEdit {
                font-size: 13px; font-family: 'Amiri';
                border: 1px solid #cbd5e1; border-radius: 8px;
                padding: 8px; background: #fff;
            }
            QTextEdit:focus { border-color: #3b82f6; background: #eff6ff; }
        """)
        eval_layout.addWidget(self.director_note_input)

        # ─ زر الطباعة الفردية ─
        print_row = QHBoxLayout()
        self.print_btn = ActionButton("طباعة الاستمارة", "print", "primary")
        self.print_btn.clicked.connect(self._print_individual)
        print_row.addWidget(self.print_btn)
        print_row.addStretch()
        eval_layout.addLayout(print_row)

        eval_layout.addStretch()
        layout.addWidget(self.eval_container)

        scroll.setWidget(scroll_w)
        wrapper = QVBoxLayout(tab)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(scroll)

        # ─ تحديث المجال أول مرة ─
        self._refresh_eval_limits()

        return tab

    @staticmethod
    def _spin_style():
        return """
            QDoubleSpinBox {
                font-size: 13px; font-weight: bold;
                border: 1px solid #94a3b8; border-radius: 6px;
                padding: 3px 6px; background: #fff;
            }
            QDoubleSpinBox:focus { border-color: #3b82f6; background: #eff6ff; }
        """

    # ══════════════════════════════════════════════════════════════════════
    #  INTERACTIVITY
    # ══════════════════════════════════════════════════════════════════════

    def _on_grade_changed(self, text):
        is_teacher = "أستاذ" in text
        self.subject_input.setVisible(is_teacher)
        self.subject_label.setVisible(is_teacher)

        # الرتب المعفاة ليس لها درجة ولا تاريخ سريان
        is_worker = any(w in text for w in WORKER_GRADES)
        if hasattr(self, 'degree_label'):
            self.degree_label.setVisible(not is_worker)
            self.degree_input.setVisible(not is_worker)
        if is_worker and hasattr(self, 'effective_date'):
            self.effective_date.setVisible(False)
            self.effective_date_label.setVisible(False)

        self._refresh_eval_eligibility()

    def _on_degree_changed(self, text):
        self._refresh_eval_limits()
        # إخفاء + تفريغ تاريخ السريان إذا الدرجة فارغة أو 0
        deg_str = text.strip()
        has_degree = False
        try:
            has_degree = bool(deg_str) and int(deg_str) > 0
        except ValueError:
            has_degree = bool(deg_str)
        if hasattr(self, 'effective_date'):
            self.effective_date.setVisible(has_degree)
            if not has_degree:
                # تفريغ التاريخ تلقائياً
                self.effective_date.clear_date()
        if hasattr(self, 'effective_date_label'):
            self.effective_date_label.setVisible(has_degree)

    def _refresh_eval_eligibility(self):
        """تحقق الإعفاء بناءً على الرتبة والدرجة."""
        grade = self.grade_combo.currentText().strip() if hasattr(self, 'grade_combo') else ""
        degree_str = self.degree_input.text().strip() if hasattr(self, 'degree_input') else ""

        exempt = False
        if "عامل مهني" in grade:
            exempt = True
        try:
            if degree_str and int(degree_str) == 0:
                exempt = True
        except ValueError:
            pass

        if hasattr(self, 'exempt_label'):
            self.exempt_label.setVisible(exempt)
            self.eval_container.setVisible(not exempt)

    def _refresh_eval_limits(self):
        """ضبط حدود SpinBox الإدارية + الملاحظة حسب الدرجة."""
        degree_str = self.degree_input.text().strip() if hasattr(self, 'degree_input') else ""

        try:
            degree = max(1, int(degree_str))
        except (ValueError, TypeError):
            degree = 1

        base_min, max_limit = compute_score_limits(degree)

        if hasattr(self, 'range_label'):
            self.range_label.setText(
                f"سلّم التنقيط للدرجة {degree}:  الحد الأدنى = {base_min}  |  "
                f"الحد الأقصى = {max_limit}  |  الخطوة = 0.5"
            )

        # ضبط حدود كل SpinBox إدارية
        # minimum = base_min - 0.5 للسماح بقيمة "فارغة" تُعرض كـ "/"
        for yr, edu_spin, edu_date, adm_spin, adm_date, remark_lbl in self._eval_widgets:
            old_val = adm_spin.value()
            adm_spin.blockSignals(True)
            adm_spin.setMinimum(base_min - 0.5)
            adm_spin.setMaximum(max_limit)
            adm_spin.setSpecialValueText("/")
            # إذا القيمة الحالية خارج المجال → إعادة ضبطها
            if old_val < base_min:
                adm_spin.setValue(base_min - 0.5)  # empty
            elif old_val > max_limit:
                adm_spin.setValue(max_limit)
            else:
                adm_spin.setValue(old_val)
            adm_spin.blockSignals(False)
            # تحديث الملاحظة
            self._on_admin_score_changed(adm_spin.value(), remark_lbl)

        self._refresh_eval_eligibility()

    def _on_admin_score_changed(self, value: float, remark_label: QLabel):
        """تحديث ملصق الملاحظة لحظياً."""
        degree_str = self.degree_input.text().strip() if hasattr(self, 'degree_input') else ""
        try:
            degree = max(1, int(degree_str))
        except (ValueError, TypeError):
            degree = 1
        base_min, _ = compute_score_limits(degree)

        if value < base_min:
            remark_label.setText("/")
            remark_label.setStyleSheet(
                "font-size: 11px; font-weight: bold; border-radius: 6px; "
                "padding: 3px 6px; background: #f1f5f9; color: #64748b;"
            )
            return

        remark = get_remark(value, base_min)
        color_map = {
            "دون الوسط": ("#fff7ed", "#c2410c"),
            "متوسط":     ("#fef9c3", "#854d0e"),
            "جيد":        ("#f0fdf4", "#166534"),
            "جيد جداً":  ("#ecfdf5", "#065f46"),
            "ممتاز":     ("#eff6ff", "#1d4ed8"),
        }
        bg, fg = color_map.get(remark, ("#f1f5f9", "#334155"))
        remark_label.setText(remark)
        remark_label.setStyleSheet(
            f"font-size: 11px; font-weight: bold; border-radius: 6px; "
            f"padding: 3px 6px; background: {bg}; color: {fg};"
        )

    # ══════════════════════════════════════════════════════════════════════
    #  POPULATE / LOAD
    # ══════════════════════════════════════════════════════════════════════

    def _populate(self, emp):
        # Tab 1
        self.last_name_input.setText(emp["last_name"] or "")
        self.first_name_input.setText(emp["first_name"] or "")
        try:
            self.maiden_name_input.setText(emp["maiden_name"] or "")
        except (IndexError, KeyError):
            pass
        self.birth_date.setText(emp["birth_date"] or "")
        try:
            self.birth_place_input.setText(emp["birth_place"] or "")
        except (IndexError, KeyError):
            pass
        try:
            family_val = emp["family_status"] or ""
            idx = self.family_status_combo.findText(family_val)
            if idx >= 0:
                self.family_status_combo.setCurrentIndex(idx)
            else:
                self.family_status_combo.setEditText(family_val)
        except (IndexError, KeyError):
            pass
        self.national_id_input.setText(emp["national_id"] or "")
        try:
            self.social_security_input.setText(emp["social_security"] or "")
        except KeyError:
            pass
        self.phone_input.setText(emp["phone"] or "")
        self.address_input.setText(emp["address"] or "")

        # Tab 2
        self.code_input.setText(emp["employee_code"] or "")

        grade_val = emp["grade"] or ""
        idx = self.grade_combo.findText(grade_val)
        if idx >= 0:
            self.grade_combo.setCurrentIndex(idx)
        else:
            self.grade_combo.setEditText(grade_val)

        self.subject_input.setText(emp["subject"] or "")
        try:
            self.category_input.setText(emp["category"] or "")
        except (IndexError, KeyError):
            pass
        self.degree_input.setText(emp["degree"] or "")
        self.effective_date.setText(emp["effective_date"] or "")
        try:
            self.diploma_input.setText(emp["diploma"] or "")
        except (IndexError, KeyError):
            pass
        try:
            self.diploma_date_input.setText(emp["diploma_date"] or "")
        except (IndexError, KeyError):
            pass
        try:
            self.account_number_input.setText(emp["account_number"] or "")
            self.account_key_input.setText(emp["account_key"] or "")
        except (IndexError, KeyError):
            pass

    def _load_evaluations(self):
        """ملء SpinBoxes الـ4 سنوات + ملاحظة المدير من قاعدة البيانات."""
        if not self.employee:
            return
        emp_id = self.employee["id"]
        evals = db.get_evaluations_for_employee(emp_id)
        evals_dict = {ev["school_year"]: ev for ev in evals}

        settings = db.get_all_settings()
        current_year = settings.get("school_year", "2025/2026")

        for yr, edu_spin, edu_date, adm_spin, adm_date, remark_lbl in self._eval_widgets:
            ev = evals_dict.get(yr)
            if not ev:
                continue

            # النقطة التربوية
            edu_val = ev.get("edu_score")
            if edu_val is not None and float(edu_val) > 0:
                edu_spin.setValue(float(edu_val))
            else:
                edu_spin.setValue(-0.5)  # empty

            edu_date.setText(ev.get("edu_date") or "")

            # النقطة الإدارية
            adm_val = ev.get("admin_score")
            if adm_val is not None and float(adm_val) > 0:
                adm_spin.setValue(float(adm_val))
            else:
                adm_spin.setValue(adm_spin.minimum())  # empty

            adm_date.setText((ev.get("eval_date") or "").replace("-", "/"))

            # ملاحظة المدير — نحمّلها من السنة الحالية فقط
            if yr == current_year and hasattr(self, 'director_note_input'):
                note = ev.get("director_note") or ""
                self.director_note_input.setPlainText(note)

    # ══════════════════════════════════════════════════════════════════════
    #  SAVE
    # ══════════════════════════════════════════════════════════════════════

    def _save(self):
        last = self.last_name_input.text().strip()
        first = self.first_name_input.text().strip()
        if not last and not first:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل")
            return
        self.accept()

    def get_data(self):
        return {
            "employee_code": self.code_input.text().strip(),
            "last_name": self.last_name_input.text().strip(),
            "first_name": self.first_name_input.text().strip(),
            "maiden_name": self.maiden_name_input.text().strip(),
            "birth_date": self.birth_date.text().replace("/", "-"),
            "birth_place": self.birth_place_input.text().strip(),
            "family_status": self.family_status_combo.currentText().strip(),
            "grade": self.grade_combo.currentText().strip(),
            "subject": self.subject_input.text().strip(),
            "category": self.category_input.text().strip(),
            "degree": self.degree_input.text().strip(),
            "effective_date": self.effective_date.text().replace("/", "-"),
            "diploma": self.diploma_input.text().strip(),
            "diploma_date": self.diploma_date_input.text().replace("/", "-"),
            "phone": self.phone_input.text().strip(),
            "address": self.address_input.text().strip(),
            "national_id": self.national_id_input.text().strip(),
            "social_security": self.social_security_input.text().strip(),
            "account_number": self.account_number_input.text().strip(),
            "account_key": self.account_key_input.text().strip(),
            "notes": "",
        }

    def get_evaluation_data(self) -> list:
        """
        إرجاع قائمة بسجلات التقييم لحفظها فى قاعدة البيانات.
        كل عنصر: dict(employee_id, school_year, admin_score, edu_score, ...).
        النقطة فارغة (value < valid min) تُحذف ولا تُحفظ.
        """
        if not self.employee:
            return []
        emp_id = self.employee["id"]

        degree_str = self.degree_input.text().strip()
        try:
            degree = max(1, int(degree_str))
        except (ValueError, TypeError):
            degree = 1
        base_min, _ = compute_score_limits(degree)

        settings = db.get_all_settings()
        current_year = settings.get("school_year", "2025/2026")
        director_note = self.director_note_input.toPlainText().strip() if hasattr(self, 'director_note_input') else ""

        records = []
        for yr, edu_spin, edu_date_w, adm_spin, adm_date_w, remark_lbl in self._eval_widgets:
            edu_val = edu_spin.value()
            adm_val = adm_spin.value()

            # كلاهما فارغ → لا نحفظ
            if edu_val < 0 and adm_val < base_min:
                continue

            # تحضير القيم
            edu_score = edu_val if edu_val >= 0 else None
            admin_score = adm_val if adm_val >= base_min else None
            remark = get_remark(adm_val, base_min) if admin_score else ""

            rec = {
                "employee_id": emp_id,
                "school_year": yr,
                "admin_score": admin_score if admin_score else 0,
                "edu_score": edu_score,
                "edu_date": edu_date_w.text().strip(),
                "eval_date": adm_date_w.text().strip().replace("/", "-"),
                "remark": remark,
                "director_note": director_note if yr == current_year else "",
            }
            records.append(rec)
        return records

    # ══════════════════════════════════════════════════════════════════════
    #  PRINTING
    # ══════════════════════════════════════════════════════════════════════

    def _print_individual(self):
        """حفظ البيانات + إغلاق النافذة + طباعة الاستمارة."""
        if not self.employee:
            QMessageBox.warning(self, "تنبيه", "يرجى حفظ الموظف أولاً ثم طباعة الاستمارة.")
            return

        # ─ 1. التحقق من صحة الاسم ─
        last = self.last_name_input.text().strip()
        first = self.first_name_input.text().strip()
        if not last and not first:
            QMessageBox.warning(self, "تنبيه", "يرجى إدخال اسم الموظف على الأقل")
            return

        emp_data = self.get_data()
        emp_data["id"] = self.employee["id"]

        settings = db.get_all_settings()
        current_year = settings.get("school_year", "2025/2026")

        # بناء قائمة evals من القيم الحالية
        degree_str = self.degree_input.text().strip()
        try:
            degree = max(1, int(degree_str))
        except (ValueError, TypeError):
            degree = 1
        base_min, _ = compute_score_limits(degree)

        evals = []
        current_adm_score = None
        current_remark = ""

        for yr, edu_spin, edu_date_w, adm_spin, adm_date_w, remark_lbl in self._eval_widgets:
            edu_val = edu_spin.value()
            adm_val = adm_spin.value()
            ev = {
                "school_year": yr,
                "edu_score": edu_val if edu_val >= 0 else None,
                "edu_date": edu_date_w.text().strip(),
                "admin_score": adm_val if adm_val >= base_min else None,
                "eval_date": adm_date_w.text().strip(),
            }
            evals.append(ev)

        # نبحث عن النقطة الإدارية في السنة الحالية (آخر عنصر)
        if self._eval_widgets:
            _, _, _, last_adm, _, last_remark_lbl = self._eval_widgets[-1]
            last_val = last_adm.value()
            if last_val >= base_min:
                current_adm_score = last_val
                current_remark = get_remark(last_val, base_min)

        # ملاحظة المدير
        director_note = self.director_note_input.toPlainText().strip() if hasattr(self, 'director_note_input') else ""

        # ─ 2. توليد HTML ─
        html = EvaluationPrinter.generate_html(
            employee=emp_data,
            evals=evals,
            settings=settings,
            current_score=current_adm_score,
            current_year=current_year,
            current_remark=current_remark,
            director_note=director_note,
        )

        # ─ 3. حفظ HTML لإظهاره بعد إغلاق النافذة ─
        self._pending_print_html = html

        # ─ 4. حفظ البيانات وإغلاق النافذة ─
        self.accept()


# ══════════════════════════════════════════════════════════════════════════
#  EMPLOYEES PAGE
# ══════════════════════════════════════════════════════════════════════════

class EmployeesPage(QWidget):
    """Main dashboard for employee management — table only, stats in sidebar."""

    employee_count_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self.refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 12)

        # Header row: title + buttons
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header = QLabel("إدارة الموظفين 👥")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        header_row.addWidget(header)
        header_row.addStretch()

        # ─ طباعة جماعية لاستمارات التنقيط ─
        batch_btn = ActionButton("طباعة استمارات التنقيط", "print", "warning")
        batch_btn.setMinimumHeight(40)
        batch_btn.clicked.connect(self._batch_print_evaluations)
        header_row.addWidget(batch_btn, alignment=Qt.AlignTop)

        add_btn = ActionButton("إضافة موظف", "➕", "primary")
        add_btn.setMinimumHeight(40)
        add_btn.clicked.connect(self._add_employee)
        header_row.addWidget(add_btn, alignment=Qt.AlignTop)
        layout.addLayout(header_row)

        # Search bar
        self.search_bar = SearchBar("بحث بالاسم أو الرمز أو الرتبة أو المادة...")
        self.search_bar.search_changed.connect(self._on_search)
        layout.addWidget(self.search_bar)

        # Table — takes all remaining space
        self.table = QTableWidget()
        self.table.setLayoutDirection(Qt.RightToLeft)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "الرمز الوظيفي", "اللقب", "الاسم", "الرتبة",
            "المادة", "الدرجة", "تاريخ السريان", "إجراءات"
        ])

        # Hide less important columns
        self.table.setColumnHidden(0, True)  # الرمز الوظيفي
        self.table.setColumnHidden(4, True)  # المادة
        self.table.setColumnHidden(5, True)  # الدرجة

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.table, stretch=1)

    def refresh_table(self, employees=None):
        if employees is None:
            employees = db.get_all_employees()

        self.table.setRowCount(0)
        self.table.setRowCount(len(employees))

        for row, emp in enumerate(employees):
            self.table.setItem(row, 0, self._item(emp["employee_code"] or ""))
            self.table.setItem(row, 1, self._item(emp["last_name"] or ""))
            self.table.setItem(row, 2, self._item(emp["first_name"] or ""))
            self.table.setItem(row, 3, self._item(emp["grade"] or ""))
            self.table.setItem(row, 4, self._item(emp["subject"] or ""))
            self.table.setItem(row, 5, self._item(emp["degree"] or ""))
            self.table.setItem(row, 6, self._item(emp["effective_date"] or ""))

            # Action buttons
            actions = QWidget()
            actions.setLayoutDirection(Qt.RightToLeft)
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(4)

            options_btn = QPushButton(" خيارات")
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

            edit_action = menu.addAction(get_icon("edit", color="#475569"), "تعديل بيانات الموظف")
            edit_action.triggered.connect(lambda checked, eid=emp["id"]: self._edit_employee(eid))

            inquiry_action = menu.addAction(get_icon("inquiry", color="#475569"), "استفسار")
            inquiry_action.triggered.connect(lambda checked, eid=emp["id"]: self._open_inquiry(eid))

            # ── النقطة الإدارية → يفتح تعديل البيانات على تبويب التقييم ──
            if is_eligible_for_evaluation(emp):
                eval_action = menu.addAction(get_icon("document", color="#7c3aed"), "🌟  النقطة الإدارية")
                eval_action.triggered.connect(lambda checked, eid=emp["id"]: self._open_evaluation(eid))

            # ── طلب عطلة مرضية ──
            sick_leave_action = menu.addAction(get_icon("sick_leave", color="#0891b2"), "🏥  طلب عطلة مرضية")
            sick_leave_action.triggered.connect(lambda checked, eid=emp["id"]: self._new_sick_leave_for_employee(eid))

            menu.addSeparator()
            del_action = menu.addAction(get_icon("delete", color="#ef4444"), "حذف الموظف")
            del_action.triggered.connect(lambda checked, eid=emp["id"]: self._delete_employee(eid))

            options_btn.setMenu(menu)
            al.addWidget(options_btn)
            al.addStretch()
            self.table.setCellWidget(row, 7, actions)
            self.table.setRowHeight(row, 48)

        self.employee_count_changed.emit()

    def _item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    def get_stats(self):
        employees = db.get_all_employees()
        total = len(employees)
        teachers = sum(1 for e in employees if "أستاذ" in (e["grade"] or ""))
        admins = sum(1 for e in employees if e["grade"] and "أستاذ" not in e["grade"]
                     and "عامل" not in e["grade"] and "حارس" not in e["grade"])
        workers = sum(1 for e in employees if e["grade"]
                      and ("عامل" in e["grade"] or "حارس" in e["grade"]))
        return {
            "total": total,
            "teachers": teachers,
            "admins": admins,
            "workers": workers,
        }

    def _on_search(self):
        query = self.search_bar.text().strip()
        if query:
            employees = db.search_employees(query)
        else:
            employees = db.get_all_employees()
        self.refresh_table(employees)

    # ── CRUD ─────────────────────────────────────────────────────────────

    def _add_employee(self):
        dialog = EmployeeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            db.add_employee(data)
            self.refresh_table()

    def _edit_employee(self, emp_id, initial_tab=0):
        emp = db.get_employee(emp_id)
        if not emp:
            return
        dialog = EmployeeDialog(self, employee=emp, initial_tab=initial_tab)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            db.update_employee(emp_id, data)
            # حفظ بيانات التقييم
            eval_records = dialog.get_evaluation_data()
            for rec in eval_records:
                db.upsert_evaluation(rec)
            self.refresh_table()

            # ─ إذا طُلبت الطباعة → نعرض المعاينة بعد الحفظ والإغلاق ─
            print_html = getattr(dialog, '_pending_print_html', None)
            if print_html:
                from pdf_generator_v2 import AdvancedPdfPreviewDialog
                dlg = AdvancedPdfPreviewDialog(
                    html_content=print_html, parent=self, margins_mm=(15, 15, 15, 15)
                )
                dlg.exec_()

    def _open_evaluation(self, emp_id):
        """يفتح نافذة تعديل الموظف مباشرةً على تبويب التقييم."""
        self._edit_employee(emp_id, initial_tab=2)

    def _delete_employee(self, emp_id):
        emp = db.get_employee(emp_id)
        if not emp:
            return
        full_name = db.get_employee_full_name(emp)
        reply = QMessageBox.question(
            self, "تأكيد الحذف",
            "هل أنت متأكد من حذف الموظف:\n%s؟\n\nسيتم حذف جميع البيانات المرتبطة به." % full_name,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            db.delete_employee(emp_id)
            self.refresh_table()

    def _print_doc(self, emp_id, doc_type):
        emp = db.get_employee(emp_id)
        if not emp:
            return
        dialog = PrintDocumentDialog(emp, doc_type, self)
        dialog.exec_()

    def _open_inquiry(self, emp_id):
        emp = db.get_employee(emp_id)
        if not emp:
            return
        dialog = InquiryDialog(emp, self)
        dialog.exec_()

    def _new_sick_leave_for_employee(self, emp_id):
        emp = db.get_employee(emp_id)
        if not emp:
            return

        from ui.sick_leave_page import SickLeaveRequestDialog, SubstitutionDetailsDialog
        from PyQt5.QtWidgets import QDialog, QMessageBox

        dialog = SickLeaveRequestDialog(self, employee=emp)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = dialog.get_data()
        sl_id = db.add_sick_leave(data)

        if dialog.needs_substitution():
            subst_dialog = SubstitutionDetailsDialog(
                emp, sl_id, data["start_date"], data["end_date"], self
            )
            if subst_dialog.exec_() == QDialog.Accepted:
                subst_data = subst_dialog.get_data()
                db.add_substitution(subst_data)
                QMessageBox.information(
                    self, "نجاح",
                    "✅ تم تسجيل العطلة المرضية والاستخلاف بنجاح.\n"
                    "يمكنك طباعة المحضر من صفحة العطل المرضية."
                )
            else:
                QMessageBox.information(
                    self, "تنبيه",
                    "تم تسجيل العطلة المرضية بدون استخلاف.\n"
                    "يمكنك إضافة الاستخلاف لاحقاً من صفحة العطل المرضية."
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
        from ui.sick_leave_page import SickLeavePage
        dummy = SickLeavePage.__new__(SickLeavePage)
        html = dummy._generate_sick_leave_html(sl, emp, settings)
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        preview = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=False)
        preview.exec_()

    # ── طباعة جماعية لاستمارات التنقيط ──────────────────────────────────

    def _batch_print_evaluations(self):
        """طباعة استمارات التنقيط لجميع الموظفين المؤهلين."""
        eligible = get_eligible_employees()
        if not eligible:
            QMessageBox.information(
                self, "تنبيه",
                "لا يوجد موظفون خاضعون للتقييم في القائمة الحالية."
            )
            return

        reply = QMessageBox.question(
            self, "طباعة جماعية",
            f"سيتم توليد استمارات التنقيط لـ {len(eligible)} موظف(ة).\n"
            "هل تريد المتابعة؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        settings = db.get_all_settings()
        current_year = settings.get("school_year", "2025/2026")

        # ─ توليد HTML مع شريط تقدّم ─
        from PyQt5.QtWidgets import QApplication
        progress = QProgressDialog(
            "جاري توليد الاستمارات...", "إلغاء", 0, len(eligible), self
        )
        progress.setWindowTitle("طباعة جماعية")
        progress.setLayoutDirection(Qt.RightToLeft)
        progress.setMinimumWidth(360)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        pages = []
        for i, emp in enumerate(eligible):
            if progress.wasCanceled():
                return

            emp_dict = dict(emp) if not isinstance(emp, dict) else emp
            emp_name = f"{emp_dict.get('last_name','')} {emp_dict.get('first_name','')}"
            progress.setLabelText(f"جاري توليد استمارة: {emp_name}  ({i+1}/{len(eligible)})")

            evals = db.get_evaluations_for_employee(emp_dict["id"])

            cur_score = None
            cur_remark = ""
            cur_dir_note = ""
            for ev in evals:
                ev_d = dict(ev) if not isinstance(ev, dict) else ev
                if ev_d["school_year"] == current_year:
                    s = ev_d.get("admin_score")
                    if s and float(s) > 0:
                        cur_score = float(s)
                        cur_remark = ev_d.get("remark") or ""
                    cur_dir_note = ev_d.get("director_note") or ""
                    break

            html = EvaluationPrinter.generate_html(
                employee=emp_dict, evals=evals, settings=settings,
                current_score=cur_score, current_year=current_year,
                current_remark=cur_remark, director_note=cur_dir_note,
            )
            pages.append(html)
            progress.setValue(i + 1)
            QApplication.processEvents()

        progress.close()

        if not pages:
            return

        # ─ دمج الصفحات ─
        import re
        combined_bodies = []
        style_content = ""
        for i, page_html in enumerate(pages):
            if i == 0:
                sm = re.search(r'<style>(.*?)</style>', page_html, re.DOTALL)
                style_content = sm.group(1) if sm else ""
            bm = re.search(r'<body[^>]*>(.*?)</body>', page_html, re.DOTALL)
            body = bm.group(1) if bm else page_html
            if i > 0:
                combined_bodies.append('<div style="page-break-before: always;"></div>')
            combined_bodies.append(body)

        final_html = (
            '<!DOCTYPE html><html dir="rtl" lang="ar"><head>'
            f'<meta charset="UTF-8"><style>{style_content}</style></head>'
            f'<body>{"".join(combined_bodies)}</body></html>'
        )

        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dlg = AdvancedPdfPreviewDialog(
            html_content=final_html, parent=self, margins_mm=(15, 15, 15, 15), disable_regex=True
        )
        dlg.exec_()

    def refresh(self):
        self.refresh_table()

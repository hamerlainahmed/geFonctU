# -*- coding: utf-8 -*-
"""
Employee Management Page — Clean list with search and CRUD.
Stats moved to sidebar for maximum table space.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QDialog, QMessageBox, QHeaderView, QAbstractItemView, QSizePolicy,
    QFormLayout, QTextEdit, QSpacerItem, QLabel, QMenu, QPushButton,
    QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCursor

from ui.widgets import (
    ArabicLineEdit, ArabicLabel, ArabicComboBox, ArabicDateEdit,
    Card, SearchBar, ActionButton, ArabicFormLayout, Separator,
    PageHeader,
)
from ui.documents_modal import PrintDocumentDialog
from ui.inquiry_dialog import InquiryDialog
from ui.icons import get_icon
import database as db

GRADES = [
    "أستاذ التعليم المتوسط", "أستاذ التعليم الابتدائي", "أستاذ التعليم الثانوي",
    "أستاذ رئيسي", "أستاذ مكوّن", "مساعد تربوي", "مستشار التربية",
    "مستشار التوجيه", "مقتصد", "نائب مقتصد", "مدير", "نائب مدير",
    "عامل مهني", "حارس", "كاتب", "محاسب", "إداري",
]


class EmployeeDialog(QDialog):
    """Dialog for adding / editing an employee."""

    def __init__(self, parent=None, employee=None):
        super().__init__(parent)
        self.employee = employee
        self.setWindowTitle("تعديل موظف" if employee else "إضافة موظف جديد")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(560)
        self._build_ui()

        if employee:
            self._populate(employee)

    def _build_ui(self):
        from PyQt5.QtWidgets import QGridLayout, QScrollArea

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # Scrollable form content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("تعديل بيانات الموظف ✏️" if self.employee else "إضافة موظف جديد ➕")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b; margin-bottom: 8px;")
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setSpacing(14)
        
        form_left = ArabicFormLayout()
        form_right = ArabicFormLayout()

        # Right Column
        self.code_input = ArabicLineEdit("الرمز الوظيفي")
        form_right.addRow("الرمز الوظيفي:", self.code_input)

        self.last_name_input = ArabicLineEdit("اللقب بالعربية")
        form_right.addRow("اللقب *:", self.last_name_input)

        self.first_name_input = ArabicLineEdit("الاسم بالعربية")
        form_right.addRow("الاسم *:", self.first_name_input)

        self.birth_date = ArabicDateEdit()
        form_right.addRow("تاريخ الازدياد:", self.birth_date)

        self.national_id_input = ArabicLineEdit("رقم البطاقة الوطنية")
        form_right.addRow("رقم التعريف:", self.national_id_input)

        # Left Column
        self.grade_combo = ArabicComboBox()
        self.grade_combo.setEditable(True)
        # Combine standard grades with any custom grades from the database
        all_grades = list(GRADES)
        try:
            custom_grades = db.get_all_grades()
            for cg in custom_grades:
                if cg not in all_grades:
                    all_grades.append(cg)
        except Exception:
            pass  # Fallback to standard if get_all_grades fails
            
        self.grade_combo.addItems(all_grades)
        self.grade_combo.currentTextChanged.connect(self._on_grade_changed)
        form_left.addRow("الرتبة:", self.grade_combo)

        self.subject_input = ArabicLineEdit("المادة (للأساتذة فقط)")
        self.subject_label = QLabel("مادة التخصص:")
        form_left.addRow(self.subject_label, self.subject_input)

        self.degree_input = ArabicLineEdit("الدرجة (رقم)")
        form_left.addRow("الدرجة:", self.degree_input)

        self.effective_date = ArabicDateEdit()
        form_left.addRow("تاريخ السريان:", self.effective_date)

        self.phone_input = ArabicLineEdit("رقم الهاتف")
        form_left.addRow("الهاتف:", self.phone_input)

        self.account_number_input = ArabicLineEdit("رقم الحساب الجاري")
        form_left.addRow("رقم الحساب:", self.account_number_input)

        self.account_key_input = ArabicLineEdit("المفتاح")
        form_left.addRow("المفتاح:", self.account_key_input)

        # Full Width
        self.address_input = ArabicLineEdit("العنوان")

        grid.addLayout(form_right, 0, 1)
        grid.addLayout(form_left, 0, 0)
        
        layout.addLayout(grid)
        
        address_form = ArabicFormLayout()
        address_form.addRow("العنوان:", self.address_input)
        layout.addLayout(address_form)

        # Show/hide subject based on grade
        self._on_grade_changed(self.grade_combo.currentText())

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll, 1)

        # Buttons — fixed at the bottom outside the scroll area
        btn_layout = QHBoxLayout()
        save_btn = ActionButton("حفظ", "\U0001F4BE", "success")
        save_btn.clicked.connect(self._save)
        cancel_btn = ActionButton("إلغاء", "\u274C", "outline")
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def _on_grade_changed(self, text):
        is_teacher = "أستاذ" in text
        self.subject_input.setVisible(is_teacher)
        self.subject_label.setVisible(is_teacher)

    def _populate(self, emp):
        self.code_input.setText(emp["employee_code"] or "")
        self.last_name_input.setText(emp["last_name"] or "")
        self.first_name_input.setText(emp["first_name"] or "")
        self.degree_input.setText(emp["degree"] or "")
        self.subject_input.setText(emp["subject"] or "")
        self.phone_input.setText(emp["phone"] or "")
        self.national_id_input.setText(emp["national_id"] or "")
        self.address_input.setText(emp["address"] or "")
        try:
            self.account_number_input.setText(emp["account_number"] or "")
            self.account_key_input.setText(emp["account_key"] or "")
        except (IndexError, KeyError):
            pass

        grade_val = emp["grade"] or ""
        idx = self.grade_combo.findText(grade_val)
        if idx >= 0:
            self.grade_combo.setCurrentIndex(idx)
        else:
            self.grade_combo.setEditText(grade_val)

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
            "birth_date": self.birth_date.date().toString("yyyy-MM-dd"),
            "grade": self.grade_combo.currentText().strip(),
            "subject": self.subject_input.text().strip(),
            "degree": self.degree_input.text().strip(),
            "effective_date": self.effective_date.date().toString("yyyy-MM-dd"),
            "phone": self.phone_input.text().strip(),
            "address": self.address_input.text().strip(),
            "national_id": self.national_id_input.text().strip(),
            "account_number": self.account_number_input.text().strip(),
            "account_key": self.account_key_input.text().strip(),
            "notes": "",
        }


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

        # Header row: title + add button
        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        header = QLabel("إدارة الموظفين 👥")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b;")
        header_row.addWidget(header)
        header_row.addStretch()

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
        self.table.setColumnHidden(0, True) # الرمز الوظيفي
        self.table.setColumnHidden(4, True) # المادة
        self.table.setColumnHidden(5, True) # الدرجة
        
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
            
            # Using QToolButton for a sleek dropdown menu instead of multiple buttons
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

        # Emit signal so sidebar can update stats
        self.employee_count_changed.emit()

    def _item(self, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        return item

    def get_stats(self):
        """Return stats dict for sidebar display."""
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

    def _add_employee(self):
        dialog = EmployeeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            db.add_employee(data)
            self.refresh_table()

    def _edit_employee(self, emp_id):
        emp = db.get_employee(emp_id)
        if not emp:
            return
        dialog = EmployeeDialog(self, employee=emp)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            db.update_employee(emp_id, data)
            self.refresh_table()

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
        """Open the premium inquiry dialog for an employee."""
        emp = db.get_employee(emp_id)
        if not emp:
            return
        dialog = InquiryDialog(emp, self)
        dialog.exec_()

    def _new_sick_leave_for_employee(self, emp_id):
        """Open sick leave request dialog pre-filled with the selected employee."""
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
            # الأستاذ في عطلة > 7 أيام → طلب بيانات المستخلف
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
            # طباعة طلب العطلة المرضية
            self._print_sick_leave_request(sl_id, emp)

    def _print_sick_leave_request(self, sl_id, emp):
        """Print the sick leave request form directly."""
        sl = db.get_sick_leave(sl_id)
        if not sl:
            return
        settings = db.get_all_settings()
        # Reuse the HTML generator from SickLeavePage
        from ui.sick_leave_page import SickLeavePage
        dummy = SickLeavePage.__new__(SickLeavePage)  # no __init__ call
        html = dummy._generate_sick_leave_html(sl, emp, settings)
        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        preview = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=False)
        preview.exec_()

    def refresh(self):
        self.refresh_table()

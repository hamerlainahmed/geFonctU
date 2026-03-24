# -*- coding: utf-8 -*-
"""
Archive Page — Interface for starting new school year and searching/printing from archives.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from ui.widgets import (
    Card, ActionButton, SearchBar, Separator, PageHeader, ArabicComboBox,
    ArabicLineEdit, ArabicDateEdit, ArabicFormLayout
)
from ui.documents_modal import PrintDocumentDialog
from ui.icons import get_icon
import archive_manager

class ArchivePage(QWidget):
    """Page for archiving current data and searching past school years."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        header = PageHeader(
            "الأرشيف الشامل", 
            "البحث عن الموظفين والمستخلفين، واستخراج وثائق من السنوات السابقة بكل سهولة."
        )
        # layout.addWidget(header)
        # No top section anymore
        
        # Bottom section: Search Archives
        search_layout = QHBoxLayout()
        
        lbl_search = QLabel("البحث الشامل في الأرشيف:")
        lbl_search.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        
        self.search_box = SearchBar()
        self.search_box.search_changed.connect(self._perform_search)
        
        search_layout.addWidget(lbl_search)
        search_layout.addSpacing(16)
        search_layout.addWidget(self.search_box)
        search_layout.addStretch()
        
        layout.addLayout(search_layout)

        # Results Table
        self.table = QTableWidget()
        self.table.setLayoutDirection(Qt.RightToLeft)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "السنة الدراسية", "اللقب والإسم", "الرتبة", "المادة", "تاريخ الميلاد", "إجراء"
        ])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in [0, 2, 3, 4]:
            header_view.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            
        header_view.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 100)
            
        layout.addWidget(self.table)



    def refresh(self):
        self._perform_search()

    def _perform_search(self):
        query = self.search_box.text().strip()
        # Even without query, we can load ALL from archives (maybe limited to 100 rows if too big)
        
        try:
            results = archive_manager.search_archives(query)
            self._populate_table(results[:200]) # Cap to 200 to keep UI responsive
        except Exception as e:
            print(f"Archive search error: {e}")

    def _populate_table(self, results):
        self.table.setRowCount(len(results))
        for row, data in enumerate(results):
            # "السنة الدراسية"
            self.table.setItem(row, 0, self._create_item(data["year"]))
            
            # "اللقب والإسم"
            full_name = f"{data['last_name']} {data['first_name']}"
            if data['is_sub']:
                full_name += " (مستخلف)"
            
            self.table.setItem(row, 1, self._create_item(full_name))
            
            # "الرتبة"
            self.table.setItem(row, 2, self._create_item(data["grade"]))
            
            # "المادة"
            self.table.setItem(row, 3, self._create_item(data["subject"]))
            
            # "تاريخ الميلاد"
            self.table.setItem(row, 4, self._create_item(data["birth_date"]))
            
            # "إجراء" (Buttons)
            from PyQt5.QtWidgets import QToolButton
            from ui.icons import get_icon
            
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(12)
            actions_layout.setAlignment(Qt.AlignCenter)
            
            btn_print = QToolButton()
            btn_print.setIcon(get_icon("print", color="#3b82f6"))
            btn_print.setFixedSize(36, 36)
            btn_print.setStyleSheet("QToolButton { border: 1px solid #3b82f6; border-radius: 6px; background: transparent; padding: 0px; margin: 0px; } QToolButton:hover { background: #eff6ff; }")
            btn_print.setCursor(Qt.PointingHandCursor)
            btn_print.setToolTip("طباعة شهادة عمل")
            btn_print.clicked.connect(lambda checked, d=data: self._print_certificate(d))
            
            btn_edit = QToolButton()
            btn_edit.setIcon(get_icon("edit", color="#3b82f6"))
            btn_edit.setFixedSize(36, 36)
            btn_edit.setStyleSheet("QToolButton { border: 1px solid #3b82f6; border-radius: 6px; background: transparent; padding: 0px; margin: 0px; } QToolButton:hover { background: #eff6ff; }")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setToolTip("تعديل معلومات المستخلف")
            btn_edit.clicked.connect(lambda checked, d=data: self._edit_substitute(d))
            
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_print)
            self.table.setCellWidget(row, 5, actions_widget)

    def _create_item(self, text):
        if text is None: text = ""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignCenter)
        return item
        
    def _print_certificate(self, metadata):
        """Extract the exact dict for the employee from the specific DB and print"""
        db_path = metadata["db_path"]
        emp_id = metadata["id"]
        is_sub = metadata["is_sub"]
        
        emp_dict = archive_manager.get_employee_dict_from_archive(db_path, emp_id, is_sub)
        old_settings = archive_manager.get_settings_dict_from_archive(db_path)
        
        if not emp_dict:
            QMessageBox.warning(self, "تنبيه", "تعذر استخراج بينات الموظف من الأرشيف.")
            return
            
        dialog = PrintDocumentDialog(emp_dict, "شهادة عمل", self, custom_settings=old_settings)
        dialog.exec_()

    def _edit_substitute(self, metadata):
        """Allows quick editing of archived substitute."""
        db_path = metadata["db_path"]
        emp_id = metadata["id"]
        is_sub = metadata["is_sub"]
        
        if not is_sub:
            QMessageBox.warning(self, "ملاحظة", "تعديل واجهة الموظفين الدائمين من الأرشيف غير مدعوم حاليا، المستخلفون فقط.")
            return
            
        emp_dict = archive_manager.get_employee_dict_from_archive(db_path, emp_id, is_sub)
        if not emp_dict:
            return
            
        dialog = EditArchiveSubstituteDialog(emp_dict, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("""
                    UPDATE substitutions 
                    SET substitute_first_name = ?, substitute_last_name = ?, 
                        substitute_birth_date = ?
                    WHERE id = ?
                """, (new_data["first_name"], new_data["last_name"], new_data["birth_date"], emp_id))
                conn.commit()
                conn.close()
                QMessageBox.information(self, "نجاح", "تم تعديل معلومات المستخلف في الأرشيف بنجاح.")
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "خطأ", f"تعذر تحديث قاعدة الأرشيف: {e}")

class EditArchiveSubstituteDialog(QDialog):
    def __init__(self, emp_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تعديل معلومات المستخلف (في الأرشيف)")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(400)
        
        self.emp_dict = emp_dict
        
        layout = QVBoxLayout(self)
        form = ArabicFormLayout()
        
        self.first_input = ArabicLineEdit("الاسم")
        self.first_input.setText(emp_dict.get("first_name", ""))
        form.addRow("الاسم:", self.first_input)
        
        self.last_input = ArabicLineEdit("اللقب")
        self.last_input.setText(emp_dict.get("last_name", ""))
        form.addRow("اللقب:", self.last_input)
        
        self.dob_input = ArabicLineEdit("تاريخ الميلاد (مثال: 1990-01-01)")
        self.dob_input.setText(emp_dict.get("birth_date", ""))
        form.addRow("تاريخ الميلاد:", self.dob_input)
        
        layout.addLayout(form)
        
        btn_layout = QHBoxLayout()
        save_btn = ActionButton("حفظ التغييرات", "save", "primary")
        save_btn.clicked.connect(self.accept)
        cancel_btn = ActionButton("إلغاء", "close", "outline")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
    def get_data(self):
        return {
            "first_name": self.first_input.text().strip(),
            "last_name": self.last_input.text().strip(),
            "birth_date": self.dob_input.text().strip()
        }

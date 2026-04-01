# -*- coding: utf-8 -*-
"""
Settings Page — Clean Card UI with institution information and code.
"""

import sys
import os
import subprocess

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QLabel,
    QGridLayout, QFrame, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor

from ui.widgets import (
    ArabicLineEdit, ArabicComboBox, ActionButton, ArabicFormLayout,
    ScrollablePageWidget, Card
)
from ui.icons import get_icon, ICON_COLORS
import database as db
import archive_manager


class SettingsPage(ScrollablePageWidget):
    """Application settings page built on top of ScrollablePageWidget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        # We use self.layout from ScrollablePageWidget
        self.layout.setSpacing(24)
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        # Page Title with icon
        title_row = QHBoxLayout()
        title_icon = QLabel()
        title_icon.setPixmap(get_icon("settings", color="#3b82f6").pixmap(28, 28))
        title_icon.setFixedSize(32, 32)
        title_icon.setStyleSheet("background: transparent;")
        title_row.addWidget(title_icon)
        
        title = QLabel("إعدادات النظام")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #0f172a; margin-bottom: 8px;")
        title_row.addWidget(title)
        title_row.addStretch()
        self.layout.addLayout(title_row)

        # ── School Info Card ──
        school_card = Card()
        school_layout = QVBoxLayout(school_card)
        school_layout.setSpacing(16)
        
        school_header = QHBoxLayout()
        school_icon = QLabel()
        school_icon.setPixmap(get_icon("institution", color="#3b82f6").pixmap(22, 22))
        school_icon.setFixedSize(24, 24)
        school_icon.setStyleSheet("background: transparent;")
        school_header.addWidget(school_icon)
        
        school_title = QLabel("معلومات المؤسسة")
        school_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        school_header.addWidget(school_title)
        school_header.addStretch()
        school_layout.addLayout(school_header)
        
        school_form = ArabicFormLayout()
        
        self.school_name_input = ArabicLineEdit("اسم المؤسسة التعليمية")
        school_form.addRow("اسم المؤسسة:", self.school_name_input)
        
        self.school_code_input = ArabicLineEdit("رمز المؤسسة (مثل: 123456)")
        school_form.addRow("رمز المؤسسة:", self.school_code_input)

        self.school_address_input = ArabicLineEdit("عنوان المؤسسة")
        school_form.addRow("البلدية:", self.school_address_input)

        self.wilaya_input = ArabicLineEdit("الولاية")
        school_form.addRow("الولاية:", self.wilaya_input)

        self.moudiriya_input = ArabicLineEdit("مديرية التربية")
        school_form.addRow("المديرية:", self.moudiriya_input)

        self.director_input = ArabicLineEdit("اسم المدير(ة)")
        school_form.addRow("المدير(ة):", self.director_input)

        # Removed school_year_input completely from here

        school_layout.addLayout(school_form)
        self.layout.addWidget(school_card)

        # ── Start New Year / Archive Card ──
        new_year_card = Card()
        ny_layout = QVBoxLayout(new_year_card)
        ny_layout.setSpacing(12)
        
        lbl = QLabel("إغلاق السنة الحالية وأرشفة البيانات")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        lbl.setLayoutDirection(Qt.RightToLeft)
        ny_layout.addWidget(lbl)
        
        desc = QLabel(
            "هذه العملية ستحتفظ ببيانات الموظفين، الإعدادات، وأرصدة العطل، بينما تُفرغ جداول غيابات السنة المنصرمة. "
            "نسخة كاملة من القاعدة ستحفظ في صفحة (الأرشيف) لتتمكن من طباعة شهادات سنوات سابقة."
        )
        desc.setStyleSheet("color: #64748b; font-size: 14px;")
        desc.setLayoutDirection(Qt.RightToLeft)
        desc.setWordWrap(True)
        ny_layout.addWidget(desc)
        
        ny_controls = QHBoxLayout()
        ny_controls.setSpacing(16)
        
        import datetime
        self.new_year_input = ArabicComboBox()
        self.new_year_input.setMinimumWidth(220)
        
        current_active_year = archive_manager.get_current_school_year()
        old_years = archive_manager.get_available_archive_years()
        
        cal_year = datetime.datetime.now().year
        ny_1 = f"{cal_year}/{cal_year+1}"
        ny_2 = f"{cal_year+1}/{cal_year+2}"
        
        years_set = set(old_years)
        years_set.add(current_active_year)
        years_set.add(ny_1)
        years_set.add(ny_2)
        
        sorted_years = sorted(list(years_set))
        self.new_year_input.addItems(sorted_years)
        self.new_year_input.setCurrentText(current_active_year)
        
        ny_btn = ActionButton("تطبيق السنة المحددة", "inventory_2", "primary")
        ny_btn.setMinimumWidth(180)
        ny_btn.clicked.connect(self._manage_school_year)
        
        ny_controls.addWidget(ny_btn)
        ny_controls.addWidget(self.new_year_input)
        ny_controls.addStretch()
        
        ny_layout.addLayout(ny_controls)
        self.layout.addWidget(new_year_card)

        # ── Control Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)
        
        save_btn = ActionButton("حفظ الإعدادات", "save", "primary")
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        reset_btn = ActionButton("إعادة تحميل", "refresh", "outline")
        reset_btn.clicked.connect(self._load_settings)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)
        self.layout.addStretch()

    def _load_settings(self):
        settings = db.get_all_settings()
        self.school_name_input.setText(settings.get("school_name", ""))
        self.school_code_input.setText(settings.get("school_code", ""))
        self.school_address_input.setText(settings.get("school_address", ""))
        self.wilaya_input.setText(settings.get("wilaya", ""))
        self.moudiriya_input.setText(settings.get("moudiriya", ""))
        self.director_input.setText(settings.get("director_name", ""))


    def _save_settings(self):
        db.set_setting("school_name", self.school_name_input.text().strip())
        db.set_setting("school_code", self.school_code_input.text().strip())
        db.set_setting("school_address", self.school_address_input.text().strip())
        db.set_setting("wilaya", self.wilaya_input.text().strip())
        db.set_setting("moudiriya", self.moudiriya_input.text().strip())
        db.set_setting("director_name", self.director_input.text().strip())
        # db.set_setting("school_year", ...) removed because it's managed via archive_manager

        QMessageBox.information(self, "نجاح", "✅ تم حفظ الإعدادات بنجاح")

    def refresh(self):
        self._load_settings()

    def _manage_school_year(self):
        selected_year = self.new_year_input.currentText().strip()
        current_year = archive_manager.get_current_school_year()
        
        if selected_year == current_year:
            QMessageBox.information(self, "تنبيه", f"السنة '{selected_year}' هي السنة النشطة حالياً.")
            return
            
        old_years = archive_manager.get_available_archive_years()
        
        try:
            selected_start = int(selected_year.split("/")[0])
            current_start = int(current_year.split("/")[0])
        except ValueError:
            QMessageBox.warning(self, "خطأ", "نسق السنة المحددة غير صالح.")
            return

        if selected_start > current_start:
            # ── Show preview of what will happen ──
            try:
                import year_transition
                preview = year_transition.preview_transition()
                preview_text = (
                    f"• عدد الموظفين: {preview['total_employees']}\n"
                    f"• الموظفون الذين لديهم نقطة حالية: {preview['employees_with_rating']}\n"
                    f"• سجلات الغيابات التي ستُحذف: {preview['absences_count']}\n"
                    f"• سجلات الاستفسارات التي ستُحذف: {preview['inquiries_count']}\n"
                )
            except Exception:
                preview_text = ""

            reply = QMessageBox.question(
                self, "فتح سنة جديدة", 
                f"هل أنت متأكد أنك تريد إغلاق السنة الحالية '{current_year}' وبدء سنة '{selected_year}'؟\n\n"
                f"{preview_text}\n"
                "• سيتم حفظ نسخة كاملة في الأرشيف\n"
                "• سيتم تفريغ سجلات الغيابات والاستفسارات\n"
                "• نقاط التقييم للسنة الحالية ستُحفظ وتظهر كنقاط السنة السابقة\n"
                "• نقاط السنة الجديدة ستكون فارغة\n\n"
                "⚠️ العملية ذرية: إما تنجح كاملة أو لا يتغير شيء.\n\n"
                "سيتم إعادة تشغيل البرنامج تلقائياً.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    archive_manager.start_new_school_year(selected_year)
                    QMessageBox.information(
                        self, "نجاح",
                        f"✅ تم إنشاء السنة الدراسية '{selected_year}' بنجاح!\n\n"
                        f"• نقاط التقييم للسنة '{current_year}' محفوظة\n"
                        "• نقاط السنة الجديدة فارغة وجاهزة للإدخال\n\n"
                        "سيتم إعادة تشغيل البرنامج الآن..."
                    )
                    self._restart_application()
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء أرشفة القاعدة:\n{e}")
        else:
            reply = QMessageBox.question(
                self, "استرجاع أرشيف قديم", 
                f"هل تريد إعادة فتح السنة الدراسية المعزولة '{selected_year}'؟\n\nتنبيه: سيتم أرشفة السنة الحالية تلقائياً وإحلال السنة القديمة محلها كواجهة نشطة.\n\nسيتم إعادة تشغيل البرنامج تلقائياً.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                try:
                    archive_manager.restore_school_year(selected_year)
                    QMessageBox.information(
                        self, "نجاح",
                        "تم استرجاع السنة القديمة بنجاح.\n\n"
                        "سيتم إعادة تشغيل البرنامج الآن..."
                    )
                    self._restart_application()
                except Exception as e:
                    QMessageBox.critical(self, "خطأ", f"حدث خطأ أثناء الاسترجاع: {e}")

    def _restart_application(self):
        """إعادة تشغيل البرنامج تلقائياً لتطبيق إعدادات السنة الجديدة."""
        try:
            # Determine the executable path
            if getattr(sys, 'frozen', False):
                # Running as compiled exe (PyInstaller)
                exe_path = sys.executable
                subprocess.Popen([exe_path])
            else:
                # Running as Python script
                python = sys.executable
                script = os.path.abspath(sys.argv[0])
                subprocess.Popen([python, script])
            
            # Close the current application
            from PyQt5.QtWidgets import QApplication
            QApplication.instance().quit()
        except Exception as e:
            QMessageBox.warning(
                self, "تنبيه",
                f"تعذّر إعادة التشغيل التلقائي:\n{e}\n\n"
                "يرجى إغلاق البرنامج وإعادة تشغيله يدوياً."
            )

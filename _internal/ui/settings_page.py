# -*- coding: utf-8 -*-
"""
Settings Page — Clean Card UI with institution information and code.
"""

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

        self.school_year_input = ArabicLineEdit("السنة الدراسية (مثلاً 2025/2026)")
        school_form.addRow("السنة الدراسية:", self.school_year_input)

        school_layout.addLayout(school_form)
        self.layout.addWidget(school_card)

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
        self.school_year_input.setText(settings.get("school_year", ""))

    def _save_settings(self):
        db.set_setting("school_name", self.school_name_input.text().strip())
        db.set_setting("school_code", self.school_code_input.text().strip())
        db.set_setting("school_address", self.school_address_input.text().strip())
        db.set_setting("wilaya", self.wilaya_input.text().strip())
        db.set_setting("moudiriya", self.moudiriya_input.text().strip())
        db.set_setting("director_name", self.director_input.text().strip())
        db.set_setting("school_year", self.school_year_input.text().strip())

        QMessageBox.information(self, "نجاح", "✅ تم حفظ الإعدادات بنجاح")

    def refresh(self):
        self._load_settings()

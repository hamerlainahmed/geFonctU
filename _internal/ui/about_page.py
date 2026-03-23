# -*- coding: utf-8 -*-
"""
About Page — Premium Information Display.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from ui.widgets import ScrollablePageWidget, Card, ArabicLabel

class AboutPage(ScrollablePageWidget):
    """A dedicated page for information about the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self._build_ui()

    def _build_ui(self):
        self.layout.setSpacing(12)
        self.layout.setContentsMargins(40, 40, 40, 40)

        # Page Title
        title = QLabel('<div align="right" dir="rtl">عن البرنامج</div>')
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #0f172a; margin-bottom: 2px;")
        self.layout.addWidget(title)

        # Main Info Card
        info_card = Card()
        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(16)

        app_title = QLabel('<div align="right" dir="rtl">نظام تسيير الموظفين (geFonct)</div>')
        app_title.setStyleSheet(" font-size: 22px; font-weight: bold; color: #1e293b;")
        info_layout.addWidget(app_title)

        version = QLabel('<div align="right" dir="rtl">الإصدار 2.1.7</div>')
        version.setStyleSheet(" font-size: 14px; color: #3b82f6; font-weight: bold;")
        info_layout.addWidget(version)
        #developer
        developer = QLabel(
            '<div align="right" dir="rtl">'
            'المطور: أحمد حمرالعين - 2026'
            '</div>'
        )
        developer.setWordWrap(True)
        developer.setStyleSheet(" font-size: 15px; color: #475569; line-height: 1.8;")
        info_layout.addWidget(developer)
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("background-color: #e2e8f0; border: none; min-height: 1px;")
        info_layout.addWidget(separator)

        description = QLabel(
            '<div align="right" dir="rtl">'
            'نظام إداري متكامل مصمم خصيصاً لتلبية احتياجات المؤسسات التعليمية '
            'في تسيير شؤون الموظفين. يتميز البرنامج بواجهة عصرية سهلة الاستخدام '
            'ودعم كامل للوثائق الرسمية.</div>'
        )
        description.setWordWrap(True)
        description.setStyleSheet(" font-size: 15px; color: #475569; line-height: 1.8;")
        info_layout.addWidget(description)
       

        self.layout.addWidget(info_card)

        # Features Section
        features_title = QLabel('<div align="right" dir="rtl">مميزات النظام 🌟</div>')
        features_title.setStyleSheet(" font-size: 20px; font-weight: bold; color: #1e293b; margin-top: 16px;")
        self.layout.addWidget(features_title)

        features_card = Card()
        features_layout = QVBoxLayout(features_card)
        features_layout.setSpacing(12)

        features = [
            "✅ إدارة شاملة لبيانات الموظفين والأساتذة.",
            "✅ نظام متابعة العطل المرضية والاستخلاف القانوني.",
            "✅ تسجيل الغيابات والتأخرات مع إحصائيات دقيقة.",
            "✅ استخراج وطباعة الوثائق الإدارية (شهادة عمل، محضر تنصيب، إلخ).",
            "✅ استيراد وتصدير البيانات من وإلى ملفات Excel بكل سهولة.",
            "✅ واجهة مستخدم متطورة تدعم الشاشات الحديثة وويندوز 7.",
        ]

        for f in features:
            f_lbl = QLabel(f'<div align="right" dir="rtl">{f}</div>')
            f_lbl.setStyleSheet(" font-size: 14px; color: #334155; padding: 4px 0;")
            features_layout.addWidget(f_lbl)

        self.layout.addWidget(features_card)

       
        self.layout.addStretch()

# -*- coding: utf-8 -*-
"""
Home Page — Premium Dashboard with Material Design icons.
Provides a stunning overview of the app's state, quick actions,
and high-level statistics.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QPushButton, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont

from ui.widgets import ScrollablePageWidget, ActionButton
from ui.icons import get_icon, ICON_COLORS
import database as db

class DashboardCard(QFrame):
    def __init__(self, title, value, icon_name, gradient_start, gradient_end, parent=None):
        super().__init__(parent)
        self.setObjectName("dash_card")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumHeight(140)
        
        self.setStyleSheet(f"""
            QFrame#dash_card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {gradient_start}, stop:1 {gradient_end});
                border-radius: 18px;
                color: white;
            }}
        """)
        
        # Shadow effect
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(24)
        effect.setXOffset(0)
        effect.setYOffset(10)
        effect.setColor(QColor(gradient_start).darker(150))
        self.setGraphicsEffect(effect)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Top Row: Title + Icon
        top_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; background: transparent; color: rgba(255,255,255,0.9);")
        
        icon_lbl = QLabel()
        icon_lbl.setPixmap(get_icon(icon_name, color="#ffffff").pixmap(32, 32))
        icon_lbl.setFixedSize(40, 40)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("background: rgba(255,255,255,0.2); border-radius: 10px;")
        
        top_row.addWidget(title_lbl)
        top_row.addStretch()
        top_row.addWidget(icon_lbl)
        layout.addLayout(top_row)
        
        layout.addStretch()
        
        # Bottom Row: Value - explicitly aligned right in RTL
        self.val_lbl = QLabel(str(value))
        self.val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_lbl.setStyleSheet("font-size: 42px; font-weight: bold; background: transparent; color: white;")
        layout.addWidget(self.val_lbl)

    def set_value(self, value):
        self.val_lbl.setText(str(value))

class QuickActionButton(QPushButton):
    def __init__(self, title, desc, icon_name, parent=None):
        super().__init__(parent)
        self.setObjectName("quick_action_btn")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(80)
        
        self.setStyleSheet("""
            QPushButton#quick_action_btn {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                text-align: right;
            }
            QPushButton#quick_action_btn:hover {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        
        # Material icon in a colored container
        icon_container = QLabel()
        icon_container.setPixmap(get_icon(icon_name, color="#3b82f6").pixmap(28, 28))
        icon_container.setFixedSize(44, 44)
        icon_container.setAlignment(Qt.AlignCenter)
        icon_container.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eff6ff, stop:1 #dbeafe);
            border-radius: 12px;
        """)
        layout.addWidget(icon_container)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; background: transparent;")
        text_layout.addWidget(t_lbl)
        
        d_lbl = QLabel(desc)
        d_lbl.setStyleSheet("font-size: 13px; color: #64748b; background: transparent;")
        text_layout.addWidget(d_lbl)
        
        layout.addLayout(text_layout)
        layout.addStretch()

class HomePage(ScrollablePageWidget):
    """The main dashboard page."""
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window # Reference to switch pages
        self._build_ui()
        self.refresh()
        
    def _build_ui(self):
        self.layout.setSpacing(32)
        self.layout.setContentsMargins(40, 40, 40, 40)
        
        # Welcome header
       
        
        # Cards Grid
        grid = QGridLayout()
        grid.setSpacing(24)
        
        self.card_total = DashboardCard("إجمالي الموظفين", "0", "people", "#3b82f6", "#2563eb")
        self.card_teachers = DashboardCard("الأساتذة", "0", "teacher", "#10b981", "#059669")
        self.card_leaves = DashboardCard("عطل مرضية جارية", "0", "hospital", "#f59e0b", "#d97706")
        self.card_absences = DashboardCard("غيابات هذا الشهر", "0", "absence", "#ef4444", "#dc2626")
        
        grid.addWidget(self.card_total, 0, 0)
        grid.addWidget(self.card_teachers, 0, 1)
        grid.addWidget(self.card_leaves, 0, 2)
        grid.addWidget(self.card_absences, 0, 3)
        
        self.layout.addLayout(grid)
        
        # Quick Actions
        actions_row = QHBoxLayout()
        actions_icon = QLabel()
        actions_icon.setPixmap(get_icon("quick_action", color="#f59e0b").pixmap(24, 24))
        actions_icon.setFixedSize(28, 28)
        actions_icon.setStyleSheet("background: transparent;")
        actions_row.addWidget(actions_icon)
        
        a_title = QLabel("إجراءات سريعة")
        a_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1e293b; margin-top: 20px;")
        actions_row.addWidget(a_title)
        actions_row.addStretch()
        self.layout.addLayout(actions_row)
        
        actions_grid = QGridLayout()
        actions_grid.setSpacing(12)
        
        # btn_add_emp = QuickActionButton("إضافة موظف جديد", "تسجيل موظف أو أستاذ", "add")
        # btn_add_emp.clicked.connect(lambda: self.main_window._on_nav_clicked(1))
        
        btn_add_leave = QuickActionButton("إضافة عطلة مرضية", "تسجيل عطلة ومتابعتها", "medical")
        btn_add_leave.clicked.connect(lambda: self.main_window._on_nav_clicked(2))
        
        btn_add_absence = QuickActionButton("تسجيل غياب أو تأخر", "حجز غيابات الموظفين", "delay")
        btn_add_absence.clicked.connect(lambda: self.main_window._on_nav_clicked(3))
        
        btn_inquiries = QuickActionButton("الاستفسارات", "إدارة الاستفسارات وقرارات المدير", "inquiry")
        btn_inquiries.clicked.connect(lambda: self.main_window._on_nav_clicked(4))

        btn_deductions = QuickActionButton("الاقتطاعات", "طباعة إشعارات وكشوف الخصم", "deduction")
        btn_deductions.clicked.connect(lambda: self.main_window._on_nav_clicked(5))

        # btn_settings = QuickActionButton("إعدادات النظام", "تغيير بيانات المؤسسة", "settings")
        # btn_settings.clicked.connect(lambda: self.main_window._on_nav_clicked(6))

        btn_import_excel = QuickActionButton("استيراد من إكسل", "إضافة قوائم موظفين بالتشغيل السريع", "file_excel")
        btn_import_excel.clicked.connect(lambda: self.main_window._import_excel())
        
        # actions_grid.addWidget(btn_add_emp, 0, 0)
        actions_grid.addWidget(btn_add_leave, 0, 0)
        actions_grid.addWidget(btn_add_absence, 0, 1)
        actions_grid.addWidget(btn_inquiries, 0, 2)
        actions_grid.addWidget(btn_deductions, 1, 0)
        # actions_grid.addWidget(btn_settings, 1, 1)
        actions_grid.addWidget(btn_import_excel, 1, 1)
        
        self.layout.addLayout(actions_grid)
        self.layout.addStretch()

    def refresh(self):
        # Update Cards
        employees = db.get_all_employees()
        total = len(employees)
        teachers = sum(1 for e in employees if "أستاذ" in (e["grade"] or ""))
        
        leaves = db.get_active_sick_leaves()
        
        from PyQt5.QtCore import QDate
        current_month = QDate.currentDate().month()
        current_year = QDate.currentDate().year()
        absences_rows = db.get_monthly_absence_summary(current_year, current_month)
        monthly_absences = sum(r["absences_count"] for r in absences_rows)
        
        self.card_total.set_value(total)
        self.card_teachers.set_value(teachers)
        self.card_leaves.set_value(len(leaves))
        self.card_absences.set_value(monthly_absences)

# -*- coding: utf-8 -*-
"""
Main Window — Premium Material Design sidebar with Dashboard home.
Features Material Design icons, animated transitions, and polished UI.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel, QFileDialog, QMessageBox, QDialog,
    QSpacerItem, QSizePolicy, QStatusBar, QAction,
    QMenuBar, QMenu, QFrame, QGraphicsDropShadowEffect,
)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap

from ui.widgets import SidebarButton, Separator, SidebarSeparator
from ui.icons import get_icon, get_colored_icon, ICON_COLORS, SIDEBAR_ICONS
from ui.home_page import HomePage
from ui.employees_page import EmployeesPage
from ui.settings_page import SettingsPage
from ui.sick_leave_page import SickLeavePage
from ui.absences_page import AbsencesPage
from ui.inquiries_page import InquiriesPage
from ui.deductions_page import DeductionsPage
from ui.archive_page import ArchivePage
from ui.about_page import AboutPage

import excel_handler
import database as db
from updater_integration import UpdateCheckThread, UpdateNotificationDialog, trigger_updater, check_show_whats_new

class MainWindow(QMainWindow):
    """Main application window with RTL sidebar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام تسيير الموظفين")
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumSize(1100, 700)
        self.resize(1320, 820)
        
        # Set window icon
        self.setWindowIcon(get_icon("institution", color="#3b82f6"))

        self._build_menu()
        self._build_ui()
        self._build_statusbar()

        # Select first page
        self._nav_buttons[0].setChecked(True)
        self._on_nav_clicked(0)

        # Show "What's New" dialog if just updated
        check_show_whats_new(self)

        # Start smart background update check
        self.check_for_updates()

    def check_for_updates(self):
        """Fires the background thread to check for updates."""
        try:
            self.update_thread = UpdateCheckThread()
            self.update_thread.update_available.connect(self.prompt_update)
            self.update_thread.start()
        except Exception as e:
            print(f"Failed to start update checker: {e}")

    def prompt_update(self, new_version, release_notes):
        """Pops up the elegant notification dialog."""
        dialog = UpdateNotificationDialog(new_version, release_notes, self)
        # Use exec_ for PyQt5
        if dialog.exec_() == QDialog.Accepted:
            trigger_updater(self)

    def _build_menu(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        menubar.setLayoutDirection(Qt.RightToLeft)

        # File menu
        file_menu = menubar.addMenu("ملف")
        file_menu.setLayoutDirection(Qt.RightToLeft)

        import_action = QAction(get_icon("import", color="#374151"), "استيراد من إكسل", self)
        import_action.triggered.connect(self._import_excel)
        file_menu.addAction(import_action)

        export_action = QAction(get_icon("export", color="#374151"), "تصدير إلى إكسل", self)
        export_action.triggered.connect(self._export_excel)
        file_menu.addAction(export_action)

        template_action = QAction(get_icon("template", color="#374151"), "تصدير نموذج فارغ", self)
        template_action.triggered.connect(self._export_template)
        file_menu.addAction(template_action)

        file_menu.addSeparator()

        exit_action = QAction(get_icon("exit", color="#374151"), "خروج", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("مساعدة")
        help_menu.setLayoutDirection(Qt.RightToLeft)

        about_action = QAction(get_icon("about", color="#374151"), "حول التطبيق", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_ui(self):
        """Build the main UI layout."""
        central = QWidget()
        central.setLayoutDirection(Qt.RightToLeft)
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(270)
        sidebar.setLayoutDirection(Qt.RightToLeft)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App Title with icon
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(20, 24, 20, 4)
        title_layout.setSpacing(2)

        # Title row with logo icon
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        
        title_label = QLabel("نظام تسيير الموظفين")
        title_label.setObjectName("sidebar_title")
        title_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        title_label.setFixedWidth(150) # Fixed to prevent resize jumping
        
        app_icon_label = QLabel()
        app_icon_label.setPixmap(get_icon("institution", color="#60a5fa").pixmap(32, 32))
        app_icon_label.setFixedSize(36, 36)
        app_icon_label.setAlignment(Qt.AlignCenter)
        app_icon_label.setStyleSheet("background: rgba(59, 130, 246, 0.15); border-radius: 8px; padding: 2px;")
        
        title_row.addWidget(title_label)
        title_row.addWidget(app_icon_label)
        
        title_layout.addLayout(title_row)

        # subtitle = QLabel("إدارة شؤون الموظفين والوثائق")
        # subtitle.setObjectName("sidebar_subtitle")
        # subtitle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        # subtitle.setLayoutDirection(Qt.RightToLeft)
        # subtitle.setWordWrap(True)
        # title_layout.addWidget(subtitle)

        sidebar_layout.addWidget(title_widget)
        sidebar_layout.addWidget(SidebarSeparator())
        sidebar_layout.addSpacing(12)

        # Navigation with Material icons
        nav_items = [
            ("الرئيسية",             "home"),
            ("إدارة الموظفين",       "employees"),
            ("العطل المرضية",        "sick_leave"),
            ("الغيابات والتأخرات",   "absences"),
            ("الاستفسارات",         "inquiries"),
            ("الاقتطاعات",          "deductions"),
            ("الأرشيف والسنوات",   "archive"),
            ("الإعدادات",           "settings"),
            ("عن البرنامج",         "about"),
        ]

        self._nav_buttons = []
        for idx, (text, icon_name) in enumerate(nav_items):
            btn = SidebarButton(text, icon_name)
            btn.clicked.connect(lambda checked, i=idx: self._on_nav_clicked(i))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Sidebar footer
        sidebar_layout.addWidget(SidebarSeparator())
        sidebar_layout.addSpacing(12)


        # ── Content Area ──
        self.stack = QStackedWidget()
        self.stack.setLayoutDirection(Qt.RightToLeft)

        self.home_page = HomePage(self) # Pass self so it can navigate
        self.employees_page = EmployeesPage()
        self.sick_leave_page = SickLeavePage()
        self.absences_page = AbsencesPage()
        self.inquiries_page = InquiriesPage()
        self.deductions_page = DeductionsPage()
        self.archive_page = ArchivePage()
        self.settings_page = SettingsPage()
        self.about_page = AboutPage()

        # We keep the employee count changed signal to update status bar, no more side bar stats
        self.employees_page.employee_count_changed.connect(self._update_statusbar)
        
        # When pages change, we can also refresh home
        self.employees_page.employee_count_changed.connect(self.home_page.refresh)

        self.stack.addWidget(self.home_page)       # 0
        self.stack.addWidget(self.employees_page)   # 1
        self.stack.addWidget(self.sick_leave_page)  # 2
        self.stack.addWidget(self.absences_page)    # 3
        self.stack.addWidget(self.inquiries_page)   # 4
        self.stack.addWidget(self.deductions_page)  # 5
        self.stack.addWidget(self.archive_page)     # 6
        self.stack.addWidget(self.settings_page)    # 7
        self.stack.addWidget(self.about_page)       # 8

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, stretch=1)

    def _build_statusbar(self):
        """Create the status bar."""
        self.status_bar = QStatusBar()
        self.status_bar.setLayoutDirection(Qt.RightToLeft)
        self.setStatusBar(self.status_bar)
        self._update_statusbar()

    def _on_nav_clicked(self, index):
        """Switch to the selected page."""
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self.stack.setCurrentIndex(index)

        # Refresh the page
        page = self.stack.currentWidget()
        if hasattr(page, 'refresh'):
            page.refresh()

        self._update_statusbar()

    def _update_statusbar(self):
        employees = db.get_all_employees()
        active_leaves = db.get_active_sick_leaves()
        self.status_bar.showMessage(
            "إجمالي الموظفين: %d  |  عطل مرضية جارية: %d  |  السنة الدراسية: %s" % (
                len(employees),
                len(active_leaves),
                db.get_setting('school_year', '2025/2026')
            )
        )

    # ── Excel Operations ──

    def _import_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "استيراد من إكسل",
            "", "Excel Files (*.xlsx *.xls)"
        )
        if not filepath:
            return

        try:
            imported, skipped, errors = excel_handler.import_employees(filepath)
            msg = "تم استيراد %d موظف(ين) بنجاح.\n" % imported
            if skipped:
                msg += "تم تخطي %d صف(وف).\n" % skipped
            if errors:
                msg += "\nالأخطاء:\n" + "\n".join(errors[:10])

            QMessageBox.information(self, "نتيجة الاستيراد", msg)
            self.employees_page.refresh_table()
            self._update_statusbar()
            self.home_page.refresh()
        except Exception as e:
            QMessageBox.critical(self, "خطأ", "فشل الاستيراد:\n%s" % str(e))

    def _export_excel(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "تصدير إلى إكسل",
            "employees.xlsx", "Excel Files (*.xlsx)"
        )
        if not filepath:
            return

        try:
            count = excel_handler.export_employees(filepath)
            QMessageBox.information(
                self, "نجاح",
                "تم تصدير %d موظف(ين) بنجاح إلى:\n%s" % (count, filepath)
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", "فشل التصدير:\n%s" % str(e))

    def _export_template(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "تصدير نموذج فارغ",
            "employee_template.xlsx", "Excel Files (*.xlsx)"
        )
        if not filepath:
            return

        try:
            excel_handler.export_template(filepath)
            QMessageBox.information(
                self, "نجاح",
                "تم تصدير النموذج بنجاح إلى:\n%s" % filepath
            )
        except Exception as e:
            QMessageBox.critical(self, "خطأ", "فشل التصدير:\n%s" % str(e))

    def _show_about(self):
        """Navigate to the About page."""
        # 8 is the index of the about_page (0-8)
        self._on_nav_clicked(8)

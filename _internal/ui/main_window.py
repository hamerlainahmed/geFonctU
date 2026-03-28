# -*- coding: utf-8 -*-
"""
Main Window — Refactored to use MSFluentWindow for the Windows 11 Fluent Design aesthetic.
"""

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog, QApplication
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from qfluentwidgets import (MSFluentWindow, NavigationItemPosition, 
                           FluentIcon as FIF, InfoBar, InfoBarPosition)

import excel_handler
import database as db
from updater_integration import UpdateCheckThread, UpdateNotificationDialog, trigger_updater, check_show_whats_new

from ui.home_page import HomePage
from ui.employees_page import EmployeesPage
from ui.settings_page import SettingsPage
from ui.sick_leave_page import SickLeavePage
from ui.absences_page import AbsencesPage
from ui.inquiries_page import InquiriesPage
from ui.deductions_page import DeductionsPage
from ui.archive_page import ArchivePage
from ui.about_page import AboutPage

class MainWindow(MSFluentWindow):
    """Main application window structured with Windows 11 Fluent UI sidebar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام تسيير الموظفين")
        self.setMinimumSize(1100, 700)
        self.showMaximized()
        
        # We can set the window icon natively
        self.setWindowIcon(QIcon("app_icon.ico"))

        # Initialize UI parts
        self._init_pages()
        self._build_navigation()

        # Connect signals for status updates
        self.employees_page.employee_count_changed.connect(self._update_status)
        self.employees_page.employee_count_changed.connect(self.home_page.refresh)

        # Show "What's New" dialog if just updated
        check_show_whats_new(self)

        # Start smart background update check
        self.check_for_updates()
        
        # Initial status update
        self._update_status()

    def check_for_updates(self):
        try:
            self.update_thread = UpdateCheckThread()
            self.update_thread.update_available.connect(self.prompt_update)
            self.update_thread.start()
        except Exception as e:
            print(f"Failed to start update checker: {e}")

    def prompt_update(self, new_version, release_notes):
        dialog = UpdateNotificationDialog(new_version, release_notes, self)
        if dialog.exec_() == QDialog.Accepted:
            trigger_updater(self)

    def _init_pages(self):
        """Create all the main pages."""
        self.home_page = HomePage(self) # Some pages expect parent=self to call self._on_nav_clicked or stack
        self.home_page.setObjectName("HomePage")
        
        self.employees_page = EmployeesPage()
        self.employees_page.setObjectName("EmployeesPage")
        
        self.sick_leave_page = SickLeavePage()
        self.sick_leave_page.setObjectName("SickLeavePage")
        
        self.absences_page = AbsencesPage()
        self.absences_page.setObjectName("AbsencesPage")
        
        self.inquiries_page = InquiriesPage()
        self.inquiries_page.setObjectName("InquiriesPage")
        
        self.deductions_page = DeductionsPage()
        self.deductions_page.setObjectName("DeductionsPage")
        
        self.archive_page = ArchivePage()
        self.archive_page.setObjectName("ArchivePage")
        
        self.settings_page = SettingsPage()
        self.settings_page.setObjectName("SettingsPage")
        
        self.about_page = AboutPage()
        self.about_page.setObjectName("AboutPage")

        # Mock out stack indexing if sub-pages try to call self.stack.setCurrentIndex(index)
        if not hasattr(self, 'stack'):
            self.stack = self.stackedWidget

    def _on_nav_clicked(self, index):
        """Helper to catch old manual navigation from inner pages (e.g. from Home -> Setup)"""
        map_index_to_page = {
            0: self.home_page,
            1: self.employees_page,
            2: self.sick_leave_page,
            3: self.absences_page,
            4: self.inquiries_page,
            5: self.deductions_page,
            6: self.archive_page,
            7: self.settings_page,
            8: self.about_page,
        }
        if index in map_index_to_page:
            obj_name = map_index_to_page[index].objectName()
            self.navigationInterface.setCurrentItem(obj_name)
            self.switchTo(map_index_to_page[index])

    def _build_navigation(self):
        """Assemble the sidebar Navigation Interface."""
        # Top pages
        self.addSubInterface(self.home_page, FIF.HOME, "الرئيسية", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.employees_page, FIF.PEOPLE, "إدارة الموظفين", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.sick_leave_page, FIF.HEART, "العطل المرضية", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.absences_page, FIF.CALENDAR, "الغيابات والتأخرات", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.inquiries_page, FIF.HELP, "الاستفسارات", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.deductions_page, FIF.CUT, "الاقتطاعات", position=NavigationItemPosition.TOP)
        self.addSubInterface(self.archive_page, FIF.FOLDER, "الأرشيف والسنوات", position=NavigationItemPosition.TOP)
        
        # Bottom Actions 
        # self.navigationInterface.addItem(
        #     routeKey='ImportExcel',
        #     icon=FIF.DOWNLOAD,
        #     text='استيراد من إكسل',
        #     onClick=self._import_excel,
        #     selectable=False,
        #     position=NavigationItemPosition.BOTTOM
        # )
        # self.navigationInterface.addItem(
        #     routeKey='ExportExcel',
        #     icon=FIF.SHARE,
        #     text='تصدير إلى إكسل',
        #     onClick=self._export_excel,
        #     selectable=False,
        #     position=NavigationItemPosition.BOTTOM
        # )
        # self.navigationInterface.addItem(
        #     routeKey='ExportTemplate',
        #     icon=FIF.DOCUMENT,
        #     text='تصدير نموذج فارغ',
        #     onClick=self._export_template,
        #     selectable=False,
        #     position=NavigationItemPosition.BOTTOM
        # )
        
        # Bottom Navigation Interfaces
        self.addSubInterface(self.settings_page, FIF.SETTING, "الإعدادات", position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.about_page, FIF.INFO, "عن البرنامج", position=NavigationItemPosition.BOTTOM)
        
        # Exit Action
        self.navigationInterface.addItem(
            routeKey='ExitApp',
            icon=FIF.POWER_BUTTON,
            text='خروج',
            onClick=self.close,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )
        
        # Set default active
        self.navigationInterface.setCurrentItem(self.home_page.objectName())
        
    def _update_status(self):
        # Update the main window title for status
        employees = db.get_all_employees()
        active_leaves = db.get_active_sick_leaves()
        year = db.get_setting('school_year', '2025/2026')
        
        title = f"نظام تسيير الموظفين  —  إجمالي الموظفين: {len(employees)}  |  عطل مرضية جارية: {len(active_leaves)}  |  السنة الدراسية: {year}"
        self.setWindowTitle(title)

    # ── Excel Operations ──
    def _import_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "استيراد من إكسل",
            "", "Excel Files (*.xlsx *.xls)"
        )
        if not filepath:
            return

        try:
            imported, skipped, errors, updated = excel_handler.import_employees(filepath)
            msg = f"تم استيراد {imported} موظف(ين) جديد(ين).\n"
            if updated:
                msg += f"تم تحديث {updated} موظف(ين) موجودين.\n"
            if skipped:
                msg += f"تم تخطي {skipped} صف(وف).\n"
            if errors:
                msg += "\nالأخطاء:\n" + "\n".join(errors[:10])
            
            InfoBar.success("نتيجة الاستيراد", msg, parent=self, duration=4000)
            self.employees_page.refresh_table()
            self._update_status()
            self.home_page.refresh()
        except Exception as e:
            InfoBar.error("خطأ", f"فشل الاستيراد:\n{str(e)}", parent=self, duration=4000)

    def _export_excel(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "تصدير إلى إكسل",
            "employees.xlsx", "Excel Files (*.xlsx)"
        )
        if not filepath:
            return

        try:
            count = excel_handler.export_employees(filepath)
            InfoBar.success("نجاح", f"تم تصدير {count} موظف(ين) بنجاح إلى:\n{filepath}", parent=self, duration=4000)
        except Exception as e:
            InfoBar.error("خطأ", f"فشل التصدير:\n{str(e)}", parent=self, duration=4000)

    def _export_template(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "تصدير نموذج فارغ",
            "employee_template.xlsx", "Excel Files (*.xlsx)"
        )
        if not filepath:
            return

        try:
            excel_handler.export_template(filepath)
            InfoBar.success("نجاح", f"تم تصدير النموذج بنجاح إلى:\n{filepath}", parent=self, duration=4000)
        except Exception as e:
             InfoBar.error("خطأ", f"فشل التصدير:\n{str(e)}", parent=self, duration=4000)

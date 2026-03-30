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
        self._customize_nav_buttons()

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
        
        # Scrollable pages
        self.addSubInterface(self.employees_page, FIF.PEOPLE, "إدارة الموظفين", position=NavigationItemPosition.SCROLL)
        self.addSubInterface(self.sick_leave_page, FIF.HEART, "العطل المرضية", position=NavigationItemPosition.SCROLL)
        self.addSubInterface(self.absences_page, FIF.CALENDAR, "الغيابات والتأخرات", position=NavigationItemPosition.SCROLL)
        self.addSubInterface(self.inquiries_page, FIF.HELP, "الاستفسارات", position=NavigationItemPosition.SCROLL)
        self.addSubInterface(self.deductions_page, FIF.CUT, "الاقتطاعات", position=NavigationItemPosition.SCROLL)
        self.addSubInterface(self.archive_page, FIF.FOLDER, "الأرشيف والسنوات", position=NavigationItemPosition.SCROLL)
        
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

    def _customize_nav_buttons(self):
        """تخصيص أزرار القائمة الجانبية لتكون أوسع وأكثر ارتفاعاً لمنع تداخل/اقتطاع النص العربي."""
        from PyQt5.QtCore import QRect, QRectF
        from PyQt5.QtGui import QPainter
        from PyQt5.QtCore import Qt as _Qt
        from qfluentwidgets.components.navigation.navigation_bar import NavigationBarPushButton
        from qfluentwidgets.common.icon import drawIcon, FluentIconBase
        from qfluentwidgets.common.config import isDarkTheme
        from qfluentwidgets.common.color import autoFallbackThemeColor
        
        # Make the navigation bar wider to fit Arabic text
        self.navigationInterface.setFixedWidth(106)
        
        # Adjust layout spacing to prevent overlapping
        self.navigationInterface.topLayout.setSpacing(4)
        self.navigationInterface.bottomLayout.setSpacing(4)
        self.navigationInterface.scrollLayout.setSpacing(4)
        self.navigationInterface.topLayout.setContentsMargins(4, 10, 4, 0)
        self.navigationInterface.bottomLayout.setContentsMargins(4, 0, 4, 10)
        self.navigationInterface.scrollLayout.setContentsMargins(4, 5, 4, 5)
        
        # إظهار شريط التمرير بشكل دائم ليكون واضحا للمستخدم أنه يمكن التمرير
        self.navigationInterface.scrollArea.setVerticalScrollBarPolicy(_Qt.ScrollBarAlwaysOn)
        
        # تلوين مسار شريط التمرير قليلاً لتمييز منطقة التمرير
        self.navigationInterface.scrollArea.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: rgba(0, 0, 0, 0.03); width: 8px; border-radius: 4px; }"
        )
        
        def _custom_drawText(self_btn, painter: QPainter):
            """رسم النص مع التفاف الكلمات (word wrap) ومحاذاة في الوسط."""
            if self_btn.isSelected and not self_btn._isSelectedTextVisible:
                return
            
            if self_btn.isSelected or self_btn.isAboutSelected:
                painter.setPen(autoFallbackThemeColor(self_btn.lightSelectedColor, self_btn.darkSelectedColor))
            else:
                painter.setPen(_Qt.white if isDarkTheme() else _Qt.black)
            
            font = self_btn.font()
            font.setPointSize(9)
            painter.setFont(font)
            # Text starts at y=34, spanning 40 pixels vertically
            rect = QRect(2, 34, self_btn.width() - 4, 40)
            painter.drawText(rect, _Qt.AlignHCenter | _Qt.AlignTop | _Qt.TextWordWrap, self_btn.text())
        
        def _custom_drawIcon(self_btn, painter: QPainter):
            """رسم الأيقونة في الوسط (مع تعديل المحاذاة)."""
            if (self_btn.isPressed or not self_btn.isEnter) and not (self_btn.isSelected or self_btn.isAboutSelected):
                painter.setOpacity(0.6)
            if not self_btn.isEnabled():
                painter.setOpacity(0.4)
            
            # Center icon horizontally, start slightly higher
            iw, ih = 22, 22
            x = (self_btn.width() - iw) / 2
            if self_btn._isSelectedTextVisible:
                rect = QRectF(x, 8, iw, ih)
            else:
                rect = QRectF(x, 8 + self_btn.iconAni.offset, iw, ih)
            
            selectedIcon = self_btn._selectedIcon or self_btn._icon
            if isinstance(selectedIcon, FluentIconBase) and (self_btn.isSelected or self_btn.isAboutSelected):
                color = autoFallbackThemeColor(self_btn.lightSelectedColor, self_btn.darkSelectedColor)
                selectedIcon.render(painter, rect, fill=color.name())
            elif self_btn.isSelected or self_btn.isAboutSelected:
                drawIcon(selectedIcon, painter, rect)
            else:
                drawIcon(self_btn._icon, painter, rect)
        
        def _custom_indicatorRect(self_btn):
            """Adjust indicator position for wider/taller buttons."""
            return QRectF(0, 18, 4, 30)
        
        # Resize all navigation buttons and monkey-patch their draw methods
        for button in self.navigationInterface.findChildren(NavigationBarPushButton):
            button.setFixedSize(98, 76)
            # Bind methods
            import types
            button._drawText = types.MethodType(_custom_drawText, button)
            button._drawIcon = types.MethodType(_custom_drawIcon, button)
            button.indicatorRect = types.MethodType(_custom_indicatorRect, button)

    def _update_status(self):
        # Update the main window title for status
        employees = db.get_all_employees()
        active_leaves = db.get_active_sick_leaves()
        year = db.get_setting('school_year', '2025/2026')
        
        title = f"نظام تسيير الموظفين  —  إجمالي الموظفين: {len(employees)}  |  عطل مرضية جارية: {len(active_leaves)}  |  السنة الدراسية: {year}"
        self.setWindowTitle(title)

    # ── Excel Operations ──
    def _import_excel(self):
        msg = ("يمكنك استيراد قاعدة بيانات الموظفين من الملفات التالية:\n"
               "1. ملف وزارة التربية الوطنية المتواجد في الرقمنة (.xls)\n"
               "2. ملف بيانات المستخدمين (سالمي طاهر) (.xlsx)\n"
               "3. ملف بطاقة المعلومات للمستخدمين (سالمي طاهر) (.xlsx)\n"
               "سيقوم البرنامج بتحديث الموظفين الموجودين بناءً على الرقم الوظيفي آلياً\n")
        reply = QMessageBox.information(
            self, "تعليمات استيراد الإكسل", msg, QMessageBox.Ok | QMessageBox.Cancel
        )
        if reply == QMessageBox.Cancel:
            return
            
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

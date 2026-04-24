# -*- coding: utf-8 -*-
"""
Inquiry Dialog — Premium dialog for employee inquiries.
Dynamic form adapts based on the selected reason type.
Uses stacked label-above-field layout for proper RTL full-width fields.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTextEdit, QCheckBox, QWidget, QGraphicsDropShadowEffect,
    QSizePolicy, QTimeEdit, QScrollArea, QApplication, QGridLayout,
    QMessageBox, QComboBox,
)
from PyQt5.QtCore import Qt, QDate, QTime, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QColor

from ui.widgets import (
    ArabicLineEdit, ArabicLabel, ArabicDateEdit,
    ActionButton, Separator,
)
import database as db
from datetime import datetime

INQUIRY_REFERENCES = [
    "ملاحظات المدير",
    "المصلحة البيداغوجية",
    "المصلحة الاقتصادية",
]


INQUIRY_REASONS = [
    "\u063a\u064a\u0627\u0628",
    "\u062a\u0623\u062e\u0631",
    "\u0639\u062f\u0645 \u062a\u0623\u062f\u064a\u0629 \u0645\u0647\u0627\u0645 \u0645\u0648\u0643\u0644\u0629 \u0644\u0644\u0645\u0648\u0638\u0641",
]

REASON_ICONS = {
    "\u063a\u064a\u0627\u0628": "\U0001f6ab",
    "\u062a\u0623\u062e\u0631": "\u23f0",
    "\u0639\u062f\u0645 \u062a\u0623\u062f\u064a\u0629 \u0645\u0647\u0627\u0645 \u0645\u0648\u0643\u0644\u0629 \u0644\u0644\u0645\u0648\u0638\u0641": "\U0001f4cb",
}

REASON_COLORS = {
    "\u063a\u064a\u0627\u0628": {"bg": "#fef2f2", "border": "#fecaca", "text": "#b91c1c", "accent": "#dc2626"},
    "\u062a\u0623\u062e\u0631": {"bg": "#fffbeb", "border": "#fde68a", "text": "#92400e", "accent": "#d97706"},
    "\u0639\u062f\u0645 \u062a\u0623\u062f\u064a\u0629 \u0645\u0647\u0627\u0645 \u0645\u0648\u0643\u0644\u0629 \u0644\u0644\u0645\u0648\u0638\u0641": {"bg": "#eff6ff", "border": "#bfdbfe", "text": "#1e40af", "accent": "#3b82f6"},
}

FIELD_LABEL_STYLE = "font-size: 13px; font-weight: bold; color: #475569; background: transparent; margin-bottom: 2px;"


class AnimatedContainer(QWidget):
    """A widget that can smoothly animate its height for show/hide transitions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_height = 0
        self.setMaximumHeight(0)
        self._animation = QPropertyAnimation(self, b"maximumHeight")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

    def show_animated(self):
        self.show()
        self._animation.stop()
        self._animation.setStartValue(self.maximumHeight())
        self._animation.setEndValue(self._target_height)
        self._animation.start()

    def hide_animated(self):
        self._animation.stop()
        self._animation.setStartValue(self.maximumHeight())
        self._animation.setEndValue(0)
        self._animation.start()

    def set_target_height(self, h):
        self._target_height = h


def _field_group(label_text, widget):
    """Create a label-above-field group that spans full width."""
    box = QVBoxLayout()
    box.setSpacing(4)
    box.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(label_text)
    lbl.setStyleSheet(FIELD_LABEL_STYLE)
    lbl.setAlignment(Qt.AlignRight)
    widget.setMinimumHeight(38)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    box.addWidget(lbl)
    box.addWidget(widget)
    return box


class InquiryDialog(QDialog):
    """Premium dialog for creating an official inquiry for an employee."""

    def __init__(self, employee, parent=None):
        super().__init__(parent)
        self.employee = employee
        emp_name = db.get_employee_full_name(employee)
        self.setWindowTitle("\u0627\u0633\u062a\u0641\u0633\u0627\u0631 \u2014 %s" % emp_name)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumWidth(560)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 10)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setLayoutDirection(Qt.RightToLeft)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setLayoutDirection(Qt.RightToLeft)
        lay = QVBoxLayout(content)
        lay.setSpacing(10)
        lay.setContentsMargins(20, 16, 20, 8)

        # ── Header ──
        emp_name = db.get_employee_full_name(self.employee)
        header = QLabel("\U0001f4dd \u0627\u0633\u062a\u0641\u0633\u0627\u0631 \u0645\u0648\u0638\u0641")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        lay.addWidget(header)

        emp_grade = self.employee["grade"] or ""
        info = ArabicLabel("\u0627\u0644\u0645\u0648\u0638\u0641(\u0629): %s  |  \u0627\u0644\u0631\u062a\u0628\u0629: %s" % (emp_name, emp_grade))
        info.setObjectName("badge_info")
        lay.addWidget(info)
        lay.addWidget(Separator())

        # ── Reference Selector (مرجع الاستفسار) — mandatory ──
        ref_lbl = QLabel("📌 مرجع الاستفسار *")
        ref_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        lay.addWidget(ref_lbl)

        self.reference_combo = QComboBox()
        self.reference_combo.setLayoutDirection(Qt.RightToLeft)
        self.reference_combo.setMinimumHeight(38)
        self.reference_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: bold;
                color: #374151;
                background: #f8fafc;
            }
            QComboBox:focus { border-color: #3b82f6; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { border: 1px solid #cbd5e1; border-radius: 4px; }
        """)
        # Empty placeholder (mandatory — no default value)
        self.reference_combo.addItem("-- اختر مرجع الاستفسار --", None)
        for ref in INQUIRY_REFERENCES:
            self.reference_combo.addItem(ref, ref)
        lay.addWidget(self.reference_combo)

        # ── Report Date ──
        date_lbl = QLabel("📅 تاريخ التقرير *")
        date_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        lay.addWidget(date_lbl)

        self.report_date = ArabicDateEdit()
        self.report_date.setDate(QDate.currentDate())
        lay.addWidget(self.report_date)

        lay.addWidget(Separator())

        # ── Reason Selector ──
        reason_lbl = QLabel("\u26a1 \u0633\u0628\u0628 \u0627\u0644\u0627\u0633\u062a\u0641\u0633\u0627\u0631")
        reason_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        lay.addWidget(reason_lbl)

        reason_row = QHBoxLayout()
        reason_row.setSpacing(8)
        self.reason_cards = []
        for reason in INQUIRY_REASONS:
            card = self._create_reason_card(reason)
            reason_row.addWidget(card)
            self.reason_cards.append(card)
        lay.addLayout(reason_row)

        # ══════════════════════════════════════════════
        # ABSENCE CONTAINER
        # ══════════════════════════════════════════════
        self.absence_container = AnimatedContainer()
        self.absence_container.set_target_height(200)
        ac = QVBoxLayout(self.absence_container)
        ac.setContentsMargins(0, 8, 0, 0)
        ac.setSpacing(8)

        ah = QLabel("\U0001f6ab \u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u063a\u064a\u0627\u0628")
        ah.setStyleSheet("font-size: 13px; font-weight: bold; color: #b91c1c; background: transparent;")
        ac.addWidget(ah)

        # Date + Full day in a row
        abs_row = QHBoxLayout()
        abs_row.setSpacing(16)

        self.absence_date = ArabicDateEdit()
        abs_row.addLayout(_field_group("\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u063a\u064a\u0627\u0628:", self.absence_date), stretch=1)

        self.full_day_check = QCheckBox("\u064a\u0648\u0645 \u0643\u0627\u0645\u0644")
        self.full_day_check.setLayoutDirection(Qt.RightToLeft)
        self.full_day_check.setChecked(True)
        self.full_day_check.setStyleSheet("""
            QCheckBox { font-size: 14px; font-weight: bold; color: #374151; spacing: 8px; background: transparent; padding-top: 20px; }
            QCheckBox::indicator { width: 22px; height: 22px; border-radius: 4px; border: 2px solid #cbd5e1; }
            QCheckBox::indicator:checked { background-color: #3b82f6; border-color: #3b82f6; }
        """)
        self.full_day_check.toggled.connect(self._on_full_day_toggled)
        abs_row.addWidget(self.full_day_check)
        ac.addLayout(abs_row)

        # Duration (hidden by default when full day is checked)
        self.absence_duration = ArabicLineEdit("\u0645\u062f\u0629 \u0627\u0644\u063a\u064a\u0627\u0628 (\u0645\u062b\u0627\u0644: \u0633\u0627\u0639\u062a\u0627\u0646)")
        self.absence_duration_label = QLabel("\u0645\u062f\u0629 \u0627\u0644\u063a\u064a\u0627\u0628:")
        self.absence_duration_label.setStyleSheet(FIELD_LABEL_STYLE)
        self.absence_duration.setMinimumHeight(38)
        self.absence_duration.setVisible(False)
        self.absence_duration_label.setVisible(False)
        ac.addWidget(self.absence_duration_label)
        ac.addWidget(self.absence_duration)

        lay.addWidget(self.absence_container)

        # ══════════════════════════════════════════════
        # LATENESS CONTAINER
        # ══════════════════════════════════════════════
        self.lateness_container = AnimatedContainer()
        self.lateness_container.set_target_height(200)
        lc = QVBoxLayout(self.lateness_container)
        lc.setContentsMargins(0, 8, 0, 0)
        lc.setSpacing(8)

        lh = QLabel("\u23f0 \u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u062a\u0623\u062e\u0631")
        lh.setStyleSheet("font-size: 13px; font-weight: bold; color: #92400e; background: transparent;")
        lc.addWidget(lh)

        # Date + Time in a row
        late_row1 = QHBoxLayout()
        late_row1.setSpacing(16)

        self.lateness_date = ArabicDateEdit()
        late_row1.addLayout(_field_group("\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u062a\u0623\u062e\u0631:", self.lateness_date), stretch=1)

        self.lateness_time = QTimeEdit()
        self.lateness_time.setLayoutDirection(Qt.RightToLeft)
        self.lateness_time.setDisplayFormat("HH:mm")
        self.lateness_time.setTime(QTime(8, 0))
        late_row1.addLayout(_field_group("\u0648\u0642\u062a \u0627\u0644\u062a\u0623\u062e\u0631:", self.lateness_time), stretch=1)

        lc.addLayout(late_row1)

        # Duration full width
        self.lateness_duration = ArabicLineEdit("\u0645\u062f\u0629 \u0627\u0644\u062a\u0623\u062e\u0631 (\u0645\u062b\u0627\u0644: 30 \u062f\u0642\u064a\u0642\u0629)")
        lc.addLayout(_field_group("\u0645\u062f\u0629 \u0627\u0644\u062a\u0623\u062e\u0631:", self.lateness_duration))

        lay.addWidget(self.lateness_container)

        # ══════════════════════════════════════════════
        # TASK FAILURE CONTAINER
        # ══════════════════════════════════════════════
        self.task_container = AnimatedContainer()
        self.task_container.set_target_height(170)
        tc = QVBoxLayout(self.task_container)
        tc.setContentsMargins(0, 8, 0, 0)
        tc.setSpacing(6)

        th = QLabel("\U0001f4cb \u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u0645\u0647\u0627\u0645")
        th.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e40af; background: transparent;")
        tc.addWidget(th)

        tdl = QLabel("\u0648\u0635\u0641 \u0627\u0644\u0645\u0647\u0627\u0645 \u0627\u0644\u062a\u064a \u0644\u0645 \u064a\u062a\u0645 \u062a\u0623\u062f\u064a\u062a\u0647\u0627:")
        tdl.setStyleSheet("font-size: 12px; color: #64748b; background: transparent;")
        tc.addWidget(tdl)

        self.task_description = QTextEdit()
        self.task_description.setLayoutDirection(Qt.RightToLeft)
        self.task_description.setPlaceholderText(
            "\u0627\u0643\u062a\u0628 \u0647\u0646\u0627 \u0648\u0635\u0641\u0627\u064b \u0645\u0641\u0635\u0644\u0627\u064b \u0644\u0644\u0645\u0647\u0627\u0645..."
        )
        self.task_description.setMinimumHeight(80)
        self.task_description.setMaximumHeight(110)
        tc.addWidget(self.task_description)
        lay.addWidget(self.task_container)

        # ══════════════════════════════════════════════
        # ADDITIONAL NOTES
        # ══════════════════════════════════════════════
        nlbl = QLabel("\u0645\u0644\u0627\u062d\u0638\u0627\u062a \u0625\u0636\u0627\u0641\u064a\u0629 (\u0627\u062e\u062a\u064a\u0627\u0631\u064a):")
        nlbl.setStyleSheet("font-size: 12px; color: #64748b; margin-top: 4px;")
        lay.addWidget(nlbl)

        self.additional_notes = QTextEdit()
        self.additional_notes.setLayoutDirection(Qt.RightToLeft)
        self.additional_notes.setPlaceholderText("\u0623\u064a \u0645\u0644\u0627\u062d\u0638\u0627\u062a \u0625\u0636\u0627\u0641\u064a\u0629...")
        self.additional_notes.setMinimumHeight(50)
        self.additional_notes.setMaximumHeight(65)
        lay.addWidget(self.additional_notes)

        scroll.setWidget(content)
        main_layout.addWidget(scroll, stretch=1)

        # ── Buttons — OUTSIDE scroll ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setContentsMargins(20, 4, 20, 0)

        preview_btn = ActionButton("\u0645\u0639\u0627\u064a\u0646\u0629 \u0648\u0637\u0628\u0627\u0639\u0629", "\U0001f5a8\ufe0f", "primary")
        preview_btn.setMinimumHeight(42)
        preview_btn.clicked.connect(self._preview_print)

        cancel_btn = ActionButton("\u0625\u0644\u063a\u0627\u0621", "\u2716", "outline")
        cancel_btn.setMinimumHeight(42)
        cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # Limit height
        screen = QApplication.primaryScreen()
        if screen:
            self.setMaximumHeight(int(screen.availableGeometry().height() * 0.82))

        # Default selection
        self._selected_reason = None
        self._select_reason("\u063a\u064a\u0627\u0628")

    # ──────────────────────────────────────────────
    # Reason card creation & selection
    # ──────────────────────────────────────────────
    def _create_reason_card(self, reason):
        colors = REASON_COLORS[reason]
        icon = REASON_ICONS[reason]

        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        card.setProperty("reason", reason)
        card.setFixedHeight(52)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        cl = QHBoxLayout(card)
        cl.setContentsMargins(8, 4, 8, 4)
        cl.setSpacing(6)

        il = QLabel(icon)
        il.setFixedWidth(24)
        il.setAlignment(Qt.AlignCenter)
        il.setStyleSheet("font-size: 16px; background: transparent;")
        cl.addWidget(il)

        tl = QLabel(reason)
        tl.setWordWrap(True)
        tl.setStyleSheet("font-size: 11px; font-weight: bold; color: %s; background: transparent;" % colors["text"])
        cl.addWidget(tl, stretch=1)

        card._icon_label = il
        card._text_label = tl
        card.setStyleSheet("""
            QFrame { background-color: #f8fafc; border: 2px solid #e5e7eb; border-radius: 10px; }
            QFrame:hover { border-color: %s; background-color: %s; }
        """ % (colors["border"], colors["bg"]))

        card.mousePressEvent = lambda event, r=reason: self._select_reason(r)
        return card

    def _select_reason(self, reason):
        self._selected_reason = reason
        for card in self.reason_cards:
            r = card.property("reason")
            colors = REASON_COLORS[r]
            if r == reason:
                card.setStyleSheet("QFrame { background-color: %s; border: 2px solid %s; border-radius: 10px; }" % (colors["bg"], colors["accent"]))
                card._text_label.setStyleSheet("font-size: 11px; font-weight: bold; color: %s; background: transparent;" % colors["accent"])
            else:
                card.setStyleSheet("QFrame { background-color: #f8fafc; border: 2px solid #e5e7eb; border-radius: 10px; } QFrame:hover { border-color: %s; background-color: %s; }" % (colors["border"], colors["bg"]))
                card._text_label.setStyleSheet("font-size: 11px; font-weight: bold; color: %s; background: transparent;" % colors["text"])

        if reason == "\u063a\u064a\u0627\u0628":
            self.absence_container.show_animated()
            self.lateness_container.hide_animated()
            self.task_container.hide_animated()
        elif reason == "\u062a\u0623\u062e\u0631":
            self.absence_container.hide_animated()
            self.lateness_container.show_animated()
            self.task_container.hide_animated()
        else:
            self.absence_container.hide_animated()
            self.lateness_container.hide_animated()
            self.task_container.show_animated()

    def _on_full_day_toggled(self, checked):
        self.absence_duration.setVisible(not checked)
        self.absence_duration_label.setVisible(not checked)

    # ──────────────────────────────────────────────
    # Data helpers
    # ──────────────────────────────────────────────
    def _get_reason_details(self):
        reason = self._selected_reason
        if reason == "\u063a\u064a\u0627\u0628":
            d = self.absence_date.date().toString("yyyy/MM/dd")
            if self.full_day_check.isChecked():
                return "\u063a\u064a\u0627\u0628 \u064a\u0648\u0645 \u0643\u0627\u0645\u0644 \u0628\u062a\u0627\u0631\u064a\u062e: %s" % d
            else:
                dur = self.absence_duration.text().strip() or "\u063a\u064a\u0631 \u0645\u062d\u062f\u062f"
                return "\u063a\u064a\u0627\u0628 \u0628\u062a\u0627\u0631\u064a\u062e: %s\u060c \u0627\u0644\u0645\u062f\u0629: %s" % (d, dur)
        elif reason == "\u062a\u0623\u062e\u0631":
            d = self.lateness_date.date().toString("yyyy/MM/dd")
            t = self.lateness_time.time().toString("HH:mm")
            dur = self.lateness_duration.text().strip() or "\u063a\u064a\u0631 \u0645\u062d\u062f\u062f"
            return "\u062a\u0623\u062e\u0631 \u0628\u062a\u0627\u0631\u064a\u062e: %s\u060c \u0627\u0644\u0648\u0642\u062a: %s\u060c \u0627\u0644\u0645\u062f\u0629: %s" % (d, t, dur)
        else:
            txt = self.task_description.toPlainText().strip() or "المهام الموكلة"
            return txt

    # ──────────────────────────────────────────────
    # HTML Document Generation
    # ──────────────────────────────────────────────
    def _generate_html(self):
        emp = self.employee
        settings = db.get_all_settings()

        school = db.get_formatted_school_name()
        wilaya = settings.get("wilaya", "")
        director = settings.get("director_name", "")
        school_year = settings.get("school_year", "2025/2026")

        emp_name = db.get_employee_full_name(emp)
        emp_grade = emp["grade"] or "\u0640\u0640\u0640\u0640\u0640\u0640"
        emp_subject = emp["subject"] or ""
        today = datetime.now().strftime("%Y/%m/%d")

        reason = self._selected_reason
        reason_details = self._get_reason_details()
        additional = self.additional_notes.toPlainText().strip()
        additional_line = ""
        if additional:
            additional_line = "<br/>\u0645\u0644\u0627\u062d\u0638\u0629: <b>%s</b>" % additional

        subject_line = ""
        if emp_subject:
            subject_line = "\u060c \u0645\u0627\u062f\u0629: <b>%s</b>" % emp_subject

        if reason == "\u063a\u064a\u0627\u0628":
            reason_paragraph = """
                <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right; text-indent: 40px;">
                    \u0646\u0639\u0644\u0645\u0643\u0645 \u0623\u0646\u0647 \u0628\u0646\u0627\u0621 \u0639\u0644\u0649 \u0633\u062c\u0644 \u0627\u0644\u062d\u0636\u0648\u0631 \u0628\u0627\u0644\u0645\u0624\u0633\u0633\u0629 \u0627\u0644\u0623\u0633\u062a\u0627\u0630(\u0629) : <b>%(en)s</b>\u060c 
                    \u0628\u0635\u0641\u062a\u0647(\u0647\u0627): <b>%(eg)s</b>%(sl)s\u060c
                    \u062a\u063a\u064a\u0628(\u062a) \u0639\u0646 \u0645\u0646\u0635\u0628 \u0639\u0645\u0644\u0647(\u0647\u0627) <b>%(rd)s</b>
                    \u0628\u062f\u0648\u0646 \u0645\u0628\u0631\u0631 \u0645\u0642\u0628\u0648\u0644 \u0648\u0644\u0627 \u0625\u0630\u0646 \u0645\u0633\u0628\u0642.
                </p>
            """
        elif reason == "\u062a\u0623\u062e\u0631":
            reason_paragraph = """
                <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right; text-indent: 40px;">
                    \u0646\u0639\u0644\u0645\u0643\u0645 \u0623\u0646\u0647 \u0628\u0646\u0627\u0621 \u0639\u0644\u0649 \u0633\u062c\u0644 \u0627\u0644\u062d\u0636\u0648\u0631 \u0628\u0627\u0644\u0645\u0624\u0633\u0633\u0629 \u0627\u0644\u0623\u0633\u062a\u0627\u0630(\u0629) : <b>%(en)s</b>\u060c 
                    \u0628\u0635\u0641\u062a\u0647(\u0647\u0627): <b>%(eg)s</b>%(sl)s\u060c
                    \u0627\u0644\u0645\u0639\u0646\u064a(\u0629) \u0628\u0627\u0644\u0623\u0645\u0631 \u0642\u062f \u062a\u0623\u062e\u0631(\u062a) \u0639\u0646 \u0627\u0644\u0627\u0644\u062a\u062d\u0627\u0642 \u0628\u0645\u0646\u0635\u0628 \u0639\u0645\u0644\u0647(\u0647\u0627)\u060c <b>%(rd)s</b>.
                </p>
            """
        else:
            reason_paragraph = """
                <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right; text-indent: 40px;">
                    \u0646\u0639\u0644\u0645\u0643\u0645 \u0623\u0646\u0647 \u062a\u0645 \u0645\u0644\u0627\u062d\u0638\u0629 \u0623\u0646 \u0627\u0644\u0623\u0633\u062a\u0627\u0630(\u0629) : <b>%(en)s</b>\u060c 
                    \u0628\u0635\u0641\u062a\u0647(\u0647\u0627): <b>%(eg)s</b>%(sl)s\u060c
                    \u0644\u0645 \u064a\u0642\u0645 (\u062a\u0642\u0645) \u0628\u062a\u0623\u062f\u064a\u0629 \u0627\u0644\u0645\u0647\u0627\u0645 \u0627\u0644\u0645\u0648\u0643\u0644\u0629 \u0625\u0644\u064a\u0647(\u0647\u0627) \u0639\u0644\u0649 \u0623\u0643\u0645\u0644 \u0648\u062c\u0647.
                    <br/>\u062a\u0641\u0627\u0635\u064a\u0644 \u0627\u0644\u0645\u0647\u0627\u0645: <b>%(rd)s</b>
                </p>
            """

        reason_paragraph = reason_paragraph % {"en": emp_name, "eg": emp_grade, "sl": subject_line, "rd": reason_details}

        html = """
        <html dir="rtl">
        <head><style>
            body { font-family: 'Amiri', 'Traditional Arabic', serif;
                   direction: rtl; text-align: right; margin: 30px; line-height: 1.8; }
            h2 { text-align: center; color: #000; margin: 20px 0; font-weight: bold; }
        </style></head>
        <body dir="rtl">
            <div style="text-align:center; margin-bottom: 8px; font-weight: bold;">
                <div style="font-size:16px;">\u0627\u0644\u062c\u0645\u0647\u0648\u0631\u064a\u0629 \u0627\u0644\u062c\u0632\u0627\u0626\u0631\u064a\u0629 \u0627\u0644\u062f\u064a\u0645\u0642\u0631\u0627\u0637\u064a\u0629 \u0627\u0644\u0634\u0639\u0628\u064a\u0629</div>
                <div style="font-size:14px;">\u0648\u0632\u0627\u0631\u0629 \u0627\u0644\u062a\u0631\u0628\u064a\u0629 \u0627\u0644\u0648\u0637\u0646\u064a\u0629</div>
            </div>
            <table dir="rtl" width="100%%%%" style="font-weight: bold; font-size: 14px; margin-bottom: 10px;">
                <tr>
                    <td style="text-align:right; width:50%%%%;">
                        \u0645\u062f\u064a\u0631\u064a\u0629 \u0627\u0644\u062a\u0631\u0628\u064a\u0629 \u0644\u0648\u0644\u0627\u064a\u0629 %(wilaya)s<br/>%(school)s
                    </td>
                    <td style="text-align:left; width:50%%%%;">
                        \u0627\u0644\u0633\u0646\u0629 \u0627\u0644\u062f\u0631\u0627\u0633\u064a\u0629: %(school_year)s
                    </td>
                </tr>
            </table>
            <hr style="border:1px solid #333;"/>
            <h2 style="font-size: 28px; text-decoration: underline;">\u0627\u0633\u0640\u062a\u0640\u0641\u0640\u0633\u0640\u0627\u0631</h2>
            <table dir="rtl" width="100%%%%" style="font-size: 16px; font-weight: bold; margin-bottom: 10px;">
                <tr>
                    <td style="text-align:right; width:100%%%%;">
                        \u0625\u0644\u0649 \u0627\u0644\u0633\u064a\u062f(\u0629): <b>%(emp_name)s</b><br/>
                        \u0627\u0644\u0631\u062a\u0628\u0629: <b>%(emp_grade)s</b>%(subject_line)s<br/>
                        \u0628\u0645\u0624\u0633\u0633\u0629: <b>%(school)s</b>
                    </td>
                </tr>
            </table>
            <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right;">
                <u>\u0627\u0644\u0645\u0648\u0636\u0648\u0639:</u> \u0627\u0633\u062a\u0641\u0633\u0627\u0631 \u0628\u0633\u0628\u0628 <b>%(reason)s</b>
            </p>
            %(reason_paragraph)s
            <p style="font-size:16px; line-height:2; font-weight:bold; text-align: right; text-indent: 40px;">
                \u0644\u0630\u0644\u0643 \u0646\u0637\u0644\u0628 \u0645\u0646\u0643\u0645 \u062a\u0642\u062f\u064a\u0645 \u062a\u0628\u0631\u064a\u0631\u0627\u062a\u0643\u0645 \u0648\u062a\u0648\u0636\u064a\u062d\u0627\u062a\u0643\u0645 \u0643\u062a\u0627\u0628\u064a\u0627\u064b
                \u0641\u064a \u0623\u062c\u0644 \u0623\u0642\u0635\u0627\u0647 <b>48 \u0633\u0627\u0639\u0629</b> \u0645\u0646 \u062a\u0627\u0631\u064a\u062e \u0627\u0633\u062a\u0644\u0627\u0645 \u0647\u0630\u0627 \u0627\u0644\u0627\u0633\u062a\u0641\u0633\u0627\u0631.%(additional_line)s
            </p>
            <p style="font-size:14px; line-height:2; font-weight:bold; text-align: right; margin-top: 20px;">
                \u26a0\ufe0f \u0646\u0630\u0643\u0631\u0643\u0645 \u0628\u0623\u0646 \u0639\u062f\u0645 \u0627\u0644\u0631\u062f \u0641\u064a \u0627\u0644\u0622\u062c\u0627\u0644 \u0627\u0644\u0645\u062d\u062f\u062f\u0629 \u064a\u0639\u062a\u0628\u0631 \u0642\u0628\u0648\u0644\u0627\u064b \u0644\u0644\u0645\u062e\u0627\u0644\u0641\u0629 \u0627\u0644\u0645\u0646\u0633\u0648\u0628\u0629 \u0625\u0644\u064a\u0643\u0645.
            </p>
            <br/><br/>
            <table width="100%%%%" dir="rtl" style="margin-top: 20px;">
                <tr>
                    <td style="text-align:left; width:50%%%%;">
                        <div style="font-size:16px; font-weight:bold;">
                            %(wilaya)s \u0641\u064a: %(today)s<br/>\u0627\u0644\u0645\u062f\u064a\u0631(\u0629)<br/><br/><br/>
                        </div>
                    </td>
                    <td style="text-align:right; width:50%%%%;">
                        <div style="font-size:16px; font-weight:bold;">
                            \u0625\u0645\u0636\u0627\u0621 \u0627\u0644\u0645\u0639\u0646\u064a(\u0629) \u0628\u0627\u0644\u0623\u0645\u0631<br/><br/><br/>
                        </div>
                    </td>
                </tr>
            </table>
        </body></html>
        """ % {
            "wilaya": wilaya, "school": school, "school_year": school_year,
            "emp_name": emp_name, "emp_grade": emp_grade, "subject_line": subject_line,
            "reason": reason, "reason_paragraph": reason_paragraph,
            "additional_line": additional_line, "today": today, "director": director,
        }
        return html

    def _preview_print(self):
        # Validate mandatory reference field
        selected_ref = self.reference_combo.currentData()
        if not selected_ref:
            QMessageBox.warning(
                self, "تنبيه",
                "يرجى اختيار مرجع الاستفسار؟\n(ملاحظات المدير • المصلحة البيداغوجية • المصلحة الاقتصادية)"
            )
            return

        reason = self._selected_reason
        details = self._get_reason_details()

        # Save inquiry to database
        inquiry_data = {
            "employee_id": self.employee["id"],
            "inquiry_type": reason,
            "inquiry_date": datetime.now().strftime("%Y-%m-%d"),
            "inquiry_time": datetime.now().strftime("%H:%M"),
            "details": details,
            "additional_notes": self.additional_notes.toPlainText().strip(),
            "status": "معلّق",
            "inquiry_reference": selected_ref,
            "report_date": self.report_date.date().toString("yyyy-MM-dd")
        }
        inq_id = db.add_inquiry(inquiry_data)

        # Also add a corresponding absence record so it appears in the Absences page
        if reason == "غياب":
            absence_date = self.absence_date.date().toString("yyyy-MM-dd")
            if self.full_day_check.isChecked():
                duration = "يوم كامل"
                absence_time = ""
            else:
                duration = self.absence_duration.text().strip() or "غير محدد"
                absence_time = ""
            absence_data = {
                "employee_id": self.employee["id"],
                "absence_type": "غياب",
                "absence_date": absence_date,
                "absence_time": absence_time,
                "duration": duration,
                "is_justified": 0,
                "justification": "",
                "director_decision": "",
                "salary_deduction": "",
                "performance_deduction": "",
                "notes": self.additional_notes.toPlainText().strip(),
            }
            db.add_absence(absence_data)
        elif reason == "تأخر":
            absence_date = self.lateness_date.date().toString("yyyy-MM-dd")
            absence_time = self.lateness_time.time().toString("HH:mm")
            duration = self.lateness_duration.text().strip() or "غير محدد"
            absence_data = {
                "employee_id": self.employee["id"],
                "absence_type": "تأخر",
                "absence_date": absence_date,
                "absence_time": absence_time,
                "duration": duration,
                "is_justified": 0,
                "justification": "",
                "director_decision": "",
                "salary_deduction": "",
                "performance_deduction": "",
                "notes": self.additional_notes.toPlainText().strip(),
            }
            db.add_absence(absence_data)

        # Use the new official template from InquiriesPage
        from ui.inquiries_page import InquiriesPage
        inquiry = db.get_inquiry(inq_id)
        settings = db.get_all_settings()
        # Build a temporary InquiriesPage instance just to call the html generator
        # (no parent/window needed, we call the method directly)
        html = InquiriesPage._generate_inquiry_html(None, inquiry, self.employee, settings)

        from pdf_generator_v2 import AdvancedPdfPreviewDialog
        dialog = AdvancedPdfPreviewDialog(html_content=html, parent=self, landscape=True)
        dialog.exec_()
        self.accept()



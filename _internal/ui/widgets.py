# -*- coding: utf-8 -*-
"""
Custom RTL Arabic Widgets — Premium Material Design components.
Uses qtawesome Material Design icons instead of emoji.
"""

from PyQt5.QtWidgets import (
    QLineEdit, QLabel, QComboBox, QDateEdit, QFrame,
    QHBoxLayout, QVBoxLayout, QFormLayout, QPushButton,
    QWidget, QGraphicsDropShadowEffect, QSizePolicy,
    QScrollArea, QToolButton, QGraphicsOpacityEffect,
)
from PyQt5.QtCore import (
    Qt, QDate, pyqtSignal, QPropertyAnimation, QEasingCurve, 
    QSize, QTimer, QParallelAnimationGroup, QSequentialAnimationGroup
)
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QIcon

from ui.icons import get_icon, get_colored_icon, ICON_COLORS


class ArabicLineEdit(QLineEdit):
    """Line edit with RTL alignment and Arabic placeholder."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setLayoutDirection(Qt.RightToLeft)
        if placeholder:
            self.setPlaceholderText(placeholder)


class ArabicLabel(QLabel):
    """Label with RTL alignment."""

    def __init__(self, text="", parent=None, object_name=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setLayoutDirection(Qt.RightToLeft)
        if object_name:
            self.setObjectName(object_name)


class ArabicComboBox(QComboBox):
    """ComboBox with RTL layout."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)


class ArabicDateEdit(QDateEdit):
    """Date edit with RTL layout and Arabic date format."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy/MM/dd")
        self.setDate(QDate.currentDate())


class ArabicFormLayout(QFormLayout):
    """Form layout with labels on the right side (RTL)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setFormAlignment(Qt.AlignRight | Qt.AlignTop)
        self.setHorizontalSpacing(16)
        self.setVerticalSpacing(14)


class Card(QFrame):
    """A styled card frame with optional drop shadow."""

    def __init__(self, parent=None, shadow=True):
        super().__init__(parent)
        self.setObjectName("card")
        self.setLayoutDirection(Qt.RightToLeft)

        if shadow:
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(24)
            effect.setXOffset(0)
            effect.setYOffset(4)
            effect.setColor(QColor(0, 0, 0, 40))
            self.setGraphicsEffect(effect)


class StatCard(QFrame):
    """A statistics card with Material icon, value, and label."""

    def __init__(self, title, value, icon_name="", variant="blue", parent=None):
        super().__init__(parent)
        self.setObjectName("stat_card_%s" % variant)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        # Icon + Value row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        if icon_name:
            color_map = {
                "blue": "#1d4ed8",
                "green": "#047857",
                "amber": "#b45309",
                "red": "#b91c1c",
            }
            icon_color = color_map.get(variant, "#1d4ed8")
            icon_label = QLabel()
            icon_label.setPixmap(get_icon(icon_name, color=icon_color).pixmap(28, 28))
            icon_label.setFixedSize(32, 32)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setStyleSheet("background: transparent;")
            top_row.addWidget(icon_label)

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("stat_value")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.value_label.setLayoutDirection(Qt.RightToLeft)

        color_map = {
            "blue": "#1d4ed8",
            "green": "#047857",
            "amber": "#b45309",
            "red": "#b91c1c",
        }
        color = color_map.get(variant, "#1d4ed8")
        self.value_label.setStyleSheet(
            "color: %s; font-size: 24px; font-weight: bold; background: transparent;" % color
        )

        top_row.addWidget(self.value_label)
        top_row.addStretch()
        layout.addLayout(top_row)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("stat_label")
        self.title_label.setAlignment(Qt.AlignRight)
        self.title_label.setStyleSheet("font-size: 12px; color: #6b7280; background: transparent;")
        layout.addWidget(self.title_label)

        # Shadow
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(20)
        effect.setXOffset(0)
        effect.setYOffset(3)
        effect.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(effect)

    def set_value(self, value):
        self.value_label.setText(str(value))


class SidebarButton(QPushButton):
    """A navigation button for the sidebar with Material Design icon."""

    def __init__(self, text, icon_name="", parent=None):
        super().__init__(parent)
        self.setObjectName("nav_btn")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setMinimumHeight(56)
        
        self._text = text
        self._icon_name = icon_name
        self._active = False
        
        # Set text and icon
        self.setText("  " + text)
        if icon_name:
            icon = get_icon(icon_name, color=ICON_COLORS["sidebar"])
            self.setIcon(icon)
            self.setIconSize(QSize(22, 22))
    
    def setChecked(self, checked):
        super().setChecked(checked)
        self._active = checked
        if self._icon_name:
            color = ICON_COLORS["sidebar_active"] if checked else ICON_COLORS["sidebar"]
            icon = get_icon(self._icon_name, color=color)
            self.setIcon(icon)


class SearchBar(QWidget):
    """A search bar with Material Design icon."""

    search_changed = pyqtSignal(str)

    def __init__(self, placeholder="بحث...", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
            }
            QFrame:focus-within {
                border-color: #3b82f6;
            }
        """)

        inner = QHBoxLayout(container)
        inner.setContentsMargins(14, 0, 8, 0)
        inner.setSpacing(8)

        icon_label = QLabel()
        icon_label.setPixmap(get_icon("search", color="#9ca3af").pixmap(20, 20))
        icon_label.setFixedWidth(28)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        inner.addWidget(icon_label)

        self.search_input = QLineEdit()
        self.search_input.setAlignment(Qt.AlignRight)
        self.search_input.setLayoutDirection(Qt.RightToLeft)
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: none;
                background: transparent;
                padding: 10px 4px;
                font-size: 14px;
                color: #111827;
            }
        """)
        self.search_input.textChanged.connect(self.search_changed.emit)
        inner.addWidget(self.search_input)

        layout.addWidget(container)

    def text(self):
        return self.search_input.text()

    def clear(self):
        self.search_input.clear()


class ActionButton(QPushButton):
    """Styled action button with Material Design icon."""

    def __init__(self, text, icon_name="", variant="primary", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._set_variant(variant)
        
        icon_color_map = {
            "primary": "#ffffff", "danger": "#ffffff", "success": "#ffffff",
            "warning": "#ffffff", "outline": "#3b82f6", "ghost": "#64748b",
            "icon": "#64748b",
        }
        icon_color = icon_color_map.get(variant, "#ffffff")
        
        # Comprehensive mapping to explicitly supported ICONS in icons.py
        emoji_to_icon = {
            "💾": "save", "🔄": "refresh", "⎙": "print", "✔": "check",
            "➕": "add", "✖": "cancel", "✕": "close", "📄": "document",
            "🖨️": "print", "🖨": "print", "📝": "inquiry", "💰": "deduction",
            "⚙️": "settings", "🏥": "hospital", "⏰": "clock",
            "👥": "employees", "🏠": "home", "ℹ️": "about",
            "📋": "absences", "🔍": "search", "⚖": "decision", "⚖️": "decision",
            "🚫": "cancel", "🗑": "delete", "🗑️": "delete",
            "📁": "document", "💸": "salary", "🔔": "notification",
            "✏️": "edit", "✏": "edit", "🏁": "completed",
            "❌": "cancel", "❌️": "cancel", "✅": "check",
            "→": "forward", "←": "back", "ℹ": "about",
            "\U0001f4be": "save", "\u274c": "cancel", "\u2714": "check", "\u2716": "cancel"
        }
        
        # Check if text contains an emoji (and we either have no icon_name or a dummy one)
        if text:
            for emj, mapped_name in emoji_to_icon.items():
                if emj in text:
                    if not icon_name:
                        icon_name = mapped_name
                    # Strip emoji from text
                    text = text.replace(emj, "").strip()

            if icon_name in emoji_to_icon:
                text = text.replace(icon_name, "").strip()

        if text:
            self.setText(" " + text)
        
        if icon_name:
            mapped = emoji_to_icon.get(icon_name, icon_name)
            icon = get_icon(mapped, color=icon_color)
            self.setIcon(icon)
            self.setIconSize(QSize(20, 20))

    def _set_variant(self, variant):
        if variant == "danger": self.setObjectName("btn_danger")
        elif variant == "success": self.setObjectName("btn_success")
        elif variant == "warning": self.setObjectName("btn_warning")
        elif variant == "outline": self.setObjectName("btn_outline")
        elif variant == "ghost": self.setObjectName("btn_ghost")
        elif variant == "icon": self.setObjectName("btn_icon")


class Separator(QFrame):
    """A horizontal separator line."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: #e5e7eb; border: none;")


class SidebarSeparator(QFrame):
    """A horizontal separator for sidebar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.HLine)
        self.setFixedHeight(1)
        self.setStyleSheet("background-color: #334155; border: none; margin: 8px 16px;")


class PageHeader(QWidget):
    """A page header with title and subtitle."""

    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(4)

        title_label = ArabicLabel(title, object_name="page_title")
        layout.addWidget(title_label)

        if subtitle:
            sub_label = ArabicLabel(subtitle, object_name="page_subtitle")
            layout.addWidget(sub_label)


class ScrollablePageWidget(QScrollArea):
    """A scrollable page container."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.content = QWidget()
        self.content.setLayoutDirection(Qt.RightToLeft)
        self.setWidget(self.content)

        self.layout = QVBoxLayout(self.content)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(28, 28, 28, 28)


class ToastNotification(QFrame):
    """A modern toast notification with Material icon and auto-dismiss."""
    
    def __init__(self, message, variant="info", duration=4000, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedHeight(56)
        self.setMinimumWidth(350)
        
        # Styling based on variant
        style_map = {
            "info": {"bg": "#eff6ff", "border": "#bfdbfe", "color": "#1d4ed8", "icon": "info"},
            "success": {"bg": "#ecfdf5", "border": "#a7f3d0", "color": "#047857", "icon": "success"},
            "warning": {"bg": "#fffbeb", "border": "#fde68a", "color": "#b45309", "icon": "warning"},
            "danger": {"bg": "#fef2f2", "border": "#fecaca", "color": "#b91c1c", "icon": "error"},
        }
        style = style_map.get(variant, style_map["info"])
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-radius: 12px;
                padding: 8px 16px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)
        
        # Icon
        icon_label = QLabel()
        icon_label.setPixmap(get_icon(style['icon'], color=style['color']).pixmap(22, 22))
        icon_label.setFixedSize(24, 24)
        icon_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(icon_label)
        
        # Message
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"color: {style['color']}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(msg_label)
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton()
        close_btn.setIcon(get_icon("close", color=style['color']))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 4px;
                min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
            }}
            QPushButton:hover {{ background: rgba(0,0,0,0.1); }}
        """)
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn)
        
        # Shadow
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(20)
        effect.setXOffset(0)
        effect.setYOffset(6)
        effect.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(effect)
        
        # Auto dismiss
        if duration > 0:
            QTimer.singleShot(duration, self._dismiss)
    
    def _dismiss(self):
        self.hide()
        self.deleteLater()

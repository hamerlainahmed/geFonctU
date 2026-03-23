# -*- coding: utf-8 -*-
"""
Material Design Icons — Centralized icon management using QtAwesome.
Provides consistent, beautiful Material Design icons across the entire application.
"""

import qtawesome as qta
from PyQt5.QtGui import QIcon, QColor


# ── Icon Color Palette ──────────────────────────────────────────
ICON_COLORS = {
    "sidebar":          "#94a3b8",
    "sidebar_active":   "#ffffff",
    "primary":          "#3b82f6",
    "secondary":        "#64748b",
    "success":          "#059669",
    "warning":          "#d97706",
    "danger":           "#dc2626",
    "info":             "#0891b2",
    "white":            "#ffffff",
    "dark":             "#1e293b",
    "muted":            "#9ca3af",
    "accent":           "#6366f1",
}


def get_icon(name, color=None, size=None):
    """Get a Material Design icon by name.
    
    Args:
        name: Icon name from the ICONS mapping or a direct qtawesome icon name
        color: Override color (hex string)
        size: Override size
    
    Returns:
        QIcon instance
    """
    icon_name = ICONS.get(name, name)
    opts = {}
    if color:
        opts["color"] = QColor(color)
    else:
        opts["color"] = QColor(ICON_COLORS["secondary"])
    if size:
        opts["scale_factor"] = size
    
    try:
        return qta.icon(icon_name, **opts)
    except Exception:
        return QIcon()


def get_colored_icon(name, color_key="primary"):
    """Get icon with a predefined color from the palette."""
    color = ICON_COLORS.get(color_key, color_key)
    return get_icon(name, color=color)


# ── Icon Name Mapping (Semantic → FontAwesome 6 Solid) ──────────────
ICONS = {
    # Navigation / Sidebar
    "home":             "fa6s.house",
    "employees":        "fa6s.users",
    "sick_leave":       "fa6s.stethoscope",
    "absences":         "fa6s.user-clock",
    "inquiries":        "fa6s.clipboard-question",
    "deductions":       "fa6s.money-bill-transfer",
    "settings":         "fa6s.gear",
    "about":            "fa6s.circle-info",
    
    # Actions
    "add":              "fa6s.circle-plus",
    "edit":             "fa6s.pen-to-square",
    "delete":           "fa6s.trash-can",
    "save":             "fa6s.floppy-disk",
    "print":            "fa6s.print",
    "preview":          "fa6s.eye",
    "search":           "fa6s.magnifying-glass",
    "filter":           "fa6s.filter",
    "refresh":          "fa6s.arrow-rotate-right",
    "close":            "fa6s.xmark",
    "cancel":           "fa6s.circle-xmark",
    "check":            "fa6s.circle-check",
    "export":           "fa6s.file-export",
    "import":           "fa6s.file-import",
    "download":         "fa6s.download",
    "upload":           "fa6s.upload",
    "options":          "fa6s.ellipsis-vertical",
    "menu":             "fa6s.bars",
    "back":             "fa6s.arrow-right",
    "forward":          "fa6s.arrow-left",
    
    # Status
    "active":           "fa6s.certificate",
    "pending":          "fa6s.clock",
    "completed":        "fa6s.check-double",
    "expired":          "fa6s.triangle-exclamation",
    "warning":          "fa6s.triangle-exclamation",
    "error":            "fa6s.circle-xmark",
    "info":             "fa6s.circle-info",
    "success":          "fa6s.circle-check",
    
    # Domain-specific
    "employee":         "fa6s.user",
    "teacher":          "fa6s.chalkboard-user",
    "document":         "fa6s.file-lines",
    "certificate":      "fa6s.certificate",
    "calendar":         "fa6s.calendar-days",
    "clock":            "fa6s.clock",
    "hospital":         "fa6s.hospital",
    "medical":          "fa6s.briefcase-medical",
    "substitute":       "fa6s.user-group",
    "absence":          "fa6s.user-slash",
    "delay":            "fa6s.user-clock",
    "inquiry":          "fa6s.clipboard-question",
    "decision":         "fa6s.gavel",
    "deduction":        "fa6s.money-bill-wave",
    "salary":           "fa6s.sack-dollar",
    "performance":      "fa6s.arrow-trend-down",
    "notification":     "fa6s.bell",
    "mail":             "fa6s.envelope",
    "phone":            "fa6s.phone",
    "address":          "fa6s.location-dot",
    "id_card":          "fa6s.id-card",
    "grade":            "fa6s.star",
    "subject":          "fa6s.book",
    "date":             "fa6s.calendar",
    "notes":            "fa6s.note-sticky",
    "logo":             "fa6s.image",
    "institution":      "fa6s.building-columns",
    "director":         "fa6s.user-tie",
    "year":             "fa6s.calendar-days",
    "location":         "fa6s.map-location-dot",
    "wilaya":           "fa6s.city",
    
    # Dashboard
    "dashboard":        "fa6s.chart-pie",
    "stats":            "fa6s.chart-simple",
    "trend_up":         "fa6s.arrow-trend-up",
    "trend_down":       "fa6s.arrow-trend-down",
    "people":           "fa6s.users",
    "quick_action":     "fa6s.bolt",
    
    # UI Controls
    "zoom_in":          "fa6s.magnifying-glass-plus",
    "zoom_out":         "fa6s.magnifying-glass-minus",
    "fullscreen":       "fa6s.expand",
    "collapse":         "fa6s.chevron-up",
    "expand":           "fa6s.chevron-down",
    "sort":             "fa6s.sort",
    "copy":             "fa6s.copy",
    "paste":            "fa6s.paste",
    "help":             "fa6s.circle-question",
    "theme":            "fa6s.circle-half-stroke",
    "exit":             "fa6s.right-from-bracket",
    "file_excel":       "fa6s.file-excel",
    "template":         "fa6s.file-excel",
    "resume":           "fa6s.play",
    "stop":             "fa6s.stop",
}


# ── Sidebar Icon List (matches nav_items order) ──────────────────
SIDEBAR_ICONS = [
    "home", "employees", "sick_leave", "absences",
    "inquiries", "deductions", "settings", "about"
]


def get_sidebar_icon(index, active=False):
    """Get sidebar navigation icon."""
    if index < len(SIDEBAR_ICONS):
        name = SIDEBAR_ICONS[index]
        color = ICON_COLORS["sidebar_active"] if active else ICON_COLORS["sidebar"]
        return get_icon(name, color=color)
    return QIcon()

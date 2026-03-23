# -*- coding: utf-8 -*-
"""
Premium Dark/Light RTL Stylesheet — Modern Administrative System.
Inspired by Material Design 3 with Arabic-first aesthetics.
Enhanced with glassmorphism, micro-animations, and refined color palette.
"""

# ── Color Palette ──────────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg_primary":       "#f0f2f5",
    "bg_secondary":     "#e4e7ec",
    "bg_card":          "#ffffff",
    "bg_sidebar":       "#0f172a",
    "bg_sidebar_hover": "#1e293b",
    "bg_sidebar_active":"#3b82f6",
    "bg_hover":         "#f8fafc",
    "bg_selected":      "#eff6ff",
    "bg_input":         "#f9fafb",
    "bg_table_alt":     "#f8fafc",

    # Accent
    "accent":           "#3b82f6",
    "accent_light":     "#60a5fa",
    "accent_dark":      "#2563eb",
    "accent_glow":      "rgba(59, 130, 246, 0.15)",
    "accent_subtle":    "rgba(59, 130, 246, 0.08)",

    # Semantic
    "success":          "#059669",
    "success_light":    "#d1fae5",
    "success_bg":       "#ecfdf5",
    "warning":          "#d97706",
    "warning_light":    "#fef3c7",
    "warning_bg":       "#fffbeb",
    "danger":           "#dc2626",
    "danger_light":     "#fee2e2",
    "danger_bg":        "#fef2f2",
    "info":             "#0891b2",
    "info_light":       "#cffafe",
    "info_bg":          "#ecfeff",

    # Text
    "text_primary":     "#111827",
    "text_secondary":   "#374151",
    "text_muted":       "#6b7280",
    "text_light":       "#f1f5f9",
    "text_sidebar":     "#94a3b8",

    # Borders
    "border":           "#e5e7eb",
    "border_light":     "#f3f4f6",
    "border_focus":     "#3b82f6",

    # Scrollbar
    "scrollbar":        "#d1d5db",
    "scrollbar_hover":  "#9ca3af",

    # Gradients
    "gradient_start":   "#3b82f6",
    "gradient_end":     "#1d4ed8",
    
    # Glass Effect
    "glass_bg":         "rgba(255, 255, 255, 0.7)",
    "glass_border":     "rgba(255, 255, 255, 0.3)",
}

C = COLORS


def get_stylesheet():
    return """
    /* ═══════════════════════════════════════════════════════════
       GLOBAL RESET & BASE
    ═══════════════════════════════════════════════════════════ */
    QWidget {{
        background-color: {bg_primary};
        color: {text_primary};
        font-family: 'Amiri', 'Tajawal', 'Segoe UI', 'Arial';
        font-size: 14px;
        selection-background-color: {accent};
        selection-color: #ffffff;
    }}

    QMainWindow {{
        background-color: {bg_primary};
    }}

    /* ═══════════════════════════════════════════════════════════
       SIDEBAR — Premium Dark Gradient
    ═══════════════════════════════════════════════════════════ */
    #sidebar {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f172a, stop:0.5 #131c31, stop:1 #1a2744);
        border: none;
        min-width: 270px;
        max-width: 270px;
    }}

    #sidebar QWidget {{
        background: transparent;
        color: {text_light};
    }}

    #sidebar_stat {{
        background: rgba(255, 255, 255, 0.04);
        border-radius: 8px;
        margin: 1px 8px;
    }}

    #sidebar_stat:hover {{
        background: rgba(255, 255, 255, 0.08);
    }}

    #sidebar_title {{
        color: #ffffff;
        font-size: 18px;
        font-weight: bold;
        letter-spacing: 0.5px;
        padding: 0;
    }}

    #sidebar_subtitle {{
        color: #64748b;
        font-size: 12px;
        padding: 0;
    }}

    /* ── Sidebar Navigation Buttons — Material Style ── */
    QPushButton#nav_btn {{
        background-color: transparent;
        color: {text_sidebar};
        border: none;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: left;
        font-size: 16px;
        font-weight: bold;
        margin: 4px 14px;
        min-height: 24px;
    }}

    QPushButton#nav_btn:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        color: #e2e8f0;
    }}

    QPushButton#nav_btn:checked,
    QPushButton#nav_btn[active="true"] {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent}, stop:1 #6366f1);
        color: #ffffff;
        font-weight: bold;
    }}

    /* ═══════════════════════════════════════════════════════════
       CARDS & PANELS — Glassmorphism Effect
    ═══════════════════════════════════════════════════════════ */
    QFrame#card {{
        background-color: {bg_card};
        border: 1px solid {border};
        border-radius: 16px;
        padding: 24px;
    }}

    QFrame#stat_card {{
        background-color: {bg_card};
        border: 1px solid {border};
        border-radius: 16px;
        padding: 20px;
        min-width: 160px;
    }}

    QFrame#stat_card_blue {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #eff6ff, stop:1 #dbeafe);
        border: 1px solid #bfdbfe;
        border-radius: 16px;
        padding: 20px;
        min-width: 160px;
    }}

    QFrame#stat_card_green {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ecfdf5, stop:1 #d1fae5);
        border: 1px solid #a7f3d0;
        border-radius: 16px;
        padding: 20px;
        min-width: 160px;
    }}

    QFrame#stat_card_amber {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fffbeb, stop:1 #fef3c7);
        border: 1px solid #fde68a;
        border-radius: 16px;
        padding: 20px;
        min-width: 160px;
    }}

    QFrame#stat_card_red {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fef2f2, stop:1 #fee2e2);
        border: 1px solid #fecaca;
        border-radius: 16px;
        padding: 20px;
        min-width: 160px;
    }}

    /* ═══════════════════════════════════════════════════════════
       LABELS
    ═══════════════════════════════════════════════════════════ */
    QLabel {{
        color: {text_primary};
        background: transparent;
        qproperty-alignment: 'AlignRight | AlignVCenter';
    }}

    QLabel#page_title {{
        font-size: 26px;
        font-weight: bold;
        color: {text_primary};
        padding: 4px 0;
    }}

    QLabel#page_subtitle {{
        font-size: 14px;
        color: {text_muted};
        padding: 0 0 8px 0;
    }}

    QLabel#section_title {{
        font-size: 18px;
        font-weight: bold;
        color: {text_secondary};
        padding: 4px 0;
    }}

    QLabel#stat_value {{
        font-size: 34px;
        font-weight: bold;
        color: {accent_dark};
    }}

    QLabel#stat_label {{
        font-size: 13px;
        color: {text_muted};
    }}

    QLabel#badge_info {{
        background-color: {info_bg};
        color: {info};
        border: 1px solid {info_light};
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: bold;
    }}

    QLabel#badge_success {{
        background-color: {success_bg};
        color: {success};
        border: 1px solid {success_light};
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: bold;
    }}

    QLabel#badge_warning {{
        background-color: {warning_bg};
        color: {warning};
        border: 1px solid {warning_light};
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: bold;
    }}

    QLabel#badge_danger {{
        background-color: {danger_bg};
        color: {danger};
        border: 1px solid {danger_light};
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: bold;
    }}

    /* ═══════════════════════════════════════════════════════════
       INPUTS — Refined Material Style
    ═══════════════════════════════════════════════════════════ */
    QLineEdit, QDateEdit, QSpinBox {{
        background-color: {bg_input};
        color: {text_primary};
        border: 2px solid {border};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
        qproperty-alignment: 'AlignRight | AlignVCenter';
    }}

    QTextEdit {{
        background-color: {bg_input};
        color: {text_primary};
        border: 2px solid {border};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }}

    QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, QSpinBox:focus {{
        border: 2px solid {accent};
        background-color: #ffffff;
    }}

    QLineEdit:hover, QTextEdit:hover, QDateEdit:hover {{
        border-color: {accent_light};
    }}

    QLineEdit::placeholder, QTextEdit::placeholder {{
        color: #9ca3af;
    }}

    /* ═══════════════════════════════════════════════════════════
       COMBO BOX — Material Dropdown
    ═══════════════════════════════════════════════════════════ */
    QComboBox {{
        background-color: {bg_input};
        color: {text_primary};
        border: 2px solid {border};
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
        min-width: 140px;
    }}

    QComboBox:focus {{
        border: 2px solid {accent};
    }}

    QComboBox:hover {{
        border-color: {accent_light};
    }}

    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top left;
        width: 32px;
        border-left: 2px solid {border};
        border-top-left-radius: 10px;
        border-bottom-left-radius: 10px;
        background: transparent;
    }}

    QComboBox QAbstractItemView {{
        background-color: {bg_card};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 10px;
        selection-background-color: {accent_light};
        selection-color: #ffffff;
        padding: 6px;
        outline: 0;
    }}

    QComboBox QAbstractItemView::item {{
        padding: 8px 14px;
        border-radius: 6px;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: {bg_hover};
    }}

    /* ═══════════════════════════════════════════════════════════
       BUTTONS — Material Elevation & Gradient
    ═══════════════════════════════════════════════════════════ */
    QPushButton {{
        background-color: {accent};
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-size: 14px;
        font-weight: bold;
        min-width: 90px;
    }}

    QPushButton:hover {{
        background-color: {accent_light};
    }}

    QPushButton:pressed {{
        background-color: {accent_dark};
    }}

    QPushButton:disabled {{
        background-color: {border};
        color: {text_muted};
    }}

    QPushButton#btn_danger {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc2626, stop:1 #ef4444);
    }}
    QPushButton#btn_danger:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #f87171);
    }}
    QPushButton#btn_danger:pressed {{
        background-color: #b91c1c;
    }}

    QPushButton#btn_success {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #059669, stop:1 #10b981);
    }}
    QPushButton#btn_success:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #34d399);
    }}
    QPushButton#btn_success:pressed {{
        background-color: #047857;
    }}

    QPushButton#btn_warning {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #d97706, stop:1 #f59e0b);
        color: #ffffff;
    }}
    QPushButton#btn_warning:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f59e0b, stop:1 #fbbf24);
    }}

    QPushButton#btn_outline {{
        background-color: transparent;
        color: {accent};
        border: 2px solid {accent};
    }}
    QPushButton#btn_outline:hover {{
        background-color: {accent_glow};
        color: {accent_dark};
    }}

    QPushButton#btn_ghost {{
        background-color: transparent;
        color: {text_secondary};
        border: none;
        font-weight: normal;
    }}
    QPushButton#btn_ghost:hover {{
        background-color: {bg_hover};
        color: {accent};
    }}

    QPushButton#btn_icon {{
        background-color: transparent;
        color: {text_muted};
        border: none;
        border-radius: 8px;
        padding: 6px;
        min-width: 34px;
        max-width: 34px;
        min-height: 34px;
        max-height: 34px;
        font-size: 14px;
    }}
    QPushButton#btn_icon:hover {{
        background-color: {accent_glow};
        color: {accent};
    }}
    QPushButton#btn_icon:pressed {{
        background-color: {bg_selected};
    }}

    /* ═══════════════════════════════════════════════════════════
       TABLE — Refined Data Grid
    ═══════════════════════════════════════════════════════════ */
    QTableWidget {{
        background-color: {bg_card};
        color: {text_primary};
        border: 1px solid {border};
        border-radius: 12px;
        gridline-color: {border_light};
        font-size: 14px;
        selection-background-color: {bg_selected};
        selection-color: {text_primary};
        alternate-background-color: {bg_table_alt};
    }}

    QTableWidget::item {{
        padding: 6px 10px;
        border-bottom: 1px solid {border_light};
    }}

    QTableWidget::item:selected {{
        background-color: {bg_selected};
        color: {accent_dark};
    }}

    QTableWidget::item:hover {{
        background-color: {bg_hover};
    }}

    QHeaderView::section {{
        background-color: {bg_primary};
        color: {text_secondary};
        border: none;
        border-bottom: 2px solid {border};
        padding: 12px 10px;
        font-weight: bold;
        font-size: 13px;
    }}

    QTableCornerButton::section {{
        background-color: {bg_primary};
        border: none;
    }}

    /* ═══════════════════════════════════════════════════════════
       SCROLLBAR — Sleek & Minimal
    ═══════════════════════════════════════════════════════════ */
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {scrollbar};
        border-radius: 5px;
        min-height: 40px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {scrollbar_hover};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}

    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {scrollbar};
        border-radius: 5px;
        min-width: 40px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {scrollbar_hover};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}

    /* ═══════════════════════════════════════════════════════════
       GROUP BOX — Refined Section Container
    ═══════════════════════════════════════════════════════════ */
    QGroupBox {{
        background-color: {bg_card};
        border: 1px solid {border};
        border-radius: 14px;
        margin-top: 20px;
        padding: 24px 20px 20px 20px;
        font-weight: bold;
        color: {accent_dark};
        font-size: 15px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top right;
        padding: 0 14px;
        bottom: 10px;
    }}

    /* ═══════════════════════════════════════════════════════════
       DIALOGS & MESSAGES
    ═══════════════════════════════════════════════════════════ */
    QMessageBox, QDialog {{
        background-color: {bg_card};
    }}

    QMessageBox QLabel {{
        color: {text_primary};
        font-size: 14px;
    }}

    QMessageBox QPushButton {{
        min-width: 80px;
        padding: 8px 16px;
    }}

    /* ═══════════════════════════════════════════════════════════
       MENUS — Material Popup
    ═══════════════════════════════════════════════════════════ */
    QMenu {{
        background-color: {bg_card};
        border: 1px solid {border};
        padding: 6px;
        border-radius: 12px;
    }}
    QMenu::item {{
        padding: 10px 24px 10px 16px;
        border-radius: 8px;
        font-size: 14px;
    }}
    QMenu::item:selected {{
        background-color: {bg_selected};
        color: {accent_dark};
    }}
    QMenu::separator {{
        height: 1px;
        background: {border};
        margin: 4px 8px;
    }}

    /* ═══════════════════════════════════════════════════════════
       TAB WIDGET — Pill-style Tabs
    ═══════════════════════════════════════════════════════════ */
    QTabWidget::pane {{
        border: 1px solid {border};
        border-radius: 12px;
        background: {bg_card};
        padding: 16px;
    }}
    QTabBar::tab {{
        background: {bg_primary};
        color: {text_muted};
        border: none;
        padding: 12px 24px;
        font-size: 14px;
        font-weight: bold;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        margin-left: 2px;
    }}
    QTabBar::tab:selected {{
        background: {bg_card};
        color: {accent};
        border-bottom: 3px solid {accent};
    }}
    QTabBar::tab:hover:!selected {{
        background: {bg_hover};
        color: {text_primary};
    }}

    /* ═══════════════════════════════════════════════════════════
       STATUS BAR — Clean Footer
    ═══════════════════════════════════════════════════════════ */
    QStatusBar {{
        background-color: {bg_card};
        color: {text_muted};
        border-top: 1px solid {border};
        padding: 6px 16px;
        font-size: 13px;
    }}

    /* ═══════════════════════════════════════════════════════════
       TOOL TIP — Material Tooltip
    ═══════════════════════════════════════════════════════════ */
    QToolTip {{
        background-color: #1e293b;
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    
    /* ═══════════════════════════════════════════════════════════
       PROGRESS BAR — Material Style
    ═══════════════════════════════════════════════════════════ */
    QProgressBar {{
        background-color: {border};
        border: none;
        border-radius: 6px;
        height: 8px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent}, stop:1 #6366f1);
        border-radius: 6px;
    }}
    """.format(**C)

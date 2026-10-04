"""Cores, estilo visual (QSS) e ícone do aplicativo.

Para mudar a aparência, altere apenas este arquivo.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap

# Paleta
BG = "#171a21"
BG_ALT = "#1f232c"
CARD = "#252a35"
BORDER = "#323846"
TEXT = "#e8eaf0"
TEXT_MUTED = "#9aa1b2"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#8f74ff"
RED = "#ff5c6c"
YELLOW = "#ffc145"
GREEN = "#3ddc84"
GRAY = "#6b7280"

APP_STYLESHEET = f"""
QWidget {{
    color: {TEXT};
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 10pt;
}}
QMainWindow, QDialog, QStackedWidget, QScrollArea, #PageRoot {{
    background: {BG};
}}
QScrollArea > QWidget > QWidget {{ background: {BG}; }}
QLabel#PageTitle {{ font-size: 18pt; font-weight: 600; }}
QLabel#Muted {{ color: {TEXT_MUTED}; }}
QListWidget#Sidebar {{
    background: {BG_ALT};
    border: none;
    border-right: 1px solid {BORDER};
    padding-top: 8px;
    outline: 0;
}}
QListWidget#Sidebar::item {{
    padding: 10px 18px;
    border-radius: 8px;
    margin: 2px 8px;
}}
QListWidget#Sidebar::item:selected {{ background: {ACCENT}; color: white; }}
QListWidget#Sidebar::item:hover:!selected {{ background: {CARD}; }}
QFrame#Card, QGroupBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QGroupBox {{ margin-top: 14px; padding: 16px 12px 12px 12px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {TEXT_MUTED}; }}
QLabel#CardValue {{ font-size: 24pt; font-weight: 700; }}
QLabel#CardLabel {{ color: {TEXT_MUTED}; }}
QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {GRAY}; }}
QPushButton#Primary {{ background: {ACCENT}; border: none; color: white; font-weight: 600; }}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#PauseButton {{
    font-size: 14pt; font-weight: 700; padding: 16px; border-radius: 12px;
    background: {RED}; color: white; border: none;
}}
QPushButton#PauseButton:checked {{ background: {GREEN}; color: #10261a; }}
QLineEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QTimeEdit, QDateEdit, QComboBox, QDateTimeEdit {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{ background: {BG_ALT}; selection-background-color: {ACCENT}; }}
QTableWidget, QListWidget {{
    background: {BG_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    gridline-color: {BORDER};
    alternate-background-color: {CARD};
}}
QHeaderView::section {{
    background: {CARD}; color: {TEXT_MUTED}; border: none; padding: 6px; font-weight: 600;
}}
QCheckBox::indicator, QRadioButton::indicator {{ width: 16px; height: 16px; }}
QMenu {{ background: {BG_ALT}; border: 1px solid {BORDER}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px; border-radius: 4px; }}
QMenu::item:selected {{ background: {ACCENT}; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {GRAY}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QToolTip {{ background: {BG_ALT}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""

FLOATING_STYLESHEET = f"""
#FloatingCard {{
    background: rgba(23, 26, 33, 245);
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
#FloatingTitle {{ font-weight: 700; font-size: 10pt; letter-spacing: 1px; }}
#SectionTitle {{ color: {TEXT_MUTED}; font-size: 8pt; font-weight: 700; letter-spacing: 1px; margin-top: 6px; }}
#RowText {{ font-size: 9pt; }}
#RowOverdue {{ font-size: 9pt; color: {RED}; }}
#EmptyText {{ color: {GRAY}; font-size: 9pt; font-style: italic; }}
#StatusLine {{ color: {TEXT_MUTED}; font-size: 8pt; }}
QPushButton#HeaderButton {{
    background: transparent; border: none; padding: 0; font-size: 11pt; color: {TEXT_MUTED};
    min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; border-radius: 6px;
}}
QPushButton#HeaderButton:hover {{ background: {CARD}; color: {TEXT}; }}
QPushButton#RowButton {{
    background: transparent; border: none; color: {TEXT_MUTED}; padding: 0;
    min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px; border-radius: 4px;
}}
QPushButton#RowButton:hover {{ background: {GREEN}; color: #10261a; }}
QPushButton#NewTaskButton {{
    background: {ACCENT}; color: white; border: none; border-radius: 8px; padding: 6px; font-weight: 600;
}}
QPushButton#NewTaskButton:hover {{ background: {ACCENT_HOVER}; }}
"""


def dot_style(color: str, size: int = 10) -> str:
    """Estilo de uma 'bolinha' colorida (indicador de status)."""
    return (
        f"background: {color}; border-radius: {size // 2}px; "
        f"min-width: {size}px; max-width: {size}px; min-height: {size}px; max-height: {size}px;"
    )


def make_app_icon(size: int = 64) -> QIcon:
    """Desenha o ícone (não precisa de arquivo de imagem)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor(ACCENT))
    gradient.setColorAt(1, QColor("#d14bff"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(2, 2, size - 4, size - 4), size * 0.22, size * 0.22)
    painter.fillPath(path, gradient)
    font = QFont("Segoe UI")
    font.setPixelSize(int(size * 0.55))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "K")
    painter.end()
    return QIcon(pixmap)

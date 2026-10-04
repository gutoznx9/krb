"""Peças comuns às páginas."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class Page(QWidget):
    """Página com título. Subclasses adicionam conteúdo em self.content."""

    title = ""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PageRoot")
        self.content = QVBoxLayout(self)
        self.content.setContentsMargins(28, 24, 28, 24)
        self.content.setSpacing(14)
        self.content.addWidget(QLabel(self.title, objectName="PageTitle"))

    def on_show(self) -> None:
        """Chamado sempre que a página é aberta (para recarregar dados)."""


class PlaceholderPage(Page):
    """Tela que será construída numa fase futura."""

    def __init__(self, title: str, phase: str, description: str, parent: QWidget | None = None) -> None:
        self.title = title
        super().__init__(parent)
        card = QFrame(objectName="Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        badge = QLabel(f"Disponível na {phase}")
        badge.setStyleSheet("font-weight: 600;")
        text = QLabel(description, objectName="Muted")
        text.setWordWrap(True)
        layout.addWidget(badge)
        layout.addWidget(text)
        self.content.addWidget(card)
        self.content.addStretch(1)


def stat_card(label: str, color: str) -> tuple[QFrame, QLabel]:
    """Cartão com um número grande. Retorna (cartão, label do número)."""
    card = QFrame(objectName="Card")
    card.setMinimumWidth(170)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    value = QLabel("0", objectName="CardValue")
    value.setStyleSheet(f"color: {color};")
    text = QLabel(label, objectName="CardLabel")
    text.setWordWrap(True)
    layout.addWidget(value, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(text)
    return card, value

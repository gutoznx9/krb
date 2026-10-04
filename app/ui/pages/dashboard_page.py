"""Tela Dashboard: resumo do dia + controle da automação."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QPushButton, QRadioButton

from app.config import MODE_APPROVAL, MODE_AUTOMATIC, MODE_MONITOR, SettingsManager
from app.ui import theme
from app.ui.pages.base import Page, stat_card

MODE_TEXTS = [
    (MODE_AUTOMATIC, "Modo automático", "Responde sozinho o que for autorizado e tiver confiança alta."),
    (MODE_APPROVAL, "Modo aprovação", "Toda resposta vira sugestão para você aprovar."),
    (MODE_MONITOR, "Somente monitoramento", "Só lê e salva as mensagens. Nunca responde."),
]


class DashboardPage(Page):
    title = "Dashboard"
    pause_toggled = Signal(bool)
    mode_changed = Signal(str)

    def __init__(self, settings: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings

        self.whatsapp_label = QLabel(objectName="Muted")
        self.content.addWidget(self.whatsapp_label)

        grid = QGridLayout()
        grid.setSpacing(12)
        cards = [
            ("customers_waiting", "Clientes aguardando resposta", theme.RED),
            ("orders_today", "Pedidos hoje", theme.ACCENT),
            ("awaiting_payment", "Aguardando pagamento", theme.YELLOW),
            ("in_preparation", "Pedidos em preparação", theme.TEXT),
            ("ready", "Pedidos prontos", theme.GREEN),
            ("auto_replies_today", "Respondidas automaticamente hoje", theme.TEXT_MUTED),
        ]
        self.values: dict[str, QLabel] = {}
        for i, (key, label, color) in enumerate(cards):
            card, value = stat_card(label, color)
            self.values[key] = value
            grid.addWidget(card, i // 3, i % 3)
        self.content.addLayout(grid)

        # Controle da automação
        box = QGroupBox("Automação")
        box_layout = QGridLayout(box)
        self.pause_button = QPushButton(objectName="PauseButton")
        self.pause_button.setCheckable(True)
        self.pause_button.toggled.connect(self._on_pause_clicked)
        box_layout.addWidget(self.pause_button, 0, 0, 1, 2)

        self.mode_group = QButtonGroup(self)
        for row, (mode, label, tip) in enumerate(MODE_TEXTS, start=1):
            radio = QRadioButton(label)
            radio.setProperty("mode", mode)
            self.mode_group.addButton(radio)
            box_layout.addWidget(radio, row, 0)
            hint = QLabel(tip, objectName="Muted")
            box_layout.addWidget(hint, row, 1)
        self.mode_group.buttonClicked.connect(lambda btn: self.mode_changed.emit(btn.property("mode")))

        info = QLabel(
            "Com a automação pausada, o sistema continua recebendo e salvando mensagens, "
            "mas não envia nada automaticamente.",
            objectName="Muted",
        )
        info.setWordWrap(True)
        box_layout.addWidget(info, len(MODE_TEXTS) + 1, 0, 1, 2)
        self.content.addWidget(box)

        footer = QHBoxLayout()
        self.pending_label = QLabel(objectName="Muted")
        footer.addWidget(self.pending_label)
        footer.addStretch(1)
        self.content.addLayout(footer)
        self.content.addStretch(1)

        self.sync_automation_controls()

    def _on_pause_clicked(self, paused: bool) -> None:
        self._update_pause_text(paused)
        self.pause_toggled.emit(paused)

    def _update_pause_text(self, paused: bool) -> None:
        self.pause_button.setText("▶  RETOMAR AUTOMAÇÃO" if paused else "❚❚  PAUSAR AUTOMAÇÃO")

    def sync_automation_controls(self) -> None:
        """Atualiza botões a partir das configurações (ex.: pausado pela bandeja)."""
        paused = bool(self.settings.get("automation.paused"))
        self.pause_button.blockSignals(True)
        self.pause_button.setChecked(paused)
        self.pause_button.blockSignals(False)
        self._update_pause_text(paused)
        mode = self.settings.get("automation.mode")
        for btn in self.mode_group.buttons():
            btn.setChecked(btn.property("mode") == mode)

    def update_snapshot(self, snapshot) -> None:
        stats = snapshot.stats
        for key, label in self.values.items():
            label.setText(str(getattr(stats, key)))
        self.pending_label.setText(f"Mensagens aguardando aprovação: {stats.pending_approvals}")
        self.whatsapp_label.setText(snapshot.whatsapp_status)

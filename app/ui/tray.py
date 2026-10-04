"""Ícone na bandeja do Windows (perto do relógio)."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

log = logging.getLogger("krb.ui.tray")


class TrayIcon(QObject):
    open_main_requested = Signal()
    show_panel_requested = Signal()
    new_task_requested = Signal()
    pause_toggled = Signal(bool)
    quit_requested = Signal()

    def __init__(self, icon: QIcon, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.available = QSystemTrayIcon.isSystemTrayAvailable()
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("KRB Assistant")

        self.menu = QMenu()
        self.menu.addAction("Abrir KRB Assistant", self.open_main_requested.emit)
        self.menu.addAction("Mostrar painel flutuante", self.show_panel_requested.emit)
        self.menu.addAction("Nova tarefa", self.new_task_requested.emit)
        self.menu.addSeparator()
        self.pause_action = QAction("Pausar automação", self.menu)
        self.pause_action.setCheckable(True)
        self.pause_action.toggled.connect(self.pause_toggled.emit)
        self.menu.addAction(self.pause_action)
        self.menu.addSeparator()
        self.menu.addAction("Sair", self.quit_requested.emit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

        if not self.available:
            log.warning("Bandeja do sistema não disponível; o ícone não será exibido")

    def show(self) -> None:
        if self.available:
            self.tray.show()

    def hide(self) -> None:
        self.tray.hide()

    def set_paused(self, paused: bool) -> None:
        """Atualiza o menu sem disparar o sinal de novo."""
        self.pause_action.blockSignals(True)
        self.pause_action.setChecked(paused)
        self.pause_action.blockSignals(False)
        self.tray.setToolTip("KRB Assistant" + (" (automação pausada)" if paused else ""))

    def notify(self, title: str, message: str, warning: bool = False) -> None:
        """Mostra uma notificação do Windows."""
        if not self.available or not self.tray.isVisible():
            log.info("Notificação (sem bandeja): %s - %s", title, message)
            return
        icon = QSystemTrayIcon.MessageIcon.Warning if warning else QSystemTrayIcon.MessageIcon.Information
        self.tray.showMessage(title, message, icon, 8000)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # clique simples: mostra o painel flutuante; duplo clique: janela principal
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_panel_requested.emit()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_main_requested.emit()

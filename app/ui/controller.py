"""UiController: liga as janelas, a bandeja e os dados.

- Atualiza periodicamente o painel flutuante e o Dashboard.
- Recebe os pedidos das janelas (nova tarefa, pausar automação...) e
  chama os serviços certos.
- Erros aqui são registrados e mostrados, mas nunca derrubam o programa.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox

from app.core.context import AppContext
from app.core.dashboard_service import DashboardStats
from app.database.database import DatabaseError
from app.database.models import LogCategory, TaskStatus
from app.ui import theme
from app.ui.floating_panel import FloatingPanel
from app.ui.main_window import MainWindow
from app.ui.task_dialog import TaskDialog
from app.ui.tray import TrayIcon

log = logging.getLogger("krb.ui.controller")


@dataclass
class Snapshot:
    """Fotografia dos dados mostrados nas telas."""

    stats: DashboardStats = field(default_factory=DashboardStats)
    tasks: list[dict] = field(default_factory=list)
    orders: list[dict] = field(default_factory=list)
    # Fase 2 vai preencher com o estado real do WhatsApp
    whatsapp_state: str = "not_configured"
    whatsapp_status: str = "WhatsApp: não configurado (Fase 2)"


class _SettingsBridge(QObject):
    """Leva avisos de configuração alterada para a thread da interface."""

    changed = Signal(str, object)


class UiController(QObject):
    def __init__(self, app: QApplication, ctx: AppContext) -> None:
        super().__init__()
        self.app = app
        self.ctx = ctx
        self.icon = theme.make_app_icon()
        self.snapshot = Snapshot()

        app.setWindowIcon(self.icon)
        app.setStyleSheet(theme.APP_STYLESHEET)

        self.main_window = MainWindow(ctx, self.icon)
        self.panel = FloatingPanel(ctx.settings)
        self.panel.setWindowIcon(self.icon)
        self.tray = TrayIcon(self.icon, self)

        self._bridge = _SettingsBridge()
        self._bridge.changed.connect(self._on_setting_changed)
        ctx.settings.add_listener(lambda key, value: self._bridge.changed.emit(key, value))

        self._connect_signals()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)

    # --------------------------------------------------------------- ligações
    def _connect_signals(self) -> None:
        self.panel.open_main_requested.connect(self.show_main_window)
        self.panel.new_task_requested.connect(self.new_task)
        self.panel.complete_task_requested.connect(
            lambda task_id: self.change_task_status(task_id, str(TaskStatus.CONCLUIDA))
        )

        self.tray.open_main_requested.connect(self.show_main_window)
        self.tray.show_panel_requested.connect(self.panel.show_panel)
        self.tray.new_task_requested.connect(self.new_task)
        self.tray.pause_toggled.connect(self.set_paused)
        self.tray.quit_requested.connect(self.quit)

        dash = self.main_window.dashboard
        dash.pause_toggled.connect(self.set_paused)
        dash.mode_changed.connect(self.set_mode)

        agenda = self.main_window.agenda
        agenda.new_task_requested.connect(self.new_task)
        agenda.status_change_requested.connect(self.change_task_status)

        self.main_window.settings_page.saved.connect(self._on_settings_saved)

    # ---------------------------------------------------------------- início
    def start(self) -> None:
        settings = self.ctx.settings
        self.tray.set_paused(bool(settings.get("automation.paused")))
        self.tray.show()
        self.refresh()
        if settings.get("ui.floating.visible", True):
            self.panel.show_panel()
        # sem bandeja, a janela principal é o único jeito de usar o programa
        if settings.get("ui.show_main_window_on_start", False) or not self.tray.available:
            self.show_main_window()
        self._restart_timer()
        if self.tray.available and not settings.get("ui.floating.visible", True):
            self.tray.notify("KRB Assistant", "Rodando na bandeja. Clique no ícone para abrir.")

    def _restart_timer(self) -> None:
        seconds = max(2, int(self.ctx.settings.get("ui.refresh_seconds", 10)))
        self.timer.start(seconds * 1000)

    # ---------------------------------------------------------- atualização
    def refresh(self) -> None:
        try:
            self.snapshot = Snapshot(
                stats=self.ctx.dashboard.stats(),
                tasks=self.ctx.tasks.upcoming(limit=5),
                orders=self.ctx.dashboard.open_orders(limit=5),
            )
        except DatabaseError:
            # mantém os dados anteriores na tela; o erro já está no log
            log.warning("Atualização do painel adiada por erro no banco")
        except Exception:
            log.exception("Erro inesperado ao atualizar o painel")
        try:
            self.panel.update_snapshot(self.snapshot)
            self.main_window.update_snapshot(self.snapshot)
        except Exception:
            log.exception("Erro ao desenhar o painel")

    # --------------------------------------------------------------- ações
    def show_main_window(self) -> None:
        self.main_window.bring_to_front()

    def new_task(self) -> None:
        parent = self.main_window if self.main_window.isVisible() else None
        dialog = TaskDialog(self.ctx.db, parent)
        dialog.setWindowIcon(self.icon)
        if parent is None:  # aberto pelo painel/bandeja: não pode ficar atrás do painel
            dialog.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        if dialog.exec() and dialog.result_task:
            try:
                task_id = self.ctx.tasks.create(dialog.result_task)
                self.ctx.activity.record(
                    LogCategory.ALTERACAO_MANUAL,
                    f"Tarefa criada: {dialog.result_task.title}",
                    contact_id=dialog.result_task.contact_id,
                    details={"task_id": task_id},
                )
            except (DatabaseError, ValueError) as exc:
                QMessageBox.warning(parent, "Nova tarefa", f"Não foi possível salvar a tarefa:\n{exc}")
                return
            self._after_task_change()

    def change_task_status(self, task_id: int, status: str) -> None:
        try:
            self.ctx.tasks.set_status(task_id, TaskStatus(status))
            task = self.ctx.tasks.get(task_id) or {}
            self.ctx.activity.record(
                LogCategory.ALTERACAO_MANUAL,
                f"Tarefa '{task.get('title', task_id)}' marcada como {status}",
                contact_id=task.get("contact_id"),
            )
        except DatabaseError as exc:
            QMessageBox.warning(None, "Tarefa", f"Não foi possível alterar a tarefa:\n{exc}")
            return
        self._after_task_change()

    def _after_task_change(self) -> None:
        self.refresh()
        if self.main_window.agenda.isVisible():
            self.main_window.agenda.reload()

    def set_paused(self, paused: bool) -> None:
        if bool(self.ctx.settings.get("automation.paused")) == paused:
            return
        self.ctx.settings.set("automation.paused", paused)
        self.ctx.activity.record(
            LogCategory.ALTERACAO_MANUAL, "Automação PAUSADA" if paused else "Automação RETOMADA"
        )

    def set_mode(self, mode: str) -> None:
        if self.ctx.settings.get("automation.mode") == mode:
            return
        self.ctx.settings.set("automation.mode", mode)
        self.ctx.activity.record(LogCategory.ALTERACAO_MANUAL, f"Modo de automação alterado para {mode}")

    def _on_setting_changed(self, key: str, _value: Any) -> None:
        if key in ("automation.paused", "automation.mode"):
            self.tray.set_paused(bool(self.ctx.settings.get("automation.paused")))
            self.main_window.dashboard.sync_automation_controls()
            self.panel.update_snapshot(self.snapshot)

    def _on_settings_saved(self) -> None:
        level = self.ctx.settings.get("system.log_level", "INFO")
        logging.getLogger().setLevel(level)
        self.panel.apply_settings()
        self._restart_timer()
        self.ctx.activity.record(LogCategory.ALTERACAO_MANUAL, "Configurações alteradas")
        self.refresh()

    # ----------------------------------------------------------------- saída
    def quit(self) -> None:
        log.info("Saída solicitada pelo usuário")
        self.timer.stop()
        self.tray.hide()
        self.panel.close()
        self.app.quit()

"""Janela principal com menu lateral.

Fechar a janela (X) apenas esconde: o sistema continua rodando na bandeja.
Para sair de verdade: clique direito no ícone da bandeja -> Sair.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QHBoxLayout, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QWidget

from app import APP_NAME, __version__
from app.core.context import AppContext
from app.ui.pages.agenda_page import AgendaPage
from app.ui.pages.base import Page, PlaceholderPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.logs_page import LogsPage
from app.ui.pages.settings_page import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext, icon: QIcon) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.setWindowIcon(icon)
        self.resize(1100, 720)
        self.setMinimumSize(QSize(860, 560))

        self.dashboard = DashboardPage(ctx.settings)
        self.agenda = AgendaPage(ctx.tasks)
        self.settings_page = SettingsPage(ctx.settings)
        self.logs = LogsPage(ctx.activity, ctx.paths.logs)

        pages: list[tuple[str, Page]] = [
            ("Dashboard", self.dashboard),
            ("Clientes", PlaceholderPage("Clientes", "Fase 3",
                "Cadastro de clientes, classificação (cliente / não cliente) e página individual.")),
            ("Conversas", PlaceholderPage("Conversas", "Fase 2",
                "Mensagens lidas do WhatsApp Web, salvas no banco.")),
            ("Pedidos", PlaceholderPage("Pedidos", "Fase 6",
                "Pedidos criados a partir das listas de músicas, com status editável.")),
            ("Agenda", self.agenda),
            ("Aprovações", PlaceholderPage("Mensagens aguardando aprovação", "Fase 5",
                "Respostas sugeridas que precisam do seu OK: Enviar, Editar ou Ignorar.")),
            ("Automações", PlaceholderPage("Automações", "Fase 5",
                "Ligar/desligar cada automação e editar os textos (templates).")),
            ("Configurações", self.settings_page),
            ("Logs", self.logs),
        ]

        self.sidebar = QListWidget(objectName="Sidebar")
        self.sidebar.setFixedWidth(200)
        self.stack = QStackedWidget()
        for name, page in pages:
            self.sidebar.addItem(QListWidgetItem(name))
            self.stack.addWidget(page)
        self.sidebar.currentRowChanged.connect(self._on_page_changed)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        self.sidebar.setCurrentRow(0)

    def _on_page_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if isinstance(page, Page):
            page.on_show()

    def show_page(self, page: Page) -> None:
        self.sidebar.setCurrentRow(self.stack.indexOf(page))

    def bring_to_front(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def update_snapshot(self, snapshot) -> None:
        self.dashboard.update_snapshot(snapshot)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Não encerra o programa: só esconde a janela.
        event.ignore()
        self.hide()

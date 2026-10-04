"""Tela Logs: registro de atividades + atalho para a pasta de arquivos de log."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from app.core.activity import ActivityLog
from app.database.database import DatabaseError
from app.database.models import LogCategory
from app.ui import theme
from app.ui.pages.base import Page

log = logging.getLogger("krb.ui.logs")

LEVEL_COLORS = {"ERROR": theme.RED, "WARNING": theme.YELLOW}


class LogsPage(Page):
    title = "Logs"

    def __init__(self, activity: ActivityLog, logs_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.activity = activity
        self.logs_dir = logs_dir

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Tipo:"))
        self.filter = QComboBox()
        self.filter.addItem("Todos", None)
        for cat in LogCategory:
            self.filter.addItem(cat.value.replace("_", " ").title(), cat.value)
        self.filter.currentIndexChanged.connect(self.reload)
        bar.addWidget(self.filter)
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self.reload)
        bar.addWidget(refresh)
        bar.addStretch(1)
        open_folder = QPushButton("Abrir pasta de logs")
        open_folder.clicked.connect(self._open_folder)
        bar.addWidget(open_folder)
        self.content.addLayout(bar)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Data/hora", "Tipo", "Contato", "Evento"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.content.addWidget(self.table, 1)

        hint = QLabel(
            f"Arquivos detalhados: {logs_dir} (krb.log = tudo, errors.log = só erros)", objectName="Muted"
        )
        hint.setWordWrap(True)
        self.content.addWidget(hint)

    def on_show(self) -> None:
        self.reload()

    def reload(self) -> None:
        try:
            rows = self.activity.recent(limit=500, category=self.filter.currentData())
        except DatabaseError:
            return  # erro já registrado no log
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            values = [row["timestamp"], row["category"], row.get("contact_name") or "", row["message"]]
            color = LEVEL_COLORS.get(row["level"])
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if color:
                    item.setForeground(QColor(color))
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.logs_dir)))

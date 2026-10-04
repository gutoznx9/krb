"""Tela Agenda (versão inicial: lista de tarefas pendentes).

Calendário, filtros e lembretes com notificação chegam na Fase 7.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QHeaderView, QPushButton, QTableWidget, QTableWidgetItem

from app.core.timeutil import from_db
from app.database.database import DatabaseError
from app.database.models import TaskStatus
from app.scheduler.tasks import TaskRepository
from app.ui.pages.base import Page
from app.ui.task_dialog import PRIORITY_LABELS


class AgendaPage(Page):
    title = "Agenda"
    new_task_requested = Signal()
    status_change_requested = Signal(int, str)

    def __init__(self, tasks: TaskRepository, parent=None) -> None:
        super().__init__(parent)
        self.tasks = tasks

        buttons = QHBoxLayout()
        new_btn = QPushButton("+ Nova tarefa", objectName="Primary")
        new_btn.clicked.connect(self.new_task_requested.emit)
        done_btn = QPushButton("Concluir selecionada")
        done_btn.clicked.connect(lambda: self._change_selected(TaskStatus.CONCLUIDA))
        cancel_btn = QPushButton("Cancelar selecionada")
        cancel_btn.clicked.connect(lambda: self._change_selected(TaskStatus.CANCELADA))
        for b in (new_btn, done_btn, cancel_btn):
            buttons.addWidget(b)
        buttons.addStretch(1)
        self.content.addLayout(buttons)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Quando", "Título", "Cliente", "Prioridade", "Descrição"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.content.addWidget(self.table, 1)

    def on_show(self) -> None:
        self.reload()

    def reload(self) -> None:
        try:
            rows = self.tasks.upcoming(limit=500)
        except DatabaseError:
            return  # erro já registrado no log
        self.table.setRowCount(len(rows))
        for r, task in enumerate(rows):
            due = from_db(task.get("due_at"))
            values = [
                due.strftime("%d/%m/%Y %H:%M") if due else "(sem horário)",
                task["title"],
                task.get("contact_name") or "",
                PRIORITY_LABELS.get(task["priority"], task["priority"]),
                task.get("description") or "",
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, task["id"])
                self.table.setItem(r, c, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)

    def _change_selected(self, status: TaskStatus) -> None:
        items = self.table.selectedItems()
        if items:
            self.status_change_requested.emit(items[0].data(Qt.ItemDataRole.UserRole), str(status))

"""Janela "Nova tarefa"."""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QDateTime, QTime
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
)

from app.database.database import Database, DatabaseError
from app.database.models import TaskPriority
from app.scheduler.tasks import NewTask

PRIORITY_LABELS = {TaskPriority.BAIXA: "Baixa", TaskPriority.MEDIA: "Média", TaskPriority.ALTA: "Alta"}


class TaskDialog(QDialog):
    def __init__(self, db: Database, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nova tarefa")
        self.setMinimumWidth(380)
        self.result_task: NewTask | None = None

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Ex.: Conferir pagamento do Carlos")

        self.contact_combo = QComboBox()
        self.contact_combo.addItem("(nenhum)", None)
        try:
            for row in db.query_all(
                "SELECT id, name, phone FROM contacts WHERE is_group = 0 ORDER BY name COLLATE NOCASE"
            ):
                self.contact_combo.addItem(row["name"] or row["phone"] or f"#{row['id']}", row["id"])
        except DatabaseError:
            pass  # sem lista de clientes, mas a tarefa ainda pode ser criada

        self.has_time = QCheckBox("Definir data e horário")
        self.has_time.setChecked(True)
        default_dt = (datetime.now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        self.due_edit = QDateTimeEdit(QDateTime(default_dt))
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.has_time.toggled.connect(self.due_edit.setEnabled)

        self.priority_combo = QComboBox()
        for value, label in PRIORITY_LABELS.items():
            self.priority_combo.addItem(label, value)
        self.priority_combo.setCurrentIndex(1)

        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText("Detalhes (opcional)")
        self.description_edit.setFixedHeight(80)

        form = QFormLayout()
        form.addRow("Título*", self.title_edit)
        form.addRow("Cliente", self.contact_combo)
        form.addRow(self.has_time)
        form.addRow("Quando", self.due_edit)
        form.addRow("Prioridade", self.priority_combo)
        form.addRow("Descrição", self.description_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Salvar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Nova tarefa", "Informe um título para a tarefa.")
            return
        due = None
        if self.has_time.isChecked():
            qdt = self.due_edit.dateTime()
            qdt.setTime(QTime(qdt.time().hour(), qdt.time().minute()))
            due = qdt.toPython()
        self.result_task = NewTask(
            title=title,
            due_at=due,
            description=self.description_edit.toPlainText(),
            priority=self.priority_combo.currentData(),
            contact_id=self.contact_combo.currentData(),
        )
        self.accept()

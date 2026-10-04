"""Tarefas da agenda (criar, listar, concluir).

Na Fase 1 já dá para criar e ver tarefas no painel flutuante.
Lembretes com notificação do Windows chegam na Fase 7 (scheduler/reminders.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.timeutil import now_str, to_db
from app.database.database import Database
from app.database.models import TaskPriority, TaskStatus


@dataclass
class NewTask:
    title: str
    due_at: datetime | None = None
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIA
    contact_id: int | None = None


class TaskRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(self, task: NewTask) -> int:
        title = task.title.strip()
        if not title:
            raise ValueError("A tarefa precisa de um título.")
        ts = now_str()
        return self.db.execute(
            "INSERT INTO tasks (title, contact_id, description, due_at, priority, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                title,
                task.contact_id,
                task.description.strip(),
                to_db(task.due_at) if task.due_at else None,
                str(task.priority),
                str(TaskStatus.PENDENTE),
                ts,
                ts,
            ),
        )

    def get(self, task_id: int) -> dict | None:
        return self.db.query_one("SELECT * FROM tasks WHERE id = ?", (task_id,))

    def set_status(self, task_id: int, status: TaskStatus) -> None:
        ts = now_str()
        completed = ts if status == TaskStatus.CONCLUIDA else None
        self.db.execute(
            "UPDATE tasks SET status = ?, updated_at = ?, completed_at = ? WHERE id = ?",
            (str(status), ts, completed, task_id),
        )

    def upcoming(self, limit: int = 5) -> list[dict]:
        """Tarefas pendentes, das mais próximas para as mais distantes.

        Tarefas sem horário aparecem depois das que têm horário.
        """
        return self.db.query_all(
            "SELECT t.*, c.name AS contact_name FROM tasks t "
            "LEFT JOIN contacts c ON c.id = t.contact_id "
            "WHERE t.status = ? "
            "ORDER BY t.due_at IS NULL, t.due_at, t.id LIMIT ?",
            (str(TaskStatus.PENDENTE), limit),
        )

"""Números e listas mostrados no painel flutuante e no Dashboard.

Só faz leituras no banco. A interface chama estas funções periodicamente.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.database.database import Database
from app.database.models import OPEN_ORDER_STATUSES, CustomerClass, MessageDirection, OrderStatus, PendingStatus


@dataclass
class DashboardStats:
    customers_waiting: int = 0
    orders_today: int = 0
    awaiting_payment: int = 0
    in_preparation: int = 0
    ready: int = 0
    auto_replies_today: int = 0
    pending_approvals: int = 0


class DashboardService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def _count_orders(self, status: OrderStatus) -> int:
        return int(self.db.query_value("SELECT COUNT(*) FROM orders WHERE status = ?", (str(status),), 0))

    def stats(self) -> DashboardStats:
        q = self.db.query_value
        return DashboardStats(
            customers_waiting=int(
                q(
                    "SELECT COUNT(DISTINCT cv.contact_id) FROM conversations cv "
                    "JOIN contacts c ON c.id = cv.contact_id "
                    "WHERE cv.awaiting_reply = 1 AND c.classification != ?",
                    (str(CustomerClass.NAO_CLIENTE),),
                    0,
                )
            ),
            orders_today=int(
                q("SELECT COUNT(*) FROM orders WHERE date(created_at) = date('now', 'localtime')", (), 0)
            ),
            awaiting_payment=self._count_orders(OrderStatus.AGUARDANDO_PAGAMENTO),
            in_preparation=self._count_orders(OrderStatus.EM_PREPARACAO),
            ready=self._count_orders(OrderStatus.PRONTO),
            auto_replies_today=int(
                q(
                    "SELECT COUNT(*) FROM messages WHERE direction = ? AND sent_by_system = 1 "
                    "AND date(timestamp) = date('now', 'localtime')",
                    (str(MessageDirection.OUT),),
                    0,
                )
            ),
            pending_approvals=int(
                q("SELECT COUNT(*) FROM pending_responses WHERE status = ?", (str(PendingStatus.PENDENTE),), 0)
            ),
        )

    def open_orders(self, limit: int = 5) -> list[dict]:
        placeholders = ",".join("?" * len(OPEN_ORDER_STATUSES))
        return self.db.query_all(
            "SELECT o.id, o.status, o.updated_at, c.name AS contact_name, c.phone "
            "FROM orders o JOIN contacts c ON c.id = o.contact_id "
            f"WHERE o.status IN ({placeholders}) "
            "ORDER BY o.updated_at DESC LIMIT ?",
            (*[str(s) for s in OPEN_ORDER_STATUSES], limit),
        )

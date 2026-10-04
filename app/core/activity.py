"""Registro de atividades do negócio (aparece na tela Logs).

Exemplo do que será gravado nas próximas fases:
    14:31:07 - MENSAGEM_RECEBIDA - João
    14:31:08 - CLASSIFICACAO - CLIENTE_CONFIRMADO
    14:31:09 - AUTOMACAO - SEND_CATALOG

Cada evento vai para a tabela `logs` do banco E para o arquivo logs/krb.log.
Se o banco falhar, o evento ainda fica no arquivo (nunca derruba o sistema).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.timeutil import now_str
from app.database.database import Database, DatabaseError
from app.database.models import LogCategory

log = logging.getLogger("krb.activity")


class ActivityLog:
    def __init__(self, db: Database) -> None:
        self.db = db

    def record(
        self,
        category: LogCategory | str,
        message: str,
        *,
        contact_id: int | None = None,
        details: dict[str, Any] | None = None,
        level: str = "INFO",
    ) -> None:
        category = str(category)
        log.log(getattr(logging, level, logging.INFO), "[%s] %s", category, message)
        try:
            self.db.execute(
                "INSERT INTO logs (timestamp, level, category, contact_id, message, details) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    now_str(),
                    level,
                    category,
                    contact_id,
                    message,
                    json.dumps(details, ensure_ascii=False, default=str) if details else None,
                ),
            )
        except DatabaseError:
            log.error("Evento não pôde ser gravado no banco (ficou só no arquivo): %s", message)

    def error(self, message: str, **kwargs: Any) -> None:
        self.record(LogCategory.ERRO, message, level="ERROR", **kwargs)

    def recent(self, limit: int = 300, category: str | None = None) -> list[dict]:
        sql = (
            "SELECT l.*, c.name AS contact_name FROM logs l "
            "LEFT JOIN contacts c ON c.id = l.contact_id "
        )
        params: list[Any] = []
        if category:
            sql += "WHERE l.category = ? "
            params.append(category)
        sql += "ORDER BY l.id DESC LIMIT ?"
        params.append(limit)
        return self.db.query_all(sql, params)

    def purge_older_than(self, days: int) -> int:
        """Apaga eventos antigos do banco (os arquivos têm rotação própria)."""
        return self.db.execute_rowcount(
            "DELETE FROM logs WHERE timestamp < datetime('now', 'localtime', ?)", (f"-{int(days)} days",)
        )

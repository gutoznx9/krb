"""Acesso ao banco SQLite (data/app.db).

- Cada thread recebe sua própria conexão (o WhatsApp vai rodar em outra
  thread na Fase 2, e o SQLite não permite compartilhar conexões).
- Modo WAL: leitura e escrita ao mesmo tempo sem travar a interface.
- Se o banco estiver bloqueado, tenta de novo algumas vezes; se ainda
  falhar, registra no log e levanta DatabaseError para quem chamou decidir
  o que fazer (o sistema não cai por causa disso).
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

log = logging.getLogger("krb.database")

BUSY_TIMEOUT_MS = 10_000
LOCK_RETRIES = 3


class DatabaseError(Exception):
    """Erro de banco já registrado no log. Pode ser tratado por quem chamou."""


def _is_locked(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._local = threading.local()
        self._all_connections: list[sqlite3.Connection] = []
        self._conn_lock = threading.Lock()

    # ------------------------------------------------------------ conexão
    def connection(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                self.path,
                timeout=BUSY_TIMEOUT_MS / 1000,
                isolation_level=None,  # controlamos transações manualmente
                check_same_thread=True,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            self._local.conn = conn
            with self._conn_lock:
                self._all_connections.append(conn)
        return conn

    def close(self) -> None:
        """Fecha todas as conexões (chamado ao sair do programa)."""
        with self._conn_lock:
            for conn in self._all_connections:
                try:
                    conn.close()
                except sqlite3.Error:
                    pass
            self._all_connections.clear()
        self._local = threading.local()

    # ------------------------------------------------------- execução segura
    def _run(self, func, description: str):
        last_exc: Exception | None = None
        for attempt in range(1, LOCK_RETRIES + 1):
            try:
                return func(self.connection())
            except sqlite3.OperationalError as exc:
                last_exc = exc
                if _is_locked(exc) and attempt < LOCK_RETRIES:
                    log.warning("Banco bloqueado (%s), tentativa %d/%d", description, attempt, LOCK_RETRIES)
                    time.sleep(0.5 * attempt)
                    continue
                break
            except sqlite3.Error as exc:
                last_exc = exc
                break
        log.error("Erro no banco (%s): %s", description, last_exc)
        raise DatabaseError(f"{description}: {last_exc}") from last_exc

    def execute(self, sql: str, params: Sequence[Any] | dict = ()) -> int:
        """Executa INSERT/UPDATE/DELETE. Retorna o id inserido (lastrowid)."""
        return self._run(lambda c: c.execute(sql, params).lastrowid, sql.split()[0])

    def execute_rowcount(self, sql: str, params: Sequence[Any] | dict = ()) -> int:
        """Executa e retorna quantas linhas foram afetadas."""
        return self._run(lambda c: c.execute(sql, params).rowcount, sql.split()[0])

    def query_all(self, sql: str, params: Sequence[Any] | dict = ()) -> list[dict]:
        return self._run(lambda c: [dict(r) for r in c.execute(sql, params).fetchall()], "SELECT")

    def query_one(self, sql: str, params: Sequence[Any] | dict = ()) -> dict | None:
        def run(c):
            row = c.execute(sql, params).fetchone()
            return dict(row) if row else None

        return self._run(run, "SELECT")

    def query_value(self, sql: str, params: Sequence[Any] | dict = (), default: Any = None) -> Any:
        row = self._run(lambda c: c.execute(sql, params).fetchone(), "SELECT")
        return row[0] if row and row[0] is not None else default

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Agrupa vários comandos: ou tudo é gravado, ou nada é.

        with db.transaction() as conn:
            conn.execute(...)
            conn.execute(...)
        """
        conn = self.connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as exc:
            log.error("Não foi possível iniciar transação: %s", exc)
            raise DatabaseError(str(exc)) from exc
        try:
            yield conn
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        else:
            try:
                conn.execute("COMMIT")
            except sqlite3.Error as exc:
                conn.execute("ROLLBACK")
                log.error("Falha ao gravar transação: %s", exc)
                raise DatabaseError(str(exc)) from exc

    # ------------------------------------------------------------- backup
    def backup_to(self, target: Path) -> None:
        """Cópia segura do banco (funciona mesmo com o banco aberto)."""
        target.parent.mkdir(parents=True, exist_ok=True)
        dest = sqlite3.connect(target)
        try:
            self.connection().backup(dest)
        finally:
            dest.close()

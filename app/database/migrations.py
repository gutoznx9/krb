"""Migrations: evolução do banco sem apagar dados.

Como funciona:
- A tabela schema_migrations guarda quais versões já foram aplicadas.
- Ao iniciar, o sistema aplica somente as versões novas, em ordem.
- Antes de alterar um banco que já tem dados, é feito um backup automático
  em data/backups/.
- Cada migration roda dentro de uma transação: se der erro, nada é alterado.

Para mudar o banco no futuro: NUNCA edite uma migration antiga.
Adicione uma nova função no final da lista MIGRATIONS (versão seguinte).
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.core.timeutil import now_str
from app.database.database import Database, DatabaseError

log = logging.getLogger("krb.migrations")


def _execute_script(conn: sqlite3.Connection, script: str) -> None:
    """Executa vários comandos SQL dentro da transação atual.

    (conn.executescript não serve: ele faz COMMIT automático no meio.)
    """
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            conn.execute(buffer)
            buffer = ""
    if buffer.strip():
        raise ValueError(f"Comando SQL incompleto na migration: {buffer.strip()[:80]}")


# ---------------------------------------------------------------- versão 1
def _m001_initial_schema(conn: sqlite3.Connection) -> None:
    _execute_script(
        conn,
        """
        CREATE TABLE contacts (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            name                  TEXT,
            phone                 TEXT UNIQUE,
            wa_id                 TEXT,                 -- identificador do chat no WhatsApp
            is_group              INTEGER NOT NULL DEFAULT 0,
            classification        TEXT NOT NULL DEFAULT 'DESCONHECIDO',
            classification_score  REAL NOT NULL DEFAULT 0,
            classification_source TEXT NOT NULL DEFAULT 'AUTO',   -- AUTO ou MANUAL
            first_contact         TEXT,
            last_contact          TEXT,
            total_orders          INTEGER NOT NULL DEFAULT 0,
            notes                 TEXT NOT NULL DEFAULT '',
            automation_enabled    INTEGER NOT NULL DEFAULT 1,
            summary               TEXT NOT NULL DEFAULT '',       -- resumo para a IA
            created_at            TEXT NOT NULL,
            updated_at            TEXT NOT NULL
        );
        CREATE INDEX idx_contacts_classification ON contacts(classification);
        CREATE INDEX idx_contacts_last_contact ON contacts(last_contact);
        CREATE INDEX idx_contacts_wa_id ON contacts(wa_id);

        CREATE TABLE conversations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id       INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            status           TEXT NOT NULL DEFAULT 'ABERTA',
            awaiting_reply   INTEGER NOT NULL DEFAULT 0,   -- cliente esperando resposta
            unread_count     INTEGER NOT NULL DEFAULT 0,
            last_intent      TEXT,
            last_message_at  TEXT,
            summary          TEXT NOT NULL DEFAULT '',
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        );
        CREATE INDEX idx_conversations_contact ON conversations(contact_id);
        CREATE INDEX idx_conversations_awaiting ON conversations(awaiting_reply);

        CREATE TABLE messages (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id        INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            conversation_id   INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
            external_id       TEXT UNIQUE,              -- id do WhatsApp: evita duplicar
            direction         TEXT NOT NULL,            -- IN ou OUT
            from_me           INTEGER NOT NULL DEFAULT 0,
            sent_by_system    INTEGER NOT NULL DEFAULT 0, -- 1 = enviada pela automação
            body              TEXT NOT NULL DEFAULT '',
            timestamp         TEXT NOT NULL,
            intent            TEXT,
            intent_confidence REAL,
            processed         INTEGER NOT NULL DEFAULT 0,
            created_at        TEXT NOT NULL
        );
        CREATE INDEX idx_messages_contact_time ON messages(contact_id, timestamp);
        CREATE INDEX idx_messages_processed ON messages(processed);
        CREATE INDEX idx_messages_timestamp ON messages(timestamp);

        CREATE TABLE orders (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id         INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            status             TEXT NOT NULL DEFAULT 'NOVO',
            total_amount       REAL,
            notes              TEXT NOT NULL DEFAULT '',
            source_message_id  INTEGER REFERENCES messages(id) ON DELETE SET NULL,
            created_at         TEXT NOT NULL,
            updated_at         TEXT NOT NULL
        );
        CREATE INDEX idx_orders_status ON orders(status);
        CREATE INDEX idx_orders_contact ON orders(contact_id);
        CREATE INDEX idx_orders_created ON orders(created_at);

        CREATE TABLE order_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            position    INTEGER NOT NULL DEFAULT 0,
            title       TEXT NOT NULL DEFAULT '',
            artist      TEXT NOT NULL DEFAULT '',
            url         TEXT NOT NULL DEFAULT '',
            raw_text    TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL
        );
        CREATE INDEX idx_order_items_order ON order_items(order_id);

        CREATE TABLE tasks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT NOT NULL,
            contact_id    INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
            description   TEXT NOT NULL DEFAULT '',
            due_at        TEXT,                       -- 'AAAA-MM-DD HH:MM:SS'
            priority      TEXT NOT NULL DEFAULT 'MEDIA',
            status        TEXT NOT NULL DEFAULT 'PENDENTE',
            notified      INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            completed_at  TEXT
        );
        CREATE INDEX idx_tasks_status_due ON tasks(status, due_at);

        CREATE TABLE message_templates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            key         TEXT NOT NULL UNIQUE,
            name        TEXT NOT NULL,
            body        TEXT NOT NULL,
            enabled     INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL
        );

        CREATE TABLE automation_rules (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            key               TEXT NOT NULL UNIQUE,
            name              TEXT NOT NULL,
            description       TEXT NOT NULL DEFAULT '',
            intent            TEXT,
            action            TEXT NOT NULL,
            template_key      TEXT,
            enabled           INTEGER NOT NULL DEFAULT 0,
            cooldown_minutes  INTEGER,                -- vazio = usa o padrão das configurações
            created_at        TEXT NOT NULL,
            updated_at        TEXT NOT NULL
        );

        CREATE TABLE pending_responses (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id          INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            message_id          INTEGER REFERENCES messages(id) ON DELETE SET NULL,
            intent              TEXT,
            confidence          REAL,
            action              TEXT,
            suggested_response  TEXT NOT NULL DEFAULT '',
            final_response      TEXT,
            reason              TEXT NOT NULL DEFAULT '',
            status              TEXT NOT NULL DEFAULT 'PENDENTE',
            created_at          TEXT NOT NULL,
            resolved_at         TEXT
        );
        CREATE INDEX idx_pending_status ON pending_responses(status);

        -- Estado interno do sistema (chave/valor). As configurações que VOCÊ
        -- edita ficam em config/settings.json.
        CREATE TABLE settings (
            key         TEXT PRIMARY KEY,
            value       TEXT,
            updated_at  TEXT NOT NULL
        );

        -- Registro de atividades (mensagem recebida, intenção, envio, erro...)
        CREATE TABLE logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            level       TEXT NOT NULL DEFAULT 'INFO',
            category    TEXT NOT NULL,
            contact_id  INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
            message     TEXT NOT NULL,
            details     TEXT
        );
        CREATE INDEX idx_logs_timestamp ON logs(timestamp);
        CREATE INDEX idx_logs_category ON logs(category);
        CREATE INDEX idx_logs_contact ON logs(contact_id);
        """
    )


# ---------------------------------------------------------------- versão 2
# Textos iniciais: você pode editar tudo depois (tela Automações - Fase 5).
# Marcadores como {empresa} são preenchidos com as Configurações.
_DEFAULT_TEMPLATES = [
    ("SAUDACAO", "Saudação", "Olá! Tudo bem? Como posso ajudar?"),
    (
        "PRECO",
        "Preço",
        "Trabalhamos com pacotes de músicas para karaokê. Me diga aproximadamente quantas "
        "músicas você procura que eu verifico a melhor opção para você.",
    ),
    ("CATALOGO", "Catálogo", "Aqui está o nosso catálogo: {link_catalogo}"),
    ("PEDIDO", "Pedido", "Pode me enviar os nomes ou links das músicas que você deseja."),
    ("PIX", "Dados de pagamento", "{dados_pagamento}"),
    ("AGRADECIMENTO", "Agradecimento", "Eu que agradeço! Qualquer coisa é só chamar."),
]

# (key, nome, descrição, intenção, ação, template, ativada?)
_DEFAULT_RULES = [
    ("responder_saudacao", "Responder saudação", "", "SAUDACAO", "SEND_TEMPLATE", "SAUDACAO", 1),
    ("enviar_catalogo", "Enviar catálogo", "", "PEDIR_CATALOGO", "SEND_CATALOG", "CATALOGO", 1),
    ("responder_preco", "Responder preço", "", "PEDIR_PRECO", "SEND_TEMPLATE", "PRECO", 1),
    ("pedir_lista", "Pedir lista de músicas", "", "QUER_COMPRAR", "SEND_TEMPLATE", "PEDIDO", 1),
    ("enviar_pix", "Enviar PIX automaticamente", "", "DUVIDA_PAGAMENTO", "SEND_PAYMENT_INFO", "PIX", 0),
    (
        "confirmar_pagamento",
        "Confirmar pagamento automaticamente",
        "",
        "PAGAMENTO_REALIZADO",
        "CONFIRM_PAYMENT",
        None,
        0,
    ),
]


def _m002_seed_templates_and_rules(conn: sqlite3.Connection) -> None:
    ts = now_str()
    conn.executemany(
        "INSERT OR IGNORE INTO message_templates (key, name, body, enabled, created_at, updated_at) "
        "VALUES (?, ?, ?, 1, ?, ?)",
        [(k, n, b, ts, ts) for k, n, b in _DEFAULT_TEMPLATES],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO automation_rules "
        "(key, name, description, intent, action, template_key, enabled, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(*r, ts, ts) for r in _DEFAULT_RULES],
    )


# Lista oficial. Apenas ADICIONE itens no final.
MIGRATIONS: list[tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "estrutura inicial", _m001_initial_schema),
    (2, "templates e regras padrão", _m002_seed_templates_and_rules),
]


def current_version(db: Database) -> int:
    db.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )
    return int(db.query_value("SELECT MAX(version) FROM schema_migrations", default=0))


def run_migrations(db: Database, backup_dir: Path | None = None) -> int:
    """Aplica as migrations pendentes. Retorna a versão final do banco."""
    version = current_version(db)
    pending = [m for m in MIGRATIONS if m[0] > version]
    if not pending:
        log.info("Banco de dados atualizado (versão %d)", version)
        return version

    if version > 0 and backup_dir is not None:
        backup_file = backup_dir / f"app_v{version}_{datetime.now():%Y%m%d_%H%M%S}.db"
        db.backup_to(backup_file)
        log.info("Backup do banco criado antes da atualização: %s", backup_file)

    for number, name, func in pending:
        log.info("Aplicando migration %d: %s", number, name)
        try:
            with db.transaction() as conn:
                func(conn)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?)",
                    (number, name, now_str()),
                )
        except Exception as exc:
            log.exception("Falha na migration %d (%s). Nenhuma alteração dela foi gravada.", number, name)
            raise DatabaseError(f"Falha ao atualizar banco (migration {number}): {exc}") from exc
        version = number
    log.info("Banco de dados na versão %d", version)
    return version

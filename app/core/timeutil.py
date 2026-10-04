"""Funções de data/hora.

Padrão do sistema: datas gravadas no banco como texto no horário LOCAL do PC,
no formato 'AAAA-MM-DD HH:MM:SS'. Assim dá para ler direto no banco e comparar
com datetime('now', 'localtime') do SQLite.
"""

from __future__ import annotations

from datetime import datetime

DB_FORMAT = "%Y-%m-%d %H:%M:%S"


def now_str() -> str:
    return datetime.now().strftime(DB_FORMAT)


def to_db(value: datetime) -> str:
    return value.strftime(DB_FORMAT)


def from_db(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, DB_FORMAT)
    except ValueError:
        return None

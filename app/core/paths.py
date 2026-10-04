"""Caminhos de pastas do sistema (dados, logs, configurações).

Tudo fica dentro da pasta do projeto, para ser fácil de achar e de fazer backup.
A variável de ambiente KRB_HOME permite usar outra pasta (usado nos testes).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _detect_base_dir() -> Path:
    env = os.environ.get("KRB_HOME")
    if env:
        return Path(env).resolve()
    if getattr(sys, "frozen", False):  # executável gerado no futuro (Fase 9)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


class Paths:
    """Agrupa todos os caminhos usados pelo sistema."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base = Path(base_dir) if base_dir else _detect_base_dir()
        self.data = self.base / "data"
        self.backups = self.data / "backups"
        self.logs = self.base / "logs"
        self.config = self.base / "config"
        self.database_file = self.data / "app.db"
        self.settings_file = self.config / "settings.json"
        self.whatsapp_profile = self.data / "whatsapp_profile"

    def ensure(self) -> None:
        """Cria as pastas que não existirem (nunca apaga nada)."""
        for folder in (self.data, self.backups, self.logs, self.config):
            folder.mkdir(parents=True, exist_ok=True)

"""Configuração dos logs em arquivo.

Arquivos gerados na pasta logs/:
- krb.log     -> tudo (INFO ou mais), um arquivo por dia, guarda N dias
- errors.log  -> somente avisos e erros, para achar problemas rápido

Também instala "ganchos" que registram qualquer erro não tratado
(inclusive em outras threads) em vez de deixar o programa fechar sozinho.
"""

from __future__ import annotations

import logging
import sys
import threading
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(threadName)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(log_dir: Path, level: str = "INFO", retention_days: int = 30) -> None:
    global _configured
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    if _configured:
        root.setLevel(level)
        return

    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))

    main_handler = TimedRotatingFileHandler(
        log_dir / "krb.log", when="midnight", backupCount=max(1, int(retention_days)), encoding="utf-8"
    )
    main_handler.setFormatter(formatter)
    root.addHandler(main_handler)

    error_handler = RotatingFileHandler(
        log_dir / "errors.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)
    root.addHandler(error_handler)

    # Console (útil quando rodar pelo terminal). Com pythonw não há console.
    if sys.stderr is not None:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        root.addHandler(console)

    _install_exception_hooks()
    _configured = True


def _install_exception_hooks() -> None:
    crash_log = logging.getLogger("krb.crash")

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        crash_log.critical("Erro não tratado", exc_info=(exc_type, exc_value, exc_tb))

    def handle_thread_exception(args: threading.ExceptHookArgs):
        crash_log.critical(
            "Erro não tratado na thread %s",
            getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception

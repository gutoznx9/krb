"""AppContext: monta e guarda as peças principais do sistema.

Em vez de cada módulo criar suas próprias conexões e configurações, todos
recebem este "contexto". Isso deixa o projeto modular e fácil de testar.
Este arquivo NÃO depende da interface gráfica.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app import APP_NAME, __version__
from app.config import SettingsManager
from app.core.activity import ActivityLog
from app.core.dashboard_service import DashboardService
from app.core.logging_setup import setup_logging
from app.core.paths import Paths
from app.database.database import Database
from app.database.migrations import run_migrations
from app.database.models import LogCategory
from app.scheduler.tasks import TaskRepository

log = logging.getLogger("krb.context")


@dataclass
class AppContext:
    paths: Paths
    settings: SettingsManager
    db: Database
    activity: ActivityLog
    tasks: TaskRepository
    dashboard: DashboardService

    def shutdown(self) -> None:
        log.info("Encerrando %s", APP_NAME)
        try:
            self.activity.record(LogCategory.SISTEMA, "Sistema encerrado")
        finally:
            self.db.close()


def build_context(paths: Paths | None = None) -> AppContext:
    """Prepara pastas, logs, configurações e banco. Levanta exceção se o banco falhar."""
    paths = paths or Paths()
    paths.ensure()

    settings = SettingsManager(paths.settings_file)
    # logs primeiro com padrão, para registrar problemas ao ler as configurações
    setup_logging(paths.logs)
    settings.load()
    setup_logging(
        paths.logs,
        level=settings.get("system.log_level", "INFO"),
        retention_days=settings.get("system.log_retention_days", 30),
    )
    log.info("=== %s %s iniciando (pasta: %s) ===", APP_NAME, __version__, paths.base)

    db = Database(paths.database_file)
    run_migrations(db, backup_dir=paths.backups)

    activity = ActivityLog(db)
    try:
        removed = activity.purge_older_than(int(settings.get("system.log_retention_days", 30)))
        if removed:
            log.info("%d eventos antigos removidos do registro", removed)
    except Exception:
        log.exception("Falha ao limpar eventos antigos (ignorado)")

    ctx = AppContext(
        paths=paths,
        settings=settings,
        db=db,
        activity=activity,
        tasks=TaskRepository(db),
        dashboard=DashboardService(db),
    )
    activity.record(LogCategory.SISTEMA, f"Sistema iniciado (versão {__version__})")
    return ctx

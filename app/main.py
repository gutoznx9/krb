"""Ponto de entrada do KRB Assistant.

Como executar (na pasta do projeto, com o ambiente virtual ativado):
    python -m app.main
"""

from __future__ import annotations

import logging
import signal
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from app import APP_NAME
from app.core.context import build_context
from app.core.paths import Paths

log = logging.getLogger("krb.main")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("KRB")
    # Fechar janelas não encerra o programa: ele continua na bandeja.
    app.setQuitOnLastWindowClosed(False)

    # Importado aqui para o QApplication já existir
    from app.ui.single_instance import SingleInstance

    instance = SingleInstance()
    if instance.already_running():
        print("KRB Assistant já está aberto; a janela existente foi exibida.")
        return 0

    paths = Paths()
    try:
        ctx = build_context(paths)
    except Exception as exc:
        log.exception("Falha ao iniciar")
        QMessageBox.critical(
            None,
            APP_NAME,
            f"Não foi possível iniciar o sistema:\n\n{exc}\n\nDetalhes em: {paths.logs / 'errors.log'}",
        )
        return 1

    from app.ui.controller import UiController

    controller = UiController(app, ctx)
    instance.activated.connect(controller.show_main_window)
    controller.start()

    # Permite fechar com Ctrl+C quando rodando pelo terminal
    signal.signal(signal.SIGINT, lambda *_: controller.quit())
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: None)  # deixa o Python processar o Ctrl+C
    heartbeat.start(500)

    exit_code = app.exec()
    ctx.shutdown()
    log.info("Programa finalizado (código %s)", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

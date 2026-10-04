"""Garante que só exista UM KRB Assistant aberto.

Se você abrir o programa de novo, a cópia nova apenas avisa a que já está
rodando (que mostra a janela principal) e fecha. Isso evita dois robôs
respondendo o mesmo WhatsApp.
"""

from __future__ import annotations

import getpass
import logging
import re

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger("krb.single_instance")


def _server_name() -> str:
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    return "KRBAssistant-" + re.sub(r"[^A-Za-z0-9_-]", "_", user)


class SingleInstance(QObject):
    activated = Signal()  # outra cópia pediu para mostrar a janela

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.name = _server_name()
        self.server: QLocalServer | None = None

    def already_running(self) -> bool:
        """True se já existe uma cópia aberta (e ela foi avisada)."""
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if socket.waitForConnected(500):
            socket.write(b"show")
            socket.flush()
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            return True
        self._listen()
        return False

    def _listen(self) -> None:
        QLocalServer.removeServer(self.name)  # limpa resto de execução que travou
        self.server = QLocalServer(self)
        if not self.server.listen(self.name):
            log.warning("Não foi possível ativar controle de instância única: %s", self.server.errorString())
            return
        self.server.newConnection.connect(self._on_connection)

    def _on_connection(self) -> None:
        while self.server and self.server.hasPendingConnections():
            conn = self.server.nextPendingConnection()
            conn.readyRead.connect(lambda c=conn: self._read(c))
            if conn.bytesAvailable():  # dados podem ter chegado antes da conexão do sinal
                self._read(conn)

    def _read(self, conn: QLocalSocket) -> None:
        if bytes(conn.readAll()).strip() == b"show":
            log.info("Outra cópia foi aberta; mostrando a janela existente")
            self.activated.emit()
        conn.disconnectFromServer()

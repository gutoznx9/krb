"""Painel flutuante compacto (sempre no topo, preso a um canto, arrastável).

Este arquivo só cuida da APARÊNCIA e do comportamento da janela.
Os dados chegam prontos pelo método update_snapshot() (enviados pelo controller).
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config import MODE_APPROVAL, MODE_AUTOMATIC, MODE_MONITOR, SettingsManager
from app.core.timeutil import from_db
from app.database.models import ORDER_STATUS_LABELS, OrderStatus
from app.ui import theme

MARGIN = 12
WIDTH = 300
MAX_ROWS = 5

MODE_LABELS = {MODE_AUTOMATIC: "Automático", MODE_APPROVAL: "Aprovação", MODE_MONITOR: "Somente monitoramento"}


def plural(n: int, singular: str, plural_text: str) -> str:
    return f"{n} {singular if n == 1 else plural_text}"


class FloatingPanel(QWidget):
    open_main_requested = Signal()
    new_task_requested = Signal()
    complete_task_requested = Signal(int)

    def __init__(self, settings: SettingsManager) -> None:
        super().__init__(None)
        self.settings = settings
        self._drag_offset: QPoint | None = None
        self._dragged = False

        self.setWindowTitle("KRB Assistant")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(theme.FLOATING_STYLESHEET)
        self.setFixedWidth(WIDTH)
        self._build()
        self.apply_settings()

    # ------------------------------------------------------------ montagem
    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.card = QFrame(objectName="FloatingCard")
        outer.addWidget(self.card)
        root = QVBoxLayout(self.card)
        root.setContentsMargins(14, 10, 10, 12)
        root.setSpacing(4)

        # Cabeçalho
        header = QHBoxLayout()
        header.setSpacing(6)
        self.wa_dot = QLabel()
        self.wa_dot.setStyleSheet(theme.dot_style(theme.GRAY, 8))
        header.addWidget(self.wa_dot)
        header.addWidget(QLabel("KRB ASSISTANT", objectName="FloatingTitle"))
        header.addStretch(1)
        self.collapse_btn = self._header_button("–", "Recolher / expandir", self.toggle_collapsed)
        header.addWidget(self.collapse_btn)
        header.addWidget(self._header_button("□", "Abrir janela principal", self.open_main_requested.emit))
        header.addWidget(self._header_button("×", "Esconder (continua na bandeja)", self.hide_to_tray))
        root.addLayout(header)

        self.status_line = QLabel(objectName="StatusLine")
        root.addWidget(self.status_line)

        # Corpo (some quando recolhido)
        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 4, 0, 0)
        body.setSpacing(3)

        self.ind_waiting = self._indicator(body, theme.RED)
        self.ind_payment = self._indicator(body, theme.YELLOW)
        self.ind_ready = self._indicator(body, theme.GREEN)

        body.addWidget(QLabel("PRÓXIMAS TAREFAS", objectName="SectionTitle"))
        self.tasks_box = QVBoxLayout()
        self.tasks_box.setSpacing(2)
        body.addLayout(self.tasks_box)

        body.addWidget(QLabel("PEDIDOS", objectName="SectionTitle"))
        self.orders_box = QVBoxLayout()
        self.orders_box.setSpacing(2)
        body.addLayout(self.orders_box)

        new_task = QPushButton("+ Nova tarefa", objectName="NewTaskButton")
        new_task.setCursor(Qt.CursorShape.PointingHandCursor)
        new_task.clicked.connect(self.new_task_requested.emit)
        body.addSpacing(6)
        body.addWidget(new_task)

        root.addWidget(self.body)

    def _header_button(self, text: str, tip: str, slot) -> QPushButton:
        btn = QPushButton(text, objectName="HeaderButton")
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(slot)
        return btn

    def _indicator(self, layout: QVBoxLayout, color: str) -> QLabel:
        row = QHBoxLayout()
        row.setSpacing(8)
        dot = QLabel()
        dot.setStyleSheet(theme.dot_style(color))
        text = QLabel(objectName="RowText")
        row.addWidget(dot)
        row.addWidget(text, 1)
        layout.addLayout(row)
        return text

    # ---------------------------------------------------------------- dados
    def update_snapshot(self, snapshot) -> None:
        stats = snapshot.stats
        self.ind_waiting.setText(plural(stats.customers_waiting, "cliente aguardando", "clientes aguardando"))
        self.ind_payment.setText(plural(stats.awaiting_payment, "pagamento pendente", "pagamentos pendentes"))
        self.ind_ready.setText(plural(stats.ready, "pedido pronto", "pedidos prontos"))
        self._fill_tasks(snapshot.tasks)
        self._fill_orders(snapshot.orders)
        self._update_status_line(snapshot)
        self._refit()

    def _update_status_line(self, snapshot) -> None:
        paused = self.settings.get("automation.paused")
        mode = MODE_LABELS.get(self.settings.get("automation.mode"), "?")
        auto = "PAUSADA" if paused else mode
        self.status_line.setText(f"{snapshot.whatsapp_status}\nAutomação: {auto}")
        color = {"connected": theme.GREEN, "connecting": theme.YELLOW, "disconnected": theme.RED}.get(
            snapshot.whatsapp_state, theme.GRAY
        )
        self.wa_dot.setStyleSheet(theme.dot_style(color, 8))
        self.wa_dot.setToolTip(snapshot.whatsapp_status)

    @staticmethod
    def _clear(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                FloatingPanel._clear(item.layout())
                item.layout().deleteLater()

    def _fill_tasks(self, tasks: list[dict]) -> None:
        self._clear(self.tasks_box)
        if not tasks:
            self.tasks_box.addWidget(QLabel("Nenhuma tarefa pendente", objectName="EmptyText"))
            return
        now = datetime.now()
        for task in tasks[:MAX_ROWS]:
            due = from_db(task.get("due_at"))
            if due is None:
                when = "--:--"
            elif due.date() == now.date():
                when = due.strftime("%H:%M")
            else:
                when = due.strftime("%d/%m %H:%M")
            text = f"{when} - {task['title']}"
            if task.get("contact_name"):
                text += f" ({task['contact_name']})"
            row = QHBoxLayout()
            label = QLabel(text, objectName="RowOverdue" if due and due < now else "RowText")
            label.setToolTip(task.get("description") or task["title"])
            done = QPushButton("✓", objectName="RowButton")
            done.setToolTip("Marcar como concluída")
            done.setCursor(Qt.CursorShape.PointingHandCursor)
            done.clicked.connect(lambda _=False, tid=task["id"]: self.complete_task_requested.emit(tid))
            row.addWidget(label, 1)
            row.addWidget(done)
            self.tasks_box.addLayout(row)

    def _fill_orders(self, orders: list[dict]) -> None:
        self._clear(self.orders_box)
        if not orders:
            self.orders_box.addWidget(QLabel("Nenhum pedido em aberto", objectName="EmptyText"))
            return
        for order in orders[:MAX_ROWS]:
            try:
                status = ORDER_STATUS_LABELS[OrderStatus(order["status"])]
            except ValueError:
                status = order["status"]
            name = order.get("contact_name") or order.get("phone") or "?"
            self.orders_box.addWidget(QLabel(f"#{order['id']} {name} - {status}", objectName="RowText"))

    # ---------------------------------------------- aparência / configuração
    def apply_settings(self) -> None:
        """Aplica 'sempre no topo', transparência e posição a partir das configurações."""
        cfg = self.settings.get("ui.floating")
        was_visible = self.isVisible()
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if cfg.get("always_on_top", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        if self.windowFlags() != flags:
            self.setWindowFlags(flags)  # trocar flags esconde a janela
        self.setWindowOpacity(float(cfg.get("opacity", 0.95)))
        self.body.setVisible(not cfg.get("collapsed", False))
        self.collapse_btn.setText("+" if cfg.get("collapsed") else "–")
        self._refit()
        if was_visible:
            self.show()

    def _refit(self) -> None:
        self.adjustSize()
        self.place()

    def toggle_collapsed(self) -> None:
        collapsed = not self.settings.get("ui.floating.collapsed", False)
        self.settings.set("ui.floating.collapsed", collapsed)
        self.body.setVisible(not collapsed)
        self.collapse_btn.setText("+" if collapsed else "–")
        self._refit()

    def hide_to_tray(self) -> None:
        self.settings.set("ui.floating.visible", False)
        self.hide()

    def show_panel(self) -> None:
        self.settings.set("ui.floating.visible", True)
        self.place()
        self.show()
        self.raise_()

    # ------------------------------------------------------------- posição
    def _screen_geometry(self, point: QPoint | None = None):
        screen = None
        if point is not None:
            screen = QGuiApplication.screenAt(point)
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def place(self) -> None:
        """Posiciona no canto configurado ou na posição livre salva."""
        cfg = self.settings.get("ui.floating")
        x, y = cfg.get("x"), cfg.get("y")
        if not cfg.get("snap_to_corner", True) and x is not None and y is not None:
            point = QPoint(int(x), int(y))
            if QGuiApplication.screenAt(point) is not None:  # monitor ainda existe
                self.move(point)
                return
        self._move_to_corner(cfg.get("corner", "top-right"), self._screen_geometry(self.geometry().center()))

    def _move_to_corner(self, corner: str, area) -> None:
        w, h = self.width(), self.height()
        left = area.left() + MARGIN
        right = area.right() - w - MARGIN + 1
        top = area.top() + MARGIN
        bottom = area.bottom() - h - MARGIN + 1
        positions = {
            "top-left": (left, top),
            "top-right": (right, top),
            "bottom-left": (left, bottom),
            "bottom-right": (right, bottom),
        }
        self.move(*positions.get(corner, positions["top-right"]))

    def _nearest_corner(self, area) -> str:
        center = self.geometry().center()
        vertical = "top" if center.y() < area.center().y() else "bottom"
        horizontal = "left" if center.x() < area.center().x() else "right"
        return f"{vertical}-{horizontal}"

    # ------------------------------------------------------- arrastar (mouse)
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._dragged = False
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            self._dragged = True
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is None:
            return
        self._drag_offset = None
        if not self._dragged:
            return
        area = self._screen_geometry(self.geometry().center())
        if self.settings.get("ui.floating.snap_to_corner", True):
            corner = self._nearest_corner(area)
            self.settings.set("ui.floating.corner", corner)
            self._move_to_corner(corner, area)
        else:
            pos = self.pos()
            self.settings.update_many({"ui.floating.x": pos.x(), "ui.floating.y": pos.y()})
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.open_main_requested.emit()

"""Tela Configurações.

Lê e grava em config/settings.json pelo SettingsManager.
Nada de dados do negócio fica no código: tudo é preenchido aqui.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTime, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import FLOATING_CORNERS, SettingsManager
from app.ui.pages.base import Page

WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
CORNER_LABELS = {
    "top-right": "Superior direito",
    "top-left": "Superior esquerdo",
    "bottom-right": "Inferior direito",
    "bottom-left": "Inferior esquerdo",
}


class SettingsPage(Page):
    title = "Configurações"
    saved = Signal()

    def __init__(self, settings: SettingsManager, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        inner = QWidget()
        form_area = QVBoxLayout(inner)
        form_area.setSpacing(12)
        scroll.setWidget(inner)
        self.content.addWidget(scroll, 1)

        form_area.addWidget(self._business_box())
        form_area.addWidget(self._hours_box())
        form_area.addWidget(self._automation_box())
        form_area.addWidget(self._ai_box())
        form_area.addWidget(self._notifications_box())
        form_area.addWidget(self._floating_box())
        form_area.addWidget(self._system_box())
        form_area.addStretch(1)

        bar = QHBoxLayout()
        bar.addStretch(1)
        revert = QPushButton("Desfazer alterações")
        revert.clicked.connect(self.load_values)
        save = QPushButton("Salvar configurações", objectName="Primary")
        save.clicked.connect(self.save_values)
        bar.addWidget(revert)
        bar.addWidget(save)
        self.content.addLayout(bar)

        self.load_values()

    # ------------------------------------------------------------- grupos
    def _business_box(self) -> QGroupBox:
        box = QGroupBox("Empresa")
        form = QFormLayout(box)
        self.company = QLineEdit()
        self.welcome = QPlainTextEdit()
        self.welcome.setFixedHeight(70)
        self.catalog = QLineEdit()
        self.catalog.setPlaceholderText("https://...")
        self.payment = QPlainTextEdit()
        self.payment.setFixedHeight(90)
        self.payment.setPlaceholderText("Ex.: Chave PIX, nome do favorecido, banco...")
        form.addRow("Nome da empresa", self.company)
        form.addRow("Mensagem inicial", self.welcome)
        form.addRow("Link do catálogo", self.catalog)
        form.addRow("Dados de pagamento", self.payment)
        return box

    def _hours_box(self) -> QGroupBox:
        box = QGroupBox("Horário de atendimento")
        form = QFormLayout(box)
        self.hours_enabled = QCheckBox("Responder automaticamente só dentro do horário")
        self.hours_start = QTimeEdit()
        self.hours_end = QTimeEdit()
        for t in (self.hours_start, self.hours_end):
            t.setDisplayFormat("HH:mm")
        days_row = QHBoxLayout()
        self.day_checks = []
        for name in WEEKDAYS:
            check = QCheckBox(name)
            self.day_checks.append(check)
            days_row.addWidget(check)
        days_row.addStretch(1)
        form.addRow(self.hours_enabled)
        form.addRow("Início", self.hours_start)
        form.addRow("Fim", self.hours_end)
        form.addRow("Dias", days_row)
        return box

    def _automation_box(self) -> QGroupBox:
        box = QGroupBox("Automação")
        form = QFormLayout(box)
        self.auto_threshold = self._confidence_spin()
        self.approval_threshold = self._confidence_spin()
        self.reply_delay = QSpinBox()
        self.reply_delay.setRange(0, 600)
        self.reply_delay.setSuffix(" s")
        self.cooldown = QSpinBox()
        self.cooldown.setRange(0, 24 * 60)
        self.cooldown.setSuffix(" min")
        self.ignore_groups = QCheckBox("Ignorar grupos (recomendado)")
        form.addRow("Confiança para responder sozinho", self.auto_threshold)
        form.addRow("Confiança mínima para sugerir", self.approval_threshold)
        explain = QLabel(
            "Acima do 1º valor: pode responder sozinho (se a automação permitir). "
            "Entre os dois: vai para aprovação. Abaixo do 2º: só avisa no painel.",
            objectName="Muted",
        )
        explain.setWordWrap(True)
        form.addRow(explain)
        form.addRow("Tempo entre respostas", self.reply_delay)
        form.addRow("Não repetir mesma resposta por", self.cooldown)
        form.addRow(self.ignore_groups)
        return box

    def _ai_box(self) -> QGroupBox:
        box = QGroupBox("Inteligência artificial (Fase 8)")
        form = QFormLayout(box)
        self.ai_provider = QComboBox()
        self.ai_provider.addItem("Sem IA (somente regras)", "none")
        self.ai_provider.addItem("Ollama (local)", "ollama")
        self.ollama_url = QLineEdit()
        self.ollama_model = QLineEdit()
        self.ai_timeout = QSpinBox()
        self.ai_timeout.setRange(5, 300)
        self.ai_timeout.setSuffix(" s")
        form.addRow("Provedor", self.ai_provider)
        form.addRow("Endereço do Ollama", self.ollama_url)
        form.addRow("Modelo Ollama", self.ollama_model)
        form.addRow("Tempo limite", self.ai_timeout)
        return box

    def _notifications_box(self) -> QGroupBox:
        box = QGroupBox("Notificações")
        layout = QVBoxLayout(box)
        self.notify_enabled = QCheckBox("Mostrar notificações do Windows")
        self.notify_tasks = QCheckBox("Lembrar tarefas no horário")
        self.notify_messages = QCheckBox("Avisar nova mensagem de cliente")
        for w in (self.notify_enabled, self.notify_tasks, self.notify_messages):
            layout.addWidget(w)
        return box

    def _floating_box(self) -> QGroupBox:
        box = QGroupBox("Painel flutuante")
        form = QFormLayout(box)
        self.float_on_top = QCheckBox("Sempre no topo")
        self.float_snap = QCheckBox("Prender no canto mais próximo ao soltar")
        self.float_corner = QComboBox()
        for corner in FLOATING_CORNERS:
            self.float_corner.addItem(CORNER_LABELS[corner], corner)
        self.float_opacity = QSlider(Qt.Orientation.Horizontal)
        self.float_opacity.setRange(30, 100)
        self.opacity_label = QLabel()
        self.float_opacity.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(self.float_opacity, 1)
        opacity_row.addWidget(self.opacity_label)
        self.refresh_seconds = QSpinBox()
        self.refresh_seconds.setRange(2, 300)
        self.refresh_seconds.setSuffix(" s")
        form.addRow(self.float_on_top)
        form.addRow(self.float_snap)
        form.addRow("Canto", self.float_corner)
        form.addRow("Opacidade", opacity_row)
        form.addRow("Atualizar a cada", self.refresh_seconds)
        return box

    def _system_box(self) -> QGroupBox:
        box = QGroupBox("Sistema")
        form = QFormLayout(box)
        self.start_with_windows = QCheckBox("Iniciar com o Windows (disponível na Fase 9)")
        self.start_with_windows.setEnabled(False)
        self.show_main_on_start = QCheckBox("Abrir janela principal ao iniciar")
        self.log_level = QComboBox()
        for level in ("DEBUG", "INFO", "WARNING", "ERROR"):
            self.log_level.addItem(level, level)
        self.log_retention = QSpinBox()
        self.log_retention.setRange(1, 365)
        self.log_retention.setSuffix(" dias")
        form.addRow(self.start_with_windows)
        form.addRow(self.show_main_on_start)
        form.addRow("Nível de log", self.log_level)
        form.addRow("Guardar logs por", self.log_retention)
        return box

    @staticmethod
    def _confidence_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 1.0)
        spin.setSingleStep(0.05)
        spin.setDecimals(2)
        return spin

    @staticmethod
    def _set_combo(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(max(0, index))

    # ------------------------------------------------------ carregar/salvar
    def load_values(self) -> None:
        s = self.settings.get
        self.company.setText(s("business.company_name", ""))
        self.welcome.setPlainText(s("business.welcome_message", ""))
        self.catalog.setText(s("business.catalog_link", ""))
        self.payment.setPlainText(s("business.payment_info", ""))

        hours = s("business.business_hours", {})
        self.hours_enabled.setChecked(bool(hours.get("enabled")))
        self.hours_start.setTime(QTime.fromString(hours.get("start", "08:00"), "HH:mm"))
        self.hours_end.setTime(QTime.fromString(hours.get("end", "22:00"), "HH:mm"))
        days = set(hours.get("days", []))
        for i, check in enumerate(self.day_checks):
            check.setChecked(i in days)

        self.auto_threshold.setValue(float(s("automation.auto_threshold", 0.9)))
        self.approval_threshold.setValue(float(s("automation.approval_threshold", 0.65)))
        self.reply_delay.setValue(int(s("automation.reply_delay_seconds", 5)))
        self.cooldown.setValue(int(s("automation.cooldown_minutes", 30)))
        self.ignore_groups.setChecked(bool(s("automation.ignore_groups", True)))

        self._set_combo(self.ai_provider, s("ai.provider", "none"))
        self.ollama_url.setText(s("ai.ollama_url", ""))
        self.ollama_model.setText(s("ai.ollama_model", ""))
        self.ai_timeout.setValue(int(s("ai.timeout_seconds", 30)))

        self.notify_enabled.setChecked(bool(s("notifications.enabled", True)))
        self.notify_tasks.setChecked(bool(s("notifications.task_reminders", True)))
        self.notify_messages.setChecked(bool(s("notifications.new_customer_message", True)))

        self.float_on_top.setChecked(bool(s("ui.floating.always_on_top", True)))
        self.float_snap.setChecked(bool(s("ui.floating.snap_to_corner", True)))
        self._set_combo(self.float_corner, s("ui.floating.corner", "top-right"))
        self.float_opacity.setValue(int(round(float(s("ui.floating.opacity", 0.95)) * 100)))
        self.opacity_label.setText(f"{self.float_opacity.value()}%")
        self.refresh_seconds.setValue(int(s("ui.refresh_seconds", 10)))

        self.start_with_windows.setChecked(bool(s("system.start_with_windows", False)))
        self.show_main_on_start.setChecked(bool(s("ui.show_main_window_on_start", False)))
        self._set_combo(self.log_level, s("system.log_level", "INFO"))
        self.log_retention.setValue(int(s("system.log_retention_days", 30)))

    def save_values(self) -> None:
        if self.approval_threshold.value() > self.auto_threshold.value():
            QMessageBox.warning(
                self,
                "Configurações",
                "A confiança mínima para sugerir não pode ser maior que a confiança para responder sozinho.",
            )
            return
        if self.hours_start.time() >= self.hours_end.time() and self.hours_enabled.isChecked():
            QMessageBox.warning(self, "Configurações", "O horário de início deve ser antes do horário de fim.")
            return
        self.settings.update_many(
            {
                "business.company_name": self.company.text().strip(),
                "business.welcome_message": self.welcome.toPlainText().strip(),
                "business.catalog_link": self.catalog.text().strip(),
                "business.payment_info": self.payment.toPlainText().strip(),
                "business.business_hours": {
                    "enabled": self.hours_enabled.isChecked(),
                    "start": self.hours_start.time().toString("HH:mm"),
                    "end": self.hours_end.time().toString("HH:mm"),
                    "days": [i for i, c in enumerate(self.day_checks) if c.isChecked()],
                },
                "automation.auto_threshold": round(self.auto_threshold.value(), 2),
                "automation.approval_threshold": round(self.approval_threshold.value(), 2),
                "automation.reply_delay_seconds": self.reply_delay.value(),
                "automation.cooldown_minutes": self.cooldown.value(),
                "automation.ignore_groups": self.ignore_groups.isChecked(),
                "ai.provider": self.ai_provider.currentData(),
                "ai.ollama_url": self.ollama_url.text().strip(),
                "ai.ollama_model": self.ollama_model.text().strip(),
                "ai.timeout_seconds": self.ai_timeout.value(),
                "notifications.enabled": self.notify_enabled.isChecked(),
                "notifications.task_reminders": self.notify_tasks.isChecked(),
                "notifications.new_customer_message": self.notify_messages.isChecked(),
                "ui.floating.always_on_top": self.float_on_top.isChecked(),
                "ui.floating.snap_to_corner": self.float_snap.isChecked(),
                "ui.floating.corner": self.float_corner.currentData(),
                "ui.floating.opacity": self.float_opacity.value() / 100,
                "ui.refresh_seconds": self.refresh_seconds.value(),
                "ui.show_main_window_on_start": self.show_main_on_start.isChecked(),
                "system.log_level": self.log_level.currentData(),
                "system.log_retention_days": self.log_retention.value(),
            }
        )
        self.saved.emit()
        QMessageBox.information(self, "Configurações", "Configurações salvas.")

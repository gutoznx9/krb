"""Sistema de configurações (arquivo config/settings.json).

- DEFAULTS define TODAS as chaves possíveis e seus valores iniciais.
  Nada de dados do negócio (PIX, catálogo...) fica fixo no código: os padrões
  são vazios e você preenche pela tela de Configurações.
- O arquivo do usuário é mesclado com os padrões: quando uma atualização criar
  uma configuração nova, ela aparece sozinha sem apagar o que você já salvou.
- Se o arquivo estiver corrompido, ele é guardado como cópia (.corrupt-...)
  e o sistema continua com os padrões, registrando o problema no log.
- O salvamento é atômico (grava em arquivo temporário e troca), para não
  corromper o arquivo se o PC desligar no meio.

Uso:
    settings.get("automation.auto_threshold")
    settings.set("business.company_name", "KRB Karaokê")
    settings.save()
"""

from __future__ import annotations

import copy
import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("krb.config")

# Modos de operação da automação
MODE_AUTOMATIC = "AUTOMATICO"        # envia sozinho o que for autorizado e confiável
MODE_APPROVAL = "APROVACAO"          # tudo vira sugestão para você aprovar
MODE_MONITOR = "MONITORAMENTO"       # só lê e salva, nunca responde
AUTOMATION_MODES = (MODE_AUTOMATIC, MODE_APPROVAL, MODE_MONITOR)

FLOATING_CORNERS = ("top-right", "top-left", "bottom-right", "bottom-left")

DEFAULTS: dict[str, Any] = {
    "business": {
        "company_name": "",
        "welcome_message": "",
        "catalog_link": "",
        "payment_info": "",
        "business_hours": {
            "enabled": False,
            "start": "08:00",
            "end": "22:00",
            # 0 = segunda ... 6 = domingo
            "days": [0, 1, 2, 3, 4, 5, 6],
        },
    },
    "automation": {
        # Começa no modo mais seguro: só monitorar.
        "mode": MODE_MONITOR,
        "paused": False,
        "auto_threshold": 0.90,
        "approval_threshold": 0.65,
        "reply_delay_seconds": 5,
        "cooldown_minutes": 30,
        "ignore_groups": True,
    },
    "ai": {
        "provider": "none",  # "none" (só regras) ou "ollama"
        "ollama_url": "http://localhost:11434",
        "ollama_model": "llama3.1:8b",
        "timeout_seconds": 30,
    },
    "whatsapp": {
        "headless": False,
        "poll_interval_seconds": 3,
        "reconnect_delay_seconds": 15,
    },
    "notifications": {
        "enabled": True,
        "task_reminders": True,
        "new_customer_message": True,
    },
    "ui": {
        "refresh_seconds": 10,
        "show_main_window_on_start": False,
        "floating": {
            "visible": True,
            "always_on_top": True,
            "opacity": 0.95,
            "corner": "top-right",
            "snap_to_corner": True,
            "collapsed": False,
            # posição livre (usada quando snap_to_corner = False)
            "x": None,
            "y": None,
        },
    },
    "system": {
        "start_with_windows": False,
        "log_level": "INFO",
        "log_retention_days": 30,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Retorna base atualizado com os valores de override (recursivo)."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class SettingsManager:
    """Carrega, consulta e salva as configurações. Seguro para várias threads."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data: dict[str, Any] = copy.deepcopy(DEFAULTS)
        self._listeners: list[Callable[[str, Any], None]] = []

    # ------------------------------------------------------------------ carga
    def load(self) -> None:
        with self._lock:
            if not self.path.exists():
                log.info("Arquivo de configuração não existe; criando com valores padrão: %s", self.path)
                self._data = copy.deepcopy(DEFAULTS)
                self.save()
                return
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("conteúdo não é um objeto JSON")
            except (OSError, ValueError) as exc:
                backup = self.path.with_name(
                    f"{self.path.name}.corrupt-{datetime.now():%Y%m%d_%H%M%S}"
                )
                log.error("Configuração inválida (%s). Cópia salva em %s; usando padrões.", exc, backup)
                try:
                    os.replace(self.path, backup)
                except OSError:
                    log.exception("Não foi possível guardar cópia do arquivo corrompido")
                self._data = copy.deepcopy(DEFAULTS)
                self.save()
                return
            self._data = _deep_merge(DEFAULTS, raw)
            self._validate()
            # regrava para incluir chaves novas adicionadas em atualizações
            self.save()

    def _validate(self) -> None:
        """Corrige valores fora do esperado em vez de deixar o sistema quebrar."""
        auto = self._data["automation"]
        if auto.get("mode") not in AUTOMATION_MODES:
            log.warning("Modo de automação inválido (%r); usando %s", auto.get("mode"), MODE_MONITOR)
            auto["mode"] = MODE_MONITOR
        for key in ("auto_threshold", "approval_threshold"):
            try:
                auto[key] = min(1.0, max(0.0, float(auto[key])))
            except (TypeError, ValueError):
                auto[key] = DEFAULTS["automation"][key]
        if auto["approval_threshold"] > auto["auto_threshold"]:
            log.warning("approval_threshold maior que auto_threshold; ajustando")
            auto["approval_threshold"] = auto["auto_threshold"]
        floating = self._data["ui"]["floating"]
        if floating.get("corner") not in FLOATING_CORNERS:
            floating["corner"] = "top-right"
        try:
            floating["opacity"] = min(1.0, max(0.3, float(floating["opacity"])))
        except (TypeError, ValueError):
            floating["opacity"] = 0.95

    # --------------------------------------------------------------- consulta
    def get(self, dotted_key: str, default: Any = None) -> Any:
        with self._lock:
            node: Any = self._data
            for part in dotted_key.split("."):
                if not isinstance(node, dict) or part not in node:
                    return default
                node = node[part]
            return copy.deepcopy(node)

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)

    # -------------------------------------------------------------- alteração
    def set(self, dotted_key: str, value: Any, save: bool = True) -> None:
        with self._lock:
            parts = dotted_key.split(".")
            node = self._data
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            old = node.get(parts[-1])
            node[parts[-1]] = value
            if save:
                self.save()
        if old != value:
            for listener in list(self._listeners):
                try:
                    listener(dotted_key, value)
                except Exception:  # um ouvinte com erro não pode quebrar os outros
                    log.exception("Erro em ouvinte de configuração (%s)", dotted_key)

    def update_many(self, values: dict[str, Any]) -> None:
        """Altera várias chaves e salva uma vez só."""
        for key, value in values.items():
            self.set(key, value, save=False)
        with self._lock:
            self._validate()
            self.save()

    def add_listener(self, callback: Callable[[str, Any], None]) -> None:
        """Chamado como callback(chave, novo_valor) sempre que algo mudar."""
        self._listeners.append(callback)

    # ------------------------------------------------------------- gravação
    def save(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".json.tmp")
            try:
                tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, self.path)
            except OSError:
                log.exception("Falha ao salvar configurações em %s", self.path)

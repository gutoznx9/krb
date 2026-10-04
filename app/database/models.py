"""Valores fixos (categorias, status, intenções) usados em todo o sistema.

Ficam em um só lugar para não existir texto solto e diferente em cada módulo.
São StrEnum: o valor gravado no banco é o próprio texto (ex.: "PAGO").
"""

from __future__ import annotations

from enum import StrEnum


class CustomerClass(StrEnum):
    CLIENTE_CONFIRMADO = "CLIENTE_CONFIRMADO"
    PROVAVEL_CLIENTE = "PROVAVEL_CLIENTE"
    DESCONHECIDO = "DESCONHECIDO"
    NAO_CLIENTE = "NAO_CLIENTE"


class ClassificationSource(StrEnum):
    AUTO = "AUTO"        # decidido pelo sistema (regras/IA)
    MANUAL = "MANUAL"    # decidido por você -> sempre tem prioridade


class Intent(StrEnum):
    SAUDACAO = "SAUDACAO"
    PEDIR_PRECO = "PEDIR_PRECO"
    PEDIR_CATALOGO = "PEDIR_CATALOGO"
    QUER_COMPRAR = "QUER_COMPRAR"
    ENVIANDO_LISTA = "ENVIANDO_LISTA"
    DUVIDA_PAGAMENTO = "DUVIDA_PAGAMENTO"
    ENVIO_PIX = "ENVIO_PIX"
    PAGAMENTO_REALIZADO = "PAGAMENTO_REALIZADO"
    PERGUNTA_PRAZO = "PERGUNTA_PRAZO"
    PERGUNTA_ENTREGA = "PERGUNTA_ENTREGA"
    SUPORTE = "SUPORTE"
    AGRADECIMENTO = "AGRADECIMENTO"
    OUTRO = "OUTRO"


class MessageDirection(StrEnum):
    IN = "IN"    # recebida do cliente
    OUT = "OUT"  # enviada por você ou pelo sistema


class OrderStatus(StrEnum):
    NOVO = "NOVO"
    AGUARDANDO_CONFIRMACAO = "AGUARDANDO_CONFIRMACAO"
    AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    PAGO = "PAGO"
    EM_PREPARACAO = "EM_PREPARACAO"
    PRONTO = "PRONTO"
    ENTREGUE = "ENTREGUE"
    CANCELADO = "CANCELADO"


OPEN_ORDER_STATUSES = tuple(s for s in OrderStatus if s not in (OrderStatus.ENTREGUE, OrderStatus.CANCELADO))

ORDER_STATUS_LABELS = {
    OrderStatus.NOVO: "novo",
    OrderStatus.AGUARDANDO_CONFIRMACAO: "aguardando confirmação",
    OrderStatus.AGUARDANDO_PAGAMENTO: "aguardando pagamento",
    OrderStatus.PAGO: "pago",
    OrderStatus.EM_PREPARACAO: "em preparação",
    OrderStatus.PRONTO: "pronto",
    OrderStatus.ENTREGUE: "entregue",
    OrderStatus.CANCELADO: "cancelado",
}


class TaskStatus(StrEnum):
    PENDENTE = "PENDENTE"
    CONCLUIDA = "CONCLUIDA"
    CANCELADA = "CANCELADA"


class TaskPriority(StrEnum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"


class PendingStatus(StrEnum):
    PENDENTE = "PENDENTE"
    ENVIADA = "ENVIADA"
    IGNORADA = "IGNORADA"


class LogCategory(StrEnum):
    """Tipos de evento do registro de atividades (tela Logs)."""

    SISTEMA = "SISTEMA"
    MENSAGEM_RECEBIDA = "MENSAGEM_RECEBIDA"
    CLASSIFICACAO = "CLASSIFICACAO"
    INTENCAO = "INTENCAO"
    CONFIDENCE = "CONFIDENCE"
    AUTOMACAO = "AUTOMACAO"
    MENSAGEM_ENVIADA = "MENSAGEM_ENVIADA"
    ERRO = "ERRO"
    RECONEXAO = "RECONEXAO"
    ALTERACAO_MANUAL = "ALTERACAO_MANUAL"

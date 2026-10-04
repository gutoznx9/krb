# AGENTS.md — instruções para agentes de código (Codex, Claude etc.)

Este arquivo descreve o projeto KRB Assistant, o estado atual, as regras de
trabalho e a especificação das próximas fases. Leia inteiro antes de mudar algo.

## Sobre o dono do projeto

- Não é desenvolvedor experiente. **Responda sempre em português do Brasil.**
- Explique de forma simples o que está fazendo e por quê.
- Sempre diga **exatamente** quais comandos ele deve executar (Windows, `cmd`),
  a partir de qual pasta (o projeto fica em `C:\krb`).
- Gere código real e funcional, nunca só exemplos.

## Regras de trabalho (obrigatórias)

1. Projeto **modular**. Nada de código monolítico.
2. **Não reescreva arquivos inteiros sem necessidade**: faça edições pontuais.
3. Antes de começar uma fase nova, **leia o código existente** e rode os testes
   para não quebrar o que já funciona.
4. Implemente **uma fase por vez**. Não avance para a próxima fase até o dono
   confirmar que a atual funciona na máquina dele.
5. Ao encontrar um problema, **corrija a causa**, não esconda o erro.
6. Trate erros e reconexões. Nenhum erro simples pode derrubar o sistema inteiro.
7. Registre logs suficientes para diagnosticar problemas.
8. O sistema deve funcionar **sem IA** (modo só regras).
9. Ao terminar cada etapa: rode `.venv\Scripts\python.exe -m unittest discover -s tests`,
   adicione testes para o código novo e faça commit com mensagem clara.

## Ambiente

- Windows, Python 3.11+ (usa `enum.StrEnum`), ambiente virtual em `.venv`.
- `instalar.bat` cria o `.venv`, instala `requirements.txt` e roda os testes.
- `iniciar.bat` executa `python -m app.main`.
- O caminho do projeto deve ser curto (`C:\krb`): o PySide6 estoura o limite
  de 260 caracteres do Windows em pastas profundas (`tools/verificar_caminho.py`).
- Pastas `data/`, `logs/` e `config/settings.json` são do usuário e **nunca**
  vão para o git (contêm clientes, mensagens e dados de PIX).

## Arquitetura atual (Fase 1 concluída)

```
app/
  main.py                 entrada: QApplication, instância única, build_context, UiController
  config.py               SettingsManager + DEFAULTS (config/settings.json)
  core/
    paths.py              pastas (KRB_HOME sobrescreve a base; usado nos testes)
    logging_setup.py      logs/krb.log (diário), logs/errors.log, ganchos de exceção
    activity.py           ActivityLog: eventos do negócio -> tabela logs + arquivo
    context.py            AppContext / build_context(): monta tudo, sem depender de Qt
    dashboard_service.py  contagens e listas para painel/dashboard
    timeutil.py           datas como texto local 'AAAA-MM-DD HH:MM:SS'
  database/
    database.py           Database: conexão por thread, WAL, retentativa, DatabaseError
    migrations.py         migrations versionadas (schema_migrations) + backup automático
    models.py             StrEnums: CustomerClass, Intent, OrderStatus, TaskStatus, LogCategory...
  scheduler/tasks.py      TaskRepository (tarefas da agenda)
  ui/
    controller.py         UiController: liga telas, bandeja e serviços; refresh periódico (Snapshot)
    floating_panel.py     painel flutuante (sempre no topo, cantos, arrastar, recolher, opacidade)
    main_window.py        janela com menu lateral; fechar = esconder na bandeja
    tray.py               ícone da bandeja + notify()
    task_dialog.py        diálogo "Nova tarefa"
    single_instance.py    QLocalServer: impede duas cópias
    theme.py              cores, QSS, ícone desenhado
    pages/                dashboard, agenda, settings, logs, base (Page, PlaceholderPage)
  whatsapp/ crm/ ai/ automation/ orders/   reservados para as próximas fases
tests/test_core.py        testes sem interface gráfica (unittest)
```

### Convenções que devem ser seguidas

- **Banco**: sempre via `Database` (`execute`, `query_all`, `query_one`,
  `query_value`, `transaction()`). Erros viram `DatabaseError` (já logados);
  quem chama decide como seguir sem derrubar o programa.
- **Mudanças no banco**: somente adicionando uma nova função ao FINAL da lista
  `MIGRATIONS` em `app/database/migrations.py`. Nunca editar migrations antigas,
  nunca apagar o banco. Use `_execute_script` (não `executescript`, que faz COMMIT).
- **Configurações**: toda opção nova entra em `DEFAULTS` (`app/config.py`) e na
  tela `ui/pages/settings_page.py`. Nada de dados do negócio fixos no código
  (PIX, catálogo, nome da empresa, textos de resposta).
- **Valores fixos** (status, intenções, categorias): sempre os enums de `database/models.py`.
- **Eventos do negócio**: `ctx.activity.record(LogCategory.X, "texto", contact_id=...)`.
- **Novos serviços** são criados em `build_context()` e guardados no `AppContext`.
- **Interface** roda na thread principal do Qt. Trabalho demorado (Playwright,
  IA) roda em thread/worker separado e se comunica com a UI por sinais Qt.
  Cada thread usa sua própria conexão (o `Database` já faz isso).
- O resto do sistema **nunca** importa Playwright nem Ollama diretamente: só as
  interfaces `WhatsAppClient` e `AIProvider`.

## Tabelas existentes

contacts, conversations, messages (`external_id` UNIQUE, `direction` IN/OUT,
`from_me`, `sent_by_system`), orders, order_items, tasks, automation_rules,
message_templates, pending_responses, settings (estado interno chave/valor),
logs, schema_migrations. Templates (SAUDACAO, PRECO, CATALOGO, PEDIDO, PIX,
AGRADECIMENTO) e regras de automação iniciais já existem; "enviar_pix" e
"confirmar_pagamento" começam desligadas.

## Especificação das próximas fases

### FASE 2 — WhatsApp Web + leitura de mensagens
- `app/whatsapp/client.py`: interface abstrata `WhatsAppClient` com `start()`,
  `stop()`, `is_connected()`, `get_new_messages()`, `send_message(contact, message)`,
  `open_chat(contact)`. Estrutura de dados própria para mensagem (id externo,
  contato, nome, telefone, texto, horário, from_me, is_group).
- `app/whatsapp/playwright_client.py`: implementação com Playwright + Chromium em
  **perfil persistente** (`data/whatsapp_profile`), para não escanear QR Code toda vez.
- `app/whatsapp/selectors.py`: **todos** os seletores CSS/XPath centralizados aqui.
- `app/whatsapp/listener.py`: roda em thread própria; detecta mensagens novas,
  identifica contato/número/nome, texto, horário, enviada x recebida; evita
  duplicadas (`external_id`); salva no banco; **ignora grupos**; detecta
  desconexão, tenta reconectar com espera crescente, registra RECONEXAO/ERRO.
- Mostrar status do WhatsApp no painel e no Dashboard (campos `whatsapp_state`
  e `whatsapp_status` do `Snapshot` em `ui/controller.py`). Desconectado não
  encerra o programa: mostra "WhatsApp desconectado" e tenta reconectar.
- Adicionar `playwright` ao `requirements.txt` e explicar `playwright install chromium`.
- Nesta fase **nada é enviado automaticamente**.

### FASE 3 — CRM e classificação cliente / não cliente
- `crm/contacts.py`, `crm/conversations.py`, `crm/customer_classifier.py`.
- Sistema de **pontuação** (não chute): palavras como preço, valor, karaokê,
  música, vídeo, pacote, catálogo, quero comprar, como comprar, pix, pagamento;
  links do YouTube; listas de músicas; nomes de músicas em sequência; conversa
  anterior de compra; contato já cliente; pedido anterior.
- Categorias: CLIENTE_CONFIRMADO, PROVAVEL_CLIENTE, DESCONHECIDO, NAO_CLIENTE.
- "Marcar como cliente" / "Marcar como não cliente" manual **sempre** tem
  prioridade (`classification_source = MANUAL`). NAO_CLIENTE nunca recebe venda.
- Telas Clientes e Conversas; página do cliente com mensagens recentes, pedidos,
  status, observações, tarefas, última interação, automação ligada/desligada.

### FASE 4 — Detector de intenção
- Intenções do enum `Intent`. Retorno `{"intent": ..., "confidence": 0..1}`.
- Primeiro regras simples; IA só quando as regras não bastarem (via `AIProvider`).

### FASE 5 — Automação de respostas
- `automation/engine.py` é o **único** que decide enviar. A IA só devolve decisões
  estruturadas (`intent`, `confidence`, `suggested_response`, `action`).
- Limiares das configurações: `>= auto_threshold` pode responder sozinho se a
  regra estiver ativada; entre `approval_threshold` e `auto_threshold` vai para
  a fila `pending_responses`; abaixo, só avisa no painel.
- Respeitar: pausa (continua lendo/salvando, não envia), modos AUTOMATICO /
  APROVACAO / MONITORAMENTO, automação por contato, horário de atendimento,
  `reply_delay_seconds`, **cooldown por cliente** (não repetir a mesma resposta
  em X minutos), nunca responder mensagens do próprio sistema, evitar loops e
  sequências de mensagens.
- **Sempre revisão humana**: reembolso, reclamação séria, ameaça, problema
  jurídico, pagamento duvidoso, algo não entendido.
- Templates editáveis com marcadores (`{empresa}`, `{link_catalogo}`,
  `{dados_pagamento}`) preenchidos pelas configurações.
- Telas: "Mensagens aguardando aprovação" (Enviar / Editar / Ignorar) e
  Automações (ativar/desativar cada regra, editar templates).
- Registrar no log: mensagem recebida, classificação, intenção, confidence,
  automação executada, mensagem enviada, erro, alteração manual.

### FASE 6 — Pedidos
- `orders/song_parser.py` detecta listas de músicas (linhas "Música - Artista",
  links do YouTube, nomes em sequência). `orders/order_manager.py` cria pedido
  vinculado ao cliente com itens. Status do enum `OrderStatus`, alteráveis
  manualmente. Tela Pedidos.

### FASE 7 — Agenda
- Tarefas (já existe `TaskRepository`): título, cliente opcional, descrição,
  data/horário, prioridade, status PENDENTE/CONCLUIDA/CANCELADA.
- `scheduler/reminders.py`: notificação do Windows no horário (`TrayIcon.notify`),
  marcando `tasks.notified`. Tela Agenda completa.

### FASE 8 — IA / Ollama
- `ai/provider.py` (interface abstrata), `ai/rules_provider.py` (sem IA),
  `ai/ollama_provider.py`. Métodos: `classify_customer()`, `detect_intent()`,
  `extract_order_items()`, `generate_response()`, `summarize_conversation()`.
- Ordem antes de chamar IA: regras → histórico → templates → IA.
- Enviar **contexto resumido** (resumo do cliente + últimas mensagens), não a conversa inteira.
- Ollama offline → continua só com regras, sem travar. Preparado para outras APIs.

### FASE 9 — Polimento
- Opção "Iniciar com o Windows" (segura, ex.: atalho na pasta Inicializar
  usando `pythonw.exe`, sem terminal), instalador, minimizar na bandeja.

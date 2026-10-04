# KRB Assistant

Assistente local de atendimento para o negócio de músicas/karaokê: lê o WhatsApp,
organiza clientes e pedidos, sugere/envia respostas com segurança e mantém uma
agenda num painel flutuante na área de trabalho. Roda 24h no Windows.

**Status: FASE 1 concluída** (estrutura, banco, configurações, logs, interface, bandeja, painel flutuante).

---

## 1. Como instalar e rodar (Windows)

Pré-requisito: **Python 3.11 ou 3.12** instalado pelo site https://www.python.org/downloads/
(na instalação, marque **"Add python.exe to PATH"**).

**Coloque o projeto num caminho curto, como `C:\krb`.** O Windows não aceita
caminhos com mais de 260 caracteres, e o PySide6 cria pastas muito profundas;
em pastas como `Downloads\...\...` a instalação falha.

Abra a pasta do projeto no Explorer e dê **dois cliques** em:

| Arquivo        | Para quê                                                        |
|----------------|-----------------------------------------------------------------|
| `instalar.bat` | Cria o ambiente `.venv`, instala dependências e roda os testes. Rodar uma vez (e depois de cada atualização). |
| `iniciar.bat`  | Abre o KRB Assistant.                                           |

Se preferir pelo terminal (PowerShell ou Prompt de Comando), dentro da pasta do projeto:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\python.exe -m app.main
```

Fechar a janela principal **não** encerra o programa: ele continua no ícone da
bandeja (perto do relógio). Para sair: clique direito no ícone → **Sair**.

---

## 2. Arquitetura

O sistema é dividido em camadas. Cada camada só conversa com a de baixo por
meio de interfaces simples — assim dá para trocar uma peça (ex.: WhatsApp Web →
API oficial, Ollama → outra IA) sem mexer no resto.

```
┌──────────────────────────── INTERFACE (PySide6) ────────────────────────────┐
│ Painel flutuante · Janela principal (Dashboard, Clientes, ...) · Bandeja    │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ UiController (liga telas aos serviços)
┌──────────────────────────────▼──────────── SERVIÇOS ─────────────────────────┐
│ CRM · Pedidos · Agenda · AutomationEngine · Classificadores · Templates      │
└───────┬──────────────────────┬─────────────────────────────┬─────────────────┘
        │                      │                             │
┌───────▼────────┐   ┌─────────▼─────────┐        ┌──────────▼───────────┐
│ WhatsAppClient │   │  AIProvider       │        │ Banco SQLite         │
│ (interface)    │   │  (interface)      │        │ + migrations         │
│  └ Playwright  │   │  ├ RulesOnly      │        │ Configurações (JSON) │
│    (Web)       │   │  └ Ollama         │        │ Logs (arquivo + BD)  │
└────────────────┘   └───────────────────┘        └──────────────────────┘
```

### Fluxo de uma mensagem (Fases 2 a 8)

```
WhatsApp ─► Listener ─► CRM ─► Classifier ─► Intent ─► AutomationEngine ─► Resposta
```

1. **WhatsApp / Listener** (Fase 2): detecta mensagem nova, ignora grupos e
   mensagens já processadas (`external_id` único), salva no banco.
2. **CRM** (Fase 3): encontra ou cria o contato e atualiza a conversa.
3. **Classifier** (Fase 3): pontua se é cliente. Marcação **manual** sempre vence
   (ex.: "mãe = NÃO CLIENTE" → nunca recebe venda).
4. **Intent** (Fase 4): primeiro regras simples; IA só se as regras não bastarem.
   Retorna `{"intent": "...", "confidence": 0.93}`.
5. **AutomationEngine** (Fase 5): é o **único** que decide enviar algo. Verifica
   pausa, modo, automação ativada, cooldown, assuntos sensíveis e confiança:
   - `>= 0.90` → pode responder sozinho (se a automação for autorizada)
   - `0.65 a 0.89` → vai para "Mensagens aguardando aprovação"
   - `< 0.65` → não responde, só avisa no painel
6. **Resposta**: enviada pelo `WhatsAppClient` e registrada no log.

A IA **nunca executa ações**: só devolve decisões estruturadas.

---

## 3. Árvore de arquivos

Arquivos marcados com ✅ já existem (Fase 1). Os demais serão criados nas fases indicadas.

```
krb/
├── instalar.bat                  ✅ instala ambiente e dependências
├── iniciar.bat                   ✅ abre o programa
├── requirements.txt              ✅
├── app/
│   ├── main.py                   ✅ ponto de entrada
│   ├── config.py                 ✅ configurações (config/settings.json)
│   ├── core/
│   │   ├── paths.py              ✅ pastas do sistema
│   │   ├── logging_setup.py      ✅ logs em arquivo + captura de erros
│   │   ├── activity.py           ✅ registro de atividades (tela Logs)
│   │   ├── context.py            ✅ monta e liga as peças
│   │   ├── dashboard_service.py  ✅ números do painel
│   │   └── timeutil.py           ✅ datas
│   ├── database/
│   │   ├── database.py           ✅ conexão SQLite segura
│   │   ├── migrations.py         ✅ criação/atualização das tabelas
│   │   └── models.py             ✅ status, categorias, intenções
│   ├── whatsapp/                 Fase 2: client.py, playwright_client.py, listener.py, sender.py, selectors.py
│   ├── crm/                      Fase 3: contacts.py, conversations.py, customer_classifier.py
│   ├── ai/                       Fases 4/8: provider.py, rules_provider.py, ollama_provider.py, intent_detector.py, context_builder.py
│   ├── automation/               Fase 5: engine.py, rules.py, templates.py, safety.py
│   ├── orders/                   Fase 6: order_manager.py, song_parser.py
│   ├── scheduler/
│   │   ├── tasks.py              ✅ tarefas da agenda
│   │   └── reminders.py          Fase 7: notificações no horário
│   └── ui/
│       ├── controller.py         ✅ liga telas e serviços
│       ├── floating_panel.py     ✅ painel flutuante
│       ├── main_window.py        ✅ janela principal com menu lateral
│       ├── tray.py               ✅ ícone na bandeja
│       ├── task_dialog.py        ✅ "Nova tarefa"
│       ├── single_instance.py    ✅ impede duas cópias abertas
│       ├── theme.py              ✅ cores e estilo
│       └── pages/                ✅ dashboard, agenda, configurações, logs (+ futuras)
├── tests/                        ✅ testes automáticos
├── config/settings.json          (criado ao abrir; NÃO vai para o git)
├── data/app.db                   (banco; NÃO vai para o git)
├── data/backups/                 (backup automático antes de atualizar o banco)
└── logs/                         krb.log (tudo) e errors.log (só erros)
```

---

## 4. Banco de dados

Tabelas: `contacts`, `conversations`, `messages`, `orders`, `order_items`, `tasks`,
`automation_rules`, `message_templates`, `pending_responses`, `settings`, `logs`
(+ `schema_migrations`, controle interno).

- **Nunca é apagado** em atualizações. Alterações futuras entram como uma
  migration nova no fim da lista em `app/database/migrations.py`.
- Antes de aplicar uma migration num banco com dados, é feito backup em `data/backups/`.
- Templates e regras de automação iniciais são criados já editáveis.
  **"Enviar PIX" e "Confirmar pagamento" começam DESLIGADOS.**

## 5. Configurações

Tudo fica em `config/settings.json` e é editado pela tela **Configurações**.
Nenhum dado do negócio (PIX, catálogo, nome da empresa) fica no código.
O sistema começa no modo mais seguro: **Somente monitoramento**.

## 6. Logs

- `logs/krb.log`: tudo, um arquivo por dia.
- `logs/errors.log`: só avisos e erros — **primeiro lugar para olhar se algo der errado**.
- Tela **Logs** no programa: eventos do negócio (mensagem recebida, automação, alterações manuais...).

---

## 7. Plano de fases

| Fase | Conteúdo | Status |
|------|----------|--------|
| 1 | Estrutura, SQLite, configurações, logs, PySide6, bandeja, painel flutuante | ✅ |
| 2 | WhatsApp Web (Playwright, sessão persistente, leitura, reconexão) | |
| 3 | CRM e classificação cliente / não cliente | |
| 4 | Detector de intenção | |
| 5 | Automação de respostas, templates, aprovações | |
| 6 | Pedidos (detecção de lista de músicas) | |
| 7 | Agenda completa e notificações | |
| 8 | IA / Ollama | |
| 9 | Polimento, instalador, iniciar com o Windows | |

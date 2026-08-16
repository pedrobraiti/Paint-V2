# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-08-16 — versão 1.0.0 publicada

## Onde parei

Ciclo completo entregue. O Paint-V2 funciona de ponta a ponta (núcleo,
ferramentas, HUB, editor), tem 256 testes passando, foi empacotado
(`dist/Paint-V2/Paint-V2.exe`, 114 MB em pasta) e instalado na máquina do usuário
em `%LOCALAPPDATA%\Programs\Paint-V2`, com atalho no Menu Iniciar.

Publicado em <https://github.com/pedrobraiti/Paint-V2>, com a release
[v1.0.0](https://github.com/pedrobraiti/Paint-V2/releases/tag/v1.0.0) levando o
instalador anexado e CI rodando a suíte no Windows a cada push.

Não há tarefa pendente; o que vier agora são melhorias listadas em
`.claude/todo.md` (camadas, carimbo, gradiente, histórico visual).

## Contexto mental

A decisão que organiza o código inteiro está em `.claude/decisions.md`: **pincel =
ponta × modo**. Ponta (`core/brush_tips.py`) é a forma do carimbo; modo
(`core/brush_modes.py`) é o que acontece com os pixels sob ele. Por serem eixos
independentes, qualquer efeito funciona com qualquer ponta — que era o pedido
central do usuário. Há testes parametrizados que cruzam as 12 pontas com os 8
efeitos justamente para travar essa propriedade.

Duas armadilhas já resolvidas e que voltariam a morder:

1. `QPainter` sobre o documento **precisa** do gerenciador de contexto
   `tools/qt_bridge.painter_for`. Criar `QPainter(document_image(doc))` direto
   destrói o `QImage` temporário enquanto ele está sendo pintado, e o processo
   morre sem traceback.
2. Atalhos de uma letra (B, E, P, X…) ficam em `CanvasView.keyPressEvent`, não em
   `QAction`. Como `QAction` tem prioridade sobre o widget em foco, a letra seria
   roubada de quem estivesse digitando com a ferramenta de texto. Pelo mesmo
   motivo, Ctrl+C/V/X/Z e Delete passam por `MainWindow._forward_to_text_widget`.

## Próximo passo concreto

Nada obrigatório. Se o usuário voltar pedindo evolução, o item de maior impacto
da lista é **camadas** — hoje o documento é de camada única mais uma seleção
flutuante, e `core/document.py` teria de passar a compor uma pilha antes de
entregar o buffer ao `QImage`.

Ao lançar uma versão nova: subir `APP_VERSION` em `src/paintv2/__init__.py`,
`version` no `pyproject.toml`, `AppVersion` no `packaging/paintv2.iss` e os
números em `packaging/version_info.txt` — os quatro precisam bater.

## Em aberto / armadilhas

- O executável não é assinado: o SmartScreen vai avisar na primeira execução
  ("Mais informações" → "Executar assim mesmo"). Assinar exigiria um certificado
  de code signing pago.
- `dist/` e `build/` estão no `.gitignore` — o instalador vai por release, não
  pelo repositório.
- A `.spec` remove DLLs do Qt que o hook do PySide6 insiste em trazer (QML,
  Quick, PDF, OpenGL por software). Se alguma tela nova precisar de OpenGL ou
  SVG, revisar `UNREACHABLE_BINARIES` antes de investigar o erro.
- O tamanho de pincel é compartilhado entre todas as ferramentas de traço, por
  decisão de produto: mudar isso quebraria a expectativa registrada em
  `tools/settings.py`.

## Como retomar rápido

- Rodar: `& ".venv\Scripts\python.exe" -m paintv2`
- Testar: `& ".venv\Scripts\python.exe" -m pytest`  (256 testes, ~2 s)
- Empacotar: `& ".venv\Scripts\python.exe" scripts\build_app.py`
- Capturas do README: `& ".venv\Scripts\python.exe" scripts\capture_screenshots.py`
- Ler antes de mexer no motor de pincel: `.claude/decisions.md` e
  `src/paintv2/core/stroke.py` (o comentário do topo explica a acumulação em
  modo *screen*).

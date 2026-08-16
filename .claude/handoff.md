# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-08-16 — versão 1.0.0 pronta e empacotada

## Onde parei

O Paint-V2 está funcional de ponta a ponta: núcleo, ferramentas, HUB, editor,
testes (256 passando) e empacotamento. O executável foi gerado em
`dist/Paint-V2/Paint-V2.exe` (114 MB em pasta) e o instalador em
`dist/installer/Paint-V2-Setup-1.0.0.exe`. O app foi instalado na máquina do
usuário em `%LOCALAPPDATA%\Programs\Paint-V2` com atalho no Menu Iniciar.

Falta apenas publicar: criar o repositório público `Paint-V2` no GitHub, dar push
e anexar o instalador a uma release 1.0.0.

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

Criar o repositório e publicar:

```powershell
gh repo create Paint-V2 --public --source=. --remote=origin --push
gh release create v1.0.0 "dist/installer/Paint-V2-Setup-1.0.0.exe" --title "Paint-V2 1.0.0" --notes "..."
```

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

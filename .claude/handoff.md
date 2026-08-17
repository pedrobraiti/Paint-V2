# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-08-16 — versão 1.1.0 publicada, sessão encerrada

## Estado em uma linha

Projeto entregue e aprovado pelo usuário em uso real. Nada pendente: a 1.1.0 está
publicada, instalada na máquina dele, com README, badges, tópicos do repositório
e CI em dia. O que vier a seguir são melhorias do `todo.md`.

## Onde parei

A 1.1.0 responde ao primeiro uso real do usuário. Ele testou a 1.0.0, aprovou
(usou principalmente a saturação) e apontou seis coisas — todas atendidas:

1. **Tamanho do pincel travado em 500.** Agora o motor vai até `MAX_SIZE = 5000`;
   a rampa da barra de opções para em `BRUSH_SLIDER_MAX = 1000` e o campo ao lado
   aceita o resto. A rampa parou em 1000 porque acima disso cada pixel dela vira
   um salto grande demais para ajuste fino.
2. **Travamento em área grande.** Resolvido em `core/parallel.py`: cada carimbo é
   fatiado em faixas horizontais processadas em threads. Medido em 3840×2160 com
   pincel de 500 px — saturação 848 → 185 ms, desfoque 1874 → 667 ms, pintura
   742 → 229 ms. GPU foi avaliada e descartada (ver `decisions.md`).
3. **Ferramenta de contraste** — `ContrastMode`, contraste linear clássico.
4. **"Color ramp"** — virou `LevelsMode` ("Realce tonal"), curva em S sobre a
   luminância. A escolha da curva em vez de auto-níveis está em `decisions.md`:
   auto-níveis mediria estatística por faixa e sairia listrado.
5. **Botões de voltar/avançar e `Ctrl+Shift+Z`** — barra de ações rápidas
   (`MainWindow._build_toolbar`) reaproveitando as `QAction` do menu, e a ação de
   refazer agora tem dois atalhos.
6. **`Ctrl+Z` reiniciava o zoom.** `_after_history_step` só reenquadra quando o
   passo mudou as dimensões, comparando com `CanvasView.framed_size`.

285 testes passando, lint limpo, CI verde. README com badges de CI, release e
licença; repositório com descrição e tópicos.

## Contexto mental

A arquitetura central continua sendo **pincel = ponta × modo** (veja
`decisions.md`). O que mudou de estrutura foi o caminho quente do traço:

`StrokeEngine._apply_accumulated` agora (a) captura os ladrilhos do snapshot
**antes** de dividir o trabalho — é a única etapa que escreve no dicionário do
snapshot —, (b) fatia o retângulo com `split_into_bands(rect, mode.halo)` e (c)
roda as faixas em paralelo. Modos que leem vizinhos declaram `halo` (desfoque usa
o raio, nitidez usa 1) e recebem linhas extras que são descartadas ao escrever;
sem isso apareceria uma emenda a cada divisão — há teste para isso
(`test_banded_stroke_leaves_no_seams`).

O blend é o único modo `sequential`: carrega estado entre carimbos, então é
fatiado **sem** paralelismo e recebe `set_band()` antes de cada faixa para
alinhar o acumulador, que vive no tamanho do carimbo inteiro.

Armadilhas antigas que continuam valendo:

- `QPainter` sobre o documento só através do contexto `tools.qt_bridge.painter_for`;
  criar `QPainter(document_image(doc))` direto mata o processo sem traceback.
- Atalhos de uma letra ficam em `CanvasView.keyPressEvent`, não em `QAction`, para
  não roubar a tecla de quem digita com a ferramenta de texto. Os atalhos com
  Ctrl passam por `MainWindow._forward_to_text_widget`.

## Próximo passo concreto

Nada pendente. Se o usuário voltar, o item de maior impacto da lista do
`todo.md` é **camadas**; o de menor esforço é a prévia dos ajustes limitada à
área visível (hoje o diálogo recalcula a imagem inteira a cada movimento de
slider, com 90 ms de espera, o que numa foto 4K ainda pesa).

Ao lançar uma versão nova: subir `APP_VERSION` em `src/paintv2/__init__.py`,
`version` no `pyproject.toml`, `AppVersion` no `packaging/paintv2.iss` e os
números em `packaging/version_info.txt` — os quatro precisam bater.

## Em aberto / armadilhas

- **Nunca apagar `%APPDATA%\Paint-V2\library.json` para limpar teste.** Aconteceu
  nesta sessão e levou junto o projeto que o usuário tinha salvo. Scripts de
  teste e captura devem construir a biblioteca com `ProjectLibrary(root=tmp)` —
  `scripts/capture_screenshots.py` e os testes já fazem isso; o que sujou foram
  scripts avulsos que subiam o `PaintApplication` inteiro.
- O executável não é assinado: o SmartScreen avisa na primeira execução.
- `BAND_PIXEL_BUDGET` (32k px) e `HALO_BAND_RATIO` (6) em `core/parallel.py` foram
  achados por medição nesta máquina (32 núcleos lógicos). Faixas menores ajudam a
  saturação e atrapalham o desfoque, porque a borda de segurança vira retrabalho —
  por isso o piso proporcional ao halo. Mexer nesses números pede novo benchmark.
- `MAX_WORKERS` está em 16. Subir mais não ajudou: o gargalo é tráfego de memória,
  não CPU.

## Como retomar rápido

- Rodar: `& ".venv\Scripts\python.exe" -m paintv2`
- Testar: `& ".venv\Scripts\python.exe" -m pytest`  (285 testes, ~3 s)
- Empacotar: `& ".venv\Scripts\python.exe" scripts\build_app.py`
- Capturas do README: `& ".venv\Scripts\python.exe" scripts\capture_screenshots.py`
- Antes de mexer no motor: `.claude/decisions.md`, `core/stroke.py` e
  `core/parallel.py` (os comentários do topo explicam o porquê de cada escolha).

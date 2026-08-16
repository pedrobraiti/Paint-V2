# Decisões arquiteturais/técnicas

Registro de decisões com o "porquê". Append-only — não edita entradas antigas.

<!-- Formato:
## YYYY-MM-DD — Título curto da decisão
**Motivo:** por que foi decidido assim.
**Alternativas consideradas:** o que ficou de fora e por quê.
-->

## 2026-08-16 — Python 3.12 + PySide6 como stack do app desktop

**Motivo:** o requisito é um app nativo Windows (não-web) com processamento pesado de
pixels. PySide6 dá janela/menus/atalhos nativos e um `QImage` que compartilha memória
com um array NumPy sem cópia, então os pincéis de efeito (saturação, blend, blur)
rodam vetorizados em NumPy e aparecem na tela sem conversão intermediária. Também é
a stack que o ambiente do usuário já padroniza.

**Alternativas consideradas:** C#/WPF — mais nativo, porém manipulação de pixels
exigiria muito mais código para o mesmo conjunto de ferramentas; Electron/web — o
usuário descartou explicitamente.

## 2026-08-16 — Pincel = ponta (tip) × modo (mode), ortogonais

**Motivo:** o pedido "quero que a saturação localizada funcione com todos os tipos de
pincel" só é sustentável se a forma do pincel e o efeito forem eixos independentes.
A ponta gera uma máscara alpha (float32) e o modo decide o que fazer com os pixels
sob essa máscara. Adicionar um efeito novo não toca em nenhuma ponta, e vice-versa.

**Alternativas consideradas:** uma classe de ferramenta por combinação (SprayDeSaturação,
CaligrafiaDeBlur…) — explosão combinatória; efeito fixo por ferramenta como no Paint —
não atende o requisito.

## 2026-08-16 — Máscara acumulada por traço + snapshot do início do traço

**Motivo:** efeitos como saturação e blur são idempotentes por natureza ("deixe esta
área com +30% de saturação"). Se cada stamp fosse aplicado sobre o resultado do stamp
anterior, passar o mouse devagar saturaria muito mais que passar rápido, e o traço
ficaria com faixas escuras nas sobreposições. Acumulando a máxima do alpha numa máscara
do traço e aplicando sempre contra o snapshot do início, o resultado depende só de
*onde* o traço passou, não de quantas amostras caíram ali.

**Alternativas consideradas:** aplicar stamp a stamp direto no canvas — o que o blend
(smudge) de fato precisa, por ser sequencial por definição; por isso o blend é o único
modo marcado como `sequential` e escapa dessa regra.

## 2026-08-16 — Histórico de undo por patch (bbox + pixels anteriores)

**Motivo:** guardar a imagem inteira por passo estoura memória em imagens grandes
(uma foto 6000×4000 são ~96 MB por passo). O patch guarda só o retângulo alterado,
que num traço de pincel costuma ser uma fração mínima da tela.

**Alternativas consideradas:** snapshot completo — simples porém proibitivo; diff por
tiles — ganho marginal sobre o bbox para a carga real de um editor de pintura.

## 2026-08-16 — Biblioteca de projetos como índice de arquivos, sem formato próprio

**Motivo:** o HUB precisa listar "os projetos que eu já fiz" e o fluxo principal do
usuário é abrir uma imagem existente e salvar por cima. Um formato proprietário
obrigaria exportação a cada uso. O índice em `%APPDATA%\Paint-V2\library.json` guarda
caminho, miniatura e data — o arquivo em si continua sendo um PNG/JPG comum.

**Alternativas consideradas:** formato `.pv2` (zip com PNG + metadados) — só se
justificaria com camadas, que estão fora do escopo desta versão.

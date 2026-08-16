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

## 2026-08-16 — Carimbo processado em faixas horizontais paralelas

**Motivo:** o usuário pediu pincéis bem maiores (1000–3000 px) para retocar fotos
4K, e o caminho antigo processava o carimbo inteiro de uma vez. Um pincel de
3000 px viraria centenas de megabytes de arrays intermediários por carimbo — a
interface travava antes disso, e a memória estouraria em seguida. Fatiar o
carimbo resolve os dois problemas com o mesmo mecanismo: o pico de memória passa
a depender da faixa, e as faixas são independentes, então rodam em threads de
verdade (o NumPy libera a GIL). Medido num traço de ponta a ponta em 3840×2160,
com pincel de 500 px: saturação 848 → 185 ms, desfoque 1874 → 667 ms.

**Alternativas consideradas:** GPU via CuPy ou compute shader — traria dependência
de CUDA (ou de um pipeline gráfico inteiro) e um segundo caminho de código para
manter, em troca de um ganho que o paralelismo em CPU já entrega para esta carga;
processos em vez de threads — o custo de copiar a região para cada processo
anularia o ganho, já que o gargalo é justamente tráfego de memória.

## 2026-08-16 — Realce tonal por curva em S, e não por auto-níveis

**Motivo:** o pedido era "aumentar a diferença entre os valores mais claros e os
mais escuros". O caminho óbvio — medir o mínimo e o máximo sob o pincel e esticar
a faixa — é incompatível com o processamento em faixas: cada faixa mediria a
própria estatística e o resultado sairia listrado. A curva em S é uma função
ponto a ponto, dá o mesmo resultado independente de como o trabalho é dividido,
e ainda protege branco e preto do ceifamento. Aplicada sobre a luminância (com o
RGB reescalado junto), mexe no tom sem girar a cor.

**Alternativas consideradas:** auto-níveis com estatística do carimbo inteiro —
exigiria materializar a região toda antes de fatiar, desfazendo o limite de
memória; contraste linear — já existe como ferramenta separada, e ceifa os
extremos, que é justamente o que se quer evitar ao insistir numa área.

## 2026-08-16 — Máscara do traço acumulada em modo *screen*

**Motivo:** a regra "o efeito não se intensifica ao repassar" e a expectativa de
que Spray, Marcador e Aquarela *construam* cor em camadas parecem opostas. A
acumulação `1 - (1-a)(1-b)` concilia as duas: com fluxo total a máscara satura no
primeiro toque (repassar não muda nada), e com fluxo parcial ela cresce camada a
camada, como o depósito real dessas pontas. Como a máscara é limitada a 1 e o modo
sempre aplica contra o snapshot do início, nada dispara.

**Alternativas consideradas:** `max()` puro — mataria o comportamento do
aerógrafo; soma simples — estouraria e reintroduziria a dependência da velocidade.

## 2026-08-16 — Atalhos de uma letra no canvas, não em QAction

**Motivo:** `QAction` intercepta a tecla antes do widget em foco. Com a ferramenta
de texto aberta, digitar "b" trocaria de ferramenta em vez de escrever a letra —
e a letra sumiria. Tratando as teclas em `CanvasView.keyPressEvent`, elas só
chegam quando o próprio canvas tem o foco. Os atalhos com Ctrl continuam em
`QAction` (o usuário espera vê-los no menu) e são desviados para o campo de texto
por `MainWindow._forward_to_text_widget` quando há um em foco.

**Alternativas consideradas:** `WidgetWithChildrenShortcut` — não resolve, porque
o campo de texto é filho do canvas; desabilitar as ações enquanto o texto está
aberto — funciona, mas espalha o acoplamento por toda a janela.

## 2026-08-16 — Distribuição em pasta (onedir) com instalador Inno Setup

**Motivo:** o modo arquivo-único extrai ~110 MB de Qt para o disco a cada
execução, o que se sente num app aberto várias vezes por dia. A pasta inicia
imediatamente, e o instalador esconde essa pasta do usuário. Instalação por
usuário (`PrivilegesRequired=lowest`) evita o prompt de administrador, e o atalho
no Menu Iniciar é o que faz o app aparecer na busca do Windows — que era um
requisito explícito.

**Alternativas consideradas:** `--onefile` — mais simples de distribuir, porém
lento a cada abertura; MSIX — exigiria assinatura e certificado.

## 2026-08-16 — Biblioteca de projetos como índice de arquivos, sem formato próprio

**Motivo:** o HUB precisa listar "os projetos que eu já fiz" e o fluxo principal do
usuário é abrir uma imagem existente e salvar por cima. Um formato proprietário
obrigaria exportação a cada uso. O índice em `%APPDATA%\Paint-V2\library.json` guarda
caminho, miniatura e data — o arquivo em si continua sendo um PNG/JPG comum.

**Alternativas consideradas:** formato `.pv2` (zip com PNG + metadados) — só se
justificaria com camadas, que estão fora do escopo desta versão.

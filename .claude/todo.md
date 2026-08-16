# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

## Em progresso

Nada em aberto — a versão 1.1.0 está publicada.

## Próximas

Ideias para depois do 1.1, em ordem de valor percebido:

- [ ] Camadas (o desenho hoje é de camada única + seleção flutuante)
- [ ] Gradiente e padrões no balde de tinta
- [ ] Clonagem (carimbo) — o irmão que falta do blend
- [ ] Histórico visual navegável (lista de passos, não só Ctrl+Z)
- [ ] Exportar recorte da seleção direto para arquivo
- [ ] Preferências persistentes (última pasta, tamanho de pincel, tema)
- [ ] Prévia dos ajustes só na área visível, para responder na hora em fotos grandes

## Concluído

- [x] Setup inicial do projeto
- [x] Núcleo de imagem (`core/`)
  - [x] Documento RGBA + ponte NumPy/QImage sem cópia
  - [x] Operações de cor vetorizadas (saturação, brilho, contraste, matiz, temperatura…)
  - [x] Motor de pincel: pontas (tips) e modos (modes) ortogonais
  - [x] Histórico undo/redo por patch, com teto de memória
  - [x] Preenchimento (flood fill) com tolerância, por varredura de linhas
  - [x] Seleção retangular e por máscara, respeitada por pincéis, balde e ajustes
- [x] Ferramentas (`tools/`): lápis, pincel, spray, borracha, balde, conta-gotas,
      texto, linha, curva, 14 formas, seleção, lupa e mão
- [x] Pincéis de efeito: saturação, blend, desfoque, nitidez, clarear, escurecer, matiz
- [x] UI: janela principal, canvas com zoom/pan, barra de opções contextual,
      barra de ferramentas agrupada, paleta de cores
- [x] HUB de projetos com miniaturas + nova tela em branco + abrir arquivo
- [x] Diálogo de ajustes globais com pré-visualização ao vivo
- [x] Ícone Paint-V2 (cores invertidas) em .ico multi-resolução
- [x] Testes automatizados (256): núcleo e interface
- [x] Build PyInstaller + instalador Inno Setup
- [x] `README.md` com capturas, atalhos e arquitetura, e `LICENSE` (MIT)
- [x] Repositório público github.com/pedrobraiti/Paint-V2
- [x] Release v1.0.0 com o instalador anexado
- [x] CI no GitHub Actions rodando a suíte no Windows

### 1.1.0 — retorno do primeiro uso real

- [x] Pincel até 5000 px no campo, com a rampa parando em 1000
- [x] Carimbo processado em faixas paralelas (traço 2,5× a 5× mais rápido)
- [x] Pincéis de contraste e de realce tonal (curva em S)
- [x] Barra de ações rápidas com desfazer/refazer
- [x] `Ctrl+Shift+Z` refaz, além de `Ctrl+Y`
- [x] Desfazer uma pincelada não reenquadra mais a vista

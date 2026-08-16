# TODO

Plano vivo do projeto. Tarefas e subtarefas, marcadas conforme concluídas.

## Em progresso

Nada em aberto — a versão 1.0.0 está publicada.

## Próximas

Ideias para depois do 1.0, em ordem de valor percebido:

- [ ] Camadas (o desenho hoje é de camada única + seleção flutuante)
- [ ] Gradiente e padrões no balde de tinta
- [ ] Clonagem (carimbo) — o irmão que falta do blend
- [ ] Histórico visual navegável (lista de passos, não só Ctrl+Z)
- [ ] Exportar recorte da seleção direto para arquivo
- [ ] Preferências persistentes (última pasta, tamanho de pincel, tema)

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

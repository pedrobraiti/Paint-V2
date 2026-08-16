# Contexto do projeto

> Camada **estável** da memória: o que o projeto é e suas características macro. Muda devagar.
> O detalhe volátil de "de onde parei" fica no `handoff.md`; as tarefas, no `todo.md`;
> as decisões com o porquê, no `decisions.md`.

**Nome:** Paint-V2
**Descrição:** Editor de imagens desktop para Windows — um Paint clássico repensado, com pincéis de efeito (saturação, blend, blur, dodge/burn) e um HUB de projetos.
**Stack:** Python 3.12, PySide6 (Qt 6), NumPy, Pillow; empacotado com PyInstaller e distribuído via instalador Inno Setup.

## Visão geral

Aplicativo desktop nativo (não-web) que reproduz o Microsoft Paint e vai além:
todo pincel tem uma **ponta** (forma/dinâmica) e um **modo** (o que ele faz com os
pixels), o que permite usar o mesmo Spray/Caligrafia/Aquarela para pintar, apagar,
saturar, borrar (blend), desfocar, clarear ou escurecer. Tem também ajustes globais
de imagem com preview e um HUB inicial com os projetos recentes em miniatura.

Público: uso pessoal diário do usuário — abrir uma imagem, retocar rápido, salvar.

## Fase atual

MVP em desenvolvimento — arquitetura definida, implementação do núcleo e da UI.

## Restrições e bloqueios de longo prazo

- Alvo exclusivo Windows 10/11 x64; deve aparecer na busca do Menu Iniciar como "Paint-V2".
- Ícone próprio inspirado no Paint com cores invertidas (arte original, não asset da Microsoft).
- Sem camadas nesta versão (documento de camada única + seleção flutuante).
- Performance de pincel precisa ser fluida em imagens grandes: operações NumPy restritas
  à bounding box suja de cada traço.

# Handoff — de onde parei

> **Propósito:** este arquivo serve para que um chat NOVO saiba com precisão "de onde eu parei",
> de forma relativamente detalhada. É o PRIMEIRO arquivo que a próxima sessão lê.
> Mantenha-o vivo e específico — detalhado o bastante para retomar sem reconstruir o raciocínio.

**Última atualização:** 2026-08-16 — setup inicial

## Onde parei

Estrutura do projeto criada (`.claude/`, `CLAUDE.md`, git, venv com PySide6/NumPy/
Pillow/pytest/PyInstaller). Nenhum código de aplicação escrito ainda.

## Contexto mental

Stack decidida com o usuário: Python 3.12 + PySide6, distribuição via instalador
Inno Setup (o app precisa aparecer na busca do Windows como "Paint-V2"). A decisão
central de arquitetura está em `.claude/decisions.md`: pincel = ponta × modo, para
que saturação/blend funcionem com qualquer tipo de pincel, incluindo Spray.

## Próximo passo concreto

Implementar `src/paintv2/core/` — começando por `document.py` (buffer RGBA NumPy
compartilhado com `QImage`) e `color_ops.py` (ajustes vetorizados).

## Em aberto / armadilhas

- `QImage` que compartilha memória com NumPy exige manter uma referência viva ao
  array, senão o buffer é coletado e a imagem aponta para memória liberada.
- Inno Setup ainda não instalado na máquina (`iscc` não encontrado) — instalar via winget
  na etapa de build.

## Como retomar rápido

- `& ".venv\Scripts\python.exe" -m paintv2` para rodar o app.
- `& ".venv\Scripts\python.exe" -m pytest` para os testes.
- Ler `.claude/decisions.md` antes de mexer no motor de pincel.

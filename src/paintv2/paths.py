"""Onde o Paint-V2 guarda dados do usuário.

Tudo que persiste entre sessões (biblioteca de projetos, miniaturas, preferências)
vive em ``%APPDATA%\\Paint-V2`` no Windows. O fallback para ``~/.paintv2`` existe
apenas para que os testes rodem em qualquer plataforma.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "Paint-V2"


def app_data_dir() -> Path:
    """Diretório de dados do aplicativo, criado se ainda não existir."""
    roaming = os.environ.get("APPDATA")
    base = Path(roaming) if roaming else Path.home() / ".config"
    directory = base / APP_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def thumbnails_dir() -> Path:
    """Cache de miniaturas do HUB."""
    directory = app_data_dir() / "thumbnails"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def default_documents_dir() -> Path:
    """Pasta sugerida nos diálogos de abrir e salvar."""
    pictures = Path.home() / "Pictures"
    return pictures if pictures.is_dir() else Path.home()

"""Acesso aos arquivos embarcados (ícone do aplicativo).

Precisa funcionar tanto rodando do código-fonte quanto dentro do executável
gerado pelo PyInstaller, onde os dados ficam extraídos sob ``sys._MEIPASS``.
"""

from __future__ import annotations

import sys
from pathlib import Path

RESOURCES_DIRNAME = "resources"
APP_ICON_FILE = "paintv2.ico"


def resources_dir() -> Path:
    """Pasta de recursos válida no ambiente atual."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / "paintv2" / RESOURCES_DIRNAME
        if bundled.is_dir():
            return bundled
        return Path(bundle_root) / RESOURCES_DIRNAME
    return Path(__file__).resolve().parent / RESOURCES_DIRNAME


def resource_path(name: str) -> Path:
    """Caminho absoluto de um recurso pelo nome do arquivo."""
    return resources_dir() / name


def app_icon_path() -> Path:
    return resource_path(APP_ICON_FILE)

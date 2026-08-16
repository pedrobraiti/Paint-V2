"""Biblioteca de projetos que alimenta o HUB.

Um "projeto" aqui é apenas um arquivo de imagem que já foi aberto ou salvo no
Paint-V2 — não há formato proprietário. A biblioteca guarda o caminho, uma
miniatura e a data do último acesso, e some silenciosamente com entradas cujo
arquivo o usuário apagou ou moveu.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

from ..paths import app_data_dir, thumbnails_dir

LIBRARY_FILE = "library.json"
THUMBNAIL_SIZE = 320
MAX_ENTRIES = 60


@dataclass
class ProjectEntry:
    """Uma linha da biblioteca, já pronta para virar um cartão no HUB."""

    path: str
    name: str
    width: int
    height: int
    opened_at: str
    thumbnail: str | None = None

    @property
    def file_path(self) -> Path:
        return Path(self.path)

    @property
    def thumbnail_path(self) -> Path | None:
        return Path(self.thumbnail) if self.thumbnail else None

    @property
    def opened_datetime(self) -> datetime:
        try:
            return datetime.fromisoformat(self.opened_at)
        except ValueError:
            return datetime.fromtimestamp(0, tz=UTC)

    @property
    def exists(self) -> bool:
        return self.file_path.is_file()


class ProjectLibrary:
    """Índice persistente dos projetos recentes."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or app_data_dir()
        self._thumbnails = (
            (self._root / "thumbnails") if root else thumbnails_dir()
        )
        self._thumbnails.mkdir(parents=True, exist_ok=True)
        self._file = self._root / LIBRARY_FILE
        self._entries: list[ProjectEntry] = self._load()

    # ------------------------------------------------------------------ leitura

    def entries(self, include_missing: bool = False) -> list[ProjectEntry]:
        """Projetos do mais recente ao mais antigo."""
        entries = self._entries if include_missing else [e for e in self._entries if e.exists]
        return sorted(entries, key=lambda entry: entry.opened_datetime, reverse=True)

    def find(self, path: Path) -> ProjectEntry | None:
        key = self._normalize(path)
        return next((e for e in self._entries if self._normalize(e.file_path) == key), None)

    # ------------------------------------------------------------------ escrita

    def remember(self, path: Path, pixels: np.ndarray) -> ProjectEntry:
        """Cria ou atualiza a entrada do arquivo, regravando a miniatura."""
        height, width = pixels.shape[:2]
        entry = ProjectEntry(
            path=str(Path(path).resolve()),
            name=Path(path).name,
            width=int(width),
            height=int(height),
            opened_at=datetime.now(UTC).isoformat(timespec="seconds"),
            thumbnail=str(self._write_thumbnail(path, pixels)),
        )
        self._entries = [
            existing
            for existing in self._entries
            if self._normalize(existing.file_path) != self._normalize(path)
        ]
        self._entries.append(entry)
        self._prune()
        self._save()
        return entry

    def forget(self, path: Path) -> None:
        """Remove o projeto da lista (não apaga o arquivo do usuário)."""
        key = self._normalize(path)
        removed = [e for e in self._entries if self._normalize(e.file_path) == key]
        self._entries = [e for e in self._entries if self._normalize(e.file_path) != key]
        for entry in removed:
            self._discard_thumbnail(entry)
        self._save()

    def clear(self) -> None:
        for entry in self._entries:
            self._discard_thumbnail(entry)
        self._entries = []
        self._save()

    def prune_missing(self) -> int:
        """Descarta entradas cujo arquivo não existe mais; devolve quantas saíram."""
        alive = [entry for entry in self._entries if entry.exists]
        removed = len(self._entries) - len(alive)
        if removed:
            self._entries = alive
            self._save()
        return removed

    # ----------------------------------------------------------------- interno

    def _load(self) -> list[ProjectEntry]:
        if not self._file.is_file():
            return []
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # Um índice corrompido não pode impedir o app de abrir; recomeçar
            # dele custa ao usuário apenas a lista de recentes.
            return []
        return [
            ProjectEntry(**item)
            for item in raw.get("projects", [])
            if isinstance(item, dict) and {"path", "name"} <= item.keys()
        ]

    def _save(self) -> None:
        payload = {"version": 1, "projects": [asdict(entry) for entry in self._entries]}
        temporary = self._file.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        temporary.replace(self._file)

    def _write_thumbnail(self, path: Path, pixels: np.ndarray) -> Path:
        image = Image.fromarray(np.ascontiguousarray(pixels), mode="RGBA")
        image.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE), Image.LANCZOS)
        destination = self._thumbnails / f"{self._digest(path)}.png"
        image.save(destination, format="PNG")
        return destination

    def _discard_thumbnail(self, entry: ProjectEntry) -> None:
        thumbnail = entry.thumbnail_path
        if thumbnail and thumbnail.is_file():
            thumbnail.unlink(missing_ok=True)

    def _prune(self) -> None:
        ordered = sorted(self._entries, key=lambda e: e.opened_datetime, reverse=True)
        for stale in ordered[MAX_ENTRIES:]:
            self._discard_thumbnail(stale)
        self._entries = ordered[:MAX_ENTRIES]

    @staticmethod
    def _normalize(path: Path) -> str:
        try:
            return str(Path(path).resolve()).lower()
        except OSError:
            return str(path).lower()

    @staticmethod
    def _digest(path: Path) -> str:
        return hashlib.sha1(str(Path(path).resolve()).lower().encode("utf-8")).hexdigest()[:16]

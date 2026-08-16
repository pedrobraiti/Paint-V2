"""HUB: a tela inicial com os projetos recentes.

É o primeiro contato com o app, então ela responde a duas perguntas: "no que eu
estava trabalhando?" e "o que eu quero fazer agora?". Abrir um arquivo vem em
primeiro lugar por ser o caminho do dia a dia; a tela em branco fica ao lado.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import APP_DESCRIPTION, APP_NAME
from ..assets import app_icon_path
from ..projects import ProjectEntry, ProjectLibrary
from .icons import icon_pixmap
from .theme import PALETTE

CARD_WIDTH = 232
THUMBNAIL_HEIGHT = 136
CARDS_PER_ROW = 4


class ProjectCard(QFrame):
    """Cartão clicável de um projeto recente."""

    opened = Signal(Path)
    removed = Signal(Path)

    def __init__(self, entry: ProjectEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._entry = entry
        self.setFixedWidth(CARD_WIDTH)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {PALETTE.surface};
                border: 1px solid {PALETTE.border};
                border-radius: 12px;
            }}
            QFrame:hover {{ border-color: {PALETTE.accent}; }}
            QLabel {{ background: transparent; border: none; }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 12)
        layout.setSpacing(8)

        thumbnail = QLabel()
        thumbnail.setFixedHeight(THUMBNAIL_HEIGHT)
        thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail.setPixmap(_thumbnail_pixmap(entry))
        layout.addWidget(thumbnail)

        name = QLabel(entry.name)
        name.setToolTip(entry.path)
        name.setStyleSheet("font-weight: 600;")
        metrics = name.fontMetrics()
        name.setText(metrics.elidedText(entry.name, Qt.TextElideMode.ElideMiddle, CARD_WIDTH - 30))
        layout.addWidget(name)

        details = QLabel(f"{entry.width} × {entry.height} · {_relative_time(entry)}")
        details.setProperty("role", "muted")
        details.setStyleSheet(f"color: {PALETTE.text_muted}; font-size: 11px;")
        layout.addWidget(details)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.opened.emit(self._entry.file_path)
        super().mouseReleaseEvent(event)

    def _show_menu(self, position) -> None:
        menu = QMenu(self)
        menu.addAction("Abrir", lambda: self.opened.emit(self._entry.file_path))
        menu.addAction(
            "Mostrar na pasta", lambda: _reveal_in_explorer(self._entry.file_path)
        )
        menu.addSeparator()
        menu.addAction(
            "Remover da lista", lambda: self.removed.emit(self._entry.file_path)
        )
        menu.exec(self.mapToGlobal(position))


class HubWindow(QWidget):
    """Tela inicial do Paint-V2."""

    open_requested = Signal(Path)
    browse_requested = Signal()
    new_image_requested = Signal()

    def __init__(self, library: ProjectLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._filter = ""

        self.setWindowTitle(f"{APP_NAME} — Início")
        self.setWindowIcon(QIcon(str(app_icon_path())))
        self.resize(1120, 760)
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 28)
        layout.setSpacing(24)

        layout.addLayout(self._build_header())
        layout.addLayout(self._build_actions())
        layout.addWidget(self._build_recent_section(), 1)

        self.refresh()

    # ------------------------------------------------------------------ blocos

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(16)

        logo = QLabel()
        logo.setPixmap(QPixmap(str(app_icon_path())).scaled(
            56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        ))
        header.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setProperty("role", "heading")
        subtitle = QLabel(APP_DESCRIPTION)
        subtitle.setProperty("role", "subheading")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        return header

    def _build_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)

        open_button = _action_button(
            "Abrir arquivo",
            "Uma imagem do computador — o caminho de todo dia",
            "folder",
            primary=True,
        )
        open_button.clicked.connect(self.browse_requested.emit)
        row.addWidget(open_button, 1)

        new_button = _action_button(
            "Nova tela em branco",
            "Escolha as dimensões em pixels e comece do zero",
            "new_file",
        )
        new_button.clicked.connect(self.new_image_requested.emit)
        row.addWidget(new_button, 1)

        row.addStretch(2)
        return row

    def _build_recent_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        label = QLabel("Projetos recentes")
        label.setProperty("role", "section")
        heading.addWidget(label)
        heading.addStretch(1)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filtrar por nome…")
        self._search.setFixedWidth(240)
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_filter_changed)
        heading.addWidget(self._search)
        layout.addLayout(heading)

        self._empty_label = QLabel(
            "Nada por aqui ainda. Abra uma imagem ou crie uma tela em branco — "
            "os arquivos que você editar aparecem nesta lista."
        )
        self._empty_label.setWordWrap(True)
        self._empty_label.setProperty("role", "muted")
        self._empty_label.setStyleSheet(f"color: {PALETTE.text_muted};")
        layout.addWidget(self._empty_label)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setSpacing(14)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        scroll = QScrollArea()
        scroll.setWidget(self._grid_host)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll, 1)
        return container

    # ------------------------------------------------------------------ estado

    def refresh(self) -> None:
        """Recarrega a lista a partir da biblioteca, descartando o que sumiu."""
        self._library.prune_missing()
        entries = [
            entry
            for entry in self._library.entries()
            if self._filter in entry.name.lower()
        ]

        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # setParent(None) tira o cartão da tela agora; só o deleteLater
                # deixaria o antigo desenhado até o próximo ciclo de eventos.
                widget.setParent(None)
                widget.deleteLater()

        for index, entry in enumerate(entries):
            card = ProjectCard(entry)
            card.opened.connect(self.open_requested.emit)
            card.removed.connect(self._forget)
            self._grid.addWidget(card, index // CARDS_PER_ROW, index % CARDS_PER_ROW)

        self._empty_label.setVisible(not entries)

    def _on_filter_changed(self, text: str) -> None:
        self._filter = text.strip().lower()
        self.refresh()

    def _forget(self, path: Path) -> None:
        self._library.forget(path)
        self.refresh()

    # ----------------------------------------------------------- arrastar/soltar

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                self.open_requested.emit(Path(local))
                break
        event.acceptProposedAction()


def _action_button(title: str, description: str, icon: str, primary: bool = False) -> QPushButton:
    button = QPushButton()
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(96)
    button.setMinimumWidth(300)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    button.setMaximumWidth(360)
    if primary:
        button.setProperty("variant", "primary")

    layout = QHBoxLayout(button)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(14)

    color = PALETTE.accent_text if primary else PALETTE.accent
    glyph = QLabel()
    glyph.setPixmap(icon_pixmap(icon, 30, color))
    layout.addWidget(glyph)

    text_color = PALETTE.accent_text if primary else PALETTE.text
    muted_color = PALETTE.accent_text if primary else PALETTE.text_muted

    texts = QVBoxLayout()
    texts.setSpacing(2)
    heading = QLabel(title)
    heading.setStyleSheet(
        f"background: transparent; font-size: 15px; font-weight: 600; color: {text_color};"
    )
    caption = QLabel(description)
    caption.setWordWrap(True)
    caption.setStyleSheet(
        f"background: transparent; font-size: 11px; color: {muted_color};"
    )
    for label in (glyph, heading, caption):
        # Sem isso o clique cairia no rótulo e o botão nunca dispararia; e o fundo
        # herdado do tema desenharia uma caixa escura por cima do botão.
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    glyph.setStyleSheet("background: transparent;")
    texts.addWidget(heading)
    texts.addWidget(caption)
    layout.addLayout(texts, 1)
    return button


def _thumbnail_pixmap(entry: ProjectEntry) -> QPixmap:
    """Miniatura do cartão, com um substituto neutro se o arquivo sumiu."""
    thumbnail = entry.thumbnail_path
    if thumbnail is not None and thumbnail.is_file():
        pixmap = QPixmap(str(thumbnail))
        if not pixmap.isNull():
            return pixmap.scaled(
                CARD_WIDTH - 20,
                THUMBNAIL_HEIGHT,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

    placeholder = QPixmap(CARD_WIDTH - 20, THUMBNAIL_HEIGHT)
    placeholder.fill(QColor(PALETTE.surface_raised))
    painter = QPainter(placeholder)
    painter.drawPixmap(
        (placeholder.width() - 32) // 2,
        (placeholder.height() - 32) // 2,
        icon_pixmap("image", 32, PALETTE.text_disabled),
    )
    painter.end()
    return placeholder


def _relative_time(entry: ProjectEntry) -> str:
    """Data em linguagem natural — mais útil que um carimbo exato na lista."""
    delta = datetime.now(UTC) - entry.opened_datetime
    seconds = max(delta.total_seconds(), 0)
    if seconds < 60:
        return "agora há pouco"
    if seconds < 3600:
        return f"há {int(seconds // 60)} min"
    if seconds < 86400:
        return f"há {int(seconds // 3600)} h"
    days = int(seconds // 86400)
    if days == 1:
        return "ontem"
    if days < 30:
        return f"há {days} dias"
    return entry.opened_datetime.astimezone().strftime("%d/%m/%Y")


def _reveal_in_explorer(path: Path) -> None:
    """Abre o Explorer com o arquivo já selecionado."""
    import subprocess
    import sys

    if sys.platform != "win32" or not path.exists():
        return
    subprocess.Popen(["explorer", "/select,", str(path)])

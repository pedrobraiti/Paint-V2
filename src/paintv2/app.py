"""Ponto de entrada: cria o aplicativo e alterna entre o HUB e o editor."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from . import APP_NAME, APP_ORGANIZATION, APP_VERSION
from .assets import app_icon_path
from .core.document import Document
from .paths import default_documents_dir
from .projects import ProjectLibrary
from .ui.dialogs import NewImageDialog
from .ui.hub_window import HubWindow
from .ui.main_window import MainWindow, OPEN_FILTER
from .ui.theme import build_stylesheet

WINDOWS_APP_ID = "PaintV2.Editor.1"


class PaintApplication:
    """Amarra biblioteca, HUB e editor num único fluxo."""

    def __init__(self, argv: list[str]) -> None:
        _register_windows_app_id()

        self.qt = QApplication(argv)
        self.qt.setApplicationName(APP_NAME)
        self.qt.setApplicationDisplayName(APP_NAME)
        self.qt.setOrganizationName(APP_ORGANIZATION)
        self.qt.setApplicationVersion(APP_VERSION)
        self.qt.setWindowIcon(QIcon(str(app_icon_path())))
        self.qt.setStyle("Fusion")
        self.qt.setStyleSheet(build_stylesheet())

        self.library = ProjectLibrary()
        self.hub = HubWindow(self.library)
        self.editor = MainWindow(self.library)

        self.hub.open_requested.connect(self.open_path)
        self.hub.browse_requested.connect(self.browse)
        self.hub.new_image_requested.connect(self.create_blank)
        self.editor.hub_requested.connect(self.show_hub)

    # -------------------------------------------------------------------- fluxo

    def start(self, initial_file: Path | None = None) -> None:
        if initial_file is not None and initial_file.is_file():
            self.open_path(initial_file)
            return
        self.show_hub()

    def show_hub(self) -> None:
        self.editor.hide()
        self.hub.refresh()
        self.hub.show()
        self.hub.raise_()
        self.hub.activateWindow()

    def show_editor(self) -> None:
        self.hub.hide()
        self.editor.show()
        self.editor.raise_()
        self.editor.activateWindow()

    def open_path(self, path: Path) -> None:
        try:
            document = Document.open(path)
        except Exception as error:  # noqa: BLE001 - o usuário só precisa do aviso
            QMessageBox.critical(
                self.hub, "Não foi possível abrir", f"{path}\n\n{error}"
            )
            self.library.forget(path)
            self.hub.refresh()
            return
        self.editor.load_document(document)
        self.show_editor()

    def browse(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self.hub, "Abrir imagem", str(default_documents_dir()), OPEN_FILTER
        )
        if selected:
            self.open_path(Path(selected))

    def create_blank(self) -> None:
        dialog = NewImageDialog(self.hub)
        if dialog.exec() != NewImageDialog.DialogCode.Accepted:
            return
        choice = dialog.choice()
        self.editor.load_document(
            Document.blank(choice.width, choice.height, choice.color)
        )
        self.show_editor()

    def run(self, initial_file: Path | None = None) -> int:
        self.start(initial_file)
        return self.qt.exec()


def _register_windows_app_id() -> None:
    """Faz o Windows tratar o app como próprio na barra de tarefas.

    Sem isso o atalho e a janela contam como dois programas diferentes, e o ícone
    fixado não se junta à janela aberta.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(WINDOWS_APP_ID)
    except (AttributeError, OSError):
        pass


def main(argv: list[str] | None = None) -> int:
    arguments = list(argv if argv is not None else sys.argv)
    initial = Path(arguments[1]) if len(arguments) > 1 else None
    return PaintApplication(arguments).run(initial)


if __name__ == "__main__":
    raise SystemExit(main())

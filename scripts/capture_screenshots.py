"""Gera as capturas de tela usadas no README.

Monta uma biblioteca de projetos temporária com imagens de exemplo, para que a
captura do HUB não exponha os arquivos reais de quem roda o script.

Uso:
    python scripts/capture_screenshots.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from paintv2.assets import app_icon_path  # noqa: E402
from paintv2.core.document import Document  # noqa: E402
from paintv2.projects import ProjectLibrary  # noqa: E402
from paintv2.tools.base import CanvasEvent  # noqa: E402
from paintv2.ui.hub_window import HubWindow  # noqa: E402
from paintv2.ui.main_window import MainWindow  # noqa: E402
from paintv2.ui.theme import build_stylesheet  # noqa: E402

OUTPUT_DIR = PROJECT_ROOT / "docs"
EDITOR_SIZE = (1440, 900)
HUB_SIZE = (1180, 800)


def gradient_document(width: int = 1100, height: int = 720) -> Document:
    """Imagem de exemplo com bastante cor, para os efeitos ficarem visíveis."""
    rows, columns = np.mgrid[0:height, 0:width]
    pixels = np.empty((height, width, 4), dtype=np.uint8)
    pixels[..., 0] = (128 + 127 * np.sin(columns / 90.0)).astype(np.uint8)
    pixels[..., 1] = (128 + 127 * np.sin(rows / 70.0 + 1.5)).astype(np.uint8)
    pixels[..., 2] = (128 + 127 * np.sin((rows + columns) / 110.0 + 3.0)).astype(np.uint8)
    pixels[..., 3] = 255
    return Document(pixels)


def demo_stroke(canvas, tool_key: str, points: list[tuple[float, float]]) -> None:
    """Aplica um traço real, para a captura mostrar o efeito e não a tela limpa."""
    canvas.set_tool(tool_key)
    tool = canvas.tool()
    tool.press(CanvasEvent(position=QPointF(*points[0]), button=Qt.MouseButton.LeftButton))
    for point in points[1:]:
        tool.move(CanvasEvent(position=QPointF(*point), buttons=Qt.MouseButton.LeftButton))
    tool.release(CanvasEvent(position=QPointF(*points[-1])))
    tool.commit_pending()


def sample_library(root: Path) -> ProjectLibrary:
    library = ProjectLibrary(root=root / "biblioteca")
    samples = {
        "paisagem.png": (1600, 900),
        "retrato.png": (900, 1200),
        "textura.png": (800, 800),
        "banner.png": (1920, 640),
        "icone.png": (512, 512),
        "esboço.png": (1280, 720),
    }
    for name, (width, height) in samples.items():
        document = gradient_document(width // 4, height // 4)
        path = root / name
        document.save(path)
        library.remember(path, document.pixels)
    return library


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp())

    application = QApplication.instance() or QApplication([])
    application.setStyle("Fusion")
    application.setStyleSheet(build_stylesheet())
    application.setWindowIcon(QIcon(str(app_icon_path())))

    library = sample_library(workdir)

    editor = MainWindow(library)
    editor.resize(*EDITOR_SIZE)
    editor.load_document(gradient_document())
    editor.show()

    hub = HubWindow(library)
    hub.resize(*HUB_SIZE)

    def capture_editor() -> None:
        canvas = editor._canvas
        demo_stroke(canvas, "saturation", [(x, 240 + 60 * np.sin(x / 90)) for x in range(120, 950, 12)])
        demo_stroke(canvas, "blend", [(x, 470) for x in range(200, 900, 10)])
        canvas.settings.tip_key = "airbrush"
        demo_stroke(canvas, "dodge", [(x, 610) for x in range(260, 860, 8)])
        canvas.settings.tip_key = "brush"
        canvas.set_tool("saturation")
        editor.grab().save(str(OUTPUT_DIR / "editor.png"))
        hub.refresh()
        hub.show()
        # Os cartões recém-criados só ganham posição depois de um ciclo de
        # layout; capturar antes disso renderiza a área vazia.
        QTimer.singleShot(600, capture_hub)

    def capture_hub() -> None:
        application.processEvents()
        hub.grab().save(str(OUTPUT_DIR / "hub.png"))
        print(f"Capturas salvas em {OUTPUT_DIR}")
        # Os traços de demonstração deixaram o documento sujo; sem limpar a
        # marca, fechar a janela abriria o diálogo de "salvar antes de sair" e o
        # script ficaria travado esperando um clique.
        editor.document.is_dirty = False
        editor.close()
        hub.close()
        application.quit()

    QTimer.singleShot(700, capture_editor)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())

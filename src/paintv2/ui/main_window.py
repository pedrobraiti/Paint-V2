"""Janela do editor: menus, painéis e a cola entre eles e o núcleo."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSlider,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .. import APP_NAME
from ..assets import app_icon_path
from ..core.document import READABLE_EXTENSIONS, WRITABLE_EXTENSIONS, Document
from ..paths import default_documents_dir
from ..projects import ProjectLibrary
from ..tools.qt_bridge import array_to_image, image_to_array
from ..tools.registry import DEFAULT_TOOL_KEY, TOOL_CLASSES, SelectionTool
from ..tools.settings import ToolSettings
from .canvas_view import CanvasView
from .dialogs import AdjustmentsDialog, NewImageDialog, ResizeDialog
from .icons import get_icon
from .theme import PALETTE
from .widgets import ColorPanel, OptionsBar, ToolBox

OPEN_FILTER = (
    "Imagens (" + " ".join(f"*{extension}" for extension in READABLE_EXTENSIONS) + ")"
    ";;Todos os arquivos (*)"
)
SAVE_FILTER = (
    "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;WebP (*.webp);;TIFF (*.tif *.tiff)"
)

# Larguras dos painéis laterais: cabem duas colunas de ferramentas e a paleta de
# dez colunas sem que a barra de rolagem coma a última.
TOOL_PANEL_WIDTH = 158
COLOR_PANEL_WIDTH = 302


class MainWindow(QMainWindow):
    """Editor completo de um documento."""

    hub_requested = Signal()

    def __init__(self, library: ProjectLibrary, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._library = library
        self._settings = ToolSettings()

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(app_icon_path())))
        self.resize(1440, 900)
        self.setMinimumSize(QSize(960, 620))

        self._canvas = CanvasView(self._settings)
        self._tool_box = ToolBox()
        self._options = OptionsBar(self._settings)
        self._colors = ColorPanel(self._settings)

        self._build_layout()
        self._build_actions()
        self._build_toolbar()
        self._build_status_bar()
        self._connect_signals()

        self._tool_box.set_active(DEFAULT_TOOL_KEY)
        self._options.show_for(self._canvas.tool())
        self._refresh_title()

    # ------------------------------------------------------------------ layout

    def _build_layout(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._options)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        body_layout.addWidget(_side_panel(self._tool_box, TOOL_PANEL_WIDTH))
        body_layout.addWidget(self._canvas, 1)
        body_layout.addWidget(_side_panel(self._colors, COLOR_PANEL_WIDTH))

        root.addWidget(body, 1)
        self.setCentralWidget(central)

    def _build_status_bar(self) -> None:
        bar = self.statusBar()

        self._hint_label = QLabel(self._canvas.tool().hint)
        bar.addWidget(self._hint_label, 1)

        self._position_label = QLabel("—")
        self._size_label = QLabel("—")
        self._selection_label = QLabel("")
        for label in (self._selection_label, self._position_label, self._size_label):
            bar.addPermanentWidget(label)

        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(-100, 100)
        self._zoom_slider.setFixedWidth(140)
        self._zoom_slider.setToolTip("Zoom (Ctrl + roda do mouse)")
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider)
        bar.addPermanentWidget(self._zoom_slider)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setFixedWidth(52)
        bar.addPermanentWidget(self._zoom_label)

        self._update_size_label()
        self._on_zoom_changed(self._canvas.zoom)

    # ----------------------------------------------------------------- ações

    def _build_actions(self) -> None:
        menu = self.menuBar()
        self._actions: dict[str, QAction] = {}

        file_menu = menu.addMenu("&Arquivo")
        self._add_action(file_menu, "Início", "home", "Ctrl+Shift+H", self._go_to_hub, name="hub")
        file_menu.addSeparator()
        self._add_action(file_menu, "Nova imagem", "new_file", QKeySequence.StandardKey.New, self.new_image, name="new")
        self._add_action(file_menu, "Abrir…", "folder", QKeySequence.StandardKey.Open, self.open_file, name="open")
        file_menu.addSeparator()
        self._save_action = self._add_action(
            file_menu, "Salvar", "save", QKeySequence.StandardKey.Save, self.save, name="save"
        )
        self._add_action(file_menu, "Salvar como…", "save", "Ctrl+Shift+S", self.save_as)
        file_menu.addSeparator()
        self._add_action(file_menu, "Sair", "", QKeySequence.StandardKey.Quit, self.close)

        edit_menu = menu.addMenu("&Editar")
        self._undo_action = self._add_action(
            edit_menu, "Desfazer", "undo", QKeySequence.StandardKey.Undo, self.undo, name="undo"
        )
        self._redo_action = self._add_action(
            edit_menu, "Refazer", "redo", QKeySequence.StandardKey.Redo, self.redo, name="redo"
        )
        # No Windows a tecla padrão de refazer é Ctrl+Y, mas Ctrl+Shift+Z é o que
        # a mão procura em editor de imagem. Os dois passam a valer.
        self._redo_action.setShortcuts(
            [QKeySequence(QKeySequence.StandardKey.Redo), QKeySequence("Ctrl+Shift+Z")]
        )
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Recortar", "cut", QKeySequence.StandardKey.Cut, self.cut)
        self._add_action(edit_menu, "Copiar", "copy", QKeySequence.StandardKey.Copy, self.copy)
        self._add_action(edit_menu, "Colar", "paste", QKeySequence.StandardKey.Paste, self.paste)
        self._add_action(edit_menu, "Excluir", "trash", QKeySequence.StandardKey.Delete, self.delete_selection)
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Selecionar tudo", "select_rect", QKeySequence.StandardKey.SelectAll, self.select_all)
        self._add_action(edit_menu, "Cancelar seleção", "", "Ctrl+D", self.deselect)
        self._add_action(edit_menu, "Inverter seleção", "", "Ctrl+Shift+I", self.invert_selection)
        self._add_action(edit_menu, "Recortar para a seleção", "crop", "Ctrl+Shift+X", self.crop_to_selection)
        edit_menu.addSeparator()
        # Sem atalho de QAction: a tecla X é tratada pelo canvas, para não roubar
        # a letra de quem estiver digitando com a ferramenta de texto.
        self._add_action(
            edit_menu, "Trocar cores  (X)", "palette", "", self._settings.swap_colors
        )

        image_menu = menu.addMenu("&Imagem")
        self._add_action(image_menu, "Redimensionar imagem…", "resize", "Ctrl+R", self.resize_image)
        self._add_action(image_menu, "Tamanho da tela…", "grid", "Ctrl+Shift+R", self.resize_canvas)
        image_menu.addSeparator()
        self._add_action(image_menu, "Girar 90° à direita", "rotate_right", "Ctrl+.", lambda: self.rotate(90))
        self._add_action(image_menu, "Girar 90° à esquerda", "rotate_left", "Ctrl+,", lambda: self.rotate(-90))
        self._add_action(image_menu, "Girar 180°", "rotate_right", "", lambda: self.rotate(180))
        image_menu.addSeparator()
        self._add_action(image_menu, "Inverter na horizontal", "flip_horizontal", "", lambda: self.flip(True))
        self._add_action(image_menu, "Inverter na vertical", "flip_vertical", "", lambda: self.flip(False))

        adjust_menu = menu.addMenu("A&justes")
        self._add_action(adjust_menu, "Ajustes de imagem…", "adjustments", "Ctrl+M", self.open_adjustments, name="adjustments")
        self._add_action(
            adjust_menu,
            "Ajustes na seleção…",
            "adjustments",
            "Ctrl+Shift+M",
            lambda: self.open_adjustments(restrict_to_selection=True),
        )

        view_menu = menu.addMenu("&Ver")
        self._add_action(view_menu, "Aproximar", "zoom_in", QKeySequence.StandardKey.ZoomIn, self._canvas.zoom_in, name="zoom_in")
        self._add_action(view_menu, "Afastar", "zoom_out", QKeySequence.StandardKey.ZoomOut, self._canvas.zoom_out, name="zoom_out")
        self._add_action(view_menu, "Tamanho real", "", "Ctrl+0", self._canvas.zoom_to_actual_size)
        self._add_action(view_menu, "Ajustar à janela", "resize", "Ctrl+9", self._canvas.fit_to_view, name="fit")

        help_menu = menu.addMenu("A&juda")
        self._add_action(help_menu, "Atalhos e ferramentas", "info", "F1", self.show_help)
        self._add_action(help_menu, f"Sobre o {APP_NAME}", "palette", "", self.show_about)

        self._update_history_actions()

    def _add_action(
        self, menu, text: str, icon: str, shortcut, slot, name: str | None = None
    ) -> QAction:
        action = QAction(text, self)
        if icon:
            action.setIcon(get_icon(icon, 18))
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        self.addAction(action)
        if name:
            # A barra reaproveita a mesma QAction do menu, para que estado
            # habilitado e rótulo (ex.: "Desfazer Saturação") andem juntos.
            self._actions[name] = action
        return action

    def _build_toolbar(self) -> None:
        """Barra de acesso rápido acima da barra de opções."""
        toolbar = QToolBar("Ações rápidas", self)
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        groups = (
            ("hub",),
            ("new", "open", "save"),
            ("undo", "redo"),
            ("zoom_out", "zoom_in", "fit"),
            ("adjustments",),
        )
        for index, group in enumerate(groups):
            if index:
                toolbar.addSeparator()
            for name in group:
                toolbar.addAction(self._actions[name])

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def _connect_signals(self) -> None:
        self._tool_box.tool_selected.connect(self._activate_tool)
        self._canvas.tool_shortcut_pressed.connect(self._activate_tool)
        self._canvas.tool_changed.connect(self._on_tool_changed)
        self._canvas.cursor_moved.connect(self._on_cursor_moved)
        self._canvas.cursor_left.connect(lambda: self._position_label.setText("—"))
        self._canvas.zoom_changed.connect(self._on_zoom_changed)
        self._canvas.document_modified.connect(self._on_document_modified)
        self._canvas.hint_requested.connect(self._hint_label.setText)
        self._canvas.selection_changed.connect(self._update_selection_label)

    # -------------------------------------------------------------- documento

    @property
    def document(self) -> Document:
        return self._canvas.document

    def load_document(self, document: Document) -> None:
        """Coloca um documento no editor e registra o acesso na biblioteca."""
        self._canvas.set_document(document)
        if document.path is not None:
            self._library.remember(document.path, document.pixels)
        self._refresh_title()
        self._update_size_label()
        self._update_history_actions()

    def new_image(self) -> None:
        if not self._confirm_discard():
            return
        dialog = NewImageDialog(self)
        if dialog.exec() != NewImageDialog.DialogCode.Accepted:
            return
        choice = dialog.choice()
        self.load_document(Document.blank(choice.width, choice.height, choice.color))

    def open_file(self, path: Path | None = None) -> None:
        if not self._confirm_discard():
            return
        if path is None:
            selected, _ = QFileDialog.getOpenFileName(
                self, "Abrir imagem", str(default_documents_dir()), OPEN_FILTER
            )
            if not selected:
                return
            path = Path(selected)
        try:
            document = Document.open(path)
        except Exception as error:  # noqa: BLE001 - qualquer falha vira aviso ao usuário
            QMessageBox.critical(self, "Não foi possível abrir", str(error))
            return
        self.load_document(document)

    def save(self) -> bool:
        self._canvas.commit_active_tool()
        document = self.document
        if document.path is None or document.path.suffix.lower() not in WRITABLE_EXTENSIONS:
            return self.save_as()
        return self._write(document.path)

    def save_as(self) -> bool:
        self._canvas.commit_active_tool()
        suggestion = self.document.path or (
            default_documents_dir() / f"{self.document.name}.png"
        )
        selected, _ = QFileDialog.getSaveFileName(
            self, "Salvar como", str(suggestion), SAVE_FILTER
        )
        if not selected:
            return False
        return self._write(Path(selected))

    def _write(self, path: Path) -> bool:
        try:
            saved = self.document.save(path)
        except Exception as error:  # noqa: BLE001
            QMessageBox.critical(self, "Não foi possível salvar", str(error))
            return False
        self._library.remember(saved, self.document.pixels)
        self._refresh_title()
        self._hint_label.setText(f"Salvo em {saved}")
        return True

    # ------------------------------------------------------------------ edição

    def _forward_to_text_widget(self, method: str) -> bool:
        """Devolve o atalho a quem está digitando, em vez de editar a imagem.

        A ferramenta de texto usa um campo de edição real por cima da tela. Sem
        isso, Ctrl+C ali copiaria a seleção da imagem e Delete apagaria pixels em
        vez do caractere sob o cursor.
        """
        widget = QApplication.focusWidget()
        if not isinstance(widget, (QLineEdit, QPlainTextEdit, QTextEdit)):
            return False
        if method == "delete":
            if isinstance(widget, QLineEdit):
                widget.del_()
            else:
                widget.textCursor().deleteChar()
            return True
        handler = getattr(widget, method, None)
        if callable(handler):
            handler()
        return True

    def undo(self) -> None:
        if self._forward_to_text_widget("undo"):
            return
        self._canvas.commit_active_tool()
        if self.document.undo():
            self._after_history_step()

    def redo(self) -> None:
        if self._forward_to_text_widget("redo"):
            return
        self._canvas.commit_active_tool()
        if self.document.redo():
            self._after_history_step()

    def _after_history_step(self) -> None:
        """Atualiza a vista depois de desfazer ou refazer.

        Só reenquadra quando o passo mudou as dimensões da imagem (girar,
        recortar, redimensionar). Desfazer uma pincelada não pode mexer no zoom:
        quem está trabalhando ampliado num detalhe perderia o lugar a cada
        Ctrl+Z.
        """
        if (self.document.width, self.document.height) != self._canvas.framed_size:
            self._after_document_structure_change()
            return
        self._canvas.refresh()
        self._on_document_modified()

    def copy(self) -> None:
        if self._forward_to_text_widget("copy"):
            return
        pixels = self._selection_tool().copied_pixels()
        if pixels is None:
            return
        QGuiApplication.clipboard().setImage(array_to_image(pixels))
        self._hint_label.setText("Seleção copiada.")

    def cut(self) -> None:
        if self._forward_to_text_widget("cut"):
            return
        self.copy()
        self.delete_selection()

    def paste(self) -> None:
        if self._forward_to_text_widget("paste"):
            return
        image = QGuiApplication.clipboard().image()
        if image.isNull():
            self._hint_label.setText("A área de transferência não tem imagem.")
            return
        tool = self._activate_selection_tool()
        tool.begin_paste(image_to_array(image), self._paste_origin())

    def _paste_origin(self) -> tuple[int, int]:
        """Cola no canto superior esquerdo do que está visível, nunca fora da tela."""
        visible = self._canvas.widget_to_document(QPointF(24.0, 24.0))
        return (
            max(0, min(int(visible.x()), self.document.width - 1)),
            max(0, min(int(visible.y()), self.document.height - 1)),
        )

    def delete_selection(self) -> None:
        if self._forward_to_text_widget("delete"):
            return
        self._selection_tool().delete_selection()

    def select_all(self) -> None:
        if self._forward_to_text_widget("selectAll"):
            return
        self._canvas.commit_active_tool()
        self._activate_selection_tool()
        self._canvas.selection.select_all()
        self._canvas.refresh_selection_outline()

    def deselect(self) -> None:
        self._canvas.commit_active_tool()
        self._canvas.selection.clear()
        self._canvas.refresh_selection_outline()

    def invert_selection(self) -> None:
        self._canvas.commit_active_tool()
        self._canvas.selection.invert()
        self._canvas.refresh_selection_outline()

    def crop_to_selection(self) -> None:
        self._canvas.commit_active_tool()
        bounds = self._canvas.selection.bounds
        if bounds is None:
            self._hint_label.setText("Selecione uma área antes de recortar.")
            return
        self.document.crop(bounds)
        self._after_document_structure_change()

    # ------------------------------------------------------------------ imagem

    def resize_image(self) -> None:
        self._resize_with_dialog(canvas_only=False)

    def resize_canvas(self) -> None:
        self._resize_with_dialog(canvas_only=True)

    def _resize_with_dialog(self, canvas_only: bool) -> None:
        self._canvas.commit_active_tool()
        dialog = ResizeDialog(
            self.document.width, self.document.height, canvas_only=canvas_only, parent=self
        )
        if dialog.exec() != ResizeDialog.DialogCode.Accepted:
            return
        choice = dialog.choice()
        if canvas_only:
            self.document.expand_canvas(choice.width, choice.height)
        else:
            self.document.resize(choice.width, choice.height, choice.smooth)
        self._after_document_structure_change()

    def rotate(self, degrees: float) -> None:
        self._canvas.commit_active_tool()
        self.document.rotate(degrees)
        self._after_document_structure_change()

    def flip(self, horizontal: bool) -> None:
        self._canvas.commit_active_tool()
        self.document.flip(horizontal)
        self._after_document_structure_change()

    def open_adjustments(self, restrict_to_selection: bool = False) -> None:
        self._canvas.commit_active_tool()
        if restrict_to_selection and not self._canvas.selection.is_active:
            self._hint_label.setText("Nenhuma seleção ativa — ajustando a imagem inteira.")
            restrict_to_selection = False
        dialog = AdjustmentsDialog(
            self.document, self._canvas, restrict_to_selection, parent=self
        )
        dialog.exec()
        self._update_history_actions()

    # ------------------------------------------------------------------- ajuda

    def show_help(self) -> None:
        rows = "".join(
            f"<tr><td style='padding-right:18px'><b>{tool.shortcut or '—'}</b></td>"
            f"<td style='padding-right:14px'>{tool.label}</td>"
            f"<td>{tool.hint}</td></tr>"
            for tool in TOOL_CLASSES
        )
        QMessageBox.information(
            self,
            "Atalhos e ferramentas",
            "<h3>Ferramentas</h3>"
            f"<table>{rows}</table>"
            "<h3>Navegação</h3>"
            "<p>Ctrl + roda: zoom · Roda: rolar · Shift + roda: rolar na horizontal<br>"
            "Espaço ou botão do meio: arrastar a imagem · Ctrl+0: tamanho real · "
            "Ctrl+9: ajustar à janela</p>"
            "<h3>No pincel</h3>"
            "<p>Botão direito pinta com a cor de fundo e inverte os efeitos de "
            "saturação, matiz, clarear e escurecer.</p>",
        )

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"Sobre o {APP_NAME}",
            f"<h2>{APP_NAME}</h2>"
            "<p>O Paint que você conhece, com os pincéis que ele nunca teve: "
            "saturação, blend, desfoque, nitidez, clarear, escurecer e matiz — "
            "todos funcionando com qualquer ponta, Spray incluído.</p>",
        )

    # ---------------------------------------------------------------- internos

    def _activate_tool(self, key: str) -> None:
        self._canvas.set_tool(key)
        self._tool_box.set_active(key)

    def _activate_selection_tool(self) -> SelectionTool:
        if not isinstance(self._canvas.tool(), SelectionTool):
            self._activate_tool("select_rect")
        tool = self._canvas.tool()
        assert isinstance(tool, SelectionTool)
        return tool

    def _selection_tool(self) -> SelectionTool:
        tool = self._canvas.tool()
        if isinstance(tool, SelectionTool):
            return tool
        return self._activate_selection_tool()

    def _on_tool_changed(self, key: str) -> None:
        self._tool_box.set_active(key)
        self._options.show_for(self._canvas.tool())

    def _on_cursor_moved(self, position: QPointF) -> None:
        self._position_label.setText(f"{int(position.x())}, {int(position.y())} px")

    def _on_zoom_changed(self, zoom: float) -> None:
        self._zoom_label.setText(f"{zoom * 100:.0f}%")
        self._zoom_slider.blockSignals(True)
        self._zoom_slider.setValue(int(round(_zoom_to_slider(zoom))))
        self._zoom_slider.blockSignals(False)

    def _on_zoom_slider(self, value: int) -> None:
        self._canvas.set_zoom(_slider_to_zoom(value))

    def _on_document_modified(self) -> None:
        self._refresh_title()
        self._update_history_actions()
        self._update_size_label()

    def _after_document_structure_change(self) -> None:
        self._canvas.sync_after_resize()
        self._canvas.fit_to_view()
        self._on_document_modified()

    def _update_history_actions(self) -> None:
        history = self.document.history
        self._undo_action.setEnabled(history.can_undo)
        self._redo_action.setEnabled(history.can_redo)
        self._undo_action.setText(
            f"Desfazer {history.undo_label}" if history.undo_label else "Desfazer"
        )
        self._redo_action.setText(
            f"Refazer {history.redo_label}" if history.redo_label else "Refazer"
        )

    def _update_size_label(self) -> None:
        self._size_label.setText(f"{self.document.width} × {self.document.height} px")

    def _update_selection_label(self) -> None:
        bounds = self._canvas.selection.bounds
        self._selection_label.setText(
            f"Seleção {bounds[2]} × {bounds[3]}" if bounds else ""
        )

    def _refresh_title(self) -> None:
        marker = " •" if self.document.is_dirty else ""
        self.setWindowTitle(f"{self.document.name}{marker} — {APP_NAME}")

    # -------------------------------------------------------------- fechamento

    def _confirm_discard(self) -> bool:
        """Pergunta antes de descartar alterações não salvas."""
        if not self.document.is_dirty:
            return True
        answer = QMessageBox.question(
            self,
            "Alterações não salvas",
            f"Salvar as alterações em “{self.document.name}” antes de continuar?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return False
        if answer == QMessageBox.StandardButton.Save:
            return self.save()
        return True

    def _go_to_hub(self) -> None:
        if self._confirm_discard():
            self.hub_requested.emit()

    def closeEvent(self, event) -> None:
        self._canvas.commit_active_tool()
        if self._confirm_discard():
            event.accept()
        else:
            event.ignore()


def _side_panel(content: QWidget, width: int) -> QWidget:
    """Envolve um painel lateral num scroll com largura fixa."""
    area = QScrollArea()
    area.setWidget(content)
    area.setWidgetResizable(True)
    area.setFixedWidth(width)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    area.setStyleSheet(f"QScrollArea {{ background: {PALETTE.surface}; }}")
    return area


def _zoom_to_slider(zoom: float) -> float:
    """O controle é logarítmico: cada passo dobra ou divide pela metade."""
    from math import log2

    return max(-100.0, min(100.0, log2(max(zoom, 1e-3)) * 20.0))


def _slider_to_zoom(value: int) -> float:
    return float(2.0 ** (value / 20.0))

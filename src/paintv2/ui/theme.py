"""Identidade visual do Paint-V2.

A direção é o Paint "revelado em negativo": onde o original é branco com azul, o
V2 é grafite com âmbar. Não é escuro por moda — é o mesmo motivo pelo qual todo
editor de imagem sério é: uma interface clara em volta da tela altera a percepção
de brilho e saturação do que está sendo editado.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class Palette:
    """Cores da interface. Tons frios e dessaturados para não competir com a arte."""

    background: str = "#14161B"
    surface: str = "#1C1F26"
    surface_raised: str = "#242832"
    surface_hover: str = "#2E333F"
    border: str = "#333846"
    border_strong: str = "#454C5D"

    text: str = "#E7E9EF"
    text_muted: str = "#98A0B2"
    text_disabled: str = "#5D6474"

    accent: str = "#FF9F45"
    accent_hover: str = "#FFB673"
    accent_pressed: str = "#E0842F"
    accent_text: str = "#1A1206"

    info: str = "#4CC2FF"
    danger: str = "#FF6B6B"

    canvas_void: str = "#0F1115"
    checker_light: str = "#3A3F4B"
    checker_dark: str = "#2C313B"

    def color(self, name: str) -> QColor:
        return QColor(getattr(self, name))


PALETTE = Palette()

FONT_STACK = '"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif'


def build_stylesheet(palette: Palette = PALETTE) -> str:
    """Folha de estilo global do aplicativo."""
    return f"""
    * {{
        font-family: {FONT_STACK};
        font-size: 13px;
    }}

    QWidget {{
        background-color: {palette.background};
        color: {palette.text};
    }}

    QMainWindow::separator {{
        background: {palette.border};
        width: 1px;
        height: 1px;
    }}

    QMenuBar {{
        background-color: {palette.surface};
        border-bottom: 1px solid {palette.border};
        padding: 2px 6px;
    }}
    QMenuBar::item {{
        padding: 6px 12px;
        border-radius: 6px;
        background: transparent;
    }}
    QMenuBar::item:selected {{ background: {palette.surface_hover}; }}

    QMenu {{
        background-color: {palette.surface_raised};
        border: 1px solid {palette.border};
        border-radius: 10px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 7px 28px 7px 14px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{ background: {palette.accent}; color: {palette.accent_text}; }}
    QMenu::item:disabled {{ color: {palette.text_disabled}; }}
    QMenu::separator {{
        height: 1px;
        background: {palette.border};
        margin: 6px 10px;
    }}

    QToolBar {{
        background-color: {palette.surface};
        border: none;
        border-bottom: 1px solid {palette.border};
        padding: 4px 8px;
        spacing: 4px;
    }}
    QToolBar QToolButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 6px;
    }}
    QToolBar QToolButton:hover {{
        background: {palette.surface_hover};
        border-color: {palette.border};
    }}
    QToolBar QToolButton:pressed {{ background: {palette.border}; }}
    QToolBar QToolButton:checked {{
        background: {palette.surface_raised};
        border-color: {palette.accent};
    }}
    QToolBar::separator {{
        background: {palette.border};
        width: 1px;
        margin: 6px 6px;
    }}

    QStatusBar {{
        background-color: {palette.surface};
        border-top: 1px solid {palette.border};
        color: {palette.text_muted};
    }}
    QStatusBar QLabel {{ padding: 0 10px; }}

    QDockWidget {{
        titlebar-close-icon: none;
        titlebar-normal-icon: none;
    }}
    QDockWidget::title {{
        background: {palette.surface};
        padding: 8px 12px;
        border-bottom: 1px solid {palette.border};
        font-weight: 600;
    }}

    QGroupBox {{
        border: 1px solid {palette.border};
        border-radius: 10px;
        margin-top: 14px;
        padding: 12px 10px 10px 10px;
        background: {palette.surface};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {palette.text_muted};
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
    }}

    /* Rótulos não pintam fundo próprio: dentro de um QGroupBox ou de um botão,
       o fundo herdado desenharia uma caixa escura em volta do texto. */
    QLabel {{
        background: transparent;
    }}

    QLabel[role="heading"] {{
        font-size: 26px;
        font-weight: 700;
        letter-spacing: -0.4px;
    }}
    QLabel[role="subheading"] {{
        font-size: 14px;
        color: {palette.text_muted};
    }}
    QLabel[role="section"] {{
        font-size: 11px;
        font-weight: 700;
        color: {palette.text_muted};
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }}
    QLabel[role="muted"] {{ color: {palette.text_muted}; }}

    QPushButton {{
        background-color: {palette.surface_raised};
        border: 1px solid {palette.border};
        border-radius: 8px;
        padding: 8px 16px;
        color: {palette.text};
    }}
    QPushButton:hover {{ background-color: {palette.surface_hover}; }}
    QPushButton:pressed {{ background-color: {palette.border}; }}
    QPushButton:disabled {{ color: {palette.text_disabled}; }}
    QPushButton[variant="primary"] {{
        background-color: {palette.accent};
        border-color: {palette.accent};
        color: {palette.accent_text};
        font-weight: 600;
    }}
    QPushButton[variant="primary"]:hover {{ background-color: {palette.accent_hover}; }}
    QPushButton[variant="primary"]:pressed {{ background-color: {palette.accent_pressed}; }}
    QPushButton[variant="ghost"] {{
        background: transparent;
        border-color: transparent;
        color: {palette.text_muted};
    }}
    QPushButton[variant="ghost"]:hover {{
        background: {palette.surface_hover};
        color: {palette.text};
    }}

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{
        background-color: {palette.background};
        border: 1px solid {palette.border};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {palette.accent};
        selection-color: {palette.accent_text};
    }}
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border-color: {palette.accent};
    }}
    QComboBox QAbstractItemView {{
        background: {palette.surface_raised};
        border: 1px solid {palette.border};
        border-radius: 8px;
        padding: 4px;
        selection-background-color: {palette.accent};
        selection-color: {palette.accent_text};
        outline: none;
    }}
    /* A seta do combo fica com o desenho nativo do Fusion. Já os degraus do
       spin somem: assim que a folha de estilo toca no QSpinBox, o Qt para de
       desenhar as setinhas e sobra um bloco cinza sem função aparente. Todo
       campo numérico aqui vem acompanhado de um slider, e a roda do mouse e as
       setas do teclado continuam ajustando o valor. */
    QSpinBox::up-button, QSpinBox::down-button,
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        width: 0;
        border: none;
    }}

    QCheckBox, QRadioButton {{ spacing: 8px; }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {palette.border_strong};
        background: {palette.background};
    }}
    QCheckBox::indicator {{ border-radius: 4px; }}
    QRadioButton::indicator {{ border-radius: 8px; }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {palette.accent};
        border-color: {palette.accent};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {palette.border};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {palette.accent};
        border-radius: 2px;
    }}
    /* Num controle que vai de -100 a +100, preencher a partir da esquerda faria
       o zero parecer meio caminho andado. Nesses o trilho fica neutro e só a
       posição do cursor informa o valor. */
    QSlider[bipolar="true"]::sub-page:horizontal {{
        background: {palette.border};
    }}
    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 7px;
        background: {palette.text};
    }}
    QSlider::handle:horizontal:hover {{ background: {palette.accent_hover}; }}

    QScrollBar:vertical, QScrollBar:horizontal {{
        background: transparent;
        border: none;
        margin: 0;
    }}
    QScrollBar:vertical {{ width: 12px; }}
    QScrollBar:horizontal {{ height: 12px; }}
    QScrollBar::handle {{
        background: {palette.border_strong};
        border-radius: 6px;
        min-width: 32px;
        min-height: 32px;
    }}
    QScrollBar::handle:hover {{ background: {palette.text_disabled}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QScrollArea {{ border: none; }}

    QToolTip {{
        background-color: {palette.surface_raised};
        color: {palette.text};
        border: 1px solid {palette.border_strong};
        border-radius: 6px;
        padding: 6px 9px;
    }}

    QDialog {{ background-color: {palette.surface}; }}

    QTabWidget::pane {{
        border: 1px solid {palette.border};
        border-radius: 10px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        padding: 8px 16px;
        border-radius: 8px;
        color: {palette.text_muted};
    }}
    QTabBar::tab:selected {{
        background: {palette.surface_raised};
        color: {palette.text};
    }}
    """

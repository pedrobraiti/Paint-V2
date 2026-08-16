# -*- mode: python ; coding: utf-8 -*-
"""Receita do PyInstaller para o Paint-V2.

Gera uma distribuição em pasta (``onedir``): a inicialização é bem mais rápida
que a de um único arquivo, que precisaria extrair todo o Qt para o disco a cada
execução — diferença perceptível num app que o usuário abre várias vezes ao dia.

O grosso do tamanho final vem do PySide6, por isso a lista de exclusões abaixo:
nada de WebEngine, QML, multimídia ou 3D, que este app não usa.
"""

from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).parent
SOURCE_ROOT = PROJECT_ROOT / "src"
RESOURCES = SOURCE_ROOT / "paintv2" / "resources"

EXCLUDED_MODULES = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtHttpServer",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialBus",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "matplotlib",
    "pytest",
    "scipy",
    "tkinter",
]

analysis = Analysis(
    [str(PROJECT_ROOT / "packaging" / "launcher.py")],
    pathex=[str(SOURCE_ROOT)],
    binaries=[],
    datas=[(str(RESOURCES), "paintv2/resources")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDED_MODULES,
    noarchive=False,
    optimize=0,
)

# O hook do PySide6 traz estas DLLs mesmo com os módulos Python excluídos, por
# serem dependências declaradas do pacote. Nenhuma delas é alcançável a partir
# de um app puro de QtWidgets: não há QML, nem visualizador de PDF, e o
# renderizador é o raster — o OpenGL por software (20 MB) nunca é carregado.
UNREACHABLE_BINARIES = {
    "opengl32sw.dll",
    "qt6qml.dll",
    "qt6qmlmeta.dll",
    "qt6qmlmodels.dll",
    "qt6qmlworkerscript.dll",
    "qt6quick.dll",
    "qt6quickcontrols2.dll",
    "qt6quicktemplates2.dll",
    "qt6pdf.dll",
    "qt6virtualkeyboard.dll",
}

analysis.binaries = TOC(
    entry
    for entry in analysis.binaries
    if Path(entry[0]).name.lower() not in UNREACHABLE_BINARIES
)

archive = PYZ(analysis.pure)

executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Paint-V2",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(RESOURCES / "paintv2.ico"),
    version=str(PROJECT_ROOT / "packaging" / "version_info.txt"),
)

COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Paint-V2",
)

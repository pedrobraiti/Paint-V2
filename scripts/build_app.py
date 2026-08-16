"""Constrói o Paint-V2: ícone, executável e (se possível) o instalador.

Uso:
    python scripts/build_app.py            # tudo o que estiver disponível
    python scripts/build_app.py --no-installer
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC = PROJECT_ROOT / "packaging" / "paintv2.spec"
INNO_SCRIPT = PROJECT_ROOT / "packaging" / "paintv2.iss"
DIST = PROJECT_ROOT / "dist"
BUILD = PROJECT_ROOT / "build"

INNO_CANDIDATES = tuple(
    Path(base) / "Inno Setup 6" / "ISCC.exe"
    for base in (
        os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"),
        os.environ.get("ProgramFiles", "C:/Program Files"),
        # O winget instala por usuário quando não há elevação.
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
    )
    if base
)


def run(command: list[str], description: str) -> None:
    print(f"\n▶ {description}")
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise SystemExit(f"Falhou: {description} (código {result.returncode})")


def find_inno_compiler() -> Path | None:
    """Localiza o ISCC no PATH ou nos diretórios padrão de instalação."""
    on_path = shutil.which("iscc")
    if on_path:
        return Path(on_path)
    return next((path for path in INNO_CANDIDATES if path.is_file()), None)


def main() -> int:
    parser = argparse.ArgumentParser(description="Empacota o Paint-V2 para Windows.")
    parser.add_argument(
        "--no-installer", action="store_true", help="Gera apenas a pasta com o .exe."
    )
    parser.add_argument(
        "--keep-build", action="store_true", help="Não apaga os intermediários."
    )
    arguments = parser.parse_args()

    run([sys.executable, str(PROJECT_ROOT / "scripts" / "build_icon.py")], "Gerando ícone")
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--distpath",
            str(DIST),
            "--workpath",
            str(BUILD),
            str(SPEC),
        ],
        "Compilando o executável",
    )

    executable = DIST / "Paint-V2" / "Paint-V2.exe"
    if not executable.is_file():
        raise SystemExit("O PyInstaller terminou, mas o executável não foi encontrado.")
    print(f"\n✔ Executável em {executable}")

    if arguments.no_installer:
        return 0

    compiler = find_inno_compiler()
    if compiler is None:
        print(
            "\n⚠ Inno Setup não encontrado — o instalador não foi gerado.\n"
            "  Instale com:  winget install -e --id JRSoftware.InnoSetup\n"
            "  e rode este script de novo."
        )
        return 0

    run([str(compiler), str(INNO_SCRIPT)], "Gerando o instalador")
    installers = sorted((DIST / "installer").glob("Paint-V2-Setup-*.exe"))
    if installers:
        print(f"\n✔ Instalador em {installers[-1]}")

    if not arguments.keep_build:
        shutil.rmtree(BUILD, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

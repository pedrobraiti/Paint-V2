"""Script de entrada usado pelo PyInstaller.

Existe separado de ``paintv2/__main__.py`` porque o PyInstaller precisa de um
arquivo de nível superior, e não de um módulo executado com ``-m``.
"""

import multiprocessing
import sys

from paintv2.app import main

if __name__ == "__main__":
    # Necessário para que um executável congelado não reabra a janela ao criar
    # processos filhos (comportamento padrão do multiprocessing no Windows).
    multiprocessing.freeze_support()
    sys.exit(main())

import sys
import os


def resource_path(relative_path):
    """
    Retorna o caminho correto do recurso
    tanto no modo dev quanto no .exe (PyInstaller)
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

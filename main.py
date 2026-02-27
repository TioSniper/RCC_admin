import sys
import os
import traceback
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication
from telas.principal.principal_ui import PrincipalUI
from telas.principal.principal_controller import PrincipalController
from utils.admin_realtime import iniciar_realtime

load_dotenv()
os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg=false"


def _set_taskbar_icon():
    """Define AppUserModelID para o ícone aparecer corretamente na barra de tarefas."""
    try:
        import ctypes

        app_id = f"RCC_Admin"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def main():
    _set_taskbar_icon()

    app = QApplication(sys.argv)

    from PyQt6.QtGui import QIcon
    from utils.resource_path import resource_path

    icon = QIcon(resource_path("assets/icons/app.ico"))
    app.setWindowIcon(icon)

    try:
        realtime = iniciar_realtime(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_SERVICE_KEY"),
            anon_key=os.getenv("SUPABASE_ANON_KEY", ""),
        )

        ui = PrincipalUI()
        controller = PrincipalController(ui, realtime)
        ui.show()

    except Exception:
        print("=" * 60)
        print("ERRO AO INICIAR O APP:")
        traceback.print_exc()
        print("=" * 60)
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

load_dotenv()
os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg=false"

from telas.principal.principal_ui import PrincipalUI
from telas.principal.principal_controller import PrincipalController
from utils.admin_realtime import iniciar_realtime


def main():
    app = QApplication(sys.argv)

    # Inicia Realtime antes das telas — uma única conexão para todo o Admin
    realtime = iniciar_realtime(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY"),
    )

    ui = PrincipalUI()
    controller = PrincipalController(ui, realtime)
    ui.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

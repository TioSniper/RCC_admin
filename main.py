import sys
import os
import traceback
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

load_dotenv()
os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg=false"

from telas.principal.principal_ui import PrincipalUI
from telas.principal.principal_controller import PrincipalController
from utils.admin_realtime import iniciar_realtime


def main():
    app = QApplication(sys.argv)

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

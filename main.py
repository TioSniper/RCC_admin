import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import QApplication

load_dotenv()
os.environ["QT_LOGGING_RULES"] = "qt.multimedia.ffmpeg=false"

from telas.principal.principal_ui import PrincipalUI
from telas.principal.principal_controller import PrincipalController


def main():
    app = QApplication(sys.argv)

    ui = PrincipalUI()
    controller = PrincipalController(ui)
    ui.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

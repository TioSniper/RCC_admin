from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget
)
from PyQt6.QtCore import Qt


class DialogBase(QDialog):
    """Diálogo base no padrão visual do RCC Admin."""

    def __init__(self, titulo: str, parent=None, largura: int = 400):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setFixedWidth(largura)
        self._drag_pos = None
        self._construir(titulo)

    def _construir(self, titulo: str):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(12, 12, 12, 12)

        container = QFrame()
        container.setObjectName("dialog_container")
        container.setStyleSheet("""
            QFrame#dialog_container {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a2854, stop:1 #0a1228);
                border-radius: 16px;
                border: 1px solid #FFD700;
            }
            QLabel { color: #cccccc; font-size: 12px; }
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Barra de título
        barra = QFrame()
        barra.setFixedHeight(48)
        barra.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 26, 61, 0.9);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
                border-bottom: 1px solid #FFD700;
            }
        """)

        layout_barra = QHBoxLayout(barra)
        layout_barra.setContentsMargins(16, 0, 12, 0)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setStyleSheet(
            "color: #FFD700; font-size: 13px; font-weight: bold;"
        )

        btn_fechar = QPushButton("✕")
        btn_fechar.setFixedSize(30, 30)
        btn_fechar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_fechar.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #ff4444; color: white; }
        """)
        btn_fechar.clicked.connect(self.reject)

        layout_barra.addWidget(lbl_titulo)
        layout_barra.addStretch()
        layout_barra.addWidget(btn_fechar)
        layout.addWidget(barra)

        # Corpo
        corpo = QFrame()
        corpo.setStyleSheet("background: transparent;")
        self._layout_corpo = QVBoxLayout(corpo)
        self._layout_corpo.setContentsMargins(20, 20, 20, 20)
        self._layout_corpo.setSpacing(12)
        self._layout_corpo.addStretch()
        layout.addWidget(corpo)

        # Botões
        layout_btns = QHBoxLayout()
        layout_btns.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setFixedHeight(32)
        btn_cancelar.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancelar.setStyleSheet("""
            QPushButton {
                background-color: #2a3f7a;
                color: #aaaaaa;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                border: none;
            }
            QPushButton:hover { background-color: #334d99; }
        """)
        btn_cancelar.clicked.connect(self.reject)

        self._btn_confirmar = QPushButton("✓  Confirmar")
        self._btn_confirmar.setFixedHeight(32)
        self._btn_confirmar.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_confirmar.setStyleSheet("""
            QPushButton {
                background-color: #FFD700;
                color: #0a1228;
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover { background-color: #f0c800; }
        """)

        layout_btns.addWidget(btn_cancelar)
        layout_btns.addWidget(self._btn_confirmar)
        self._layout_corpo.addLayout(layout_btns)

        raiz.addWidget(container)

        # Arrastar
        def mouse_press(e):
            if e.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = (
                    e.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
        def mouse_move(e):
            if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
                self.move(e.globalPosition().toPoint() - self._drag_pos)
        def mouse_release(e):
            self._drag_pos = None

        barra.mousePressEvent  = mouse_press
        barra.mouseMoveEvent   = mouse_move
        barra.mouseReleaseEvent = mouse_release

    def _estilo_input(self) -> str:
        return """
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #2a3f7a;
                border-radius: 8px;
                color: white;
                padding: 0 12px;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #FFD700; }
        """


class DialogConfirmacao(DialogBase):
    """Diálogo de confirmação simples."""

    def __init__(self, mensagem: str, parent=None):
        super().__init__("⚠️  Confirmação", parent)

        # Remove o stretch antes de adicionar conteúdo
        item = self._layout_corpo.takeAt(0)

        lbl = QLabel(mensagem)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #cccccc; font-size: 12px;")
        self._layout_corpo.insertWidget(0, lbl)

        self._btn_confirmar.setText("✓  Confirmar")
        self._btn_confirmar.clicked.connect(self.accept)

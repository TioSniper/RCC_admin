from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class LoginUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RCC Admin")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 520)
        self._drag_pos = None
        self._construir()

    def _construir(self):
        central = QWidget()
        central.setObjectName("widget_central")
        self.setCentralWidget(central)

        layout_raiz = QVBoxLayout(central)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        # ── Barra de título ───────────────────────────────────────
        self.barra_topo = QFrame()
        self.barra_topo.setObjectName("barra_topo")
        self.barra_topo.setFixedHeight(48)

        layout_barra = QHBoxLayout(self.barra_topo)
        layout_barra.setContentsMargins(16, 0, 8, 0)

        lbl_titulo = QLabel("🛡️  RCC Admin")
        lbl_titulo.setObjectName("label_titulo")
        lbl_titulo.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.btn_fechar = QPushButton("✕")
        self.btn_fechar.setObjectName("btn_fechar")
        self.btn_fechar.setFixedSize(32, 32)
        self.btn_fechar.setCursor(Qt.CursorShape.PointingHandCursor)

        layout_barra.addWidget(lbl_titulo)
        layout_barra.addStretch()
        layout_barra.addWidget(self.btn_fechar)

        layout_raiz.addWidget(self.barra_topo)

        # ── Corpo ─────────────────────────────────────────────────
        corpo = QWidget()
        corpo.setObjectName("corpo_login")
        layout_corpo = QVBoxLayout(corpo)
        layout_corpo.setContentsMargins(48, 40, 48, 40)
        layout_corpo.setSpacing(20)

        # Logo/título
        lbl_logo = QLabel("⚙️")
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_logo.setStyleSheet("font-size: 52px;")

        lbl_bem_vindo = QLabel("Painel Administrativo")
        lbl_bem_vindo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_bem_vindo.setStyleSheet(
            "color: #FFD700; font-size: 18px; font-weight: bold;"
        )

        lbl_sub = QLabel("Acesso restrito ao administrador")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("color: #8899bb; font-size: 12px;")

        layout_corpo.addWidget(lbl_logo)
        layout_corpo.addWidget(lbl_bem_vindo)
        layout_corpo.addWidget(lbl_sub)
        layout_corpo.addSpacing(10)

        # Username
        lbl_user = QLabel("Usuário:")
        lbl_user.setStyleSheet("color: #aaaaaa; font-size: 11px; font-weight: bold;")
        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("admin")
        self.input_usuario.setFixedHeight(40)
        self.input_usuario.setObjectName("input_login")

        # Senha master
        lbl_senha = QLabel("Senha Master:")
        lbl_senha.setStyleSheet("color: #aaaaaa; font-size: 11px; font-weight: bold;")
        self.input_senha = QLineEdit()
        self.input_senha.setPlaceholderText("••••••••")
        self.input_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_senha.setFixedHeight(40)
        self.input_senha.setObjectName("input_login")

        # Aviso
        self.lbl_aviso = QLabel("")
        self.lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        self.lbl_aviso.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_aviso.setWordWrap(True)

        # Botão entrar
        self.btn_entrar = QPushButton("Entrar")
        self.btn_entrar.setObjectName("btn_entrar")
        self.btn_entrar.setFixedHeight(42)
        self.btn_entrar.setCursor(Qt.CursorShape.PointingHandCursor)

        layout_corpo.addWidget(lbl_user)
        layout_corpo.addWidget(self.input_usuario)
        layout_corpo.addWidget(lbl_senha)
        layout_corpo.addWidget(self.input_senha)
        layout_corpo.addWidget(self.lbl_aviso)
        layout_corpo.addWidget(self.btn_entrar)
        layout_corpo.addStretch()

        layout_raiz.addWidget(corpo)

        self._aplicar_estilos()

    def _aplicar_estilos(self):
        self.setStyleSheet("""
            QWidget#widget_central {
                background: qradialgradient(cx:0.5, cy:0.5, radius:1,
                            fx:0.5, fy:0.5,
                            stop:0 #1a2854,
                            stop:1 #0a1228);
                border-radius: 18px;
            }

            QFrame#barra_topo {
                background-color: rgba(15, 26, 61, 0.8);
                border-bottom: 2px solid #FFD700;
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
            }

            #label_titulo { color: #FFD700; }

            #btn_fechar {
                background-color: #DC2626;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            #btn_fechar:hover { background-color: #B91C1C; }

            QLineEdit#input_login {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #2a3f7a;
                border-radius: 8px;
                color: white;
                padding: 0 12px;
                font-size: 13px;
            }
            QLineEdit#input_login:focus {
                border: 1px solid #FFD700;
            }

            QPushButton#btn_entrar {
                background-color: #FFD700;
                color: #0a1228;
                border-radius: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton#btn_entrar:hover {
                background-color: #f0c800;
            }
            QPushButton#btn_entrar:disabled {
                background-color: #2a3f7a;
                color: #555;
            }

            QLabel { color: #cccccc; }
        """)

    # ── Arrastar janela ───────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

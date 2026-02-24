from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon


MENU_ITENS = [
    {"id": "dashboard",   "emoji": "📊", "nome": "Dashboard"},
    {"id": "usuarios",    "emoji": "👥", "nome": "Usuários"},
    {"id": "assinaturas", "emoji": "📋", "nome": "Assinaturas"},
    {"id": "planos",      "emoji": "🎯", "nome": "Planos"},
    {"id": "modulos",     "emoji": "🧩", "nome": "Módulos"},
    {"id": "acessos",     "emoji": "🔑", "nome": "Acessos Extras"},
    {"id": "relatorios",  "emoji": "📈", "nome": "Relatórios"},
    {"id": "logs",        "emoji": "📝", "nome": "Logs"},
]


class PrincipalUI(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RCC Admin")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1200, 750)
        self._drag_pos = None
        self._menu_expandido = True
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

        self.lbl_titulo = QLabel("🛡️  RCC Admin — Painel Administrativo")
        self.lbl_titulo.setObjectName("label_titulo")
        self.lbl_titulo.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.btn_minimizar = QPushButton("─")
        self.btn_minimizar.setObjectName("btn_minimizar")
        self.btn_minimizar.setFixedSize(32, 32)
        self.btn_minimizar.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_maximizar = QPushButton("□")
        self.btn_maximizar.setObjectName("btn_maximizar")
        self.btn_maximizar.setFixedSize(32, 32)
        self.btn_maximizar.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_fechar = QPushButton("✕")
        self.btn_fechar.setObjectName("btn_fechar")
        self.btn_fechar.setFixedSize(32, 32)
        self.btn_fechar.setCursor(Qt.CursorShape.PointingHandCursor)

        layout_barra.addWidget(self.lbl_titulo)
        layout_barra.addStretch()
        layout_barra.addWidget(self.btn_minimizar)
        layout_barra.addWidget(self.btn_maximizar)
        layout_barra.addWidget(self.btn_fechar)

        layout_raiz.addWidget(self.barra_topo)

        # ── Área principal (menu + conteúdo) ──────────────────────
        area_principal = QWidget()
        area_principal.setObjectName("area_principal")
        layout_principal = QHBoxLayout(area_principal)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # ── Menu lateral ──────────────────────────────────────────
        self.menu_lateral = QFrame()
        self.menu_lateral.setObjectName("menu_lateral")
        self.menu_lateral.setFixedWidth(220)

        layout_menu = QVBoxLayout(self.menu_lateral)
        layout_menu.setContentsMargins(0, 0, 0, 0)
        layout_menu.setSpacing(0)

        # Header menu
        header_menu = QFrame()
        header_menu.setObjectName("header_menu")
        header_menu.setFixedHeight(56)

        layout_header = QHBoxLayout(header_menu)
        layout_header.setContentsMargins(16, 0, 8, 0)

        lbl_menu_header = QLabel("⚙️  Menu")
        lbl_menu_header.setObjectName("label_menu_header")
        lbl_menu_header.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.btn_toggle_menu = QPushButton("◀")
        self.btn_toggle_menu.setObjectName("btn_toggle_menu")
        self.btn_toggle_menu.setFixedSize(28, 28)
        self.btn_toggle_menu.setCursor(Qt.CursorShape.PointingHandCursor)

        layout_header.addWidget(lbl_menu_header)
        layout_header.addStretch()
        layout_header.addWidget(self.btn_toggle_menu)
        layout_menu.addWidget(header_menu)

        # Botões do menu
        self.btns_menu = {}
        for item in MENU_ITENS:
            btn = QPushButton(f"  {item['emoji']}  {item['nome']}")
            btn.setObjectName("btn_menu")
            btn.setFixedHeight(46)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            self.btns_menu[item["id"]] = btn
            layout_menu.addWidget(btn)

        layout_menu.addStretch()

        # Versão
        lbl_versao = QLabel("v1.0.0")
        lbl_versao.setStyleSheet("color: #334466; font-size: 10px;")
        lbl_versao.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_menu.addWidget(lbl_versao)
        layout_menu.addSpacing(8)

        layout_principal.addWidget(self.menu_lateral)

        # ── Área de conteúdo ──────────────────────────────────────
        container_direito = QWidget()
        container_direito.setObjectName("container_direito")
        layout_direito = QVBoxLayout(container_direito)
        layout_direito.setContentsMargins(0, 0, 0, 0)
        layout_direito.setSpacing(0)

        self.area_conteudo = QStackedWidget()
        self.area_conteudo.setObjectName("area_conteudo")
        layout_direito.addWidget(self.area_conteudo)

        layout_principal.addWidget(container_direito)
        layout_raiz.addWidget(area_principal)

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

            QMainWindow { background-color: transparent; }

            QWidget#container_direito { background-color: transparent; }
            QWidget#area_principal    { background-color: transparent; }

            QFrame#barra_topo {
                background-color: rgba(15, 26, 61, 0.8);
                border-bottom: 2px solid #FFD700;
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
            }

            #label_titulo { color: #FFD700; }

            #btn_minimizar {
                background-color: transparent;
                color: white;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                border: none;
            }
            #btn_minimizar:hover { background-color: #2563EB; }

            #btn_maximizar {
                background-color: transparent;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            #btn_maximizar:hover { background-color: #10b981; }

            #btn_fechar {
                background-color: #DC2626;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            #btn_fechar:hover { background-color: #B91C1C; }

            QFrame#menu_lateral {
                background-color: rgba(15, 26, 61, 0.9);
                border-right: 2px solid #FFD700;
            }

            QFrame#header_menu {
                background-color: rgba(255, 215, 0, 0.1);
                border-bottom: 2px solid #FFD700;
            }

            #label_menu_header { color: #FFD700; }

            QPushButton#btn_toggle_menu {
                background-color: transparent;
                color: #FFD700;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#btn_toggle_menu:hover {
                background-color: rgba(255, 215, 0, 0.2);
                border-radius: 6px;
            }

            QPushButton#btn_menu {
                background-color: transparent;
                color: #ffffff;
                text-align: left;
                border: none;
                border-left: 3px solid transparent;
                font-size: 13px;
                padding-left: 8px;
            }
            QPushButton#btn_menu:hover {
                background-color: rgba(255, 215, 0, 0.1);
                border-left: 3px solid #FFD700;
            }
            QPushButton#btn_menu:checked {
                background-color: rgba(255, 215, 0, 0.15);
                border-left: 3px solid #FFD700;
                color: #FFD700;
                font-weight: bold;
            }

            QStackedWidget#area_conteudo { background-color: transparent; }

            QLabel { color: #cccccc; }

            QTableWidget {
                background-color: rgba(15, 26, 61, 0.5);
                border: 1px solid #2a3f7a;
                border-radius: 8px;
                color: white;
                gridline-color: #1a2854;
            }
            QTableWidget::item:selected {
                background-color: rgba(255, 215, 0, 0.15);
                color: #FFD700;
            }
            QHeaderView::section {
                background-color: rgba(15, 26, 61, 0.9);
                color: #FFD700;
                border: none;
                border-bottom: 1px solid #FFD700;
                padding: 6px;
                font-weight: bold;
            }

            QScrollBar:vertical {
                background: rgba(15, 26, 61, 0.5);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #FFD700;
                border-radius: 3px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical { height: 0px; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < 48:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

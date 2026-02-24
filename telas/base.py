from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit
)
from PyQt6.QtCore import Qt


class TelaBase(QWidget):
    """Tela base com cabeçalho padrão reutilizável."""

    def __init__(self, titulo: str, descricao: str, parent=None):
        super().__init__(parent)
        self._layout_raiz = QVBoxLayout(self)
        self._layout_raiz.setContentsMargins(24, 24, 24, 24)
        self._layout_raiz.setSpacing(16)
        self._construir_cabecalho(titulo, descricao)

    def _construir_cabecalho(self, titulo: str, descricao: str):
        cabecalho = QFrame()
        cabecalho.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 26, 61, 0.6);
                border-radius: 12px;
                border-bottom: 2px solid #FFD700;
            }
        """)
        cabecalho.setFixedHeight(70)

        layout = QHBoxLayout(cabecalho)
        layout.setContentsMargins(20, 0, 20, 0)

        col_texto = QVBoxLayout()
        col_texto.setSpacing(2)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setObjectName("titulo_pagina")
        lbl_titulo.setStyleSheet(
            "color: #FFD700; font-size: 18px; font-weight: bold;"
            "border: none; background: transparent;"
        )

        lbl_desc = QLabel(descricao)
        lbl_desc.setStyleSheet(
            "color: #8899bb; font-size: 11px;"
            "border: none; background: transparent;"
        )

        col_texto.addWidget(lbl_titulo)
        col_texto.addWidget(lbl_desc)

        layout.addLayout(col_texto)
        layout.addStretch()

        # Área para botões de ação do cabeçalho
        self._layout_acoes_cabecalho = QHBoxLayout()
        self._layout_acoes_cabecalho.setSpacing(8)
        layout.addLayout(self._layout_acoes_cabecalho)

        self._layout_raiz.addWidget(cabecalho)

    def _criar_btn_acao(self, texto: str, cor: str = "#FFD700",
                        cor_texto: str = "#0a1228") -> QPushButton:
        btn = QPushButton(texto)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cor};
                color: {cor_texto};
                border-radius: 8px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{ opacity: 0.85; }}
        """)
        return btn

    def _criar_tabela(self, colunas: list) -> QTableWidget:
        tabela = QTableWidget()
        tabela.setColumnCount(len(colunas))
        tabela.setHorizontalHeaderLabels(colunas)
        tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tabela.setAlternatingRowColors(True)
        tabela.verticalHeader().setVisible(False)
        tabela.horizontalHeader().setStretchLastSection(True)
        tabela.setShowGrid(False)
        tabela.setStyleSheet("""
            QTableWidget {
                background-color: rgba(15, 26, 61, 0.5);
                alternate-background-color: rgba(26, 40, 84, 0.4);
                border: 1px solid #2a3f7a;
                border-radius: 8px;
                color: white;
                gridline-color: transparent;
            }
            QTableWidget::item {
                padding: 6px;
                border: none;
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
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        return tabela

    def _criar_input_busca(self, placeholder: str = "🔍  Buscar...") -> QLineEdit:
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setFixedHeight(36)
        inp.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid #2a3f7a;
                border-radius: 8px;
                color: white;
                padding: 0 12px;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #FFD700; }
        """)
        return inp

    def _item_centralizado(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

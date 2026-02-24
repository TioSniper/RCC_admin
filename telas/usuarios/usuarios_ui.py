from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QFrame
from telas.base import TelaBase


class UsuariosUI(TelaBase):

    def __init__(self):
        super().__init__("👥  Usuários", "Gerencie os usuários do sistema")
        self._construir()

    def _construir(self):
        # Barra de ações
        layout_acoes = QHBoxLayout()
        layout_acoes.setSpacing(8)

        self.input_busca = self._criar_input_busca("🔍  Buscar por username...")
        self.btn_novo    = self._criar_btn_acao("➕  Novo Usuário")
        self.btn_refresh = self._criar_btn_acao("🔄", "#2a3f7a", "#FFD700")
        self.btn_refresh.setFixedWidth(40)

        layout_acoes.addWidget(self.input_busca)
        layout_acoes.addWidget(self.btn_novo)
        layout_acoes.addWidget(self.btn_refresh)

        self._layout_raiz.addLayout(layout_acoes)

        # Tabela
        self.tabela = self._criar_tabela([
            "Username", "Email", "Status", "Plano", "Expira em", "Cadastro", "Ações"
        ])
        self.tabela.setColumnWidth(0, 130)
        self.tabela.setColumnWidth(1, 180)
        self.tabela.setColumnWidth(2, 80)
        self.tabela.setColumnWidth(3, 100)
        self.tabela.setColumnWidth(4, 130)
        self.tabela.setColumnWidth(5, 110)

        self._layout_raiz.addWidget(self.tabela)

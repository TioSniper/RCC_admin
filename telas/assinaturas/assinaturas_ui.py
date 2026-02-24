from PyQt6.QtWidgets import QHBoxLayout
from telas.base import TelaBase

class AssinaturasUI(TelaBase):
    def __init__(self):
        super().__init__("📋  Assinaturas", "Gerencie as assinaturas dos usuários")
        self._construir()

    def _construir(self):
        layout_acoes = QHBoxLayout()
        self.input_busca = self._criar_input_busca("🔍  Buscar por usuário...")
        self.btn_refresh = self._criar_btn_acao("🔄", "#2a3f7a", "#FFD700")
        self.btn_refresh.setFixedWidth(40)
        layout_acoes.addWidget(self.input_busca)
        layout_acoes.addWidget(self.btn_refresh)
        self._layout_raiz.addLayout(layout_acoes)

        self.tabela = self._criar_tabela([
            "Usuário", "Plano", "Status", "Criado em", "Expira em", "Dias Restantes", "Ações"
        ])
        self.tabela.setColumnWidth(0, 120)
        self.tabela.setColumnWidth(1, 100)
        self.tabela.setColumnWidth(2, 80)
        self.tabela.setColumnWidth(3, 110)
        self.tabela.setColumnWidth(4, 110)
        self.tabela.setColumnWidth(5, 100)
        self._layout_raiz.addWidget(self.tabela)

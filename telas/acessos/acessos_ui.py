from PyQt6.QtWidgets import QHBoxLayout
from telas.base import TelaBase

class AcessosUI(TelaBase):
    def __init__(self):
        super().__init__("🔑  Acessos Extras", "Gerencie acessos temporários a módulos específicos")
        self._construir()

    def _construir(self):
        layout_acoes = QHBoxLayout()
        self.btn_novo    = self._criar_btn_acao("➕  Novo Acesso Extra")
        self.btn_refresh = self._criar_btn_acao("🔄", "#2a3f7a", "#FFD700")
        self.btn_refresh.setFixedWidth(40)
        layout_acoes.addStretch()
        layout_acoes.addWidget(self.btn_novo)
        layout_acoes.addWidget(self.btn_refresh)
        self._layout_raiz.addLayout(layout_acoes)

        self.tabela = self._criar_tabela([
            "Usuário", "Módulo", "Expira em", "Horas Restantes", "Ações"
        ])
        self.tabela.setColumnWidth(0, 130)
        self.tabela.setColumnWidth(1, 150)
        self.tabela.setColumnWidth(2, 150)
        self.tabela.setColumnWidth(3, 120)
        self._layout_raiz.addWidget(self.tabela)

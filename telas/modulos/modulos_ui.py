from PyQt6.QtWidgets import QHBoxLayout
from telas.base import TelaBase

class ModulosUI(TelaBase):
    def __init__(self):
        super().__init__("🧩  Módulos", "Gerencie os módulos do sistema")
        self._construir()

    def _construir(self):
        layout_acoes = QHBoxLayout()
        self.btn_novo    = self._criar_btn_acao("➕  Novo Módulo")
        self.btn_refresh = self._criar_btn_acao("🔄", "#2a3f7a", "#FFD700")
        self.btn_refresh.setFixedWidth(40)
        layout_acoes.addStretch()
        layout_acoes.addWidget(self.btn_novo)
        layout_acoes.addWidget(self.btn_refresh)
        self._layout_raiz.addLayout(layout_acoes)

        self.tabela = self._criar_tabela(["ID", "Nome", "Descrição", "Status", "Ações"])
        self.tabela.setColumnWidth(0, 150)
        self.tabela.setColumnWidth(1, 150)
        self.tabela.setColumnWidth(2, 250)
        self.tabela.setColumnWidth(3, 80)
        self._layout_raiz.addWidget(self.tabela)

from PyQt6.QtWidgets import QHBoxLayout
from telas.base import TelaBase

class LogsUI(TelaBase):
    def __init__(self):
        super().__init__("📝  Logs", "Histórico de ações administrativas")
        self._construir()

    def _construir(self):
        layout_acoes = QHBoxLayout()
        self.input_busca = self._criar_input_busca("🔍  Buscar por ação ou usuário...")
        self.btn_refresh = self._criar_btn_acao("🔄", "#2a3f7a", "#FFD700")
        self.btn_refresh.setFixedWidth(40)
        layout_acoes.addWidget(self.input_busca)
        layout_acoes.addWidget(self.btn_refresh)
        self._layout_raiz.addLayout(layout_acoes)

        self.tabela = self._criar_tabela([
            "Data/Hora", "Ação", "Usuário", "Detalhes"
        ])
        self.tabela.setColumnWidth(0, 140)
        self.tabela.setColumnWidth(1, 160)
        self.tabela.setColumnWidth(2, 120)
        self._layout_raiz.addWidget(self.tabela)

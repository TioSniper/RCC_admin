from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QFrame, QLabel
from telas.base import TelaBase

class RelatoriosUI(TelaBase):
    def __init__(self):
        super().__init__("📈  Relatórios", "Visão detalhada do sistema")
        self._construir()

    def _construir(self):
        layout_acoes = QHBoxLayout()
        self.btn_refresh = self._criar_btn_acao("🔄  Atualizar", "#2a3f7a", "#FFD700")
        layout_acoes.addStretch()
        layout_acoes.addWidget(self.btn_refresh)
        self._layout_raiz.addLayout(layout_acoes)

        self.tabela_expirando = self._criar_tabela([
            "Usuário", "Plano", "Expira em", "Dias Restantes"
        ])
        self._layout_raiz.addWidget(QLabel("⚠️  Expirando nos próximos 7 dias:"))
        self._layout_raiz.addWidget(self.tabela_expirando)

        self.tabela_recentes = self._criar_tabela([
            "Usuário", "Plano", "Cadastrado em"
        ])
        self._layout_raiz.addWidget(QLabel("🆕  Cadastros recentes:"))
        self._layout_raiz.addWidget(self.tabela_recentes)

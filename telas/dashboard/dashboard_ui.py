from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
)
from PyQt6.QtCore import Qt
from telas.base import TelaBase


class CardResumo(QFrame):
    def __init__(self, emoji: str, titulo: str, valor: str, cor: str = "#FFD700"):
        super().__init__()
        self.setFixedHeight(110)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(15, 26, 61, 0.7);
                border-radius: 12px;
                border-left: 4px solid {cor};
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(6)

        lbl_emoji = QLabel(f"{emoji}  {titulo}")
        lbl_emoji.setStyleSheet("color: #8899bb; font-size: 12px;")

        self.lbl_valor = QLabel(valor)
        self.lbl_valor.setStyleSheet(
            f"color: {cor}; font-size: 28px; font-weight: bold;"
        )

        layout.addWidget(lbl_emoji)
        layout.addWidget(self.lbl_valor)


class DashboardUI(TelaBase):

    def __init__(self):
        super().__init__(
            "📊  Dashboard",
            "Visão geral do sistema"
        )
        self._construir()

    def _construir(self):
        # Cards de resumo
        layout_cards = QHBoxLayout()
        layout_cards.setSpacing(16)

        self.card_usuarios    = CardResumo("👥", "Total de Usuários",       "—", "#FFD700")
        self.card_ativos      = CardResumo("✅", "Usuários Ativos",          "—", "#00ff88")
        self.card_assinaturas = CardResumo("📋", "Assinaturas Ativas",       "—", "#4da6ff")
        self.card_expirando   = CardResumo("⚠️", "Expirando em 7 dias",      "—", "#ffaa00")
        self.card_expiradas   = CardResumo("❌", "Assinaturas Expiradas",    "—", "#ff5c5c")

        for card in [
            self.card_usuarios, self.card_ativos,
            self.card_assinaturas, self.card_expirando, self.card_expiradas
        ]:
            layout_cards.addWidget(card)

        self._layout_raiz.addLayout(layout_cards)

        # Área de expirando em breve
        frame_expirando = QFrame()
        frame_expirando.setStyleSheet("""
            QFrame {
                background-color: rgba(15, 26, 61, 0.6);
                border-radius: 12px;
                border: 1px solid #2a3f7a;
            }
            QLabel { border: none; background: transparent; }
        """)

        layout_exp = QVBoxLayout(frame_expirando)
        layout_exp.setContentsMargins(20, 16, 20, 16)
        layout_exp.setSpacing(12)

        lbl_titulo_exp = QLabel("⚠️  Assinaturas Expirando em Breve")
        lbl_titulo_exp.setStyleSheet(
            "color: #ffaa00; font-size: 14px; font-weight: bold;"
        )

        self.tabela_expirando = self._criar_tabela([
            "Usuário", "Plano", "Expira em", "Dias Restantes"
        ])
        self.tabela_expirando.setMaximumHeight(220)

        btn_atualizar = self._criar_btn_acao("🔄  Atualizar", "#2a3f7a", "#FFD700")
        btn_atualizar.setObjectName("btn_atualizar_dashboard")

        layout_exp.addWidget(lbl_titulo_exp)
        layout_exp.addWidget(self.tabela_expirando)

        layout_rodape = QHBoxLayout()
        layout_rodape.addStretch()
        layout_rodape.addWidget(btn_atualizar)
        layout_exp.addLayout(layout_rodape)

        self._layout_raiz.addWidget(frame_expirando)
        self._layout_raiz.addStretch()

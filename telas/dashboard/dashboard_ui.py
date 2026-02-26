from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
)
from PyQt6.QtCore import Qt
from telas.base import TelaBase


class CardResumo(QFrame):
    def __init__(self, emoji: str, titulo: str, valor: str, cor: str = "#FFD700"):
        super().__init__()
        self.setFixedHeight(110)
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: rgba(15, 26, 61, 0.7);
                border-radius: 12px;
                border-left: 4px solid {cor};
            }}
            QLabel {{ border: none; background: transparent; }}
        """
        )

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
        super().__init__("📊  Dashboard", "Visão geral do sistema")
        self._construir()

    def _construir(self):
        # ── Cards de resumo ───────────────────────────────────────
        layout_cards = QHBoxLayout()
        layout_cards.setSpacing(16)

        self.card_usuarios = CardResumo("👥", "Total de Usuários", "—", "#FFD700")
        self.card_ativos = CardResumo("🟢", "Usuários Online", "—", "#00ff88")
        self.card_assinaturas = CardResumo("📋", "Assinaturas Ativas", "—", "#4da6ff")
        self.card_expirando = CardResumo("⚠️", "Expirando em 7 dias", "—", "#ffaa00")
        self.card_expiradas = CardResumo("❌", "Assinaturas Expiradas", "—", "#ff5c5c")

        for card in [
            self.card_usuarios,
            self.card_ativos,
            self.card_assinaturas,
            self.card_expirando,
            self.card_expiradas,
        ]:
            layout_cards.addWidget(card)

        self._layout_raiz.addLayout(layout_cards)

        # ── Layout inferior: solicitações + expirando ─────────────
        layout_inferior = QHBoxLayout()
        layout_inferior.setSpacing(16)

        # ── Painel de solicitações pendentes ──────────────────────
        frame_solicitacoes = QFrame()
        frame_solicitacoes.setStyleSheet(
            """
            QFrame {
                background-color: rgba(15, 26, 61, 0.6);
                border-radius: 12px;
                border: 1px solid #7c3aed;
            }
            QLabel { border: none; background: transparent; }
        """
        )

        layout_sol = QVBoxLayout(frame_solicitacoes)
        layout_sol.setContentsMargins(20, 16, 20, 16)
        layout_sol.setSpacing(12)

        layout_header_sol = QHBoxLayout()

        lbl_titulo_sol = QLabel("🔔  Solicitações Pendentes")
        lbl_titulo_sol.setStyleSheet(
            "color: #a78bfa; font-size: 14px; font-weight: bold;"
        )

        self.card_pendentes = QLabel("0")
        self.card_pendentes.setStyleSheet(
            """
            color: white; background-color: #7c3aed;
            border-radius: 10px; padding: 2px 10px;
            font-size: 12px; font-weight: bold;
        """
        )
        self.card_pendentes.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.card_pendentes.setFixedHeight(22)

        layout_header_sol.addWidget(lbl_titulo_sol)
        layout_header_sol.addWidget(self.card_pendentes)
        layout_header_sol.addStretch()

        self.tabela_solicitacoes = self._criar_tabela(
            ["Usuário", "Solicitado em", "Aprovar", "Rejeitar"]
        )
        self.tabela_solicitacoes.setColumnWidth(0, 120)
        self.tabela_solicitacoes.setColumnWidth(1, 130)
        self.tabela_solicitacoes.setColumnWidth(2, 80)
        self.tabela_solicitacoes.setColumnWidth(3, 80)

        layout_sol.addLayout(layout_header_sol)
        layout_sol.addWidget(self.tabela_solicitacoes)

        # ── Painel de expirando em breve ──────────────────────────
        frame_expirando = QFrame()
        frame_expirando.setStyleSheet(
            """
            QFrame {
                background-color: rgba(15, 26, 61, 0.6);
                border-radius: 12px;
                border: 1px solid #2a3f7a;
            }
            QLabel { border: none; background: transparent; }
        """
        )

        layout_exp = QVBoxLayout(frame_expirando)
        layout_exp.setContentsMargins(20, 16, 20, 16)
        layout_exp.setSpacing(12)

        lbl_titulo_exp = QLabel("⚠️  Assinaturas Expirando em Breve")
        lbl_titulo_exp.setStyleSheet(
            "color: #ffaa00; font-size: 14px; font-weight: bold;"
        )

        self.tabela_expirando = self._criar_tabela(
            ["Usuário", "Plano", "Expira em", "Dias Restantes"]
        )

        self.btn_atualizar = self._criar_btn_acao("🔄  Atualizar", "#2a3f7a", "#FFD700")
        self.btn_atualizar.setObjectName("btn_atualizar_dashboard")

        layout_exp.addWidget(lbl_titulo_exp)
        layout_exp.addWidget(self.tabela_expirando)

        layout_rodape = QHBoxLayout()
        layout_rodape.addStretch()
        layout_rodape.addWidget(self.btn_atualizar)
        layout_exp.addLayout(layout_rodape)

        layout_inferior.addWidget(frame_solicitacoes, stretch=1)
        layout_inferior.addWidget(frame_expirando, stretch=1)

        self._layout_raiz.addLayout(layout_inferior)

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
        # ── Botão 🚀 no header (canto direito) ───────────────
        self.btn_disparar_update = QPushButton("🚀")
        self.btn_disparar_update.setFixedSize(38, 38)
        self.btn_disparar_update.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_disparar_update.setToolTip("Disparar Update para Clientes")
        self.btn_disparar_update.setStyleSheet(
            """
            QPushButton {
                background-color: #2a3f7a; color: white;
                border-radius: 8px; font-size: 16px; border: none;
            }
            QPushButton:hover { background-color: #7c3aed; }
        """
        )
        # Injeta no layout de ações do cabeçalho da TelaBase
        self._layout_acoes_cabecalho.addWidget(self.btn_disparar_update)

        # ── Cards de resumo ───────────────────────────────────
        layout_cards = QHBoxLayout()
        layout_cards.setSpacing(16)

        self.card_usuarios = CardResumo("👥", "Total de Usuários", "—", "#FFD700")
        self.card_ativos = CardResumo("✅", "Usuários Ativos", "—", "#00ff88")
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

        # ── Tabelas lado a lado, expandindo até o final ───────
        layout_tabelas = QHBoxLayout()
        layout_tabelas.setSpacing(16)

        # Solicitações pendentes (esquerda)
        frame_sol = QFrame()
        frame_sol.setStyleSheet(
            """
            QFrame {
                background-color: rgba(15, 26, 61, 0.6);
                border-radius: 12px;
                border: 1px solid #2a3f7a;
            }
            QLabel { border: none; background: transparent; }
        """
        )
        layout_sol = QVBoxLayout(frame_sol)
        layout_sol.setContentsMargins(20, 16, 20, 16)
        layout_sol.setSpacing(12)

        lbl_sol = QLabel("📥  Solicitações Pendentes")
        lbl_sol.setStyleSheet("color: #FFD700; font-size: 14px; font-weight: bold;")

        self.tabela_solicitacoes = self._criar_tabela(["Usuário", "E-mail", "Ações"])

        layout_sol.addWidget(lbl_sol)
        layout_sol.addWidget(self.tabela_solicitacoes)

        # Expirando em breve (direita)
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

        lbl_exp = QLabel("⚠️  Assinaturas Expirando em Breve")
        lbl_exp.setStyleSheet("color: #ffaa00; font-size: 14px; font-weight: bold;")

        self.tabela_expirando = self._criar_tabela(
            ["Usuário", "Plano", "Expira em", "Dias Restantes"]
        )

        layout_exp.addWidget(lbl_exp)
        layout_exp.addWidget(self.tabela_expirando)

        layout_tabelas.addWidget(frame_sol)
        layout_tabelas.addWidget(frame_expirando)

        # addLayout com stretch=1 faz as tabelas expandirem até o fim
        self._layout_raiz.addLayout(layout_tabelas, stretch=1)

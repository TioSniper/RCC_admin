import threading
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import (
    resumo_geral,
    listar_expirando,
    listar_solicitacoes,
    aprovar_solicitacao,
    rejeitar_solicitacao,
)


class DashboardWorker(QObject):
    dados_prontos = pyqtSignal(dict, list, list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        resumo = resumo_geral()
        expirando = listar_expirando(7)
        solicitacoes = listar_solicitacoes()
        self.dados_prontos.emit(resumo, expirando, solicitacoes)


class AprovacaoWorker(QObject):
    """Worker para aprovar solicitação sem travar a UI."""

    sucesso = pyqtSignal(str)  # mensagem
    erro = pyqtSignal(str)  # mensagem de erro

    def __init__(self, sol_id: str, username: str, dias: int):
        super().__init__()
        self._sol_id = sol_id
        self._username = username
        self._dias = dias

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        ok, msg = aprovar_solicitacao(self._sol_id, self._username, self._dias)
        if ok:
            self.sucesso.emit(msg)
        else:
            self.erro.emit(msg)


class RejeicaoWorker(QObject):
    concluido = pyqtSignal()
    erro = pyqtSignal(str)

    def __init__(self, sol_id: str):
        super().__init__()
        self._sol_id = sol_id

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        ok, msg = rejeitar_solicitacao(self._sol_id)
        if ok:
            self.concluido.emit()
        else:
            self.erro.emit(msg)


class DashboardController:

    def __init__(self, ui):
        self.ui = ui
        self.worker = DashboardWorker()
        self._workers_aprovacao = []  # mantém referências vivas
        self.worker.dados_prontos.connect(self._atualizar_ui)
        self._conectar_eventos()
        self._carregar_dados()

    def _conectar_eventos(self):
        self.ui.btn_atualizar.clicked.connect(self._carregar_dados)

    def _carregar_dados(self):
        self.worker.buscar()

    def _atualizar_ui(self, resumo: dict, expirando: list, solicitacoes: list):
        self._atualizar_cards(resumo)
        self._preencher_expirando(expirando)
        self._preencher_solicitacoes(solicitacoes)

    # ── Cards ──────────────────────────────────────────────────

    def _atualizar_cards(self, resumo: dict):
        if not resumo:
            return
        self.ui.card_usuarios.lbl_valor.setText(str(resumo.get("total_usuarios", 0)))
        self.ui.card_ativos.lbl_valor.setText(str(resumo.get("usuarios_ativos", 0)))
        self.ui.card_assinaturas.lbl_valor.setText(
            str(resumo.get("assinaturas_ativas", 0))
        )
        self.ui.card_expirando.lbl_valor.setText(str(resumo.get("expirando_7_dias", 0)))
        self.ui.card_expiradas.lbl_valor.setText(str(resumo.get("expiradas", 0)))

    # ── Expirando ──────────────────────────────────────────────

    def _preencher_expirando(self, expirando: list):
        tabela = self.ui.tabela_expirando
        tabela.setRowCount(0)

        for dados in expirando:
            row = tabela.rowCount()
            tabela.insertRow(row)

            username = dados.get("username", "—")
            plano = dados.get("plano_nome", "—")
            expira_raw = dados.get("expira_em", "")

            try:
                dt = datetime.fromisoformat(expira_raw.replace("Z", "+00:00"))
                dias = (dt - datetime.now(timezone.utc)).days
                expira_fmt = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                dias = 0
                expira_fmt = expira_raw

            tabela.setItem(row, 0, self._item(username))
            tabela.setItem(row, 1, self._item(plano))
            tabela.setItem(row, 2, self._item(expira_fmt))

            item_dias = QTableWidgetItem(f"{dias} dias")
            item_dias.setForeground(
                Qt.GlobalColor.red if dias <= 2 else Qt.GlobalColor.yellow
            )
            item_dias.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tabela.setItem(row, 3, item_dias)

    # ── Solicitações ───────────────────────────────────────────

    def _preencher_solicitacoes(self, solicitacoes: list):
        tabela = self.ui.tabela_solicitacoes
        tabela.setRowCount(0)

        total = len(solicitacoes)
        self.ui.card_pendentes.setText(str(total))
        cor = "#dc2626" if total > 0 else "#16a34a"
        self.ui.card_pendentes.setStyleSheet(
            f"""
            color: white; background-color: {cor};
            border-radius: 10px; padding: 2px 10px;
            font-size: 12px; font-weight: bold;
        """
        )

        if not solicitacoes:
            tabela.setRowCount(1)
            item = QTableWidgetItem("✅  Nenhuma solicitação pendente")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.darkGray)
            tabela.setItem(0, 0, item)
            tabela.setSpan(0, 0, 1, 4)
            return

        for s in solicitacoes:
            row = tabela.rowCount()
            tabela.insertRow(row)

            sol_id = s.get("id", "")
            username = s.get("username", "—")
            criado = "—"

            if s.get("criado_em"):
                try:
                    dt = datetime.fromisoformat(s["criado_em"].replace("Z", "+00:00"))
                    criado = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass

            tabela.setItem(row, 0, self._item(username))
            tabela.setItem(row, 1, self._item(criado))

            def _make_btn(texto, cor, cor_hover):
                b = QPushButton(texto)
                b.setFixedHeight(28)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {cor}; color: white;
                        border-radius: 6px; font-size: 11px;
                        font-weight: bold; border: none; padding: 0 8px;
                    }}
                    QPushButton:hover {{ background-color: {cor_hover}; }}
                """
                )
                return b

            btn_aprovar = _make_btn("✅ Aprovar", "#16a34a", "#15803d")
            btn_rejeitar = _make_btn("❌ Rejeitar", "#dc2626", "#b91c1c")

            btn_aprovar.clicked.connect(
                lambda _, sid=sol_id, u=username: self._dialog_aprovar(sid, u)
            )
            btn_rejeitar.clicked.connect(
                lambda _, sid=sol_id, u=username: self._dialog_rejeitar(sid, u)
            )

            def _centralizar(btn):
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(4, 2, 4, 2)
                l.addStretch()
                l.addWidget(btn)
                l.addStretch()
                return w

            tabela.setCellWidget(row, 2, _centralizar(btn_aprovar))
            tabela.setCellWidget(row, 3, _centralizar(btn_rejeitar))
            tabela.setRowHeight(row, 40)

    # ── Diálogo aprovar ────────────────────────────────────────

    def _dialog_aprovar(self, sol_id: str, username: str):
        from telas.dialogs import DialogBase

        dialog = DialogBase("✅  Aprovar Cadastro", parent=self.ui)

        lbl_info = QLabel(f"Aprovando:  <b style='color:#FFD700'>{username}</b>")
        lbl_info.setStyleSheet("color: #cccccc; font-size: 12px;")

        lbl_dias = QLabel("Dias de acesso inicial:")
        lbl_dias.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")

        inp_dias = QLineEdit("30")
        inp_dias.setFixedHeight(36)
        inp_dias.setStyleSheet(dialog._estilo_input())

        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")

        dialog._layout_corpo.insertWidget(0, lbl_info)
        dialog._layout_corpo.insertWidget(1, lbl_dias)
        dialog._layout_corpo.insertWidget(2, inp_dias)
        dialog._layout_corpo.insertWidget(3, lbl_aviso)

        # Worker com sinais para não chamar dialog.accept() de thread secundária
        self._worker_aprov = None

        def _salvar():
            try:
                dias = int(inp_dias.text().strip())
                if dias <= 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Informe um número válido de dias.")
                return

            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Aprovando...")
            lbl_aviso.setText("")

            worker = AprovacaoWorker(sol_id, username, dias)
            self._workers_aprovacao.append(worker)  # mantém referência

            def _on_sucesso(msg: str):
                dialog.accept()  # thread principal ✅
                self._carregar_dados()
                self._workers_aprovacao.clear()

            def _on_erro(msg: str):
                lbl_aviso.setText(f"⚠️  {msg}")
                dialog._btn_confirmar.setEnabled(True)
                dialog._btn_confirmar.setText("✓  Confirmar")

            worker.sucesso.connect(_on_sucesso)
            worker.erro.connect(_on_erro)
            worker.executar()

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    # ── Diálogo rejeitar ───────────────────────────────────────

    def _dialog_rejeitar(self, sol_id: str, username: str):
        from telas.dialogs import DialogConfirmacao

        dialog = DialogConfirmacao(
            f"Deseja rejeitar a solicitação de '{username}'?\n"
            "O usuário será notificado ao abrir o app.",
            parent=self.ui,
        )
        if dialog.exec():
            worker = RejeicaoWorker(sol_id)
            self._workers_aprovacao.append(worker)

            worker.concluido.connect(self._carregar_dados)
            worker.concluido.connect(lambda: self._workers_aprovacao.clear())
            worker.executar()

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

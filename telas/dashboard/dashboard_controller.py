import threading
from PyQt6.QtWidgets import (
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import aprovar_solicitacao, rejeitar_solicitacao


class AprovacaoWorker(QObject):
    sucesso = pyqtSignal(str)
    erro = pyqtSignal(str)

    def __init__(self, sol_id, username, dias):
        super().__init__()
        self._sol_id = sol_id
        self._username = username
        self._dias = dias

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        ok, msg = aprovar_solicitacao(self._sol_id, self._username, self._dias)
        (self.sucesso if ok else self.erro).emit(msg)


class RejeicaoWorker(QObject):
    concluido = pyqtSignal()
    erro = pyqtSignal(str)

    def __init__(self, sol_id):
        super().__init__()
        self._sol_id = sol_id

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        ok, _ = rejeitar_solicitacao(self._sol_id)
        self.concluido.emit() if ok else self.erro.emit("Erro ao rejeitar")


class UpdateWorker(QObject):
    sucesso = pyqtSignal()
    erro = pyqtSignal(str)

    def __init__(self, versao, url):
        super().__init__()
        self._versao = versao
        self._url = url

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            from utils.supabase_admin import _cliente

            _cliente().rpc(
                "disparar_update",
                {
                    "p_versao": self._versao,
                    "p_url": self._url,
                },
            ).execute()
            self.sucesso.emit()
        except Exception as e:
            self.erro.emit(str(e))


class DashboardController:

    def __init__(self, ui, svc):
        self.ui = ui
        self._svc = svc
        self._workers = []

        svc.assinaturas_mudou.connect(self._carregar)
        svc.solicitacoes_mudou.connect(self._carregar)
        svc.sessoes_mudou.connect(self._carregar_sessoes)

        btn_att = self.ui.findChild(QPushButton, "btn_atualizar_dashboard")
        if btn_att:
            btn_att.clicked.connect(self._carregar)

        self.ui.btn_disparar_update.clicked.connect(self._dialog_disparar_update)

        self._carregar()

    def _carregar(self):
        from utils.supabase_admin import (
            resumo_geral,
            listar_solicitacoes,
            listar_expirando,
        )

        self._svc.fetch(
            lambda: {
                "resumo": resumo_geral(),
                "solicitacoes": listar_solicitacoes(),
                "expirando": listar_expirando(7),
            },
            self._renderizar,
        )

    def _carregar_sessoes(self):
        from utils.supabase_admin import listar_sessoes_ativas

        self._svc.fetch(listar_sessoes_ativas, self._atualizar_card_online)

    def _renderizar(self, dados):
        if not dados:
            return
        self._atualizar_cards(dados.get("resumo", {}))
        self._atualizar_solicitacoes(dados.get("solicitacoes", []))
        self._atualizar_expirando(dados.get("expirando", []))

    def _atualizar_cards(self, r):
        if not r:
            return
        self.ui.card_usuarios.lbl_valor.setText(str(r.get("total_usuarios", 0)))
        self.ui.card_assinaturas.lbl_valor.setText(str(r.get("assinaturas_ativas", 0)))
        self.ui.card_expirando.lbl_valor.setText(str(r.get("expirando_7_dias", 0)))
        self.ui.card_expiradas.lbl_valor.setText(str(r.get("expiradas", 0)))

    def _atualizar_card_online(self, sessoes):
        if sessoes is None:
            return
        self.ui.card_ativos.lbl_valor.setText(str(len(sessoes)))

    def _atualizar_solicitacoes(self, solicitacoes):
        tabela = self.ui.tabela_solicitacoes
        tabela.setRowCount(0)
        for s in solicitacoes or []:
            row = tabela.rowCount()
            tabela.insertRow(row)
            sol_id = s.get("id", "")
            username = s.get("username", "—")
            email = s.get("email", "—")
            tabela.setItem(row, 0, self._item(username))
            tabela.setItem(row, 1, self._item(email))
            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(4, 2, 4, 2)
            l.setSpacing(4)
            btn_a = QPushButton("✅ Aprovar")
            btn_r = QPushButton("❌ Rejeitar")
            for btn in [btn_a, btn_r]:
                btn.setFixedHeight(26)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_a.setStyleSheet(
                "QPushButton { background-color: #16a34a; color: white; border-radius: 5px; font-size: 11px; border: none; padding: 0 8px; }"
            )
            btn_r.setStyleSheet(
                "QPushButton { background-color: #dc2626; color: white; border-radius: 5px; font-size: 11px; border: none; padding: 0 8px; }"
            )
            btn_a.clicked.connect(
                lambda _, sid=sol_id, u=username: self._dialog_aprovar(sid, u)
            )
            btn_r.clicked.connect(
                lambda _, sid=sol_id, u=username: self._dialog_rejeitar(sid, u)
            )
            l.addWidget(btn_a)
            l.addWidget(btn_r)
            l.addStretch()
            tabela.setCellWidget(row, 2, w)
            tabela.setRowHeight(row, 40)

    def _atualizar_expirando(self, expirando):
        from datetime import datetime, timezone

        tabela = self.ui.tabela_expirando
        tabela.setRowCount(0)
        for dados in expirando or []:
            row = tabela.rowCount()
            tabela.insertRow(row)
            expira_raw = dados.get("expira_em", "")
            try:
                dt = datetime.fromisoformat(expira_raw.replace("Z", "+00:00"))
                dias = (dt - datetime.now(timezone.utc)).days
                expira = dt.strftime("%d/%m/%Y")
                dias_item = QTableWidgetItem(f"{max(0,dias)} dias")
                dias_item.setForeground(
                    Qt.GlobalColor.red
                    if dias <= 2
                    else Qt.GlobalColor.yellow if dias <= 5 else Qt.GlobalColor.white
                )
                dias_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception:
                expira = expira_raw
                dias_item = self._item("—")
            tabela.setItem(row, 0, self._item(dados.get("username", "—")))
            tabela.setItem(row, 1, self._item(dados.get("plano_nome", "—")))
            tabela.setItem(row, 2, self._item(expira))
            tabela.setItem(row, 3, dias_item)
            tabela.setRowHeight(row, 36)

    # ── Dialog Disparar Update ─────────────────────────────────

    def _dialog_disparar_update(self):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🚀  Disparar Update para Clientes", parent=self.ui)

        lbl_info = QLabel(
            "Informe a nova versão e a URL de download.\n"
            "Todos os clientes conectados serão notificados em tempo real."
        )
        lbl_info.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        lbl_info.setWordWrap(True)

        lbl_v = QLabel("Nova versão (ex: 1.2.0):")
        lbl_v.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_versao = QLineEdit()
        inp_versao.setPlaceholderText("1.2.0")
        inp_versao.setFixedHeight(36)
        inp_versao.setStyleSheet(dialog._estilo_input())

        lbl_u = QLabel("URL de download:")
        lbl_u.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_url = QLineEdit()
        inp_url.setPlaceholderText("https://github.com/TioSniper/RCC/releases/latest")
        inp_url.setFixedHeight(36)
        inp_url.setStyleSheet(dialog._estilo_input())

        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")

        for i, w in enumerate([lbl_info, lbl_v, inp_versao, lbl_u, inp_url, lbl_aviso]):
            dialog._layout_corpo.insertWidget(i, w)

        def _disparar():
            versao = inp_versao.text().strip()
            url = inp_url.text().strip()
            if not versao:
                lbl_aviso.setText("⚠️  Informe a versão.")
                return
            if not url:
                lbl_aviso.setText("⚠️  Informe a URL de download.")
                return
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Disparando...")
            w = UpdateWorker(versao, url)
            self._workers.append(w)
            w.sucesso.connect(lambda: (dialog.accept(), self._workers.clear()))
            w.erro.connect(
                lambda msg: (
                    lbl_aviso.setText(f"⚠️  {msg}"),
                    dialog._btn_confirmar.setEnabled(True),
                    dialog._btn_confirmar.setText("✓  Confirmar"),
                )
            )
            w.executar()

        dialog._btn_confirmar.clicked.connect(_disparar)
        dialog.exec()

    # ── Dialogs de solicitações ───────────────────────────────

    def _dialog_aprovar(self, sol_id: str, username: str):
        from telas.dialogs import DialogBase

        dialog = DialogBase("✅  Aprovar Solicitação", parent=self.ui)
        lbl_info = QLabel(f"Usuário: <b style='color:#FFD700'>{username}</b>")
        lbl_info.setStyleSheet("color: #cccccc; font-size: 12px;")
        lbl_dias = QLabel("Dias de acesso inicial (0 = sem expiração):")
        lbl_dias.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_dias = QLineEdit("0")
        inp_dias.setFixedHeight(36)
        inp_dias.setStyleSheet(dialog._estilo_input())
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        for i, w in enumerate([lbl_info, lbl_dias, inp_dias, lbl_aviso]):
            dialog._layout_corpo.insertWidget(i, w)

        def _salvar():
            try:
                dias = int(inp_dias.text().strip())
                if dias < 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Dias inválido.")
                return
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Aprovando...")
            w = AprovacaoWorker(sol_id, username, dias)
            self._workers.append(w)
            w.sucesso.connect(lambda _: (dialog.accept(), self._workers.clear()))
            w.erro.connect(
                lambda msg: (
                    lbl_aviso.setText(f"⚠️  {msg}"),
                    dialog._btn_confirmar.setEnabled(True),
                    dialog._btn_confirmar.setText("✓  Confirmar"),
                )
            )
            w.executar()

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _dialog_rejeitar(self, sol_id: str, username: str):
        from telas.dialogs import DialogConfirmacao

        if DialogConfirmacao(
            f"Rejeitar solicitação de '{username}'?", parent=self.ui
        ).exec():
            w = RejeicaoWorker(sol_id)
            self._workers.append(w)
            w.concluido.connect(lambda: self._workers.clear())
            w.executar()

    def _item(self, texto):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

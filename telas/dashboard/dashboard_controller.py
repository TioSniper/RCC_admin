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
        ok, msg = rejeitar_solicitacao(self._sol_id)
        self.concluido.emit() if ok else self.erro.emit(msg)


class DashboardController:

    def __init__(self, ui, store):
        self.ui = ui
        self._store = store
        self._workers = []

        # Conecta sinais do store — UI só atualiza quando cache muda
        store.resumo_atualizado.connect(self._atualizar_cards)
        store.solicitacoes_atualizadas.connect(self._atualizar_solicitacoes)
        store.sessoes_atualizadas.connect(self._atualizar_card_online)
        store.assinaturas_atualizadas.connect(self._atualizar_expirando)
        store.carregamento_completo.connect(self._render_completo)

        self.ui.btn_atualizar.clicked.connect(lambda: store.carregar_tudo())

        # Se store já tem dados (aba visitada novamente), renderiza imediato
        if store.resumo:
            self._render_completo()

    def _render_completo(self):
        self._atualizar_cards()
        self._atualizar_solicitacoes()
        self._atualizar_expirando()
        self._atualizar_card_online()

    def _atualizar_cards(self):
        r = self._store.resumo
        if not r:
            return
        self.ui.card_usuarios.lbl_valor.setText(str(r.get("total_usuarios", 0)))
        self.ui.card_assinaturas.lbl_valor.setText(str(r.get("assinaturas_ativas", 0)))
        self.ui.card_expirando.lbl_valor.setText(str(r.get("expirando_7_dias", 0)))
        self.ui.card_expiradas.lbl_valor.setText(str(r.get("expiradas", 0)))

    def _atualizar_card_online(self):
        self.ui.card_ativos.lbl_valor.setText(str(len(self._store.sessoes)))

    def _atualizar_expirando(self):
        tabela = self.ui.tabela_expirando
        tabela.setRowCount(0)
        for dados in self._store.expirando:
            row = tabela.rowCount()
            tabela.insertRow(row)
            expira_raw = dados.get("expira_em", "")
            try:
                dt = datetime.fromisoformat(expira_raw.replace("Z", "+00:00"))
                dias = (dt - datetime.now(timezone.utc)).days
                expira_fmt = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                dias = 0
                expira_fmt = expira_raw
            tabela.setItem(row, 0, self._item(dados.get("username", "—")))
            tabela.setItem(row, 1, self._item(dados.get("plano_nome", "—")))
            tabela.setItem(row, 2, self._item(expira_fmt))
            item_dias = QTableWidgetItem(f"{dias} dias")
            item_dias.setForeground(
                Qt.GlobalColor.red if dias <= 2 else Qt.GlobalColor.yellow
            )
            item_dias.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tabela.setItem(row, 3, item_dias)

    def _atualizar_solicitacoes(self):
        tabela = self.ui.tabela_solicitacoes
        tabela.setRowCount(0)
        solicitacoes = self._store.solicitacoes
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

            def _btn(txt, cor, hover):
                b = QPushButton(txt)
                b.setFixedHeight(28)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(
                    f"""
                    QPushButton {{ background-color: {cor}; color: white;
                        border-radius: 6px; font-size: 11px;
                        font-weight: bold; border: none; padding: 0 8px; }}
                    QPushButton:hover {{ background-color: {hover}; }}
                """
                )
                return b

            btn_a = _btn("✅ Aprovar", "#16a34a", "#15803d")
            btn_r = _btn("❌ Rejeitar", "#dc2626", "#b91c1c")
            btn_a.clicked.connect(
                lambda _, sid=sol_id, u=username: self._dialog_aprovar(sid, u)
            )
            btn_r.clicked.connect(
                lambda _, sid=sol_id, u=username: self._dialog_rejeitar(sid, u)
            )

            def _center(b):
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(4, 2, 4, 2)
                l.addStretch()
                l.addWidget(b)
                l.addStretch()
                return w

            tabela.setCellWidget(row, 2, _center(btn_a))
            tabela.setCellWidget(row, 3, _center(btn_r))
            tabela.setRowHeight(row, 40)

    def _dialog_aprovar(self, sol_id, username):
        from telas.dialogs import DialogBase

        dialog = DialogBase("✅  Aprovar Cadastro", parent=self.ui)
        lbl_info = QLabel(f"Aprovando: <b style='color:#FFD700'>{username}</b>")
        lbl_info.setStyleSheet("color: #cccccc; font-size: 12px;")
        lbl_dias = QLabel("Dias de acesso inicial (0 = sem expiração):")
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

        def _salvar():
            try:
                dias = int(inp_dias.text().strip())
                if dias < 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Número inválido.")
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

    def _dialog_rejeitar(self, sol_id, username):
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

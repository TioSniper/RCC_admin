import threading
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import (
    listar_usuarios,
    listar_sessoes_ativas,
    criar_usuario,
    ativar_usuario,
    desativar_usuario,
    resetar_senha,
    deletar_usuario,
    listar_planos,
    criar_assinatura,
)


class UsuariosWorker(QObject):
    dados_prontos = pyqtSignal(list, set)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.dados_prontos.emit(listar_usuarios(), listar_sessoes_ativas())


class UsuariosController:

    def __init__(self, ui, realtime=None):
        self.ui = ui
        self._todos = []
        self._online = set()
        self.worker = UsuariosWorker()
        self.worker.dados_prontos.connect(self._preencher_tabela)

        if realtime:
            # Recebe payload — atualiza só a linha afetada quando possível
            realtime.usuarios_mudou.connect(self._on_usuario_mudou)
            realtime.assinaturas_mudou.connect(self._on_assinatura_mudou)
            realtime.sessoes_mudou.connect(self._on_sessao_mudou)

        self._conectar_eventos()
        self._carregar()

    def _conectar_eventos(self):
        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.btn_novo.clicked.connect(self._dialog_novo_usuario)
        self.ui.input_busca.textChanged.connect(self._filtrar)

    # ── Handlers Realtime — cirúrgicos ────────────────────────

    def _on_usuario_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        uid = record.get("id")

        if tipo == "DELETE":
            # Remove da lista local sem re-fetch
            self._todos = [
                u
                for u in self._todos
                if u.get("id") != payload.get("old_record", {}).get("id")
            ]
            self._preencher_tabela(self._todos, self._online)
            return

        if tipo in ("INSERT", "UPDATE") and uid:
            # Atualiza/insere só este usuário
            existente = next((u for u in self._todos if u.get("id") == uid), None)
            if existente:
                existente.update(record)
            else:
                record.setdefault("assinatura", None)
                self._todos.insert(0, record)
            self._preencher_tabela(self._todos, self._online)
            return

        # Fallback: re-fetch completo
        self._carregar()

    def _on_assinatura_mudou(self, payload: dict):
        record = payload.get("record", {})
        uid = record.get("user_id")
        if not uid:
            self._carregar()
            return

        # Atualiza só o campo assinatura do usuário afetado
        for u in self._todos:
            if u.get("id") == uid:
                u["assinatura"] = record if record.get("ativo") else None
                break
        self._preencher_tabela(self._todos, self._online)

    def _on_sessao_mudou(self, payload: dict):
        tipo = payload.get("type")
        record = payload.get("record", {})
        uid = record.get("user_id") or payload.get("old_record", {}).get("user_id")
        if not uid:
            return

        if tipo == "DELETE" or not record:
            self._online.discard(uid)
        else:
            self._online.add(uid)

        # Atualiza só a célula de status deste usuário
        self._atualizar_status_linha(uid)

    def _atualizar_status_linha(self, uid: str):
        """Atualiza só a coluna status do usuário sem redesenhar a tabela toda."""
        tabela = self.ui.tabela
        for row in range(tabela.rowCount()):
            item = tabela.item(row, 0)
            if not item:
                continue
            # Encontra o usuário pelo username na linha
            usuario = next(
                (u for u in self._todos if u.get("username") == item.text()), None
            )
            if not usuario or usuario.get("id") != uid:
                continue

            ativo = usuario.get("ativo", False)
            esta_online = uid in self._online

            if esta_online:
                txt, cor = "🟢 Online", Qt.GlobalColor.green
            elif ativo:
                txt, cor = "✅ Ativo", Qt.GlobalColor.darkGreen
            else:
                txt, cor = "❌ Inativo", Qt.GlobalColor.red

            status_item = QTableWidgetItem(txt)
            status_item.setForeground(cor)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            tabela.setItem(row, 2, status_item)
            break

    # ── Carregamento completo (inicial ou fallback) ────────────

    def _carregar(self):
        self.worker.buscar()

    def _filtrar(self, texto: str):
        if not texto:
            self._preencher_tabela(self._todos, self._online)
            return
        filtrados = [
            u
            for u in self._todos
            if texto.lower() in (u.get("username") or "").lower()
            or texto.lower() in (u.get("email") or "").lower()
        ]
        self._preencher_tabela(filtrados, self._online)

    def _preencher_tabela(self, usuarios: list, online: set):
        self._todos = usuarios
        self._online = online
        tabela = self.ui.tabela
        tabela.setRowCount(0)

        for u in usuarios:
            row = tabela.rowCount()
            tabela.insertRow(row)
            uid = u["id"]
            username = u.get("username") or "—"
            email = u.get("email", "—")
            ativo = u.get("ativo", False)
            ass = u.get("assinatura") or {}
            plano = ass.get("plano_nome") or "Sem plano"
            expira = "—"
            cadastro = "—"

            if ass.get("expira_em"):
                try:
                    dt = datetime.fromisoformat(ass["expira_em"].replace("Z", "+00:00"))
                    expira = dt.strftime("%d/%m/%Y")
                except Exception:
                    pass
            elif ass.get("plano_nome"):
                expira = "Sem expiração"

            if u.get("criado_em"):
                try:
                    dt = datetime.fromisoformat(u["criado_em"].replace("Z", "+00:00"))
                    cadastro = dt.strftime("%d/%m/%Y")
                except Exception:
                    pass

            esta_online = uid in online
            if esta_online:
                status_txt, status_cor = "🟢 Online", Qt.GlobalColor.green
            elif ativo:
                status_txt, status_cor = "✅ Ativo", Qt.GlobalColor.darkGreen
            else:
                status_txt, status_cor = "❌ Inativo", Qt.GlobalColor.red

            status_item = QTableWidgetItem(status_txt)
            status_item.setForeground(status_cor)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            tabela.setItem(row, 0, self._item(username))
            tabela.setItem(row, 1, self._item(email))
            tabela.setItem(row, 2, status_item)
            tabela.setItem(row, 3, self._item(plano))
            tabela.setItem(row, 4, self._item(expira))
            tabela.setItem(row, 5, self._item(cadastro))

            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(4, 2, 4, 2)
            l.setSpacing(4)

            def _btn(txt, cor):
                b = QPushButton(txt)
                b.setFixedHeight(26)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {cor}; color: white;
                        border-radius: 5px; font-size: 11px;
                        border: none; padding: 0 8px;
                    }}
                """
                )
                return b

            btn_toggle = _btn(
                "Desativar" if ativo else "Ativar", "#dc2626" if ativo else "#16a34a"
            )
            btn_senha = _btn("Senha", "#2563eb")
            btn_del = _btn("🗑", "#7f1d1d")

            btn_toggle.clicked.connect(
                lambda _, i=uid, a=ativo: self._toggle_usuario(i, a)
            )
            btn_senha.clicked.connect(lambda _, i=uid: self._dialog_resetar_senha(i))
            btn_del.clicked.connect(
                lambda _, i=uid, n=username: self._confirmar_deletar(i, n)
            )

            l.addWidget(btn_toggle)
            l.addWidget(btn_senha)
            l.addWidget(btn_del)
            l.addStretch()
            tabela.setCellWidget(row, 6, w)
            tabela.setRowHeight(row, 40)

    def _toggle_usuario(self, user_id: str, ativo: bool):
        def _run():
            if ativo:
                desativar_usuario(user_id)
            else:
                ativar_usuario(user_id)

        threading.Thread(target=_run, daemon=True).start()

    def _dialog_resetar_senha(self, user_id: str):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🔑  Resetar Senha", parent=self.ui)
        lbl = QLabel("Nova senha:")
        lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp = QLineEdit()
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        inp.setPlaceholderText("••••••••")
        inp.setFixedHeight(36)
        inp.setStyleSheet(dialog._estilo_input())
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._layout_corpo.insertWidget(1, inp)
        dialog._layout_corpo.insertWidget(2, lbl_aviso)

        def _salvar():
            nova = inp.text().strip()
            if len(nova) < 6:
                lbl_aviso.setText("⚠️  Mínimo 6 caracteres.")
                return
            ok, _ = resetar_senha(user_id, nova)
            if ok:
                dialog.accept()
            else:
                lbl_aviso.setText("⚠️  Erro ao resetar senha.")

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _confirmar_deletar(self, user_id: str, username: str):
        from telas.dialogs import DialogConfirmacao

        if DialogConfirmacao(
            f"Deseja deletar '{username}'?\nEsta ação não pode ser desfeita.",
            parent=self.ui,
        ).exec():
            threading.Thread(
                target=lambda: deletar_usuario(user_id), daemon=True
            ).start()

    def _dialog_novo_usuario(self):
        from telas.dialogs import DialogBase

        dialog = DialogBase("➕  Novo Usuário", parent=self.ui)

        def _campo(lbl_txt, ph, idx, senha=False):
            lbl = QLabel(lbl_txt)
            lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
            inp = QLineEdit()
            inp.setPlaceholderText(ph)
            inp.setFixedHeight(36)
            inp.setStyleSheet(dialog._estilo_input())
            if senha:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
            dialog._layout_corpo.insertWidget(idx * 2, lbl)
            dialog._layout_corpo.insertWidget(idx * 2 + 1, inp)
            return inp

        inp_user = _campo("Username:", "ex: joaosilva", 0)
        inp_senha = _campo("Senha:", "••••••••", 1, senha=True)

        lbl_plano = QLabel("Plano inicial:")
        lbl_plano.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(
            """
            QComboBox { background-color: rgba(255,255,255,0.05);
                border: 1px solid #2a3f7a; border-radius: 8px;
                color: white; padding: 0 12px; font-size: 12px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #1a2854;
                color: white; border: 1px solid #FFD700; }
        """
        )
        combo.addItem("Sem plano", None)
        for p in listar_planos():
            combo.addItem(p["nome"], p["id"])

        lbl_dias = QLabel("Dias de acesso (0 = sem expiração):")
        lbl_dias.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_dias = QLineEdit("0")
        inp_dias.setFixedHeight(36)
        inp_dias.setStyleSheet(dialog._estilo_input())

        dialog._layout_corpo.insertWidget(4, lbl_plano)
        dialog._layout_corpo.insertWidget(5, combo)
        dialog._layout_corpo.insertWidget(6, lbl_dias)
        dialog._layout_corpo.insertWidget(7, inp_dias)

        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(8, lbl_aviso)

        def _salvar():
            username = inp_user.text().strip()
            senha = inp_senha.text().strip()
            plano_id = combo.currentData()
            try:
                dias = int(inp_dias.text().strip() or "0")
                if dias < 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Dias inválido.")
                return
            if not username or not senha:
                lbl_aviso.setText("⚠️  Preencha username e senha.")
                return
            if len(senha) < 6:
                lbl_aviso.setText("⚠️  Senha mínima de 6 caracteres.")
                return

            ok, resultado = criar_usuario(username, senha)
            if not ok:
                lbl_aviso.setText(f"⚠️  {resultado}")
                return
            if plano_id:
                criar_assinatura(resultado, plano_id, dias)
            dialog.accept()

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

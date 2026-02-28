import os, threading
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
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer

BASICO_ID = os.getenv("PLANO_BASICO_ID", "11111111-1111-1111-1111-111111111111")


class AssWorker(QObject):
    sucesso = pyqtSignal()
    erro = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            ok, msg = self._fn(*self._args)
            self.sucesso.emit() if ok else self.erro.emit(msg)
        except Exception as e:
            self.erro.emit(str(e))


class _RpcWorker(QObject):
    sucesso = pyqtSignal()
    erro = pyqtSignal(str)

    def __init__(self, nome, params):
        super().__init__()
        self._nome = nome
        self._params = params

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            from utils.supabase_admin import _cliente

            _cliente().rpc(self._nome, self._params).execute()
            self.sucesso.emit()
        except Exception as e:
            self.erro.emit(str(e))


def _chamar_rpc(nome, params, callback_ok, callback_err):
    w = _RpcWorker(nome, params)
    w.sucesso.connect(callback_ok)
    w.erro.connect(callback_err)
    w.executar()
    return w


class AssinaturasController:

    def __init__(self, ui, svc):
        self.ui = ui
        self._svc = svc
        self._workers = []
        self._planos = []

        # Debounce — corrige bug do QTimer com args do PyQt6
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._carregar)

        def _iniciar(*args, **kwargs):
            from PyQt6.QtCore import QMetaObject, Qt

            QMetaObject.invokeMethod(
                self._timer, "start", Qt.ConnectionType.QueuedConnection
            )

        svc.assinaturas_mudou.connect(_iniciar)
        svc.usuarios_mudou.connect(_iniciar)

        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.input_busca.textChanged.connect(self._filtrar)
        self._todos = []
        self._carregar()

    def _carregar(self):
        from utils.supabase_admin import (
            listar_assinaturas,
            listar_usuarios,
            listar_planos,
        )

        self._svc.fetch(
            lambda: {
                "assinaturas": listar_assinaturas(),
                "usuarios": listar_usuarios(),
                "planos": listar_planos(),
            },
            self._renderizar,
        )

    def _filtrar(self, texto):
        if not texto:
            self._preencher(self._todos[0], self._todos[1])
            return
        ass_f = [
            a
            for a in self._todos[0]
            if texto.lower() in (a.get("username") or "").lower()
        ]
        sem_f = [
            u
            for u in self._todos[1]
            if texto.lower() in (u.get("username") or "").lower()
        ]
        self._renderizar_dados(ass_f, sem_f)

    def _renderizar(self, dados):
        if not dados:
            return
        assinaturas = dados.get("assinaturas", [])
        usuarios = dados.get("usuarios", [])
        self._planos = [p for p in dados.get("planos", []) if p.get("id") != BASICO_ID]
        ids_com_ass = {a.get("user_id") for a in assinaturas}
        sem_assinatura = [u for u in usuarios if u["id"] not in ids_com_ass]
        self._todos = (assinaturas, sem_assinatura)
        self._preencher(assinaturas, sem_assinatura)

    def _preencher(self, assinaturas, sem_assinatura):
        tabela = self.ui.tabela
        tabela.setRowCount(0)
        for a in assinaturas:
            row = tabela.rowCount()
            tabela.insertRow(row)
            self._row_com_ass(tabela, row, a)
        for u in sem_assinatura:
            row = tabela.rowCount()
            tabela.insertRow(row)
            self._row_sem_ass(tabela, row, u)

    def _row_com_ass(self, tabela, row, a):
        username = a.get("username", "—")
        plano = a.get("plano_nome", "—")
        ativo = a.get("ativo", False)
        user_id = a.get("user_id", "")
        criado = expira = "—"
        dias = 0
        if a.get("criado_em"):
            try:
                dt = datetime.fromisoformat(a["criado_em"].replace("Z", "+00:00"))
                criado = dt.strftime("%d/%m/%Y")
            except Exception:
                pass
        if a.get("expira_em"):
            try:
                dt = datetime.fromisoformat(a["expira_em"].replace("Z", "+00:00"))
                expira = dt.strftime("%d/%m/%Y %H:%M")
                dias = (dt - datetime.now(timezone.utc)).days
            except Exception:
                pass
        else:
            expira = "Sem expiração"
            dias = 99999

        status_item = QTableWidgetItem("✅ Ativo" if ativo else "❌ Inativo")
        status_item.setForeground(Qt.GlobalColor.green if ativo else Qt.GlobalColor.red)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if dias == 99999:
            dias_item = QTableWidgetItem("∞")
            dias_item.setForeground(Qt.GlobalColor.cyan)
        else:
            dias_item = QTableWidgetItem(f"{max(0,dias)} dias")
            dias_item.setForeground(
                Qt.GlobalColor.red
                if dias <= 2
                else Qt.GlobalColor.yellow if dias <= 7 else Qt.GlobalColor.white
            )
        dias_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        tabela.setItem(row, 0, self._item(username))
        tabela.setItem(row, 1, self._item(plano))
        tabela.setItem(row, 2, status_item)
        tabela.setItem(row, 3, self._item(criado))
        tabela.setItem(row, 4, self._item(expira))
        tabela.setItem(row, 5, dias_item)

        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(4, 2, 4, 2)
        l.setSpacing(4)

        def _btn(txt, cor):
            b = QPushButton(txt)
            b.setFixedHeight(26)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                f"""QPushButton {{
                background-color: {cor}; color: white;
                border-radius: 5px; font-size: 11px;
                border: none; padding: 0 8px;
            }}"""
            )
            return b

        btn_renovar = _btn("Renovar", "#16a34a")
        btn_plano = _btn("Plano", "#2563eb")
        btn_basico = _btn("→ Básico", "#dc2626")
        btn_renovar.clicked.connect(lambda _, uid=user_id: self._dialog_renovar(uid))
        btn_plano.clicked.connect(
            lambda _, uid=user_id, u=username: self._dialog_mudar_plano(uid, u)
        )
        btn_basico.clicked.connect(
            lambda _, uid=user_id, u=username: self._revogar_para_basico(uid, u)
        )
        l.addWidget(btn_renovar)
        l.addWidget(btn_plano)
        l.addWidget(btn_basico)
        l.addStretch()
        tabela.setCellWidget(row, 6, w)
        tabela.setRowHeight(row, 40)

    def _row_sem_ass(self, tabela, row, u):
        username = u.get("username") or "—"
        user_id = u["id"]
        tabela.setItem(row, 0, self._item(username))
        tabela.setItem(row, 1, self._item("Sem plano"))
        item_s = QTableWidgetItem("— Sem assinatura")
        item_s.setForeground(Qt.GlobalColor.darkGray)
        item_s.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        tabela.setItem(row, 2, item_s)
        for col in [3, 4, 5]:
            tabela.setItem(row, col, self._item("—"))
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(4, 2, 4, 2)
        btn = QPushButton("Atribuir Plano")
        btn.setFixedHeight(26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            """QPushButton { background-color: #7c3aed; color: white;
            border-radius: 5px; font-size: 11px; border: none; padding: 0 8px; }"""
        )
        btn.clicked.connect(
            lambda _, uid=user_id, un=username: self._dialog_atribuir(uid, un)
        )
        l.addWidget(btn)
        l.addStretch()
        tabela.setCellWidget(row, 6, w)
        tabela.setRowHeight(row, 40)

    def _estilo_combo(self):
        return (
            "QComboBox { background-color: rgba(255,255,255,0.05); "
            "border: 1px solid #2a3f7a; border-radius: 8px; "
            "color: white; padding: 0 12px; font-size: 12px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #1a2854; "
            "color: white; border: 1px solid #FFD700; }"
        )

    def _dialog_atribuir(self, user_id, username):
        from utils.supabase_admin import listar_planos

        self._svc.fetch(
            listar_planos,
            lambda planos: self._abrir_dialog_atribuir(user_id, username, planos or []),
        )

    def _abrir_dialog_atribuir(self, user_id, username, planos):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🎯  Atribuir Plano", parent=self.ui)
        lbl_info = QLabel(f"Usuário: <b style='color:#FFD700'>{username}</b>")
        lbl_info.setStyleSheet("color: #cccccc; font-size: 12px;")
        lbl_plano = QLabel("Selecione o plano:")
        lbl_plano.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(self._estilo_combo())
        for p in planos:
            if p.get("id") != BASICO_ID:
                combo.addItem(p["nome"], p["id"])
        lbl_dias = QLabel("Dias de acesso (0 = sem expiração):")
        lbl_dias.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_dias = QLineEdit("30")
        inp_dias.setFixedHeight(36)
        inp_dias.setStyleSheet(dialog._estilo_input())
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(0, lbl_info)
        dialog._layout_corpo.insertWidget(1, lbl_plano)
        dialog._layout_corpo.insertWidget(2, combo)
        dialog._layout_corpo.insertWidget(3, lbl_dias)
        dialog._layout_corpo.insertWidget(4, inp_dias)
        dialog._layout_corpo.insertWidget(5, lbl_aviso)

        def _salvar():
            plano_id = combo.currentData()
            plano_nome = combo.currentText()
            if not plano_id:
                lbl_aviso.setText("⚠️  Nenhum plano disponível.")
                return
            try:
                dias = int(inp_dias.text().strip())
                if dias < 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Dias inválido.")
                return
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Salvando...")
            w = _chamar_rpc(
                "atribuir_plano",
                {"p_user_id": user_id, "p_plano_id": plano_id, "p_dias": dias},
                lambda: (
                    self._registrar_log(
                        "atribuir_plano", username, {"plano": plano_nome, "dias": dias}
                    ),
                    dialog.accept(),
                ),
                lambda msg: (
                    lbl_aviso.setText(f"⚠️  {msg}"),
                    dialog._btn_confirmar.setEnabled(True),
                    dialog._btn_confirmar.setText("✓  Confirmar"),
                ),
            )
            self._workers.append(w)

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _dialog_mudar_plano(self, user_id, username=""):
        from utils.supabase_admin import listar_planos

        self._svc.fetch(
            listar_planos,
            lambda planos: self._abrir_dialog_mudar_plano(
                user_id, username, planos or []
            ),
        )

    def _abrir_dialog_mudar_plano(self, user_id, username, planos):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🎯  Mudar Plano", parent=self.ui)
        lbl_plano = QLabel("Selecione o novo plano:")
        lbl_plano.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(self._estilo_combo())
        for p in planos:
            if p.get("id") != BASICO_ID:
                combo.addItem(p["nome"], p["id"])
        lbl_dias = QLabel("Dias de acesso (0 = sem expiração):")
        lbl_dias.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_dias = QLineEdit("30")
        inp_dias.setFixedHeight(36)
        inp_dias.setStyleSheet(dialog._estilo_input())
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(0, lbl_plano)
        dialog._layout_corpo.insertWidget(1, combo)
        dialog._layout_corpo.insertWidget(2, lbl_dias)
        dialog._layout_corpo.insertWidget(3, inp_dias)
        dialog._layout_corpo.insertWidget(4, lbl_aviso)

        def _salvar():
            plano_id = combo.currentData()
            plano_nome = combo.currentText()
            if not plano_id:
                lbl_aviso.setText("⚠️  Nenhum plano disponível.")
                return
            try:
                dias = int(inp_dias.text().strip())
                if dias < 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Dias inválido.")
                return
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Salvando...")
            w = _chamar_rpc(
                "atribuir_plano",
                {"p_user_id": user_id, "p_plano_id": plano_id, "p_dias": dias},
                lambda: (
                    self._registrar_log(
                        "mudar_plano", username, {"plano": plano_nome, "dias": dias}
                    ),
                    dialog.accept(),
                ),
                lambda msg: (
                    lbl_aviso.setText(f"⚠️  {msg}"),
                    dialog._btn_confirmar.setEnabled(True),
                    dialog._btn_confirmar.setText("✓  Confirmar"),
                ),
            )
            self._workers.append(w)

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _dialog_renovar(self, user_id):
        from telas.dialogs import DialogBase
        from utils.supabase_admin import renovar_assinatura

        dialog = DialogBase("🔄  Renovar Assinatura", parent=self.ui)
        lbl = QLabel("Quantos dias deseja adicionar?")
        lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp = QLineEdit("30")
        inp.setFixedHeight(36)
        inp.setStyleSheet(dialog._estilo_input())
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._layout_corpo.insertWidget(1, inp)
        dialog._layout_corpo.insertWidget(2, lbl_aviso)

        def _salvar():
            try:
                dias = int(inp.text().strip())
                if dias <= 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Digite um número válido.")
                return
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Salvando...")
            w = AssWorker(renovar_assinatura, user_id, dias)
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

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _revogar_para_basico(self, user_id, username):
        from telas.dialogs import DialogConfirmacao

        # Descobre plano atual antes de revogar
        plano_anterior = "?"
        try:
            from utils.supabase_admin import _cliente

            ass = (
                _cliente()
                .table("v_assinaturas")
                .select("plano_nome")
                .eq("user_id", user_id)
                .eq("ativo", True)
                .limit(1)
                .execute()
            )
            if ass.data:
                plano_anterior = ass.data[0].get("plano_nome", "?")
        except Exception:
            pass
        msg = f"Revogar plano de '{username}'? O usuário receberá o plano Básico sem expiração."
        if DialogConfirmacao(msg, parent=self.ui).exec():
            w = _chamar_rpc(
                "revogar_para_basico",
                {"p_user_id": user_id},
                lambda: self._registrar_log(
                    "revogar_para_basico", username, {"plano_anterior": plano_anterior}
                ),
                lambda e: print(f"[Revogar] Erro: {e}"),
            )
            self._workers.append(w)

    def _registrar_log(self, acao, username, detalhes):
        try:
            from utils.supabase_admin import _logs

            _logs.registrar(acao, detalhes={"username": username, **detalhes})
        except Exception as e:
            print(f"[Log] Erro: {e}")

    def _item(self, texto):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

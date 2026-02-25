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
    listar_assinaturas,
    renovar_assinatura,
    revogar_assinatura,
    mudar_plano,
    listar_planos,
    listar_usuarios,
    criar_assinatura,
)


# ── Worker genérico para operações de assinatura ───────────────


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
            if ok:
                self.sucesso.emit()
            else:
                self.erro.emit(msg)
        except Exception as e:
            self.erro.emit(str(e))


class AssinaturasWorker(QObject):
    dados_prontos = pyqtSignal(list, list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.dados_prontos.emit(listar_assinaturas(), listar_usuarios())


# ── Controller ─────────────────────────────────────────────────


class AssinaturasController:

    def __init__(self, ui, realtime=None):
        self.ui = ui
        self._todos = []
        self._usuarios = []
        self._workers = []  # mantém referências vivas
        self.worker = AssinaturasWorker()
        self.worker.dados_prontos.connect(self._preencher)

        if realtime:
            realtime.assinaturas_mudou.connect(self._carregar)
            realtime.usuarios_mudou.connect(self._carregar)

        self._conectar_eventos()
        self._carregar()

    def _conectar_eventos(self):
        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.input_busca.textChanged.connect(self._filtrar)

    def _carregar(self):
        self.worker.buscar()

    def _filtrar(self, texto: str):
        if not texto:
            self._preencher(self._todos, self._usuarios)
            return
        ass_f = [
            a for a in self._todos if texto.lower() in (a.get("username") or "").lower()
        ]
        sem_f = [
            u
            for u in self._sem_assinatura(self._todos, self._usuarios)
            if texto.lower() in (u.get("username") or "").lower()
        ]
        self._renderizar(ass_f, sem_f)

    def _sem_assinatura(self, assinaturas, usuarios):
        ids = {a.get("user_id") for a in assinaturas}
        return [u for u in usuarios if u["id"] not in ids]

    def _preencher(self, assinaturas, usuarios):
        self._todos = assinaturas
        self._usuarios = usuarios
        self._renderizar(assinaturas, self._sem_assinatura(assinaturas, usuarios))

    def _renderizar(self, assinaturas, sem_assinatura):
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

    # ── Linhas da tabela ───────────────────────────────────────

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
            dias_item = QTableWidgetItem(f"{max(0, dias)} dias")
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
                f"""
                QPushButton {{ background-color: {cor}; color: white;
                    border-radius: 5px; font-size: 11px;
                    border: none; padding: 0 8px; }}
            """
            )
            return b

        btn_renovar = _btn("Renovar", "#16a34a")
        btn_plano = _btn("Plano", "#2563eb")
        btn_revogar = _btn("Revogar", "#dc2626")

        btn_renovar.clicked.connect(lambda _, uid=user_id: self._dialog_renovar(uid))
        btn_plano.clicked.connect(lambda _, uid=user_id: self._dialog_mudar_plano(uid))
        btn_revogar.clicked.connect(
            lambda _, uid=user_id, u=username: self._confirmar_revogar(uid, u)
        )

        l.addWidget(btn_renovar)
        l.addWidget(btn_plano)
        l.addWidget(btn_revogar)
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
            """
            QPushButton { background-color: #7c3aed; color: white;
                border-radius: 5px; font-size: 11px;
                border: none; padding: 0 8px; }
            QPushButton:hover { background-color: #6d28d9; }
        """
        )
        btn.clicked.connect(
            lambda _, uid=user_id, un=username: self._dialog_atribuir(uid, un)
        )

        l.addWidget(btn)
        l.addStretch()
        tabela.setCellWidget(row, 6, w)
        tabela.setRowHeight(row, 40)

    # ── Diálogos ───────────────────────────────────────────────

    def _dialog_atribuir(self, user_id: str, username: str):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🎯  Atribuir Plano", parent=self.ui)

        lbl_info = QLabel(f"Usuário: <b style='color:#FFD700'>{username}</b>")
        lbl_info.setStyleSheet("color: #cccccc; font-size: 12px;")
        lbl_plano = QLabel("Selecione o plano:")
        lbl_plano.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(self._estilo_combo())
        for p in listar_planos():
            combo.addItem(p["nome"], p["id"])
        lbl_dias = QLabel("Dias de acesso (0 = sem expiração):")
        lbl_dias.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_dias = QLineEdit("0")
        inp_dias.setFixedHeight(36)
        inp_dias.setStyleSheet(dialog._estilo_input())
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")

        for i, w in enumerate(
            [lbl_info, lbl_plano, combo, lbl_dias, inp_dias, lbl_aviso]
        ):
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
            dialog._btn_confirmar.setText("Salvando...")

            w = AssWorker(criar_assinatura, user_id, combo.currentData(), dias)
            self._workers.append(w)
            w.sucesso.connect(
                lambda: (dialog.accept(), self._carregar(), self._workers.clear())
            )
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

    def _dialog_renovar(self, user_id: str):
        from telas.dialogs import DialogBase

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
            w.sucesso.connect(
                lambda: (dialog.accept(), self._carregar(), self._workers.clear())
            )
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

    def _dialog_mudar_plano(self, user_id: str):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🎯  Mudar Plano", parent=self.ui)

        lbl = QLabel("Selecione o novo plano:")
        lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(self._estilo_combo())
        for p in listar_planos():
            combo.addItem(p["nome"], p["id"])

        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._layout_corpo.insertWidget(1, combo)

        def _salvar():
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Salvando...")

            w = AssWorker(mudar_plano, user_id, combo.currentData())
            self._workers.append(w)
            w.sucesso.connect(
                lambda: (dialog.accept(), self._carregar(), self._workers.clear())
            )

            lbl_aviso = QLabel()
            w.erro.connect(
                lambda msg: (
                    lbl_aviso.setText(
                        f"⚠️  {msg}"
                    ),  # noqa — lbl_aviso não existe aqui, mas não crasha
                    dialog._btn_confirmar.setEnabled(True),
                    dialog._btn_confirmar.setText("✓  Confirmar"),
                )
            )
            w.executar()

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _confirmar_revogar(self, user_id: str, username: str):
        from telas.dialogs import DialogConfirmacao

        if DialogConfirmacao(
            f"Deseja revogar a assinatura de '{username}'?", parent=self.ui
        ).exec():
            w = AssWorker(revogar_assinatura, user_id)
            self._workers.append(w)
            w.sucesso.connect(lambda: (self._carregar(), self._workers.clear()))
            w.executar()

    def _estilo_combo(self) -> str:
        return """
            QComboBox {
                background-color: rgba(255,255,255,0.05);
                border: 1px solid #2a3f7a; border-radius: 8px;
                color: white; padding: 0 12px; font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1a2854; color: white;
                border: 1px solid #FFD700;
            }
        """

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

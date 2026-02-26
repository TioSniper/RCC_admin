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
import os, threading
from utils.supabase_admin import renovar_assinatura


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
    """Executa RPC em thread e emite sinais de volta na thread principal."""

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
            from supabase import create_client
            from dotenv import load_dotenv

            load_dotenv()
            cli = create_client(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
            )
            cli.rpc(self._nome, self._params).execute()
            self.sucesso.emit()
        except Exception as e:
            self.erro.emit(str(e))


def _chamar_rpc(nome: str, params: dict, callback_ok, callback_err):
    """Chama uma RPC do Supabase em thread separada, callbacks na thread principal."""
    w = _RpcWorker(nome, params)
    w.sucesso.connect(callback_ok)
    w.erro.connect(callback_err)
    w.executar()
    return w  # mantém referência viva


class AssinaturasController:

    def __init__(self, ui, store):
        self.ui = ui
        self._store = store
        self._workers = []

        # Debounce de 300ms — agrupa eventos rápidos (UPDATE + INSERT)
        # evitando o pisca de "sem assinatura" entre os dois eventos
        from PyQt6.QtCore import QTimer

        self._timer_render = QTimer()
        self._timer_render.setSingleShot(True)
        self._timer_render.setInterval(300)
        self._timer_render.timeout.connect(self._renderizar)

        store.assinaturas_atualizadas.connect(self._timer_render.start)
        store.carregamento_completo.connect(self._renderizar)

        self._conectar_eventos()
        if store.assinaturas:
            self._renderizar()

    def _conectar_eventos(self):
        self.ui.btn_refresh.clicked.connect(lambda: self._store.carregar_tudo())
        self.ui.input_busca.textChanged.connect(self._filtrar)

    def _filtrar(self, texto: str):
        if not texto:
            self._renderizar()
            return
        ass_f = [
            a
            for a in self._store.assinaturas
            if texto.lower() in (a.get("username") or "").lower()
        ]
        sem_f = [
            u
            for u in self._sem_assinatura()
            if texto.lower() in (u.get("username") or "").lower()
        ]
        self._renderizar_dados(ass_f, sem_f)

    def _sem_assinatura(self):
        ids = {a.get("user_id") for a in self._store.assinaturas}
        return [u for u in self._store.usuarios if u["id"] not in ids]

    def _renderizar(self):
        self._renderizar_dados(self._store.assinaturas, self._sem_assinatura())

    def _renderizar_dados(self, assinaturas, sem_assinatura):
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
        btn_plano.clicked.connect(lambda _, uid=user_id: self._dialog_mudar_plano(uid))
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
            "QPushButton { background-color: #7c3aed; color: white; "
            "border-radius: 5px; font-size: 11px; border: none; padding: 0 8px; }"
            "QPushButton:hover { background-color: #6d28d9; }"
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
            "QComboBox { background-color: rgba(255,255,255,0.05); border: 1px solid #2a3f7a; "
            "border-radius: 8px; color: white; padding: 0 12px; font-size: 12px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: #1a2854; color: white; border: 1px solid #FFD700; }"
        )

    def _dialog_atribuir(self, user_id: str, username: str):
        import os
        from telas.dialogs import DialogBase

        BASICO_ID = os.getenv("PLANO_BASICO_ID", "11111111-1111-1111-1111-111111111111")

        dialog = DialogBase("🎯  Atribuir Plano", parent=self.ui)

        lbl_info = QLabel(f"Usuário: <b style='color:#FFD700'>{username}</b>")
        lbl_info.setStyleSheet("color: #cccccc; font-size: 12px;")

        lbl_plano = QLabel("Selecione o plano:")
        lbl_plano.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")

        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(self._estilo_combo())
        for p in self._store.planos:
            if p["id"] != BASICO_ID:
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
                lambda: dialog.accept(),
                lambda msg: (
                    lbl_aviso.setText(f"⚠️  {msg}"),
                    dialog._btn_confirmar.setEnabled(True),
                    dialog._btn_confirmar.setText("✓  Confirmar"),
                ),
            )
            self._workers.append(w)

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

    def _dialog_mudar_plano(self, user_id: str):
        import os
        from telas.dialogs import DialogBase
        from utils.supabase_admin import criar_assinatura

        BASICO_ID = os.getenv("PLANO_BASICO_ID", "11111111-1111-1111-1111-111111111111")

        dialog = DialogBase("🎯  Mudar Plano", parent=self.ui)

        lbl_plano = QLabel("Selecione o novo plano:")
        lbl_plano.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")

        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(self._estilo_combo())
        for p in self._store.planos:
            if p["id"] != BASICO_ID:
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
                lambda: dialog.accept(),
                lambda msg: (
                    lbl_aviso.setText(f"⚠️  {msg}"),
                    dialog._btn_confirmar.setEnabled(True),
                    dialog._btn_confirmar.setText("✓  Confirmar"),
                ),
            )
            self._workers.append(w)

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _revogar_para_basico(self, user_id: str, username: str):
        from telas.dialogs import DialogConfirmacao

        if DialogConfirmacao(
            f"Revogar plano de '{username}'? O usuário receberá o plano Básico sem expiração.",
            parent=self.ui,
        ).exec():
            import threading, os
            from supabase import create_client
            from dotenv import load_dotenv

            load_dotenv()

            def _run():
                try:
                    c = create_client(
                        os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
                    )
                    c.rpc("revogar_para_basico", {"p_user_id": user_id}).execute()
                except Exception as e:
                    print(f"[Revogar] Erro: {e}")

            threading.Thread(target=_run, daemon=True).start()

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

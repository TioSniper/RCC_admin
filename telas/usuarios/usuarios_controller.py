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
from utils.supabase_admin import (
    ativar_usuario,
    desativar_usuario,
    deletar_usuario,
    resetar_senha,
    criar_usuario,
)


def _criar_usuario_completo(
    username: str, senha: str, plano_id: str, dias: int
) -> tuple[bool, str]:
    """Cria usuário e atribui plano em sequência."""
    from utils.supabase_admin import criar_usuario
    from supabase import create_client
    from dotenv import load_dotenv
    import os

    load_dotenv()
    ok, resultado = criar_usuario(username, senha)
    if not ok:
        return False, resultado
    # resultado é o user_id quando ok=True
    user_id = resultado
    if plano_id:
        try:
            cli = create_client(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY")
            )
            cli.rpc(
                "atribuir_plano",
                {
                    "p_user_id": user_id,
                    "p_plano_id": plano_id,
                    "p_dias": dias,
                },
            ).execute()
        except Exception as e:
            return True, f"Usuário criado mas erro ao atribuir plano: {e}"
    return True, "Usuário criado."


class UsuarioWorker(QObject):
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


class UsuariosController:

    def __init__(self, ui, svc):
        self.ui = ui
        self._svc = svc
        self._workers = []

        svc.usuarios_mudou.connect(self._carregar)
        svc.sessoes_mudou.connect(self._carregar)

        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.btn_novo.clicked.connect(self._dialog_novo_usuario)
        self.ui.input_busca.textChanged.connect(self._filtrar)

        self._todos = []
        self._carregar()

    def _carregar(self):
        from utils.supabase_admin import listar_usuarios, listar_sessoes_ativas

        self._svc.fetch(
            lambda: {"usuarios": listar_usuarios(), "sessoes": listar_sessoes_ativas()},
            self._renderizar,
        )

    def _filtrar(self, texto: str):
        if not self._todos:
            return
        filtrados = (
            [
                u
                for u in self._todos
                if texto.lower() in (u.get("username") or "").lower()
                or texto.lower() in (u.get("email") or "").lower()
            ]
            if texto
            else self._todos
        )
        self._preencher(filtrados, [])

    def _renderizar(self, dados):
        if not dados:
            return
        usuarios = dados.get("usuarios", [])
        sessoes = dados.get("sessoes", [])
        self._todos = usuarios
        self._preencher(usuarios, sessoes)

    def _preencher(self, usuarios, sessoes):
        from datetime import datetime, timezone

        # sessoes pode ser lista de dicts ou lista de strings (user_id direto)
        ids_online = set()
        for s in sessoes or []:
            if isinstance(s, dict):
                ids_online.add(s.get("user_id"))
            elif isinstance(s, str):
                ids_online.add(s)

        tabela = self.ui.tabela
        tabela.setRowCount(0)
        for u in usuarios:
            row = tabela.rowCount()
            tabela.insertRow(row)
            uid = u.get("id", "")
            username = u.get("username", "—")
            email = u.get("email", "—")
            ativo = u.get("ativo", False)
            online = uid in ids_online
            ass = u.get("assinatura") or {}
            plano = ass.get("plano_nome", "Sem plano")

            # Expira em
            expira_txt = "—"
            if ass.get("expira_em"):
                try:
                    dt = datetime.fromisoformat(ass["expira_em"].replace("Z", "+00:00"))
                    expira_txt = dt.strftime("%d/%m/%Y")
                except Exception:
                    pass
            elif ass.get("plano_id"):
                expira_txt = "Sem expiração"

            # Cadastro
            cadastro_txt = "—"
            if u.get("criado_em"):
                try:
                    dt = datetime.fromisoformat(u["criado_em"].replace("Z", "+00:00"))
                    cadastro_txt = dt.strftime("%d/%m/%Y")
                except Exception:
                    pass

            status_txt = (
                "🟢 Online" if online else ("✅ Ativo" if ativo else "❌ Inativo")
            )
            status_item = QTableWidgetItem(status_txt)
            status_item.setForeground(
                Qt.GlobalColor.green
                if online
                else Qt.GlobalColor.yellow if ativo else Qt.GlobalColor.red
            )
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # col 0-5: dados
            tabela.setItem(row, 0, self._item(username))
            tabela.setItem(row, 1, self._item(email))
            tabela.setItem(row, 2, status_item)
            tabela.setItem(row, 3, self._item(plano))
            tabela.setItem(row, 4, self._item(expira_txt))
            tabela.setItem(row, 5, self._item(cadastro_txt))

            # col 6: ações
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

    def _toggle_usuario(self, uid: str, ativo: bool):
        from utils.supabase_admin import desativar_usuario

        fn = desativar_usuario if ativo else ativar_usuario
        w = UsuarioWorker(fn, uid)
        self._workers.append(w)
        w.sucesso.connect(lambda: self._workers.clear())
        w.executar()

    def _dialog_resetar_senha(self, uid: str):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🔑  Resetar Senha", parent=self.ui)
        lbl = QLabel("Nova senha:")
        lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp = QLineEdit()
        inp.setPlaceholderText("••••••••")
        inp.setFixedHeight(36)
        inp.setStyleSheet(dialog._estilo_input())
        inp.setEchoMode(QLineEdit.EchoMode.Password)
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._layout_corpo.insertWidget(1, inp)
        dialog._layout_corpo.insertWidget(2, lbl_aviso)

        def _salvar():
            senha = inp.text().strip()
            if len(senha) < 6:
                lbl_aviso.setText("⚠️  Mínimo 6 caracteres.")
                return
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Salvando...")
            w = UsuarioWorker(resetar_senha, uid, senha)
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

    def _dialog_novo_usuario(self):
        from telas.dialogs import DialogBase
        from utils.supabase_admin import listar_planos
        import os

        BASICO_ID = os.getenv("PLANO_BASICO_ID", "11111111-1111-1111-1111-111111111111")
        dialog = DialogBase("➕  Novo Usuário", parent=self.ui)

        def _campo(lbl_txt, ph, idx):
            lbl = QLabel(lbl_txt)
            lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
            inp = QLineEdit()
            inp.setPlaceholderText(ph)
            inp.setFixedHeight(36)
            inp.setStyleSheet(dialog._estilo_input())
            dialog._layout_corpo.insertWidget(idx * 2, lbl)
            dialog._layout_corpo.insertWidget(idx * 2 + 1, inp)
            return inp

        inp_user = _campo("Username:", "ex: joao123", 0)
        inp_senha = _campo("Senha:", "mínimo 6 caracteres", 1)
        from PyQt6.QtWidgets import QComboBox

        lbl_plano = QLabel("Plano inicial:")
        lbl_plano.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet(
            """QComboBox { background-color: rgba(255,255,255,0.05);
            border: 1px solid #2a3f7a; border-radius: 8px; color: white; padding: 0 12px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: #1a2854; color: white; border: 1px solid #FFD700; }"""
        )
        for p in listar_planos():
            if p["id"] != BASICO_ID:
                combo.addItem(p["nome"], p["id"])
        lbl_dias = QLabel("Dias (0 = sem expiração):")
        lbl_dias.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_dias = QLineEdit("0")
        inp_dias.setFixedHeight(36)
        inp_dias.setStyleSheet(dialog._estilo_input())
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        for i, wg in enumerate(
            [lbl_plano, combo, lbl_dias, inp_dias, lbl_aviso], start=4
        ):
            dialog._layout_corpo.insertWidget(i, wg)

        def _salvar():
            u = inp_user.text().strip()
            s = inp_senha.text().strip()
            if not u or len(s) < 6:
                lbl_aviso.setText("⚠️  Preencha todos os campos (senha mín. 6 chars).")
                return
            try:
                dias = int(inp_dias.text().strip())
            except ValueError:
                lbl_aviso.setText("⚠️  Dias inválido.")
                return
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Criando...")
            w = UsuarioWorker(_criar_usuario_completo, u, s, combo.currentData(), dias)
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

    def _confirmar_deletar(self, uid: str, username: str):
        from telas.dialogs import DialogConfirmacao

        if DialogConfirmacao(
            f"Deletar usuário '{username}'? Esta ação é irreversível.", parent=self.ui
        ).exec():
            w = UsuarioWorker(deletar_usuario, uid)
            self._workers.append(w)
            w.sucesso.connect(lambda: self._workers.clear())
            w.executar()

    def _item(self, texto):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

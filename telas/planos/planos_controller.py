from PyQt6.QtWidgets import (
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from utils.supabase_admin import (
    criar_plano,
    editar_plano,
    ativar_plano,
    adicionar_modulo_plano,
    remover_modulo_plano,
    excluir_plano,
)


class PlanosWorker(QObject):
    salvar_pronto = pyqtSignal(bool, str)
    editar_pronto = pyqtSignal(bool)
    modulos_pronto = pyqtSignal()
    toggle_pronto = pyqtSignal()
    delete_pronto = pyqtSignal(bool)

    def salvar(self, nome, desc, modulos):
        ok, msg = criar_plano(nome, desc, modulos)
        self.salvar_pronto.emit(ok, msg)

    def editar(self, pid, nome, desc):
        ok, _ = editar_plano(pid, nome, desc)
        self.editar_pronto.emit(ok)

    def toggle(self, pid, ativo):
        ativar_plano(pid, not ativo)
        self.toggle_pronto.emit()

    def atualizar_modulos(self, pid, checks, atuais):
        for mid, checked in checks.items():
            if checked and mid not in atuais:
                adicionar_modulo_plano(pid, mid)
            elif not checked and mid in atuais:
                remover_modulo_plano(pid, mid)
        self.modulos_pronto.emit()

    def excluir(self, pid):
        ok = excluir_plano(pid)
        self.delete_pronto.emit(ok)


class PlanosController:

    def __init__(self, ui, svc, realtime=None):
        self.ui = ui
        self._svc = svc
        self._modulos = []

        self.thread = QThread()
        self.worker = PlanosWorker()
        self.worker.moveToThread(self.thread)
        self.worker.salvar_pronto.connect(self._finalizar_salvar)
        self.worker.editar_pronto.connect(self._finalizar_editar)
        self.worker.modulos_pronto.connect(self._finalizar_modulos)
        self.worker.toggle_pronto.connect(self._carregar)
        self.worker.delete_pronto.connect(self._finalizar_exclusao)
        self.thread.start()

        svc.planos_mudou.connect(self._carregar)

        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.btn_novo.clicked.connect(self._dialog_novo_plano)
        self._carregar()

    def _carregar(self):
        from utils.supabase_admin import listar_planos, listar_modulos

        self._svc.fetch(
            lambda: {"planos": listar_planos(), "modulos": listar_modulos()},
            self._renderizar,
        )

    def _renderizar(self, dados):
        if not dados:
            return
        self._modulos = dados.get("modulos", [])
        tabela = self.ui.tabela
        tabela.setRowCount(0)
        for p in dados.get("planos", []):
            row = tabela.rowCount()
            tabela.insertRow(row)
            ativo = p.get("ativo", True)
            plano_id = p.get("id", "")
            mids = [m["modulo_id"] for m in p.get("planos_modulos", [])]
            nomes = [m["nome"] for m in self._modulos if m["id"] in mids]
            mod_txt = ", ".join(nomes) if nomes else "Nenhum"

            status = QTableWidgetItem("✅ Ativo" if ativo else "❌ Inativo")
            status.setForeground(Qt.GlobalColor.green if ativo else Qt.GlobalColor.red)
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            tabela.setItem(row, 0, self._item(p.get("nome", "—")))
            tabela.setItem(row, 1, self._item(p.get("descricao", "—")))
            tabela.setItem(row, 2, self._item(mod_txt))
            tabela.setItem(row, 3, status)

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

            btn_editar = _btn("Editar", "#2563eb")
            btn_modulos = _btn("Módulos", "#7c3aed")
            btn_toggle = _btn(
                "Desativar" if ativo else "Ativar", "#dc2626" if ativo else "#16a34a"
            )
            btn_excluir = _btn("Excluir", "#6b7280")

            btn_editar.clicked.connect(
                lambda _, pid=plano_id, n=p.get("nome", ""), d=p.get(
                    "descricao", ""
                ): self._dialog_editar(pid, n, d)
            )
            btn_modulos.clicked.connect(
                lambda _, pid=plano_id, m=mids: self._dialog_modulos(pid, m)
            )
            btn_toggle.clicked.connect(
                lambda _, pid=plano_id, a=ativo: self.worker.toggle(pid, a)
            )
            btn_excluir.clicked.connect(
                lambda _, pid=plano_id: self._confirmar_exclusao(pid)
            )

            l.addWidget(btn_editar)
            l.addWidget(btn_modulos)
            l.addWidget(btn_toggle)
            l.addWidget(btn_excluir)
            l.addStretch()
            tabela.setCellWidget(row, 4, w)
            tabela.setRowHeight(row, 40)

    def _dialog_novo_plano(self):
        from telas.dialogs import DialogBase

        dialog = DialogBase("➕  Novo Plano", parent=self.ui)

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

        inp_nome = _campo("Nome do plano:", "Ex: Premium", 0)
        inp_desc = _campo("Descrição:", "Ex: Acesso total", 1)
        lbl_mod = QLabel("Módulos incluídos:")
        lbl_mod.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        dialog._layout_corpo.insertWidget(4, lbl_mod)
        checks = {}
        from utils.supabase_admin import listar_modulos as _lm

        for i, m in enumerate(_lm()):
            cb = QCheckBox(m["nome"])
            cb.setStyleSheet("color: white; font-size: 12px;")
            dialog._layout_corpo.insertWidget(5 + i, cb)
            checks[m["id"]] = cb
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.addWidget(lbl_aviso)

        def _salvar():
            nome = inp_nome.text().strip()
            if not nome:
                lbl_aviso.setText("⚠️  Informe o nome.")
                return
            self._dialog_ref = dialog
            self._lbl_ref = lbl_aviso
            self.worker.salvar(
                nome,
                inp_desc.text(),
                [mid for mid, cb in checks.items() if cb.isChecked()],
            )

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _finalizar_salvar(self, ok, msg):
        if ok:
            self._dialog_ref.accept()
        else:
            self._lbl_ref.setText(f"⚠️  {msg}")

    def _dialog_editar(self, pid, nome, descricao):
        from telas.dialogs import DialogBase

        dialog = DialogBase("✏️  Editar Plano", parent=self.ui)

        def _campo(lbl_txt, valor, idx):
            lbl = QLabel(lbl_txt)
            lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
            inp = QLineEdit(valor)
            inp.setFixedHeight(36)
            inp.setStyleSheet(dialog._estilo_input())
            dialog._layout_corpo.insertWidget(idx * 2, lbl)
            dialog._layout_corpo.insertWidget(idx * 2 + 1, inp)
            return inp

        inp_nome = _campo("Nome:", nome, 0)
        inp_desc = _campo("Descrição:", descricao or "", 1)

        def _salvar():
            self._dialog_ref = dialog
            self.worker.editar(pid, inp_nome.text(), inp_desc.text())

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _finalizar_editar(self, ok):
        if ok:
            self._dialog_ref.accept()

    def _dialog_modulos(self, pid, modulos_atuais):
        from telas.dialogs import DialogBase
        from utils.supabase_admin import listar_modulos

        dialog = DialogBase("🧩  Módulos do Plano", parent=self.ui)
        lbl = QLabel("Selecione os módulos incluídos:")
        lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        dialog._layout_corpo.insertWidget(0, lbl)
        checks = {}
        # Busca módulos frescos do banco ao abrir o dialog
        modulos_frescos = listar_modulos()
        for i, m in enumerate(modulos_frescos):
            cb = QCheckBox(m["nome"])
            cb.setChecked(m["id"] in modulos_atuais)
            cb.setStyleSheet("color: white; font-size: 12px;")
            dialog._layout_corpo.insertWidget(1 + i, cb)
            checks[m["id"]] = cb

        def _salvar():
            self._dialog_ref = dialog
            self.worker.atualizar_modulos(
                pid, {mid: cb.isChecked() for mid, cb in checks.items()}, modulos_atuais
            )

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _finalizar_modulos(self):
        self._dialog_ref.accept()

    def _confirmar_exclusao(self, pid):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🗑️  Excluir Plano", parent=self.ui)
        lbl = QLabel("Tem certeza que deseja excluir este plano?")
        lbl.setStyleSheet("color: #ccc; font-size: 12px;")
        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._btn_confirmar.setText("Excluir")
        dialog._btn_confirmar.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: white; border-radius: 6px; padding: 6px 12px; }"
        )

        def _confirmar():
            self._dialog_ref = dialog
            self.worker.excluir(pid)

        dialog._btn_confirmar.clicked.connect(_confirmar)
        dialog.exec()

    def _finalizar_exclusao(self, ok):
        if ok:
            self._dialog_ref.accept()

    def _item(self, texto):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

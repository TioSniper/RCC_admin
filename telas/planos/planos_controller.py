import threading
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
    listar_planos,
    criar_plano,
    editar_plano,
    ativar_plano,
    adicionar_modulo_plano,
    remover_modulo_plano,
    listar_modulos,
    excluir_plano,
)


class PlanosWorker(QObject):
    dados_prontos = pyqtSignal(list)
    toggle_pronto = pyqtSignal()
    salvar_pronto = pyqtSignal(bool, str)
    editar_pronto = pyqtSignal(bool)
    modulos_pronto = pyqtSignal()
    delete_pronto = pyqtSignal(bool)

    def buscar(self):
        self.dados_prontos.emit(listar_planos())

    def toggle(self, plano_id, ativo):
        ativar_plano(plano_id, not ativo)
        self.toggle_pronto.emit()

    def salvar(self, nome, descricao, modulos):
        ok, msg = criar_plano(nome, descricao, modulos)
        self.salvar_pronto.emit(ok, msg)

    def editar(self, plano_id, nome, descricao):
        ok, _ = editar_plano(plano_id, nome, descricao)
        self.editar_pronto.emit(ok)

    def atualizar_modulos(self, plano_id, checks, modulos_atuais):
        for mid, checked in checks.items():
            if checked and mid not in modulos_atuais:
                adicionar_modulo_plano(plano_id, mid)
            elif not checked and mid in modulos_atuais:
                remover_modulo_plano(plano_id, mid)
        self.modulos_pronto.emit()

    def excluir(self, plano_id):
        ok = excluir_plano(plano_id)
        self.delete_pronto.emit(ok)


class PlanosController:

    def __init__(self, ui, realtime=None):
        self.ui = ui
        self.thread = QThread()
        self.worker = PlanosWorker()
        self.worker.moveToThread(self.thread)

        self.worker.dados_prontos.connect(self._preencher)
        self.worker.toggle_pronto.connect(self._carregar)
        self.worker.salvar_pronto.connect(self._finalizar_salvar)
        self.worker.editar_pronto.connect(self._finalizar_editar)
        self.worker.modulos_pronto.connect(self._finalizar_modulos)
        self.worker.delete_pronto.connect(self._finalizar_exclusao)

        self.thread.start()

        if realtime:
            realtime.planos_mudou.connect(lambda _: self._carregar())
            realtime.modulos_mudou.connect(lambda _: self._carregar())

        self._conectar_eventos()
        self._carregar()

    def _conectar_eventos(self):
        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.btn_novo.clicked.connect(self._dialog_novo_plano)

    def _carregar(self):
        self.worker.buscar()

    def _preencher(self, planos: list):
        tabela = self.ui.tabela
        tabela.setRowCount(0)
        modulos_disponiveis = listar_modulos()

        for p in planos:
            row = tabela.rowCount()
            tabela.insertRow(row)
            ativo = p.get("ativo", True)
            plano_id = p.get("id", "")
            modulos_ids = [m["modulo_id"] for m in p.get("planos_modulos", [])]
            modulos_nomes = [
                m["nome"] for m in modulos_disponiveis if m["id"] in modulos_ids
            ]
            modulos_txt = ", ".join(modulos_nomes) if modulos_nomes else "Nenhum"

            status_item = QTableWidgetItem("✅ Ativo" if ativo else "❌ Inativo")
            status_item.setForeground(
                Qt.GlobalColor.green if ativo else Qt.GlobalColor.red
            )
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            tabela.setItem(row, 0, self._item(p.get("nome", "—")))
            tabela.setItem(row, 1, self._item(p.get("descricao", "—")))
            tabela.setItem(row, 2, self._item(modulos_txt))
            tabela.setItem(row, 3, status_item)

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
                lambda _, pid=plano_id, mids=modulos_ids: self._dialog_modulos(
                    pid, mids
                )
            )
            btn_toggle.clicked.connect(
                lambda _, pid=plano_id, a=ativo: self._toggle(pid, a)
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

    def _toggle(self, plano_id: str, ativo: bool):
        self.worker.toggle(plano_id, ativo)

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
        for i, m in enumerate(listar_modulos()):
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
                lbl_aviso.setText("⚠️  Informe o nome do plano.")
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
            self._carregar()
        else:
            self._lbl_ref.setText(f"⚠️  {msg}")

    def _dialog_editar(self, plano_id: str, nome: str, descricao: str):
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
            self.worker.editar(plano_id, inp_nome.text(), inp_desc.text())

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _finalizar_editar(self, ok):
        if ok:
            self._dialog_ref.accept()
            self._carregar()

    def _dialog_modulos(self, plano_id: str, modulos_atuais: list):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🧩  Módulos do Plano", parent=self.ui)

        lbl = QLabel("Selecione os módulos incluídos:")
        lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        dialog._layout_corpo.insertWidget(0, lbl)

        checks = {}
        for i, m in enumerate(listar_modulos()):
            cb = QCheckBox(m["nome"])
            cb.setChecked(m["id"] in modulos_atuais)
            cb.setStyleSheet("color: white; font-size: 12px;")
            dialog._layout_corpo.insertWidget(1 + i, cb)
            checks[m["id"]] = cb

        def _salvar():
            self._dialog_ref = dialog
            self.worker.atualizar_modulos(
                plano_id,
                {mid: cb.isChecked() for mid, cb in checks.items()},
                modulos_atuais,
            )

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _finalizar_modulos(self):
        self._dialog_ref.accept()
        self._carregar()

    def _confirmar_exclusao(self, plano_id):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🗑️  Excluir Plano", parent=self.ui)
        lbl = QLabel("Tem certeza que deseja excluir este plano?")
        lbl.setStyleSheet("color: #ccc; font-size: 12px;")
        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._btn_confirmar.setText("Excluir")
        dialog._btn_confirmar.setStyleSheet(
            """
            QPushButton { background-color: #dc2626; color: white;
                border-radius: 6px; padding: 6px 12px; }
        """
        )

        def _confirmar():
            self._dialog_ref = dialog
            self.worker.excluir(plano_id)

        dialog._btn_confirmar.clicked.connect(_confirmar)
        dialog.exec()

    def _finalizar_exclusao(self, ok):
        if ok:
            self._dialog_ref.accept()
            self._carregar()

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

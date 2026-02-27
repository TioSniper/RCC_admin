from PyQt6.QtWidgets import (
    QTableWidgetItem,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from utils.supabase_admin import (
    criar_modulo,
    editar_modulo,
    ativar_modulo,
    excluir_modulo,
)


class ModulosWorker(QObject):
    salvar_pronto = pyqtSignal(bool, str)
    editar_pronto = pyqtSignal(bool)
    toggle_pronto = pyqtSignal()
    excluir_pronto = pyqtSignal(bool, str)

    def salvar(self, id_, nome, desc):
        ok, msg = criar_modulo(id_, nome, desc)
        self.salvar_pronto.emit(ok, msg)

    def editar(self, mid, nome, desc):
        ok, _ = editar_modulo(mid, nome, desc)
        self.editar_pronto.emit(ok)

    def toggle(self, mid, ativo):
        ativar_modulo(mid, not ativo)
        self.toggle_pronto.emit()

    def excluir(self, mid):
        ok, msg = excluir_modulo(mid)
        self.excluir_pronto.emit(ok, msg)


class ModulosController:

    def __init__(self, ui, svc, realtime=None):
        self.ui = ui
        self._svc = svc

        self.thread = QThread()
        self.worker = ModulosWorker()
        self.worker.moveToThread(self.thread)
        self.worker.salvar_pronto.connect(self._finalizar_salvar)
        self.worker.editar_pronto.connect(self._finalizar_editar)
        self.worker.toggle_pronto.connect(self._carregar)
        self.worker.excluir_pronto.connect(self._finalizar_exclusao)
        self.thread.start()

        svc.modulos_mudou.connect(self._carregar)

        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.btn_novo.clicked.connect(self._dialog_novo_modulo)
        self._carregar()

    def _carregar(self):
        from utils.supabase_admin import listar_modulos

        self._svc.fetch(listar_modulos, self._renderizar)

    def _renderizar(self, modulos):
        if modulos is None:
            return
        tabela = self.ui.tabela
        tabela.setRowCount(0)
        for m in modulos:
            row = tabela.rowCount()
            tabela.insertRow(row)
            ativo = m.get("ativo", True)
            modulo_id = m.get("id", "")

            status = QTableWidgetItem("✅ Ativo" if ativo else "❌ Inativo")
            status.setForeground(Qt.GlobalColor.green if ativo else Qt.GlobalColor.red)
            status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            tabela.setItem(row, 0, self._item(m.get("id", "—")))
            tabela.setItem(row, 1, self._item(m.get("nome", "—")))
            tabela.setItem(row, 2, self._item(m.get("descricao", "—")))
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
            btn_toggle = _btn(
                "Desativar" if ativo else "Ativar", "#dc2626" if ativo else "#16a34a"
            )
            btn_excluir = _btn("Excluir", "#6b7280")

            btn_editar.clicked.connect(
                lambda _, mid=modulo_id, n=m.get("nome", ""), d=m.get(
                    "descricao", ""
                ): self._dialog_editar(mid, n, d)
            )
            btn_toggle.clicked.connect(
                lambda _, mid=modulo_id, a=ativo: self.worker.toggle(mid, a)
            )
            btn_excluir.clicked.connect(
                lambda _, mid=modulo_id, n=m.get("nome", ""): self._dialog_excluir(
                    mid, n
                )
            )

            l.addWidget(btn_editar)
            l.addWidget(btn_toggle)
            l.addWidget(btn_excluir)
            l.addStretch()
            tabela.setCellWidget(row, 4, w)
            tabela.setRowHeight(row, 40)

    def _dialog_novo_modulo(self):
        from telas.dialogs import DialogBase

        dialog = DialogBase("➕  Novo Módulo", parent=self.ui)

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

        inp_id = _campo("ID do módulo:", "ex: monitor_mercado", 0)
        inp_nome = _campo("Nome:", "ex: Monitor de Mercado", 1)
        inp_desc = _campo("Descrição:", "ex: Acompanhe ativos em tempo real", 2)
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.addWidget(lbl_aviso)

        def _salvar():
            mid = inp_id.text().strip()
            nome = inp_nome.text().strip()
            if not mid or not nome:
                lbl_aviso.setText("⚠️  ID e Nome são obrigatórios.")
                return
            self._dialog_ref = dialog
            self._lbl_ref = lbl_aviso
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Salvando...")
            self.worker.salvar(mid, nome, inp_desc.text())

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _finalizar_salvar(self, ok, msg):
        if ok:
            self._dialog_ref.accept()
        else:
            self._lbl_ref.setText(f"⚠️  {msg}")
            self._dialog_ref._btn_confirmar.setEnabled(True)
            self._dialog_ref._btn_confirmar.setText("✓  Confirmar")

    def _dialog_editar(self, mid, nome, descricao):
        from telas.dialogs import DialogBase

        dialog = DialogBase("✏️  Editar Módulo", parent=self.ui)

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
            self.worker.editar(mid, inp_nome.text(), inp_desc.text())

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _finalizar_editar(self, ok):
        if ok:
            self._dialog_ref.accept()

    def _dialog_excluir(self, mid, nome):
        from telas.dialogs import DialogBase

        dialog = DialogBase("🗑️  Excluir Módulo", parent=self.ui)
        lbl = QLabel(
            f"Excluir o módulo <b style='color:#FFD700'>{nome}</b>?<br>"
            "<small>Falha se estiver vinculado a algum plano.</small>"
        )
        lbl.setStyleSheet("color: #ccc; font-size: 12px;")
        lbl.setWordWrap(True)
        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._layout_corpo.insertWidget(1, lbl_aviso)
        dialog._btn_confirmar.setText("Excluir")
        dialog._btn_confirmar.setStyleSheet(
            "QPushButton { background-color: #dc2626; color: white; "
            "border-radius: 6px; padding: 6px 12px; }"
        )

        def _confirmar():
            self._dialog_ref = dialog
            self._lbl_ref = lbl_aviso
            dialog._btn_confirmar.setEnabled(False)
            dialog._btn_confirmar.setText("Excluindo...")
            self.worker.excluir(mid)

        dialog._btn_confirmar.clicked.connect(_confirmar)
        dialog.exec()

    def _finalizar_exclusao(self, ok, msg):
        if ok:
            self._dialog_ref.accept()
        else:
            self._lbl_ref.setText(f"⚠️  {msg}")
            self._dialog_ref._btn_confirmar.setEnabled(True)
            self._dialog_ref._btn_confirmar.setText("Excluir")

    def _item(self, texto):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

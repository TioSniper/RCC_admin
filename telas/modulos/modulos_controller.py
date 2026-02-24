import threading
from PyQt6.QtWidgets import (
    QTableWidgetItem, QWidget, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import (
    listar_modulos, criar_modulo, editar_modulo, ativar_modulo
)


class ModulosWorker(QObject):
    dados_prontos = pyqtSignal(list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.dados_prontos.emit(listar_modulos())


class ModulosController:

    def __init__(self, ui):
        self.ui     = ui
        self.worker = ModulosWorker()
        self.worker.dados_prontos.connect(self._preencher)
        self._conectar_eventos()
        self._carregar()

    def _conectar_eventos(self):
        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.btn_novo.clicked.connect(self._dialog_novo)

    def _carregar(self):
        self.worker.buscar()

    def _preencher(self, modulos: list):
        tabela = self.ui.tabela
        tabela.setRowCount(0)

        for m in modulos:
            row = tabela.rowCount()
            tabela.insertRow(row)

            ativo     = m.get("ativo", True)
            modulo_id = m.get("id", "")

            status_item = QTableWidgetItem("✅ Ativo" if ativo else "❌ Inativo")
            status_item.setForeground(Qt.GlobalColor.green if ativo else Qt.GlobalColor.red)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            tabela.setItem(row, 0, self._item(m.get("id", "—")))
            tabela.setItem(row, 1, self._item(m.get("nome", "—")))
            tabela.setItem(row, 2, self._item(m.get("descricao", "—")))
            tabela.setItem(row, 3, status_item)

            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(4, 2, 4, 2)
            l.setSpacing(4)

            def _btn(txt, cor):
                b = QPushButton(txt)
                b.setFixedHeight(26)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {cor}; color: white;
                        border-radius: 5px; font-size: 11px;
                        border: none; padding: 0 8px;
                    }}
                """)
                return b

            btn_editar = _btn("Editar", "#2563eb")
            btn_toggle = _btn(
                "Desativar" if ativo else "Ativar",
                "#dc2626" if ativo else "#16a34a"
            )

            btn_editar.clicked.connect(
                lambda _, mid=modulo_id, n=m.get("nome", ""), d=m.get("descricao", ""):
                self._dialog_editar(mid, n, d)
            )
            btn_toggle.clicked.connect(
                lambda _, mid=modulo_id, a=ativo: self._toggle(mid, a)
            )

            l.addWidget(btn_editar)
            l.addWidget(btn_toggle)
            l.addStretch()

            tabela.setCellWidget(row, 4, w)
            tabela.setRowHeight(row, 40)

    def _toggle(self, modulo_id: str, ativo: bool):
        ativar_modulo(modulo_id, not ativo)
        self._carregar()

    def _dialog_novo(self):
        from telas.dialogs import DialogBase
        dialog = DialogBase("➕  Novo Módulo", parent=self.ui)

        def _campo(label_txt, placeholder, idx):
            lbl = QLabel(label_txt)
            lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setFixedHeight(36)
            inp.setStyleSheet(dialog._estilo_input())
            dialog._layout_corpo.insertWidget(idx * 2,     lbl)
            dialog._layout_corpo.insertWidget(idx * 2 + 1, inp)
            return inp

        inp_id   = _campo("ID do módulo:", "ex: novo_modulo", 0)
        inp_nome = _campo("Nome:",         "ex: Novo Módulo",  1)
        inp_desc = _campo("Descrição:",    "ex: Descrição...", 2)

        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")
        dialog._layout_corpo.insertWidget(6, lbl_aviso)

        def _salvar():
            if not inp_id.text().strip() or not inp_nome.text().strip():
                lbl_aviso.setText("⚠️  Preencha ID e Nome.")
                return
            ok, msg = criar_modulo(inp_id.text(), inp_nome.text(), inp_desc.text())
            if ok:
                dialog.accept()
                self._carregar()
            else:
                lbl_aviso.setText(f"⚠️  {msg}")

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _dialog_editar(self, modulo_id: str, nome: str, descricao: str):
        from telas.dialogs import DialogBase
        dialog = DialogBase("✏️  Editar Módulo", parent=self.ui)

        def _campo(label_txt, valor, idx):
            lbl = QLabel(label_txt)
            lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
            inp = QLineEdit(valor)
            inp.setFixedHeight(36)
            inp.setStyleSheet(dialog._estilo_input())
            dialog._layout_corpo.insertWidget(idx * 2,     lbl)
            dialog._layout_corpo.insertWidget(idx * 2 + 1, inp)
            return inp

        inp_nome = _campo("Nome:", nome, 0)
        inp_desc = _campo("Descrição:", descricao or "", 1)

        def _salvar():
            ok, _ = editar_modulo(modulo_id, inp_nome.text(), inp_desc.text())
            if ok:
                dialog.accept()
                self._carregar()

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

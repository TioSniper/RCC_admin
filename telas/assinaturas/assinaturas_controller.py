import threading
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QTableWidgetItem, QWidget, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import (
    listar_assinaturas, renovar_assinatura,
    revogar_assinatura, mudar_plano, listar_planos
)


class AssinaturasWorker(QObject):
    dados_prontos = pyqtSignal(list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.dados_prontos.emit(listar_assinaturas())


class AssinaturasController:

    def __init__(self, ui):
        self.ui     = ui
        self._todos = []
        self.worker = AssinaturasWorker()
        self.worker.dados_prontos.connect(self._preencher)
        self._conectar_eventos()
        self._carregar()

    def _conectar_eventos(self):
        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.input_busca.textChanged.connect(self._filtrar)

    def _carregar(self):
        self.worker.buscar()

    def _filtrar(self, texto: str):
        if not texto:
            self._preencher(self._todos)
            return
        filtrados = [
            a for a in self._todos
            if texto.lower() in (a.get("username") or "").lower()
        ]
        self._preencher(filtrados)

    def _preencher(self, assinaturas: list):
        self._todos = assinaturas
        tabela = self.ui.tabela
        tabela.setRowCount(0)

        for a in assinaturas:
            row = tabela.rowCount()
            tabela.insertRow(row)

            username = a.get("username", "—")
            plano    = a.get("plano_nome", "—")
            ativo    = a.get("ativo", False)
            user_id  = a.get("user_id", "")
            criado   = expira = "—"
            dias     = 0

            if a.get("criado_em"):
                try:
                    dt     = datetime.fromisoformat(a["criado_em"].replace("Z", "+00:00"))
                    criado = dt.strftime("%d/%m/%Y")
                except Exception:
                    pass

            if a.get("expira_em"):
                try:
                    dt     = datetime.fromisoformat(a["expira_em"].replace("Z", "+00:00"))
                    expira = dt.strftime("%d/%m/%Y %H:%M")
                    dias   = (dt - datetime.now(timezone.utc)).days
                except Exception:
                    pass

            status_item = QTableWidgetItem("✅ Ativo" if ativo else "❌ Inativo")
            status_item.setForeground(Qt.GlobalColor.green if ativo else Qt.GlobalColor.red)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            dias_item = QTableWidgetItem(f"{max(0, dias)} dias")
            dias_item.setForeground(
                Qt.GlobalColor.red    if dias <= 2 else
                Qt.GlobalColor.yellow if dias <= 7 else
                Qt.GlobalColor.white
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
                b.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {cor}; color: white;
                        border-radius: 5px; font-size: 11px;
                        border: none; padding: 0 8px;
                    }}
                """)
                return b

            btn_renovar = _btn("Renovar", "#16a34a")
            btn_plano   = _btn("Plano",   "#2563eb")
            btn_revogar = _btn("Revogar", "#dc2626")

            btn_renovar.clicked.connect(
                lambda _, uid=user_id: self._dialog_renovar(uid)
            )
            btn_plano.clicked.connect(
                lambda _, uid=user_id: self._dialog_mudar_plano(uid)
            )
            btn_revogar.clicked.connect(
                lambda _, uid=user_id, u=username: self._confirmar_revogar(uid, u)
            )

            l.addWidget(btn_renovar)
            l.addWidget(btn_plano)
            l.addWidget(btn_revogar)
            l.addStretch()

            tabela.setCellWidget(row, 6, w)
            tabela.setRowHeight(row, 40)

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
            ok, msg = renovar_assinatura(user_id, dias)
            if ok:
                dialog.accept()
                self._carregar()
            else:
                lbl_aviso.setText(f"⚠️  {msg}")

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _dialog_mudar_plano(self, user_id: str):
        from telas.dialogs import DialogBase
        dialog = DialogBase("🎯  Mudar Plano", parent=self.ui)

        lbl = QLabel("Selecione o novo plano:")
        lbl.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo = QComboBox()
        combo.setFixedHeight(36)
        combo.setStyleSheet("""
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
        """)
        for p in listar_planos():
            combo.addItem(p["nome"], p["id"])

        dialog._layout_corpo.insertWidget(0, lbl)
        dialog._layout_corpo.insertWidget(1, combo)

        def _salvar():
            ok, msg = mudar_plano(user_id, combo.currentData())
            if ok:
                dialog.accept()
                self._carregar()

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _confirmar_revogar(self, user_id: str, username: str):
        from telas.dialogs import DialogConfirmacao
        dialog = DialogConfirmacao(
            f"Deseja revogar a assinatura de '{username}'?", parent=self.ui
        )
        if dialog.exec():
            revogar_assinatura(user_id)
            self._carregar()

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

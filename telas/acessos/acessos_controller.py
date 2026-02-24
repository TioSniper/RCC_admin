import threading
from datetime import datetime, timezone
from PyQt6.QtWidgets import (
    QTableWidgetItem, QWidget, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import (
    listar_acessos_extras, dar_acesso_extra,
    revogar_acesso_extra, listar_usuarios, listar_modulos
)


class AcessosWorker(QObject):
    dados_prontos = pyqtSignal(list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.dados_prontos.emit(listar_acessos_extras())


class AcessosController:

    def __init__(self, ui):
        self.ui     = ui
        self.worker = AcessosWorker()
        self.worker.dados_prontos.connect(self._preencher)
        self._conectar_eventos()
        self._carregar()

    def _conectar_eventos(self):
        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.btn_novo.clicked.connect(self._dialog_novo_acesso)

    def _carregar(self):
        self.worker.buscar()

    def _preencher(self, acessos: list):
        tabela = self.ui.tabela
        tabela.setRowCount(0)

        for a in acessos:
            row = tabela.rowCount()
            tabela.insertRow(row)

            username  = a.get("username", "—")
            modulo    = a.get("modulo_nome", "—")
            acesso_id = a.get("id", "")
            user_id   = a.get("user_id", "")
            expira    = "—"
            horas     = 0

            if a.get("expira_em"):
                try:
                    dt     = datetime.fromisoformat(a["expira_em"].replace("Z", "+00:00"))
                    expira = dt.strftime("%d/%m/%Y %H:%M")
                    diff   = dt - datetime.now(timezone.utc)
                    horas  = max(0, int(diff.total_seconds() / 3600))
                except Exception:
                    pass

            horas_item = QTableWidgetItem(f"{horas}h restantes")
            horas_item.setForeground(
                Qt.GlobalColor.red if horas <= 2 else Qt.GlobalColor.yellow
            )
            horas_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            tabela.setItem(row, 0, self._item(username))
            tabela.setItem(row, 1, self._item(modulo))
            tabela.setItem(row, 2, self._item(expira))
            tabela.setItem(row, 3, horas_item)

            w = QWidget()
            l = QHBoxLayout(w)
            l.setContentsMargins(4, 2, 4, 2)

            btn_revogar = QPushButton("Revogar")
            btn_revogar.setFixedHeight(26)
            btn_revogar.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_revogar.setStyleSheet("""
                QPushButton {
                    background-color: #dc2626; color: white;
                    border-radius: 5px; font-size: 11px;
                    border: none; padding: 0 8px;
                }
            """)
            btn_revogar.clicked.connect(
                lambda _, aid=acesso_id, uid=user_id: self._confirmar_revogar(aid, uid)
            )

            l.addWidget(btn_revogar)
            l.addStretch()
            tabela.setCellWidget(row, 4, w)
            tabela.setRowHeight(row, 40)

    def _dialog_novo_acesso(self):
        from telas.dialogs import DialogBase
        dialog = DialogBase("➕  Novo Acesso Extra", parent=self.ui)

        estilo_combo = """
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

        lbl_user = QLabel("Usuário:")
        lbl_user.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo_user = QComboBox()
        combo_user.setFixedHeight(36)
        combo_user.setStyleSheet(estilo_combo)
        for u in listar_usuarios():
            combo_user.addItem(u.get("username", u["id"]), u["id"])

        lbl_mod = QLabel("Módulo:")
        lbl_mod.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        combo_mod = QComboBox()
        combo_mod.setFixedHeight(36)
        combo_mod.setStyleSheet(estilo_combo)
        for m in listar_modulos():
            combo_mod.addItem(m["nome"], m["id"])

        lbl_horas = QLabel("Duração em horas:")
        lbl_horas.setStyleSheet("color: #aaa; font-size: 11px; font-weight: bold;")
        inp_horas = QLineEdit("24")
        inp_horas.setFixedHeight(36)
        inp_horas.setStyleSheet(dialog._estilo_input())

        lbl_aviso = QLabel("")
        lbl_aviso.setStyleSheet("color: #ff5c5c; font-size: 11px;")

        for i, w in enumerate([lbl_user, combo_user, lbl_mod, combo_mod,
                                lbl_horas, inp_horas, lbl_aviso]):
            dialog._layout_corpo.insertWidget(i, w)

        def _salvar():
            try:
                horas = int(inp_horas.text().strip())
                if horas <= 0:
                    raise ValueError
            except ValueError:
                lbl_aviso.setText("⚠️  Informe um número válido de horas.")
                return
            ok, msg = dar_acesso_extra(
                combo_user.currentData(), combo_mod.currentData(), horas
            )
            if ok:
                dialog.accept()
                self._carregar()
            else:
                lbl_aviso.setText(f"⚠️  {msg}")

        dialog._btn_confirmar.clicked.connect(_salvar)
        dialog.exec()

    def _confirmar_revogar(self, acesso_id: str, user_id: str):
        from telas.dialogs import DialogConfirmacao
        dialog = DialogConfirmacao("Deseja revogar este acesso extra?", parent=self.ui)
        if dialog.exec():
            revogar_acesso_extra(acesso_id, user_id)
            self._carregar()

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

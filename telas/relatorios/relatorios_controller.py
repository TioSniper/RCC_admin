import threading
from datetime import datetime, timezone
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import listar_expirando, listar_usuarios


class RelatoriosWorker(QObject):
    dados_prontos = pyqtSignal(list, list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        expirando = listar_expirando(7)
        usuarios  = listar_usuarios()
        self.dados_prontos.emit(expirando, usuarios[:10])


class RelatoriosController:

    def __init__(self, ui):
        self.ui     = ui
        self.worker = RelatoriosWorker()
        self.worker.dados_prontos.connect(self._atualizar)
        self.ui.btn_refresh.clicked.connect(self._carregar)
        self._carregar()

    def _carregar(self):
        self.worker.buscar()

    def _atualizar(self, expirando: list, recentes: list):
        self._preencher_expirando(expirando)
        self._preencher_recentes(recentes)

    def _preencher_expirando(self, dados: list):
        t = self.ui.tabela_expirando
        t.setRowCount(0)
        for d in dados:
            row = t.rowCount()
            t.insertRow(row)
            username = d.get("username", "—")
            plano    = d.get("plano_nome", "—")
            expira   = "—"
            dias     = 0
            if d.get("expira_em"):
                try:
                    dt     = datetime.fromisoformat(d["expira_em"].replace("Z", "+00:00"))
                    expira = dt.strftime("%d/%m/%Y")
                    dias   = (dt - datetime.now(timezone.utc)).days
                except Exception:
                    pass
            t.setItem(row, 0, self._item(username))
            t.setItem(row, 1, self._item(plano))
            t.setItem(row, 2, self._item(expira))
            item_dias = QTableWidgetItem(f"{dias} dias")
            item_dias.setForeground(
                Qt.GlobalColor.red if dias <= 2 else Qt.GlobalColor.yellow
            )
            item_dias.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            t.setItem(row, 3, item_dias)

    def _preencher_recentes(self, usuarios: list):
        t = self.ui.tabela_recentes
        t.setRowCount(0)
        for u in usuarios:
            row = t.rowCount()
            t.insertRow(row)
            ass    = u.get("assinatura") or {}
            plano  = ass.get("plano_nome", "Sem plano")
            criado = "—"
            if u.get("criado_em"):
                try:
                    dt     = datetime.fromisoformat(u["criado_em"].replace("Z", "+00:00"))
                    criado = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass
            t.setItem(row, 0, self._item(u.get("username", "—")))
            t.setItem(row, 1, self._item(plano))
            t.setItem(row, 2, self._item(criado))

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

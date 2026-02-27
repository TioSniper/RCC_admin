from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt


class LogsController:

    def __init__(self, ui, svc):
        self.ui = ui
        self._svc = svc

        svc.logs_mudou.connect(self._carregar)

        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.input_busca.textChanged.connect(self._filtrar)
        self._todos = []
        self._carregar()

    def _carregar(self):
        from utils.supabase_admin import listar_logs

        self._svc.fetch(lambda: listar_logs(200), self._renderizar)

    def _filtrar(self, texto):
        filtrados = (
            [
                l
                for l in self._todos
                if texto.lower() in (l.get("acao") or "").lower()
                or texto.lower() in (l.get("username") or "").lower()
            ]
            if texto
            else self._todos
        )
        self._preencher(filtrados)

    def _renderizar(self, logs):
        if logs is None:
            return
        self._todos = logs
        self._preencher(logs)

    def _preencher(self, logs):
        from datetime import datetime, timezone

        tabela = self.ui.tabela
        tabela.setRowCount(0)
        for l in logs:
            row = tabela.rowCount()
            tabela.insertRow(row)
            criado = "—"
            try:
                dt = datetime.fromisoformat(
                    l.get("criado_em", "").replace("Z", "+00:00")
                )
                criado = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
            tabela.setItem(row, 0, self._item(criado))
            tabela.setItem(row, 1, self._item(l.get("acao", "—")))
            tabela.setItem(row, 2, self._item(l.get("username", "—")))
            tabela.setItem(row, 3, self._item(str(l.get("detalhes", "") or "")))
            tabela.setRowHeight(row, 36)

    def _item(self, texto):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

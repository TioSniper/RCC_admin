import json
from datetime import datetime
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt


class LogsController:

    def __init__(self, ui, store):
        self.ui = ui
        self._store = store
        self._todos = []

        store.logs_atualizados.connect(self._renderizar)
        store.carregamento_completo.connect(self._renderizar)

        self.ui.btn_refresh.clicked.connect(lambda: self._store.carregar_tudo())
        self.ui.input_busca.textChanged.connect(self._filtrar)

        if store.logs:
            self._renderizar()

    def _filtrar(self, texto: str):
        if not texto:
            self._preencher(self._store.logs)
            return
        filtrados = [
            l
            for l in self._store.logs
            if texto.lower() in l.get("acao", "").lower()
            or texto.lower() in (l.get("username") or "").lower()
        ]
        self._preencher(filtrados)

    def _renderizar(self):
        self._preencher(self._store.logs)

    def _preencher(self, logs: list):
        t = self.ui.tabela
        t.setRowCount(0)
        for l in logs:
            row = t.rowCount()
            t.insertRow(row)
            data = "—"
            if l.get("criado_em"):
                try:
                    dt = datetime.fromisoformat(l["criado_em"].replace("Z", "+00:00"))
                    data = dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass
            detalhes = json.dumps(l.get("detalhes", {}), ensure_ascii=False)
            t.setItem(row, 0, self._item(data))
            t.setItem(row, 1, self._item(l.get("acao", "—")))
            t.setItem(row, 2, self._item(l.get("username") or "—"))
            t.setItem(row, 3, self._item(detalhes))
            t.setRowHeight(row, 36)

    def _item(self, texto: str) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

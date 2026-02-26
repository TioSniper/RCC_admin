import threading
import json
from datetime import datetime
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from utils.supabase_admin import listar_logs


class LogsWorker(QObject):
    dados_prontos = pyqtSignal(list)

    def buscar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        self.dados_prontos.emit(listar_logs(200))


class LogsController:

    def __init__(self, ui, realtime=None):
        self.ui = ui
        self._todos = []
        self.worker = LogsWorker()
        self.worker.dados_prontos.connect(self._preencher)

        if realtime:
            realtime.logs_mudou.connect(lambda _: self._carregar())

        self.ui.btn_refresh.clicked.connect(self._carregar)
        self.ui.input_busca.textChanged.connect(self._filtrar)
        self._carregar()

    def _carregar(self):
        self.worker.buscar()

    def _filtrar(self, texto: str):
        if not texto:
            self._preencher(self._todos)
            return
        filtrados = [
            l
            for l in self._todos
            if texto.lower() in l.get("acao", "").lower()
            or texto.lower() in (l.get("username") or "").lower()
        ]
        self._preencher(filtrados)

    def _preencher(self, logs: list):
        self._todos = logs
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

from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtCore import Qt, QTimer


class LogsController:

    def __init__(self, ui, svc):
        self.ui = ui
        self._svc = svc

        # Debounce — corrige bug do QTimer com args do PyQt6
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._carregar)

        def _iniciar(*args, **kwargs):
            from PyQt6.QtCore import QMetaObject, Qt

            QMetaObject.invokeMethod(
                self._timer, "start", Qt.ConnectionType.QueuedConnection
            )

        svc.logs_mudou.connect(_iniciar)

        # Atualiza também quando um novo log é gravado localmente
        try:
            from utils.logs_manager import _logs as _lm

            _lm.on_novo_log(_iniciar)
        except Exception:
            pass

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
                or texto.lower() in str(l.get("detalhes") or "").lower()
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

            # Extrai username dos detalhes se não estiver no campo direto
            username = l.get("username") or ""
            if not username:
                detalhes = l.get("detalhes") or {}
                if isinstance(detalhes, dict):
                    username = detalhes.get("username", "—")

            # Formata detalhes removendo o username para não duplicar
            detalhes = l.get("detalhes") or {}
            if isinstance(detalhes, dict):
                det_exibir = {k: v for k, v in detalhes.items() if k != "username"}
                det_str = (
                    ", ".join(f"{k}: {v}" for k, v in det_exibir.items())
                    if det_exibir
                    else "—"
                )
            else:
                det_str = str(detalhes) if detalhes else "—"

            tabela.setItem(row, 0, self._item(criado))
            tabela.setItem(row, 1, self._item(l.get("acao", "—")))
            tabela.setItem(row, 2, self._item(username))
            tabela.setItem(row, 3, self._item(det_str))
            tabela.setRowHeight(row, 36)

    def _item(self, texto):
        item = QTableWidgetItem(str(texto))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

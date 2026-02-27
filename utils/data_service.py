"""
DataService — sinais para os controllers e fetch thread-safe.
"""

import threading
from PyQt6.QtCore import QObject, pyqtSignal


class _FetchWorker(QObject):
    """Executa uma função em thread e entrega o resultado via sinal Qt."""

    _pronto = pyqtSignal(object)

    def __init__(self, fn, callback):
        super().__init__()
        self._fn = fn
        # Conecta com QueuedConnection — callback sempre roda na thread principal
        self._pronto.connect(
            callback,
            type=__import__(
                "PyQt6.QtCore", fromlist=["Qt"]
            ).Qt.ConnectionType.QueuedConnection,
        )

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            resultado = self._fn()
        except Exception as e:
            print(f"[DataService] Erro no fetch: {e}")
            resultado = None
        self._pronto.emit(resultado)


class DataService(QObject):
    usuarios_mudou = pyqtSignal()
    assinaturas_mudou = pyqtSignal()
    planos_mudou = pyqtSignal()
    modulos_mudou = pyqtSignal()
    logs_mudou = pyqtSignal()
    solicitacoes_mudou = pyqtSignal()
    sessoes_mudou = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._workers = []

    def fetch(self, fn, callback):
        """Executa fn() em thread separada, chama callback(resultado) na thread principal."""
        w = _FetchWorker(fn, callback)
        self._workers.append(w)
        # Limpa workers antigos
        self._workers = self._workers[-50:]
        w.start()
        return w


_service: DataService | None = None


def obter_service() -> DataService:
    global _service
    if _service is None:
        _service = DataService()
    return _service

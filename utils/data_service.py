"""
DataService — sinais para os controllers e fetch thread-safe.
"""

import threading
from PyQt6.QtCore import QObject, pyqtSignal, Qt


class _FetchWorker(QObject):
    _pronto = pyqtSignal(object)

    def __init__(self, fn, callback):
        super().__init__()
        self._fn = fn
        self._pronto.connect(callback, type=Qt.ConnectionType.QueuedConnection)

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
        w = _FetchWorker(fn, callback)
        self._workers.append(w)
        self._workers = self._workers[-50:]
        w.start()
        return w

    # ── métodos de disparo com debug ──────────────────────────
    def _emitir(self, sinal, nome):
        print(f"[DataService] disparando {nome}")
        sinal.emit()

    def emitir_usuarios(self):
        self._emitir(self.usuarios_mudou, "usuarios_mudou")

    def emitir_assinaturas(self):
        self._emitir(self.assinaturas_mudou, "assinaturas_mudou")

    def emitir_planos(self):
        self._emitir(self.planos_mudou, "planos_mudou")

    def emitir_modulos(self):
        self._emitir(self.modulos_mudou, "modulos_mudou")

    def emitir_logs(self):
        self._emitir(self.logs_mudou, "logs_mudou")

    def emitir_solicitacoes(self):
        self._emitir(self.solicitacoes_mudou, "solicitacoes_mudou")

    def emitir_sessoes(self):
        self._emitir(self.sessoes_mudou, "sessoes_mudou")


_service: DataService | None = None


def obter_service() -> DataService:
    global _service
    if _service is None:
        _service = DataService()
    return _service

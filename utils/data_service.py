"""
DataService — sinais para os controllers e fetch thread-safe.
"""

import threading
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QMetaObject


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

    # ── métodos de disparo thread-safe via QueuedConnection ───
    def _emitir(self, nome_sinal, nome_log):
        """Emite sinal sempre na thread principal via invokeMethod."""
        print(f"[DataService] disparando {nome_log}")
        QMetaObject.invokeMethod(self, nome_sinal, Qt.ConnectionType.QueuedConnection)

    def emitir_usuarios(self):
        self._emitir("usuarios_mudou", "usuarios_mudou")

    def emitir_assinaturas(self):
        self._emitir("assinaturas_mudou", "assinaturas_mudou")

    def emitir_planos(self):
        self._emitir("planos_mudou", "planos_mudou")

    def emitir_modulos(self):
        self._emitir("modulos_mudou", "modulos_mudou")

    def emitir_logs(self):
        self._emitir("logs_mudou", "logs_mudou")

    def emitir_solicitacoes(self):
        self._emitir("solicitacoes_mudou", "solicitacoes_mudou")

    def emitir_sessoes(self):
        self._emitir("sessoes_mudou", "sessoes_mudou")


_service: DataService | None = None


def obter_service() -> DataService:
    global _service
    if _service is None:
        _service = DataService()
    return _service

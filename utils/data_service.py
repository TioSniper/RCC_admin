"""
DataService — arquitetura query-on-demand.

O Realtime avisa que algo mudou → debounce 300ms → 1 query por aba → renderiza.
Sem cache em memória, sem risco de inconsistência, sempre dado real.
"""

import threading
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class DataService(QObject):
    """
    Centraliza os sinais do Realtime e expõe métodos de fetch.
    Cada controller conecta apenas os sinais relevantes para sua aba.
    """

    # ── Sinais por domínio ─────────────────────────────────────
    usuarios_mudou = pyqtSignal()
    assinaturas_mudou = pyqtSignal()
    planos_mudou = pyqtSignal()
    modulos_mudou = pyqtSignal()
    logs_mudou = pyqtSignal()
    solicitacoes_mudou = pyqtSignal()
    sessoes_mudou = pyqtSignal()

    def __init__(self):
        super().__init__()

    # ── Fetch assíncrono genérico ──────────────────────────────
    def fetch(self, fn, callback):
        """
        Executa fn() em thread separada e entrega resultado via callback
        na thread principal usando um sinal interno.
        """
        worker = _FetchWorker(fn)
        worker.pronto.connect(callback)
        worker.executar()
        return worker  # mantém referência viva


class _FetchWorker(QObject):
    pronto = pyqtSignal(object)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def executar(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            resultado = self._fn()
            self.pronto.emit(resultado)
        except Exception as e:
            print(f"[DataService] Erro no fetch: {e}")
            self.pronto.emit(None)


def _make_debounced_loader(sinal_origem, sinal_destino):
    """
    Conecta sinal_origem ao sinal_destino com debounce de 300ms.
    Usado no principal_controller para mapear sinais do Realtime.
    """
    timer = QTimer()
    timer.setSingleShot(True)
    timer.setInterval(300)
    timer.timeout.connect(sinal_destino.emit)
    sinal_origem.connect(timer.start)
    return timer  # mantém referência viva


# ── Instância global ───────────────────────────────────────────
_service: DataService | None = None


def obter_service() -> DataService:
    global _service
    if _service is None:
        _service = DataService()
    return _service

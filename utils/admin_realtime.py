import asyncio
import json
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt


class AdminRealtime(QObject):
    solicitacoes_mudou = pyqtSignal(dict)
    usuarios_mudou = pyqtSignal(dict)
    assinaturas_mudou = pyqtSignal(dict)
    logs_mudou = pyqtSignal(dict)
    planos_mudou = pyqtSignal(dict)
    modulos_mudou = pyqtSignal(dict)
    sessoes_mudou = pyqtSignal(dict)
    planos_modulos_mudou = pyqtSignal(dict)
    acessos_mudou = pyqtSignal(dict)  # mantido por compatibilidade

    _sinal_tabela = pyqtSignal(str, dict)  # (tabela, payload) — thread-safe

    _TABELAS = {
        "solicitacoes": "solicitacoes_mudou",
        "perfis": "usuarios_mudou",
        "assinaturas": "assinaturas_mudou",
        "planos": "planos_mudou",
        "modulos": "modulos_mudou",
        "sessoes_ativas": "sessoes_mudou",
        "planos_modulos": "planos_modulos_mudou",
    }

    def __init__(self, supabase_url: str, supabase_key: str, anon_key: str = ""):
        super().__init__()
        self._url = supabase_url
        self._key = supabase_key
        self._anon = anon_key or supabase_key
        self._rodando = False
        self._loop = None

        ws = supabase_url.replace("https://", "wss://").replace("http://", "ws://")
        self._ws_url = f"{ws}/realtime/v1/websocket?apikey={self._anon}&vsn=1.0.0"

        # Debounce por tabela — agrupa rajadas de eventos
        self._timers: dict[str, QTimer] = {}
        self._payloads: dict[str, dict] = {}

        for tabela in self._TABELAS:
            t = QTimer()
            t.setSingleShot(True)
            t.setInterval(200)
            t.timeout.connect(lambda tb=tabela: self._emitir(tb))
            self._timers[tabela] = t

        # QueuedConnection: slot roda na thread principal (Qt-safe)
        self._sinal_tabela.connect(
            self._on_evento,
            type=Qt.ConnectionType.QueuedConnection,
        )

    def _on_evento(self, tabela: str, payload: dict):
        """Sempre na thread principal — seguro iniciar QTimer aqui."""
        self._payloads[tabela] = payload
        if tabela in self._timers:
            self._timers[tabela].start()

    def iniciar(self):
        self._rodando = True
        t = threading.Thread(target=self._run_loop, daemon=True, name="RealTimeThread")
        t.start()
        print("[Realtime] Iniciando...")

    def parar(self):
        self._rodando = False
        for t in self._timers.values():
            t.stop()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        print("[Realtime] Parado.")

    def _run_loop(self):
        # Loop asyncio próprio — isolado do Qt
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._escutar())
        except Exception as e:
            if self._rodando:
                print(f"[Realtime] Loop encerrado: {e}")
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            if not self._loop.is_closed():
                self._loop.close()

    async def _escutar(self):
        import websockets

        while self._rodando:
            try:
                await self._conectar(websockets)
            except Exception as e:
                if self._rodando:
                    print(f"[Realtime] Reconectando em 5s... ({type(e).__name__}: {e})")
                    await asyncio.sleep(5)

    async def _conectar(self, websockets):
        async with websockets.connect(
            self._ws_url,
            additional_headers={"apikey": self._anon},
            ping_interval=25,
            ping_timeout=10,
        ) as ws:
            print("[Realtime] Conectado")
            ref = 1

            await ws.send(
                json.dumps(
                    {
                        "topic": "realtime:admin",
                        "event": "phx_join",
                        "payload": {
                            "config": {
                                "postgres_changes": [
                                    {"event": "*", "schema": "public", "table": t}
                                    for t in self._TABELAS
                                ]
                            }
                        },
                        "ref": str(ref),
                    }
                )
            )
            ref += 1

            while self._rodando:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=25)
                    msg = json.loads(raw)
                    self._processar(msg)
                except asyncio.TimeoutError:
                    # Heartbeat manual
                    await ws.send(
                        json.dumps(
                            {
                                "topic": "phoenix",
                                "event": "heartbeat",
                                "payload": {},
                                "ref": str(ref),
                            }
                        )
                    )
                    ref += 1
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self._rodando:
                        print(f"[Realtime] Erro recv: {type(e).__name__}: {e}")
                    break

    def _processar(self, msg: dict):
        event = msg.get("event", "")
        payload = msg.get("payload", {})

        if event != "postgres_changes":
            return

        data = payload.get("data", {})
        tabela = data.get("table")
        if not tabela or tabela not in self._TABELAS:
            return

        print(f"[Realtime] {data.get('type','?')} em: {tabela}")

        p = {
            "type": data.get("type"),
            "record": data.get("record", {}),
            "old_record": data.get("old_record", {}),
        }

        # Emite via sinal thread-safe — chega na thread principal via QueuedConnection
        self._sinal_tabela.emit(tabela, p)

    def _emitir(self, tabela: str):
        nome = self._TABELAS.get(tabela)
        sinal = getattr(self, nome, None)
        if sinal:
            sinal.emit(self._payloads.get(tabela, {}))


# ── Instância global ───────────────────────────────────────────

_instancia: AdminRealtime | None = None


def iniciar_realtime(
    supabase_url: str, supabase_key: str, anon_key: str = ""
) -> AdminRealtime:
    global _instancia
    if _instancia is None:
        _instancia = AdminRealtime(supabase_url, supabase_key, anon_key)
        _instancia.iniciar()
    return _instancia


def obter_realtime() -> AdminRealtime | None:
    return _instancia

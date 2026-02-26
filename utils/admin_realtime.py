import asyncio
import json
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt


class AdminRealtime(QObject):
    solicitacoes_mudou = pyqtSignal(dict)
    usuarios_mudou = pyqtSignal(dict)
    assinaturas_mudou = pyqtSignal(dict)
    acessos_mudou = pyqtSignal(dict)
    logs_mudou = pyqtSignal(dict)
    planos_mudou = pyqtSignal(dict)
    modulos_mudou = pyqtSignal(dict)
    sessoes_mudou = pyqtSignal(dict)
    planos_modulos_mudou = pyqtSignal(dict)

    # Sinal interno por tabela — emitido da thread asyncio, dispara timer na thread principal
    _evento_recebido = pyqtSignal(str)

    _TABELAS = {
        "solicitacoes": "solicitacoes_mudou",
        "perfis": "usuarios_mudou",
        "assinaturas": "assinaturas_mudou",
        "acessos_extras": "acessos_mudou",
        "logs_admin": "logs_mudou",
        "planos": "planos_mudou",
        "modulos": "modulos_mudou",
        "sessoes_ativas": "sessoes_mudou",
        "planos_modulos": "planos_modulos_mudou",
    }

    def __init__(self, supabase_url: str, supabase_key: str, anon_key: str = ""):
        super().__init__()
        self._key = supabase_key  # service_role — para operações REST
        self._anon_key = anon_key or supabase_key  # anon — para websocket Realtime
        self._rodando = False
        self._loop = None

        ws = supabase_url.replace("https://", "wss://").replace("http://", "ws://")
        # Websocket usa anon_key — service_role não é aceita pelo Realtime
        self._ws_url = f"{ws}/realtime/v1/websocket?apikey={self._anon_key}&vsn=1.0.0"

        self._timers: dict[str, QTimer] = {}
        self._payloads: dict[str, dict] = {}

        for tabela in self._TABELAS:
            t = QTimer()
            t.setSingleShot(True)
            t.setInterval(150)
            t.timeout.connect(lambda tb=tabela: self._emitir(tb))
            self._timers[tabela] = t

        # QueuedConnection garante que o slot rode na thread principal
        self._evento_recebido.connect(
            self._on_evento_recebido,
            type=Qt.ConnectionType.QueuedConnection,
        )

    def _on_evento_recebido(self, tabela: str):
        """Roda sempre na thread principal — seguro para iniciar QTimer."""
        if tabela in self._timers:
            self._timers[tabela].start()

    def iniciar(self):
        self._rodando = True
        threading.Thread(target=self._run_loop, daemon=True).start()
        print("[Realtime] Iniciando...")

    def parar(self):
        self._rodando = False
        for t in self._timers.values():
            t.stop()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._cancelar_tasks)
        print("[Realtime] Parado.")

    def _cancelar_tasks(self):
        for t in asyncio.all_tasks(self._loop):
            t.cancel()
        self._loop.stop()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._escutar())
        except (asyncio.CancelledError, RuntimeError):
            pass
        except Exception as e:
            if self._rodando:
                print(f"[Realtime] Erro fatal: {e}")
        finally:
            try:
                pending = asyncio.all_tasks(self._loop)
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            self._loop.close()

    async def _escutar(self):
        import websockets

        while self._rodando:
            try:
                await self._conectar(websockets)
            except Exception as e:
                if self._rodando:
                    print(f"[Realtime] Reconectando em 5s... ({e})")
                    await asyncio.sleep(5)

    async def _conectar(self, websockets):
        async with websockets.connect(
            self._ws_url,
            additional_headers={"apikey": self._anon_key},
            ping_interval=30,
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
                            },
                            # Sem access_token — políticas RLS with (true) permitem anon
                        },
                        "ref": str(ref),
                    }
                )
            )
            ref += 1

            while self._rodando:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=30)
                    msg = json.loads(raw)
                    self._processar(msg)
                except asyncio.TimeoutError:
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
                except Exception as e:
                    if self._rodando:
                        print(f"[Realtime] Erro recv: {e}")
                    break

    def _processar(self, msg: dict):
        event = msg.get("event", "")
        payload = msg.get("payload", {})

        # DEBUG — loga tudo exceto heartbeat
        if event not in ("heartbeat",):
            print(
                f"[Realtime DEBUG] event={event} | topic={msg.get('topic','?')} | tabela={payload.get('data', {}).get('table', '?')} | payload={json.dumps(payload)[:300]}"
            )

        if event not in ("postgres_changes",):
            return

        data = payload.get("data", {})
        tabela = data.get("table")
        if not tabela or tabela not in self._TABELAS:
            return

        print(f"[Realtime] {data.get('type','?')} em: {tabela}")

        self._payloads[tabela] = {
            "type": data.get("type"),
            "record": data.get("record", {}),
            "old_record": data.get("old_record", {}),
        }

        # Emite da thread asyncio — QueuedConnection despacha para thread principal
        self._evento_recebido.emit(tabela)

    def _emitir(self, tabela: str):
        nome_sinal = self._TABELAS.get(tabela)
        sinal = getattr(self, nome_sinal, None)
        payload = self._payloads.get(tabela, {})
        if sinal:
            sinal.emit(payload)


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

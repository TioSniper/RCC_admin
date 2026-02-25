"""
Gerenciador centralizado de Realtime para o Admin.
Uma única conexão websocket escuta todas as tabelas
e distribui eventos para os controllers via sinais Qt.
"""

import asyncio
import json
import threading
from PyQt6.QtCore import QObject, pyqtSignal


class AdminRealtime(QObject):
    # Sinais por tabela
    solicitacoes_mudou = pyqtSignal()
    usuarios_mudou = pyqtSignal()
    assinaturas_mudou = pyqtSignal()
    acessos_mudou = pyqtSignal()
    logs_mudou = pyqtSignal()
    planos_mudou = pyqtSignal()
    modulos_mudou = pyqtSignal()

    _TABELAS = {
        "solicitacoes": "solicitacoes_mudou",
        "perfis": "usuarios_mudou",
        "assinaturas": "assinaturas_mudou",
        "acessos_extras": "acessos_mudou",
        "logs_admin": "logs_mudou",
        "planos": "planos_mudou",
        "modulos": "modulos_mudou",
    }

    def __init__(self, supabase_url: str, supabase_key: str):
        super().__init__()
        self._key = supabase_key
        self._rodando = False
        self._loop = None

        ws_url = supabase_url.replace("https://", "wss://").replace("http://", "ws://")
        self._ws_url = f"{ws_url}/realtime/v1/websocket?apikey={supabase_key}&vsn=1.0.0"

    def iniciar(self):
        self._rodando = True
        threading.Thread(target=self._run_loop, daemon=True).start()
        print("[Realtime] Iniciando...")

    def parar(self):
        self._rodando = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._escutar())
        except Exception as e:
            print(f"[Realtime] Erro fatal: {e}")
        finally:
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
            additional_headers={"apikey": self._key},
            ping_interval=30,
            ping_timeout=10,
        ) as ws:
            print("[Realtime] Conectado")
            ref = 1

            # Inscreve em todas as tabelas num canal único
            await ws.send(
                json.dumps(
                    {
                        "topic": "realtime:public",
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
                    print(f"[Realtime] Erro recv: {e}")
                    break

    def _processar(self, msg: dict):
        event = msg.get("event", "")
        payload = msg.get("payload", {})

        if event in ("phx_reply", "phx_close", "heartbeat", "presence_state", "system"):
            return

        # Extrai tabela
        tabela = None
        if event == "postgres_changes":
            tabela = payload.get("data", {}).get("table")
        elif payload.get("table"):
            tabela = payload.get("table")

        if not tabela:
            return

        nome_sinal = self._TABELAS.get(tabela)
        if not nome_sinal:
            return

        print(f"[Realtime] Mudança em: {tabela}")
        sinal = getattr(self, nome_sinal, None)
        if sinal:
            sinal.emit()


# ── Instância global ───────────────────────────────────────────

_instancia: AdminRealtime | None = None


def iniciar_realtime(supabase_url: str, supabase_key: str) -> AdminRealtime:
    global _instancia
    if _instancia is None:
        _instancia = AdminRealtime(supabase_url, supabase_key)
        _instancia.iniciar()
    return _instancia


def obter_realtime() -> AdminRealtime | None:
    return _instancia

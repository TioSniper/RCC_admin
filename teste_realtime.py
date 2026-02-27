"""
Teste isolado do Realtime — rode direto no terminal:
python test_realtime.py

Coloque na raiz do projeto RCC_admin.
"""

import asyncio
import json
import os
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("SUPABASE_URL")
SVC_KEY = os.getenv("SUPABASE_SERVICE_KEY")
ANON_KEY = os.getenv("SUPABASE_ANON_KEY", SVC_KEY)

TABELAS = [
    "perfis",
    "assinaturas",
    "planos",
    "modulos",
    "sessoes_ativas",
    "solicitacoes",
]


async def main():
    import websockets

    ws_url = (
        URL.replace("https://", "wss://")
        + f"/realtime/v1/websocket?apikey={ANON_KEY}&vsn=1.0.0"
    )
    print(f"Conectando em: {ws_url[:60]}...")

    async with websockets.connect(
        ws_url,
        additional_headers={"apikey": ANON_KEY},
        ping_interval=30,
    ) as ws:
        print("✅ Conectado!\n")

        await ws.send(
            json.dumps(
                {
                    "topic": "realtime:test",
                    "event": "phx_join",
                    "payload": {
                        "config": {
                            "postgres_changes": [
                                {"event": "*", "schema": "public", "table": t}
                                for t in TABELAS
                            ]
                        }
                    },
                    "ref": "1",
                }
            )
        )
        print("📡 Inscrito nas tabelas. Aguardando eventos...")
        print("   Faça uma alteração no banco e veja se aparece aqui.\n")

        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=30)
                msg = json.loads(raw)
                ev = msg.get("event", "")
                data = msg.get("payload", {}).get("data", {})
                if ev == "postgres_changes":
                    print(
                        f"🔔 EVENTO: {data.get('type')} em {data.get('table')} → {json.dumps(data.get('record',{}))[:100]}"
                    )
                elif ev == "phx_reply":
                    status = msg.get("payload", {}).get("status", "")
                    print(
                        f"{'✅' if status=='ok' else '❌'} phx_reply: {status} — {json.dumps(msg.get('payload',{}))[:200]}"
                    )
                else:
                    print(f"ℹ️  {ev}")
            except asyncio.TimeoutError:
                await ws.send(
                    json.dumps(
                        {
                            "topic": "phoenix",
                            "event": "heartbeat",
                            "payload": {},
                            "ref": "hb",
                        }
                    )
                )
                print("💓 heartbeat")


asyncio.run(main())

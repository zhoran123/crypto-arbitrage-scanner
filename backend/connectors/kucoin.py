import asyncio
import json
import time

import requests
import websockets

from .base import BaseConnector


CONN_BATCH = 100
SUB_BATCH = 20
SUB_DELAY = 0.05


class KucoinConnector(BaseConnector):
    name = "kucoin"

    def get_fee(self):
        return 0.06

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        if symbol.startswith("BTC"):
            symbol = symbol.replace("BTC", "XBT", 1)
        return symbol + "M"

    @staticmethod
    def _restore_symbol(symbol: str) -> str:
        if symbol.endswith("M"):
            symbol = symbol[:-1]
        return symbol.replace("XBT", "BTC", 1)

    def _get_ws_token(self):
        response = requests.post(
            "https://api-futures.kucoin.com/api/v1/bullet-public",
            timeout=10,
        )
        data = response.json().get("data", {})
        token = data.get("token", "")
        servers = data.get("instanceServers", [])
        if not servers or not token:
            raise RuntimeError("KuCoin did not return a websocket token")

        server = servers[0]
        return server["endpoint"], token, server.get("pingInterval", 18000)

    async def connect(self, symbols: list[str]):
        batches = [symbols[i:i + CONN_BATCH] for i in range(0, len(symbols), CONN_BATCH)]
        print(f"[KuCoin] {len(symbols)} pairs -> {len(batches)} connections")
        await asyncio.gather(*[
            self._connect_batch(batch, index + 1, len(batches))
            for index, batch in enumerate(batches)
        ])

    async def _connect_batch(self, symbols: list[str], batch_num: int, total: int):
        while True:
            try:
                endpoint, token, ping_ms = self._get_ws_token()
                connect_id = int(time.time() * 1000)
                url = f"{endpoint}?token={token}&connectId={connect_id}"

                async with websockets.connect(url) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=10)

                    for index in range(0, len(symbols), SUB_BATCH):
                        chunk = symbols[index:index + SUB_BATCH]
                        topic = ",".join(
                            f"/contractMarket/tickerV2:{self._convert_symbol(symbol)}"
                            for symbol in chunk
                        )
                        await ws.send(json.dumps({
                            "id": int(time.time() * 1000),
                            "type": "subscribe",
                            "topic": topic,
                            "privateChannel": False,
                            "response": True,
                        }))
                        await asyncio.sleep(SUB_DELAY)

                    print(f"[KuCoin] connected batch {batch_num}/{total} ({len(symbols)} pairs)")

                    ping_sec = ping_ms / 1000 / 2

                    async def pinger():
                        while True:
                            await asyncio.sleep(ping_sec)
                            try:
                                await ws.send(json.dumps({
                                    "id": int(time.time() * 1000),
                                    "type": "ping",
                                }))
                            except Exception:
                                break

                    ping_task = asyncio.create_task(pinger())

                    try:
                        async for raw in ws:
                            data = json.loads(raw)

                            if data.get("type") == "error":
                                print(f"[KuCoin] subscription/message error batch {batch_num}: {data}")
                                continue

                            if data.get("type") != "message":
                                continue

                            topic = data.get("topic", "")
                            ticker = data.get("data", {})
                            if "/contractMarket/tickerV2:" not in topic:
                                continue

                            symbol_raw = ticker.get("symbol", "")
                            bid = ticker.get("bestBidPrice")
                            ask = ticker.get("bestAskPrice")

                            if bid and ask and symbol_raw:
                                self.on_price_update(
                                    self._restore_symbol(symbol_raw),
                                    self.name,
                                    float(bid),
                                    float(ask),
                                )
                    finally:
                        ping_task.cancel()

            except Exception as exc:
                print(f"[KuCoin] batch {batch_num} error: {exc} - reconnect in 3s")
                await asyncio.sleep(3)

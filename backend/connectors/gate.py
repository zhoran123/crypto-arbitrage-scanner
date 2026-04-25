import asyncio
import json
import time

import websockets

from .base import BaseConnector


SUB_BATCH = 80
SUB_DELAY = 0.05


class GateConnector(BaseConnector):
    name = "gate"

    def get_fee(self):
        return 0.05

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        return symbol.replace("USDT", "_USDT")

    @staticmethod
    def _restore_symbol(symbol: str) -> str:
        return symbol.replace("_USDT", "USDT")

    async def connect(self, symbols: list[str]):
        batches = [symbols[i:i + SUB_BATCH] for i in range(0, len(symbols), SUB_BATCH)]
        print(f"[Gate.io] {len(symbols)} pairs -> {len(batches)} subscription batches")
        await asyncio.gather(*[
            self._connect_batch(batch, index + 1, len(batches))
            for index, batch in enumerate(batches)
        ])

    async def _connect_batch(self, symbols: list[str], batch_num: int, total: int):
        url = "wss://fx-ws.gateio.ws/v4/ws/usdt"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    await ws.send(json.dumps({
                        "time": int(time.time()),
                        "channel": "futures.book_ticker",
                        "event": "subscribe",
                        "payload": [self._convert_symbol(symbol) for symbol in symbols],
                    }))
                    await asyncio.sleep(SUB_DELAY)

                    print(f"[Gate.io] connected batch {batch_num}/{total} ({len(symbols)} pairs)")

                    async for raw in ws:
                        data = json.loads(raw)
                        channel = data.get("channel", "")
                        event = data.get("event", "")

                        if event == "subscribe" and data.get("error"):
                            print(f"[Gate.io] subscription error batch {batch_num}: {data.get('error')}")
                            continue

                        if channel != "futures.book_ticker" or event != "update":
                            continue

                        ticker = data.get("result", {})
                        symbol_raw = ticker.get("s", "")
                        bid = ticker.get("b")
                        ask = ticker.get("a")

                        if bid and ask and symbol_raw:
                            self.on_price_update(
                                self._restore_symbol(symbol_raw),
                                self.name,
                                float(bid),
                                float(ask),
                            )
            except Exception as exc:
                print(f"[Gate.io] batch {batch_num} error: {exc} - reconnect in 3s")
                await asyncio.sleep(3)

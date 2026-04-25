import asyncio
import json

import websockets

from . import _fastjson
from .base import BaseConnector

# Bybit: подписка по 10 аргументов за запрос, до 200 пар на соединение
SUB_BATCH = 10
CONN_BATCH = 200


class BybitConnector(BaseConnector):
    name = "bybit"

    def get_fee(self):
        return 0.06

    async def connect(self, symbols: list[str]):
        """Разбиваем символы на батчи по соединениям."""
        batches = [
            symbols[i:i + CONN_BATCH]
            for i in range(0, len(symbols), CONN_BATCH)
        ]
        print(f"[Bybit] {len(symbols)} пар → {len(batches)} соединений")

        tasks = [
            self._connect_batch(batch, idx + 1, len(batches))
            for idx, batch in enumerate(batches)
        ]
        await asyncio.gather(*tasks)

    async def _connect_batch(self, symbols: list[str], batch_num: int, total: int):
        url = "wss://stream.bybit.com/v5/public/linear"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    # Подписка порциями по 10
                    for i in range(0, len(symbols), SUB_BATCH):
                        chunk = symbols[i:i + SUB_BATCH]
                        await ws.send(json.dumps({
                            "op": "subscribe",
                            "args": [f"tickers.{s}" for s in chunk]
                        }))

                    print(f"[Bybit] подключён — батч {batch_num}/{total} ({len(symbols)} пар)")

                    async for raw in ws:
                        data = _fastjson.loads(raw)
                        if data.get("topic", "").startswith("tickers."):
                            d = data.get("data", {})
                            bid = d.get("bid1Price")
                            ask = d.get("ask1Price")
                            if bid and ask:
                                self.on_price_update(
                                    d["symbol"], self.name,
                                    float(bid), float(ask)
                                )
            except Exception as e:
                print(f"[Bybit] батч {batch_num} — реконнект через 3с")
                await asyncio.sleep(3)

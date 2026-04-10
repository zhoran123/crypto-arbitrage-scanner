import asyncio, json, websockets
from .base import BaseConnector

# Binance лимит: ~200 потоков на одно WS-соединение
BATCH_SIZE = 180


class BinanceConnector(BaseConnector):
    name = "binance"

    def get_fee(self):
        return 0.04

    async def connect(self, symbols: list[str]):
        """Разбиваем символы на батчи и подключаемся параллельно."""
        batches = [
            symbols[i:i + BATCH_SIZE]
            for i in range(0, len(symbols), BATCH_SIZE)
        ]
        print(f"[Binance] {len(symbols)} пар → {len(batches)} соединений")

        tasks = [
            self._connect_batch(batch, idx + 1, len(batches))
            for idx, batch in enumerate(batches)
        ]
        await asyncio.gather(*tasks)

    async def _connect_batch(self, symbols: list[str], batch_num: int, total: int):
        """Одно WS-соединение для батча символов."""
        streams = "/".join([f"{s.lower()}@bookTicker" for s in symbols])
        url = f"wss://fstream.binance.com/stream?streams={streams}"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    print(f"[Binance] подключён — батч {batch_num}/{total} ({len(symbols)} пар)")
                    async for raw in ws:
                        data = json.loads(raw).get("data", {})
                        if "b" in data and "a" in data:
                            self.on_price_update(
                                data["s"], self.name,
                                float(data["b"]), float(data["a"]),
                            )
            except Exception as e:
                print(f"[Binance] батч {batch_num} — реконнект через 3с")
                await asyncio.sleep(3)

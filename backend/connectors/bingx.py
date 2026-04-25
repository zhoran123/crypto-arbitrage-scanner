import asyncio
import gzip
import json

import websockets

from .base import BaseConnector


CONN_BATCH = 120
SUB_DELAY = 0.02
SYNTHETIC_SPREAD = 0.0005


class BingxConnector(BaseConnector):
    name = "bingx"

    def get_fee(self):
        return 0.045

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        return symbol.replace("USDT", "-USDT")

    @staticmethod
    def _restore_symbol(symbol: str) -> str:
        return symbol.replace("-USDT", "USDT")

    async def connect(self, symbols: list[str]):
        batches = [symbols[i:i + CONN_BATCH] for i in range(0, len(symbols), CONN_BATCH)]
        print(f"[BingX] {len(symbols)} pairs -> {len(batches)} connections")
        await asyncio.gather(*[
            self._connect_batch(batch, index + 1, len(batches))
            for index, batch in enumerate(batches)
        ])

    async def _connect_batch(self, symbols: list[str], batch_num: int, total: int):
        url = "wss://open-api-swap.bingx.com/swap-market"
        unsupported_symbols: set[str] = set()

        while True:
            try:
                async with websockets.connect(
                    url,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=5,
                ) as ws:
                    for symbol in symbols:
                        await ws.send(json.dumps({
                            "id": symbol,
                            "reqType": "sub",
                            "dataType": f"{self._convert_symbol(symbol)}@ticker",
                        }))
                        await asyncio.sleep(SUB_DELAY)

                    print(f"[BingX] connected batch {batch_num}/{total} ({len(symbols)} pairs)")

                    async def keepalive():
                        while True:
                            await asyncio.sleep(10)
                            try:
                                await ws.send("Pong")
                            except Exception:
                                break

                    keepalive_task = asyncio.create_task(keepalive())

                    try:
                        async for raw in ws:
                            try:
                                text = gzip.decompress(raw).decode("utf-8") if isinstance(raw, bytes) else raw

                                if text in ("Ping", "ping"):
                                    await ws.send("Pong")
                                    continue

                                data = json.loads(text)

                                if "ping" in data:
                                    await ws.send(json.dumps({"pong": data["ping"]}))
                                    continue

                                if data.get("code") not in (None, 0, "0"):
                                    symbol = data.get("id", "")
                                    if data.get("code") == 80015 and symbol:
                                        unsupported_symbols.add(symbol)
                                        if len(unsupported_symbols) <= 5 or len(unsupported_symbols) % 50 == 0:
                                            print(
                                                f"[BingX] unsupported websocket symbols in batch {batch_num}: "
                                                f"{len(unsupported_symbols)} latest={symbol}"
                                            )
                                    else:
                                        print(f"[BingX] subscription/message error batch {batch_num}: {data}")
                                    continue

                                ticker = data.get("data", {})
                                if not ticker:
                                    continue

                                symbol_raw = (
                                    ticker.get("symbol")
                                    or ticker.get("s")
                                    or str(data.get("dataType", "")).split("@", 1)[0]
                                )
                                bid = (
                                    ticker.get("bidPrice")
                                    or ticker.get("bid1Price")
                                    or ticker.get("bestBidPrice")
                                    or ticker.get("bid")
                                )
                                ask = (
                                    ticker.get("askPrice")
                                    or ticker.get("ask1Price")
                                    or ticker.get("bestAskPrice")
                                    or ticker.get("ask")
                                )

                                if bid and ask and symbol_raw:
                                    self.on_price_update(
                                        self._restore_symbol(symbol_raw),
                                        self.name,
                                        float(bid),
                                        float(ask),
                                    )
                                    continue

                                last_price = (
                                    ticker.get("lastPrice")
                                    or ticker.get("last")
                                    or ticker.get("price")
                                    or ticker.get("close")
                                    or ticker.get("c")
                                )
                                if last_price and symbol_raw:
                                    price = float(last_price)
                                    half_spread = price * SYNTHETIC_SPREAD
                                    self.on_price_update(
                                        self._restore_symbol(symbol_raw),
                                        self.name,
                                        price - half_spread,
                                        price + half_spread,
                                    )
                            except (gzip.BadGzipFile, json.JSONDecodeError):
                                continue
                    finally:
                        keepalive_task.cancel()

            except Exception as exc:
                print(f"[BingX] batch {batch_num} error: {exc} - reconnect in 3s")
                await asyncio.sleep(3)

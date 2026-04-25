import asyncio
import json

import websockets

from . import _fastjson
from .base import BaseConnector


class OkxConnector(BaseConnector):
    """
    OKX Perpetual Swap WebSocket.
    Формат символа на OKX: BTC-USDT-SWAP (через дефис + SWAP).
    """
    name = "okx"

    def get_fee(self):
        return 0.05

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """BTCUSDT → BTC-USDT-SWAP"""
        return symbol.replace("USDT", "-USDT-SWAP")

    @staticmethod
    def _restore_symbol(inst_id: str) -> str:
        """BTC-USDT-SWAP → BTCUSDT"""
        return inst_id.replace("-USDT-SWAP", "USDT").replace("-", "")

    async def connect(self, symbols: list[str]):
        url = "wss://ws.okx.com:8443/ws/v5/public"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    # Подписка на тикеры
                    args = [
                        {"channel": "tickers", "instId": self._convert_symbol(s)}
                        for s in symbols
                    ]
                    await ws.send(json.dumps({
                        "op": "subscribe",
                        "args": args,
                    }))

                    print(f"[OKX] подключён — {len(symbols)} пар")

                    async for raw in ws:
                        text = raw
                        # OKX ping/pong
                        if text == "ping":
                            await ws.send("pong")
                            continue

                        data = _fastjson.loads(text)

                        if "data" in data and data.get("arg", {}).get("channel") == "tickers":
                            for d in data["data"]:
                                inst_id = d.get("instId", "")
                                bid = d.get("bidPx")
                                ask = d.get("askPx")

                                if bid and ask and inst_id:
                                    self.on_price_update(
                                        self._restore_symbol(inst_id),
                                        self.name,
                                        float(bid), float(ask),
                                    )
            except Exception as e:
                print(f"[OKX] ошибка: {e} — реконнект через 3с")
                await asyncio.sleep(3)

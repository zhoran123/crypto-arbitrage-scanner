import asyncio, json, websockets
from .base import BaseConnector


class GateConnector(BaseConnector):
    """
    Gate.io USDT Futures WebSocket.
    Формат символа на Gate: BTC_USDT (с подчёркиванием).
    """
    name = "gate"

    def get_fee(self):
        return 0.05

    @staticmethod
    def _convert_symbol(symbol: str) -> str:
        """BTCUSDT → BTC_USDT"""
        return symbol.replace("USDT", "_USDT")

    @staticmethod
    def _restore_symbol(symbol: str) -> str:
        """BTC_USDT → BTCUSDT"""
        return symbol.replace("_USDT", "USDT")

    async def connect(self, symbols: list[str]):
        url = "wss://fx-ws.gateio.ws/v4/ws/usdt"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    # Подписка на book_ticker для всех символов сразу
                    await ws.send(json.dumps({
                        "time": int(asyncio.get_event_loop().time()),
                        "channel": "futures.book_ticker",
                        "event": "subscribe",
                        "payload": [self._convert_symbol(s) for s in symbols],
                    }))

                    print(f"[Gate.io] подключён — {len(symbols)} пар")

                    async for raw in ws:
                        data = json.loads(raw)
                        channel = data.get("channel", "")
                        event = data.get("event", "")

                        if channel == "futures.book_ticker" and event == "update":
                            d = data.get("result", {})
                            symbol_raw = d.get("s", "")
                            bid = d.get("b")
                            ask = d.get("a")

                            if bid and ask and symbol_raw:
                                self.on_price_update(
                                    self._restore_symbol(symbol_raw),
                                    self.name,
                                    float(bid), float(ask),
                                )
            except Exception as e:
                print(f"[Gate.io] ошибка: {e} — реконнект через 3с")
                await asyncio.sleep(3)

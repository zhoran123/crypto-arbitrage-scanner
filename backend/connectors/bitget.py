import asyncio, json, websockets
from .base import BaseConnector


class BitgetConnector(BaseConnector):
    """
    Bitget USDT-M Futures WebSocket.
    Формат символа на Bitget: BTCUSDT (такой же как у нас).
    """
    name = "bitget"

    def get_fee(self):
        return 0.051

    async def connect(self, symbols: list[str]):
        url = "wss://ws.bitget.com/v2/ws/public"

        while True:
            try:
                async with websockets.connect(url, ping_interval=20) as ws:
                    # Подписка на тикеры
                    args = [
                        {
                            "instType": "USDT-FUTURES",
                            "channel": "ticker",
                            "instId": s,
                        }
                        for s in symbols
                    ]
                    await ws.send(json.dumps({
                        "op": "subscribe",
                        "args": args,
                    }))

                    print(f"[Bitget] подключён — {len(symbols)} пар")

                    async for raw in ws:
                        text = raw
                        # Bitget может слать ping в виде "ping"
                        if text == "ping":
                            await ws.send("pong")
                            continue

                        data = json.loads(text)
                        action = data.get("action", "")

                        if action == "snapshot" or action == "update":
                            arg = data.get("arg", {})
                            items = data.get("data", [])

                            for d in items:
                                symbol = d.get("instId", "")
                                bid = d.get("bidPr") or d.get("bestBid")
                                ask = d.get("askPr") or d.get("bestAsk")

                                if bid and ask and symbol:
                                    self.on_price_update(
                                        symbol, self.name,
                                        float(bid), float(ask),
                                    )
            except Exception as e:
                print(f"[Bitget] ошибка: {e} — реконнект через 3с")
                await asyncio.sleep(3)

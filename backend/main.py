import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from alerts.telegram import TelegramAlerter
from config import EXCHANGES, FEES, MIN_TG_SPREAD, SYMBOLS, load_symbols
from connectors.binance import BinanceConnector
from connectors.bingx import BingxConnector
from connectors.bitget import BitgetConnector
from connectors.bybit import BybitConnector
from connectors.dex import DexConnector
from connectors.gate import GateConnector
from connectors.kucoin import KucoinConnector
from connectors.mexc import MexcConnector
from connectors.okx import OkxConnector
from core.aggregator import Aggregator
from core.blacklist import Blacklist
from core.fill_probability import FillProbabilityModel
from core.health import HealthMonitor
from core.orderbook import OrderbookFetcher, REFRESH_INTERVAL
from core.price_store import PriceStore
from core.signal_engine import SignalEngine
from core.signal_history import SignalHistory


load_dotenv()

app = FastAPI(title="Arb-Scanner", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

aggregator = Aggregator()
engine = SignalEngine()
blacklist = Blacklist()
history = SignalHistory()
health = HealthMonitor()
price_store = PriceStore()
orderbook = OrderbookFetcher()
fill_probability = FillProbabilityModel()

tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
tg_chat = os.getenv("TELEGRAM_CHAT_ID", "")
tg_cooldown = float(os.getenv("TELEGRAM_COOLDOWN", "30"))

telegram: TelegramAlerter | None = None
if tg_token and tg_chat:
    telegram = TelegramAlerter(tg_token, tg_chat, cooldown=tg_cooldown)
    print(f"[Telegram] alerts enabled (cooldown={tg_cooldown}s, min_spread={MIN_TG_SPREAD}%)")
else:
    print("[Telegram] alerts disabled - fill backend/.env to enable")

connected_clients: list[WebSocket] = []

CONNECTOR_REGISTRY = {
    "binance": BinanceConnector,
    "bybit": BybitConnector,
    "mexc": MexcConnector,
    "bingx": BingxConnector,
    "gate": GateConnector,
    "bitget": BitgetConnector,
    "okx": OkxConnector,
    "kucoin": KucoinConnector,
    "dex": DexConnector,
}

STATIC_DIR = Path(__file__).parent / "static"


async def broadcast_signal(signal: dict):
    if not connected_clients:
        return

    message = json.dumps(signal)
    for websocket in connected_clients.copy():
        try:
            await websocket.send_text(message)
        except Exception:
            if websocket in connected_clients:
                connected_clients.remove(websocket)


signal_queue: asyncio.Queue = asyncio.Queue()


def _get_exchange_age(symbol: str, exchange: str) -> float:
    entry = aggregator.prices.get(symbol.upper(), {}).get(exchange)
    if not entry:
        return 999.0
    return max(0.0, time.time() - entry.get("ts", 0))


def _build_fill_metrics(symbol: str, buy_exchange: str, sell_exchange: str, gross_spread: float) -> tuple[float, float]:
    symbol = symbol.upper()
    max_size = orderbook.get_max_size(symbol, buy_exchange, sell_exchange)
    fill_prob = fill_probability.estimate(
        symbol=symbol,
        buy_exchange=buy_exchange,
        sell_exchange=sell_exchange,
        gross_spread_pct=gross_spread,
        max_size_usd=max_size,
        buy_age_sec=_get_exchange_age(symbol, buy_exchange),
        sell_age_sec=_get_exchange_age(symbol, sell_exchange),
        buy_health=health.get_exchange_status(buy_exchange),
        sell_health=health.get_exchange_status(sell_exchange),
    )
    return max_size, fill_prob


def on_signal(signal: dict):
    symbol = signal.get("symbol", "").upper()
    if blacklist.is_blocked(symbol):
        return

    max_size, fill_prob = _build_fill_metrics(
        symbol,
        signal.get("buy_on", ""),
        signal.get("sell_on", ""),
        signal.get("deviation_pct", 0.0),
    )
    signal["max_size_usd"] = round(max_size, 2)
    signal["fill_prob_pct"] = fill_prob

    history.add(signal)
    signal_queue.put_nowait(signal)

    net_spread = signal.get("net_spread_pct", 0)
    if telegram and net_spread >= MIN_TG_SPREAD:
        telegram.on_signal(signal)


async def signal_sender():
    while True:
        signal = await signal_queue.get()
        await broadcast_signal(signal)


def on_price_update(symbol: str, exchange: str, bid: float, ask: float):
    health.on_update(exchange, symbol)
    aggregator.update(symbol, exchange, bid, ask)
    price_store.on_price(symbol, exchange, bid, ask)
    fill_probability.on_price(symbol, exchange, bid, ask)

    prices = aggregator.get_prices(symbol)
    if prices:
        engine.on_price_update(symbol, prices)


def on_pair_evaluated(symbol: str, buy_exchange: str, sell_exchange: str, gross_spread: float, _buy_price: float, _sell_price: float):
    if "dex" in (buy_exchange, sell_exchange) and gross_spread > 50:
        return
    fill_probability.track_spread(symbol, buy_exchange, sell_exchange, gross_spread)


engine.set_on_signal(on_signal)
engine.set_on_pair(on_pair_evaluated)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    print(f"[WS] client connected. Total: {len(connected_clients)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print(f"[WS] client disconnected. Total: {len(connected_clients)}")


@app.get("/")
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    import config

    return {"app": "Arb-Scanner", "version": "0.4.0", "symbols": len(config.SYMBOLS)}


@app.get("/prices")
async def get_prices():
    return aggregator.prices


_spreads_cache: list = []
_spreads_cache_ts: float = 0.0
_SPREADS_TTL: float = 2.0


def _compute_spreads() -> list:
    prices = aggregator.prices
    blocked = set(blacklist.get_all())
    result = []

    for symbol, exchanges in prices.items():
        if symbol in blocked or len(exchanges) < 2:
            continue

        best = None
        best_net = -999.0
        exchange_items = list(exchanges.items())

        for sell_index, (sell_exchange, sell_data) in enumerate(exchange_items):
            sell_price = sell_data["bid"]
            if sell_price <= 0:
                continue

            for buy_index, (buy_exchange, buy_data) in enumerate(exchange_items):
                if sell_index == buy_index:
                    continue

                buy_price = buy_data["ask"]
                if buy_price <= 0:
                    continue

                gross = ((sell_price - buy_price) / buy_price) * 100
                if "dex" in (buy_exchange, sell_exchange) and gross > 50:
                    continue

                net = gross - FEES.get(buy_exchange, 0.05) - FEES.get(sell_exchange, 0.05)
                if net > best_net:
                    best_net = net
                    best = {
                        "symbol": symbol,
                        "buy_on": buy_exchange,
                        "sell_on": sell_exchange,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "gross_spread": round(gross, 4),
                        "net_spread": round(net, 4),
                        "exchanges": len(exchanges),
                    }

        if best:
            max_size, fill_prob = _build_fill_metrics(
                symbol,
                best["buy_on"],
                best["sell_on"],
                best["gross_spread"],
            )
            best["max_size_usd"] = round(max_size, 2)
            best["fill_prob_pct"] = fill_prob
            result.append(best)

    result.sort(key=lambda item: item["net_spread"], reverse=True)
    return result


def _snapshot_symbol_candles(symbol: str) -> dict:
    snapshot = {}
    ts = int(time.time() // 60) * 60
    for exchange, data in aggregator.prices.get(symbol.upper(), {}).items():
        bid = data.get("bid", 0)
        ask = data.get("ask", 0)
        if bid <= 0 or ask <= 0:
            continue
        mid = (bid + ask) / 2
        snapshot[exchange] = {"t": ts, "o": mid, "h": mid, "l": mid, "c": mid}
    return snapshot


@app.get("/spreads")
async def get_spreads():
    global _spreads_cache, _spreads_cache_ts
    now = time.monotonic()
    if now - _spreads_cache_ts > _SPREADS_TTL:
        _spreads_cache = _compute_spreads()
        _spreads_cache_ts = now
    return _spreads_cache


@app.get("/stats")
async def get_stats():
    return {
        "price_updates": aggregator.update_count,
        "signals_generated": engine.signal_count,
        "signals_history": history.total,
        "connected_clients": len(connected_clients),
        "telegram_sent": telegram.sent_count if telegram else 0,
        "telegram_active": telegram is not None,
        "blacklisted": len(blacklist.get_all()),
    }


class SymbolRequest(BaseModel):
    symbol: str


@app.get("/blacklist")
async def get_blacklist():
    return {"symbols": blacklist.get_all()}


@app.post("/blacklist/add")
async def add_to_blacklist(req: SymbolRequest):
    blacklist.add(req.symbol)
    return {"status": "added", "symbol": req.symbol.upper()}


@app.post("/blacklist/remove")
async def remove_from_blacklist(req: SymbolRequest):
    blacklist.remove(req.symbol)
    return {"status": "removed", "symbol": req.symbol.upper()}


@app.get("/history")
async def get_history(limit: int = 200):
    return history.get_recent(limit)


@app.get("/history/stats")
async def get_history_stats():
    return history.get_stats()


@app.get("/health")
async def get_health():
    return health.get_status()


@app.get("/price-history")
async def get_price_history(symbol: str, tf: str = "1m"):
    if tf not in ("1m", "5m", "15m", "30m", "1h", "4h"):
        return {"error": "tf must be 1m, 5m, 15m, 30m, 1h, or 4h"}

    result = price_store.get_history(symbol.upper(), tf)
    fallback = _snapshot_symbol_candles(symbol)
    for exchange, candle in fallback.items():
        if not result.get(exchange):
            result[exchange] = [candle]
    return result


@app.get("/price-history/live")
async def get_price_live(symbol: str):
    result = price_store.get_live_candles(symbol.upper())
    fallback = _snapshot_symbol_candles(symbol)
    for exchange, candle in fallback.items():
        result.setdefault(exchange, candle)
    return result


@app.get("/price-history/live/batch")
async def get_price_live_batch(symbols: str):
    result = {}
    symbol_list = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]

    for symbol in dict.fromkeys(symbol_list):
        live = price_store.get_live_candles(symbol)
        fallback = _snapshot_symbol_candles(symbol)
        for exchange, candle in fallback.items():
            live.setdefault(exchange, candle)
        result[symbol] = live

    return result


@app.get("/telegram/status")
async def get_telegram_status():
    if not telegram:
        return {"active": False, "reason": "Telegram is not configured (.env)"}

    return {
        "active": True,
        "min_tg_spread": MIN_TG_SPREAD,
        **telegram.get_diagnostics(),
    }


@app.on_event("startup")
async def startup():
    import config

    print("=" * 50)
    print("  ARB-SCANNER v0.4 starting...")

    symbols = load_symbols()

    print(f"  Symbols: {len(symbols)}")
    print(f"  Exchanges: {EXCHANGES}")
    print(f"  Blacklist: {len(blacklist.get_all())} symbols")
    print(f"  TG min spread: {MIN_TG_SPREAD}%")
    print("=" * 50)

    asyncio.create_task(signal_sender())
    await orderbook.start()

    async def flush_loop():
        while True:
            await asyncio.sleep(60)
            price_store.flush()

    asyncio.create_task(flush_loop())

    async def size_refresh_loop():
        while True:
            try:
                # Reuse the latest computed spreads snapshot so orderbook refresh
                # does not duplicate the most expensive CPU path in the app.
                current_spreads = _spreads_cache
                if not current_spreads:
                    current_spreads = _compute_spreads()
                if current_spreads:
                    await orderbook.refresh_for_spreads(current_spreads)
            except Exception as exc:
                print(f"[OrderBook] refresh error: {exc}")
            await asyncio.sleep(REFRESH_INTERVAL)

    asyncio.create_task(size_refresh_loop())

    for exchange in EXCHANGES:
        connector_cls = CONNECTOR_REGISTRY.get(exchange)
        if not connector_cls:
            print(f"[!] missing connector for '{exchange}'")
            continue

        if exchange == "dex":
            connector = connector_cls(
                on_price_update=on_price_update,
                on_liquidity=orderbook.set_dex_liquidity,
            )
        else:
            connector = connector_cls(on_price_update=on_price_update)

        asyncio.create_task(connector.connect(config.SYMBOLS))
        print(f"[+] {exchange} started")

    print()
    print("Server ready: http://localhost:8000")


@app.on_event("shutdown")
async def shutdown():
    await orderbook.stop()
    price_store.flush()


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR / "static"), name="static-assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file = STATIC_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")

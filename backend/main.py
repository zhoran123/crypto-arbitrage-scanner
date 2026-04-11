"""
main.py — точка входа Arb-Scanner v0.4

Фичи:
- 8 бирж, 700+ монет
- Чёрный список монет
- Уровни Telegram-алертов (5/10/20%)
- История сигналов
- Мониторинг здоровья бирж
"""

import asyncio
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import SYMBOLS, EXCHANGES, MIN_TG_SPREAD, FEES, load_symbols
from core.aggregator import Aggregator
from core.signal_engine import SignalEngine
from core.blacklist import Blacklist
from core.signal_history import SignalHistory
from core.health import HealthMonitor
from core.price_history import PriceHistory
from alerts.telegram import TelegramAlerter

from connectors.binance import BinanceConnector
from connectors.bybit import BybitConnector
from connectors.mexc import MexcConnector
from connectors.bingx import BingxConnector
from connectors.gate import GateConnector
from connectors.bitget import BitgetConnector
from connectors.okx import OkxConnector
from connectors.kucoin import KucoinConnector

# ======================================================================
# Инициализация
# ======================================================================

load_dotenv()

app = FastAPI(title="Arb-Scanner", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Центральные компоненты
aggregator = Aggregator()
engine = SignalEngine()
blacklist = Blacklist()
history = SignalHistory()
health = HealthMonitor()
price_history = PriceHistory()

# Telegram
tg_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
tg_chat = os.getenv("TELEGRAM_CHAT_ID", "")
tg_cooldown = float(os.getenv("TELEGRAM_COOLDOWN", "30"))

telegram: TelegramAlerter | None = None
if tg_token and tg_chat and "СЮДА" not in tg_token:
    telegram = TelegramAlerter(tg_token, tg_chat, cooldown=tg_cooldown)
    print(f"[Telegram] алерты включены (cooldown={tg_cooldown}s, min_spread={MIN_TG_SPREAD}%)")
else:
    print("[Telegram] алерты ВЫКЛЮЧЕНЫ — заполни .env")

# WebSocket клиенты
connected_clients: list[WebSocket] = []

# Реестр коннекторов
CONNECTOR_REGISTRY = {
    "binance": BinanceConnector,
    "bybit":   BybitConnector,
    "mexc":    MexcConnector,
    "bingx":   BingxConnector,
    "gate":    GateConnector,
    "bitget":  BitgetConnector,
    "okx":     OkxConnector,
    "kucoin":  KucoinConnector,
}

STATIC_DIR = Path(__file__).parent / "static"

# ======================================================================
# Рассылка сигналов
# ======================================================================

async def broadcast_signal(signal: dict):
    if not connected_clients:
        return
    message = json.dumps(signal)
    for ws in connected_clients.copy():
        try:
            await ws.send_text(message)
        except Exception:
            if ws in connected_clients:
                connected_clients.remove(ws)


signal_queue: asyncio.Queue = asyncio.Queue()


def on_signal(signal: dict):
    """Callback из SignalEngine."""
    symbol = signal.get("symbol", "")

    # Чёрный список — блокируем полностью
    if blacklist.is_blocked(symbol):
        return

    # Сохраняем в историю
    history.add(signal)

    # Шлём на фронтенд
    signal_queue.put_nowait(signal)

    # Telegram (с фильтром по спреду)
    net = signal.get("net_spread_pct", 0)
    if telegram and net >= MIN_TG_SPREAD:
        telegram.on_signal(signal)


async def signal_sender():
    while True:
        signal = await signal_queue.get()
        await broadcast_signal(signal)

# ======================================================================
# Связываем компоненты
# ======================================================================

def on_price_update(symbol: str, exchange: str, bid: float, ask: float):
    # Обновляем здоровье биржи
    health.on_update(exchange, symbol)

    aggregator.update(symbol, exchange, bid, ask)
    price_history.on_price(symbol, exchange, bid, ask)
    prices = aggregator.get_prices(symbol)
    if prices:
        engine.on_price_update(symbol, prices)


engine.set_on_signal(on_signal)

# ======================================================================
# WebSocket
# ======================================================================

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    print(f"[WS] Клиент подключён. Всего: {len(connected_clients)}")
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
        print(f"[WS] Клиент отключён. Всего: {len(connected_clients)}")

# ======================================================================
# REST API
# ======================================================================

@app.get("/")
async def root():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    import config
    return {"app": "Arb-Scanner", "version": "0.4.0", "symbols": len(config.SYMBOLS)}


@app.get("/prices")
async def get_prices():
    # Возвращаем прямую ссылку — не deep copy. FastAPI сериализует сам.
    return aggregator.prices


# --- Кэш для /spreads (самый тяжёлый endpoint) ---
_spreads_cache: list = []
_spreads_cache_ts: float = 0.0
_SPREADS_TTL: float = 2.0  # секунды


def _compute_spreads() -> list:
    """Вычислить spreads — вынесено для кэширования."""
    prices = aggregator.prices
    blocked = set(blacklist.get_all())
    result = []

    for symbol, exchanges in prices.items():
        if symbol in blocked or len(exchanges) < 2:
            continue

        best = None
        best_net = -999.0
        exch_list = list(exchanges.items())

        for i in range(len(exch_list)):
            sell_name, sell_data = exch_list[i]
            sell_price = sell_data["bid"]
            if sell_price <= 0:
                continue

            for j in range(len(exch_list)):
                if i == j:
                    continue
                buy_name, buy_data = exch_list[j]
                buy_price = buy_data["ask"]

                if buy_price <= 0:
                    continue

                gross = ((sell_price - buy_price) / buy_price) * 100
                net = gross - FEES.get(buy_name, 0.05) - FEES.get(sell_name, 0.05)

                if net > best_net:
                    best_net = net
                    best = {
                        "symbol": symbol,
                        "buy_on": buy_name,
                        "sell_on": sell_name,
                        "buy_price": buy_price,
                        "sell_price": sell_price,
                        "gross_spread": round(gross, 4),
                        "net_spread": round(net, 4),
                        "exchanges": len(exchanges),
                    }

        if best:
            result.append(best)

    result.sort(key=lambda x: x["net_spread"], reverse=True)
    return result


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


# --- Blacklist ---

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


# --- History ---

@app.get("/history")
async def get_history(limit: int = 200):
    return history.get_recent(limit)


@app.get("/history/stats")
async def get_history_stats():
    return history.get_stats()


# --- Health ---

@app.get("/health")
async def get_health():
    return health.get_status()


@app.get("/price-history")
async def get_price_history(symbol: str, tf: str = "1m"):
    if tf not in ("1m", "5m", "15m", "30m", "1h", "4h"):
        return {"error": "tf must be 1m, 5m, 15m, 30m, 1h, or 4h"}
    return price_history.get_history(symbol.upper(), tf)


@app.get("/telegram/status")
async def get_telegram_status():
    """Диагностика Telegram-бота."""
    if not telegram:
        return {"active": False, "reason": "Telegram не настроен (.env)"}
    return {
        "active": True,
        "min_tg_spread": MIN_TG_SPREAD,
        **telegram.get_diagnostics(),
    }


# ======================================================================
# Startup
# ======================================================================

@app.on_event("startup")
async def startup():
    import config

    print("=" * 50)
    print(f"  ARB-SCANNER v0.4 запускается...")

    # Загружаем символы ПАРАЛЛЕЛЬНО (раньше — последовательно при импорте)
    symbols = load_symbols()

    print(f"  Символы: {len(symbols)}")
    print(f"  Биржи:   {EXCHANGES}")
    print(f"  Blacklist: {len(blacklist.get_all())} монет")
    print(f"  TG min spread: {MIN_TG_SPREAD}%")
    print("=" * 50)

    asyncio.create_task(signal_sender())

    for exch_name in EXCHANGES:
        connector_cls = CONNECTOR_REGISTRY.get(exch_name)
        if not connector_cls:
            print(f"[!] Коннектор для '{exch_name}' не найден")
            continue
        connector = connector_cls(on_price_update=on_price_update)
        asyncio.create_task(connector.connect(config.SYMBOLS))
        print(f"[+] {exch_name} — запущен")

    print()
    print("Сервер готов: http://localhost:8000")

# ======================================================================
# Статические файлы фронтенда (монтировать ПОСЛЕ API-роутов)
# ======================================================================

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR / "static"), name="static-assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file = STATIC_DIR / path
        if file.exists() and file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")

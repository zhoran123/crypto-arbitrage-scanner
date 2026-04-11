# FlashArb — Cross-Exchange Crypto Arbitrage Scanner

## What this project does

Real-time SaaS that monitors price differences across 8 crypto exchanges (Binance, Bybit, OKX, Bitget, Gate.io, MEXC, BingX, KuCoin) for USDT perpetual futures. When a profitable spread appears, it generates a signal and sends Telegram alerts.

## Architecture

```
frontend/          React 18 SPA (hash-based routing, inline CSS-in-JS, Framer Motion)
backend/           FastAPI + Uvicorn async server
Dockerfile         Multi-stage: Node builds React → Python serves everything on :8000
docker-compose.yml Single service "arb-scanner", reads backend/.env
```

## Backend (Python, FastAPI)

- **Entry point:** `backend/main.py` — FastAPI app, startup loads symbols lazily via `config.load_symbols()`
- **Config:** `backend/config.py` — exchanges list, symbol loading, env vars (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MIN_TG_SPREAD)
- **Connectors:** `backend/connectors/` — one file per exchange, all extend `base.py`. WebSocket connections for real-time price feeds
- **Core logic:**
  - `aggregator.py` — collects prices from all exchanges, computes spreads
  - `signal_engine.py` — detects anomalies via z-score with O(1) `_RunningStats` (replaced numpy)
  - `signal_history.py` — persists signals to `signal_history.jsonl`, rotation every 500 writes
  - `symbols.py` — fetches tradable symbols in parallel via `ThreadPoolExecutor`
  - `health.py` — tracks exchange connection status
  - `blacklist.py` — user-managed symbol blocklist
- **Alerts:** `backend/alerts/telegram.py` — priority-based Telegram notifications with per-symbol throttling
- **API endpoints:** `/stats`, `/spreads` (2s TTL cache), `/health`, `/blacklist`, `/history`, `/history/stats`, `/telegram/status`
- **WebSocket:** `/ws` — streams signals to frontend in real-time
- **Dependencies:** fastapi, uvicorn, websockets, python-dotenv, requests, aiofiles (no numpy)

## Frontend (React 18)

- **Router:** `src/App.js` — hash-based (`#/`, `#/dashboard`, `#/pricing`) with Framer Motion `AnimatePresence` page transitions
- **Pages:**
  - `Landing.js` — marketing page with hero, animated stats, feature grid, live feed demo, scroll reveals
  - `Dashboard.js` — operational view with 5 tabs (Spreads, Signals, Health, History, Blacklist), WebSocket connection, 6s API polling
  - `Pricing.js` — single-plan pricing card ($29/mo) + FAQ accordion
- **Nav:** `Nav.js` — sticky nav with bilingual support (EN/RU), animated link underlines
- **Styling:** All inline CSS-in-JS (no CSS files, no Tailwind). Design system: dark charcoal (#08090e) + cyan-blue (#0ea5e9) primary + amber for profit indicators
- **Fonts:** Inter (body) + JetBrains Mono (data/metrics)
- **Animations:** Framer Motion — page transitions, scroll reveals (`useInView`), tab indicator (`layoutId`), staggered card entrances, animated filter bar, FAQ expand/collapse
- **Dependencies:** react, react-dom, react-scripts, framer-motion

## Environment Variables (backend/.env)

```
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
MIN_TG_SPREAD=0.5
```

## Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (dev)
cd frontend
npm install
npm start          # port 3000, proxies API to :8000
```

## Production deployment

```bash
docker compose up -d --build    # builds React, serves on :8000
```

Server: `91.184.240.201:8000`

## Testing

```bash
cd backend
python -m pytest test_aggregator.py test_signal_engine.py
```

## Key design decisions

- **No numpy** — z-score computed via incremental `_RunningStats` class (O(1) per update)
- **Lazy symbol loading** — `load_symbols()` runs at startup, not at import time
- **Parallel symbol fetching** — `ThreadPoolExecutor` queries all exchanges simultaneously
- **TTL cache on /spreads** — 2-second cache prevents recomputation on rapid polling
- **Bilingual UI** — all text in `L` constant objects with `en`/`ru` keys
- **No external UI framework** — all styles are inline objects, keeps bundle minimal

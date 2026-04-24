"""
convergence.py — трекинг схождения спредов.

Логика:
1. Держим rolling-пик gross_spread за последние PEAK_WINDOW секунд для каждой
   пары (symbol, buy_exch, sell_exch).
2. Если пик достиг >= PEAK_THRESHOLD% и потом опустился <= CONVERGE_THRESHOLD%,
   дёргаем колбэк (Telegram / WS).
3. После алерта — cooldown, чтобы не спамить при шуме.
"""

import time

PEAK_WINDOW = 600          # 10 минут — окно поиска пика
PEAK_THRESHOLD = 3.0       # пик должен был быть минимум 3%
CONVERGE_THRESHOLD = 0.5   # считаем сошедшимся на 0.5%
COOLDOWN = 900             # 15 минут — не алертим одну пару чаще


class ConvergenceTracker:
    def __init__(self, on_convergence=None):
        self._on_convergence = on_convergence
        # {pair_key: {"peak": float, "peak_ts": float, "alerted_ts": float}}
        self._state: dict[str, dict] = {}

    def set_on_convergence(self, cb):
        self._on_convergence = cb

    def update(
        self,
        symbol: str,
        buy_exch: str,
        sell_exch: str,
        gross_spread: float,
        buy_price: float,
        sell_price: float,
    ):
        key = f"{symbol}|{buy_exch}|{sell_exch}"
        now = time.time()
        st = self._state.get(key)

        # Новая запись или просроченный пик — начинаем заново
        if not st or (now - st["peak_ts"]) > PEAK_WINDOW:
            self._state[key] = {
                "peak": gross_spread,
                "peak_ts": now,
                "alerted_ts": st.get("alerted_ts", 0) if st else 0,
            }
            return

        # Обновляем пик если растёт
        if gross_spread > st["peak"]:
            st["peak"] = gross_spread
            st["peak_ts"] = now
            return

        # Проверяем условие конвергенции
        if (
            st["peak"] >= PEAK_THRESHOLD
            and gross_spread <= CONVERGE_THRESHOLD
            and (now - st["alerted_ts"]) > COOLDOWN
        ):
            st["alerted_ts"] = now
            payload = {
                "symbol": symbol,
                "buy_on": buy_exch,
                "sell_on": sell_exch,
                "peak_spread_pct": round(st["peak"], 4),
                "current_spread_pct": round(gross_spread, 4),
                "buy_price": buy_price,
                "sell_price": sell_price,
                "peak_age_sec": int(now - st["peak_ts"]),
            }
            if self._on_convergence:
                try:
                    self._on_convergence(payload)
                except Exception as e:
                    print(f"[Convergence] callback error: {e}")
            # Сбрасываем пик, чтобы не триггерить повторно на одной и той же серии
            st["peak"] = gross_spread
            st["peak_ts"] = now

"""
Telegram Alerts с уровнями приоритета.

Уровни:
  5%+  — обычный сигнал
  10%+ — HIGH PRIORITY (отдельное оформление)
  20%+ — CRITICAL (повторное уведомление через cooldown/2)
"""

import time
import requests
from threading import Thread
from queue import Queue, Empty


class TelegramAlerter:
    def __init__(self, bot_token: str, chat_id: str, cooldown: float = 30.0):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.cooldown = cooldown
        self._api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        # Троттлинг: {key: last_sent_time}
        self._last_sent: dict[str, float] = {}

        # Диагностика
        self._received_count = 0
        self._filtered_count = 0
        self._sent_count = 0
        self._error_count = 0

        # Очередь + фоновый поток
        self._queue: Queue = Queue()
        self._start_worker()

    def _start_worker(self):
        """Запускаем (или перезапускаем) фоновый поток отправки."""
        self._worker = Thread(target=self._sender_loop, daemon=True, name="tg-sender")
        self._worker.start()

    def on_signal(self, signal: dict):
        """Принять сигнал с учётом троттлинга и уровня приоритета."""
        self._received_count += 1
        symbol = signal.get("symbol", "")
        net_spread = signal.get("net_spread_pct", 0)
        now = time.time()

        # Определяем уровень
        if net_spread >= 20:
            level = "critical"
            cd = self.cooldown / 2
        elif net_spread >= 10:
            level = "high"
            cd = self.cooldown
        else:
            level = "normal"
            cd = self.cooldown

        # Троттлинг
        key = f"{symbol}:{level}"
        last = self._last_sent.get(key, 0)
        if now - last < cd:
            self._filtered_count += 1
            return

        self._last_sent[key] = now
        self._queue.put((signal, level))

        # Логирование каждые 10 сигналов
        if self._received_count % 10 == 0:
            print(f"[Telegram] получено: {self._received_count}, отправлено: {self._sent_count}, "
                  f"отфильтровано: {self._filtered_count}, ошибок: {self._error_count}")

    def on_convergence(self, payload: dict):
        """Алерт о схождении спреда — отдельная очередь, без троттлинга сигналов."""
        symbol = payload.get("symbol", "")
        now = time.time()
        key = f"{symbol}:convergence"
        last = self._last_sent.get(key, 0)
        if now - last < self.cooldown:
            return
        self._last_sent[key] = now
        self._queue.put((payload, "convergence"))

    def _sender_loop(self):
        """Фоновый цикл отправки сообщений."""
        print("[Telegram] sender thread запущен")
        while True:
            try:
                signal, level = self._queue.get(timeout=1)
                self._send_with_retry(signal, level)
            except Empty:
                continue
            except Exception as e:
                self._error_count += 1
                print(f"[Telegram] критическая ошибка в sender loop: {e}")
                time.sleep(5)

    def _send_with_retry(self, signal: dict, level: str, retries: int = 2):
        """Отправка с ретраями."""
        if level == "convergence":
            text = self._format_convergence(signal)
        else:
            text = self._format_message(signal, level)
        for attempt in range(1, retries + 1):
            try:
                resp = requests.post(
                    self._api_url,
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    self._sent_count += 1
                    sym = signal.get("symbol", "?")
                    if level == "convergence":
                        peak = signal.get("peak_spread_pct", 0)
                        cur = signal.get("current_spread_pct", 0)
                        print(f"[Telegram] отправлен: {sym} convergence peak={peak:.2f}% → {cur:.2f}%")
                    else:
                        net = signal.get("net_spread_pct", 0)
                        print(f"[Telegram] отправлен: {sym} net={net:+.3f}% [{level}]")
                    return
                elif resp.status_code == 429:
                    # Rate limited — ждём и ретраим
                    retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
                    print(f"[Telegram] rate limited, жду {retry_after}с")
                    time.sleep(retry_after)
                else:
                    self._error_count += 1
                    print(f"[Telegram] HTTP {resp.status_code}: {resp.text[:200]}")
                    return
            except requests.exceptions.Timeout:
                print(f"[Telegram] таймаут (попытка {attempt}/{retries})")
                if attempt < retries:
                    time.sleep(2)
            except Exception as e:
                self._error_count += 1
                print(f"[Telegram] ошибка: {e}")
                return

    @staticmethod
    def _format_message(s: dict, level: str) -> str:
        symbol = s.get("symbol", "???")
        buy_on = s.get("buy_on", "?").upper()
        sell_on = s.get("sell_on", "?").upper()
        buy_price = s.get("buy_price", 0)
        sell_price = s.get("sell_price", 0)
        spread = s.get("deviation_pct", 0)
        net = s.get("net_spread_pct", 0)
        z = s.get("z_score", 0)
        quality = s.get("quality", 0)
        fill_prob = s.get("fill_prob_pct")

        # Заголовок по уровню
        if level == "critical":
            header = f"\U0001f6a8\U0001f6a8\U0001f6a8 <b>CRITICAL \u2014 {symbol}</b> \U0001f6a8\U0001f6a8\U0001f6a8"
            divider = "\u2501" * 24
        elif level == "high":
            header = f"\u26a0\ufe0f <b>HIGH PRIORITY \u2014 {symbol}</b> \u26a0\ufe0f"
            divider = "\u2500" * 24
        else:
            header = f"\U0001f4ca <b>Signal \u2014 {symbol}</b>"
            divider = ""

        lines = [header]
        if divider:
            lines.append(divider)

        lines.extend([
            "",
            f"\U0001f4c8 Buy on <b>{buy_on}</b> \u2192 ${buy_price:,.6f}",
            f"\U0001f4c9 Sell on <b>{sell_on}</b> \u2192 ${sell_price:,.6f}",
            "",
            f"\U0001f4b0 Gross: <b>{spread:.3f}%</b>",
            f"\U0001f4b5 Net: <b>{net:+.3f}%</b>",
            f"\U0001f4ca Z-Score: {z:.1f}  |  \u2b50 Quality: {quality}/100",
        ])

        if fill_prob is not None:
            lines.append(f"\U0001f3af Fill: <b>{float(fill_prob):.0f}%</b>")

        if level == "critical":
            lines.extend(["", "\U0001f525 <b>EXCEPTIONAL OPPORTUNITY</b> \U0001f525"])
        elif level == "high":
            lines.extend(["", "\u26a1 <i>High priority signal</i>"])

        return "\n".join(lines)

    @staticmethod
    def _format_convergence(p: dict) -> str:
        symbol = p.get("symbol", "???")
        buy_on = p.get("buy_on", "?").upper()
        sell_on = p.get("sell_on", "?").upper()
        peak = p.get("peak_spread_pct", 0)
        cur = p.get("current_spread_pct", 0)
        age = p.get("peak_age_sec", 0)
        age_str = f"{age}s" if age < 60 else f"{age // 60}m {age % 60}s"
        drop = peak - cur

        lines = [
            f"\U0001f501 <b>CONVERGED \u2014 {symbol}</b>",
            "\u2500" * 24,
            "",
            f"Pair: <b>{buy_on}</b> \u2194 <b>{sell_on}</b>",
            f"Peak:    <b>{peak:.2f}%</b>  ({age_str} ago)",
            f"Current: <b>{cur:.2f}%</b>",
            f"Drop:    <b>\u2212{drop:.2f}%</b>",
            "",
            "<i>Spread has collapsed \u2014 opportunity likely closed.</i>",
        ]
        return "\n".join(lines)

    @property
    def sent_count(self) -> int:
        return self._sent_count

    def get_diagnostics(self) -> dict:
        """Диагностика для отладки."""
        return {
            "received": self._received_count,
            "sent": self._sent_count,
            "filtered_by_cooldown": self._filtered_count,
            "errors": self._error_count,
            "queue_size": self._queue.qsize(),
            "thread_alive": self._worker.is_alive(),
        }

    def __repr__(self):
        return f"<TelegramAlerter: {self._sent_count} sent, {self._received_count} received>"

import React, { useState, useEffect, useRef } from "react";
import { motion, useInView } from "framer-motion";
import Nav from "./Nav";
import "./landing.css";

/* ── Translations ── */
const L = {
  en: {
    hero_tag: "Cross-exchange arbitrage",
    hero_h1a: "Find price gaps", hero_h1b: "before anyone else.",
    hero_p: "FlashArb monitors 8 exchanges simultaneously. When prices diverge — you get the signal in milliseconds, not minutes.",
    hero_cta: "Open Scanner", hero_note: "Free access · no registration",
    demo_label: "LIVE FEED",
    phil_h: "Most scanners drown you in noise.",
    phil_p: "Hundreds of pairs with 0.01% spreads that vanish before you blink. We filter that out. You only see opportunities worth acting on.",
    f1_t: "8 Exchanges", f1_d: "Binance, Bybit, OKX, Bitget, Gate.io, MEXC, BingX, KuCoin — compared tick by tick.",
    f2_t: "700+ Pairs", f2_d: "Every USDT perpetual loaded automatically. New listings picked up on restart.",
    f3_t: "Telegram Alerts", f3_d: "Three priority tiers: normal, high, critical. Delivered in under a second.",
    f4_t: "Smart Blacklist", f4_d: "Block noisy or delisted pairs with one click. Persists across restarts.",
    f5_t: "Health Monitor", f5_d: "Real-time status of every connection. Know instantly if a feed drops.",
    f6_t: "Signal History", f6_d: "Every signal saved. Analytics by pairs, exchanges and time.",
    how_t: "How it works",
    how_1t: "Connect", how_1d: "WebSocket streams from all 8 exchanges. No polling, no delays.",
    how_2t: "Compare", how_2d: "56 exchange-pair comparisons per symbol. Every tick.",
    how_3t: "Alert", how_3d: "Spread exceeds threshold → instant signal with prices and net profit.",
    bot_cta: "Start scanning now",
    foot: "Built for traders who move fast.", copy: "© 2025 FlashArb",
  },
  ru: {
    hero_tag: "Межбиржевой арбитраж",
    hero_h1a: "Находите расхождения цен", hero_h1b: "раньше всех.",
    hero_p: "FlashArb мониторит 8 бирж одновременно. Когда цены расходятся — вы получаете сигнал за миллисекунды, а не минуты.",
    hero_cta: "Открыть сканер", hero_note: "Бесплатный доступ · без регистрации",
    demo_label: "LIVE",
    phil_h: "Большинство сканеров тонут в шуме.",
    phil_p: "Сотни пар со спредами 0.01%, которые исчезают раньше, чем вы моргнёте. Мы это отфильтровываем. Вы видите только то, на чём можно заработать.",
    f1_t: "8 бирж", f1_d: "Binance, Bybit, OKX, Bitget, Gate.io, MEXC, BingX, KuCoin — сравнение тик за тиком.",
    f2_t: "700+ пар", f2_d: "Все USDT-перпетуалы. Загружаются автоматически.",
    f3_t: "Telegram-алерты", f3_d: "Три уровня: обычный, высокий, критический. Менее секунды.",
    f4_t: "Чёрный список", f4_d: "Блокируйте шумные пары в один клик.",
    f5_t: "Мониторинг", f5_d: "Статус каждого соединения в реальном времени.",
    f6_t: "История", f6_d: "Каждый сигнал сохранён. Аналитика по парам и биржам.",
    how_t: "Как это работает",
    how_1t: "Подключение", how_1d: "WebSocket-потоки со всех 8 бирж. Без задержек.",
    how_2t: "Сравнение", how_2d: "56 комбинаций бирж на символ. Каждый тик.",
    how_3t: "Алерт", how_3d: "Спред превышает порог → мгновенный сигнал с ценами и прибылью.",
    bot_cta: "Начать сканирование",
    foot: "Создан для трейдеров, которые действуют быстро.", copy: "© 2025 FlashArb",
  },
};

/* ── Feature icons (SVG) ── */
const ICONS = {
  exchanges: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>,
  pairs: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
  telegram: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2L11 13"/><path d="M22 2L15 22L11 13L2 9L22 2Z"/></svg>,
  blacklist: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  health: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
  history: <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
};
const ICON_KEYS = ["exchanges", "pairs", "telegram", "blacklist", "health", "history"];

/* ── Animated counter ── */
function AnimN({ to, suf = "" }) {
  const [v, setV] = useState(0);
  const ref = useRef();
  const inView = useInView(ref, { once: true, margin: "-60px" });
  useEffect(() => {
    if (!inView) return;
    let c = 0;
    const step = Math.max(1, Math.floor(to / 30));
    const id = setInterval(() => { c += step; if (c >= to) { setV(to); clearInterval(id); } else setV(c); }, 25);
    return () => clearInterval(id);
  }, [inView, to]);
  return <span ref={ref}>{v.toLocaleString()}{suf}</span>;
}

/* ── Live feed demo ── */
const FEED = [
  { sym: "PEPE", buy: "mexc", sell: "binance", sp: "+2.41" },
  { sym: "FLOKI", buy: "bybit", sell: "okx", sp: "+5.87" },
  { sym: "BONK", buy: "gate", sell: "bitget", sp: "+1.23" },
  { sym: "WIF", buy: "kucoin", sell: "binance", sp: "+3.05" },
  { sym: "SUI", buy: "bingx", sell: "bybit", sp: "+0.94" },
  { sym: "INJ", buy: "mexc", sell: "okx", sp: "+4.12" },
];

function LiveFeed({ label }) {
  const [i, setI] = useState(0);
  useEffect(() => { const id = setInterval(() => setI(x => (x + 1) % FEED.length), 2800); return () => clearInterval(id); }, []);
  const items = [FEED[i], FEED[(i + 1) % FEED.length], FEED[(i + 2) % FEED.length]];
  return (
    <motion.div
      className="feed"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6, duration: 0.5 }}
    >
      <div className="feed-header">
        <span className="feed-dot" />
        <span className="feed-label">{label}</span>
      </div>
      {items.map((f, j) => (
        <motion.div
          key={f.sym + i + j}
          className="feed-row"
          style={{ opacity: j === 0 ? 1 : j === 1 ? 0.4 : 0.15 }}
          initial={j === 0 ? { opacity: 0, x: -10 } : false}
          animate={j === 0 ? { opacity: 1, x: 0 } : false}
          transition={{ duration: 0.35 }}
        >
          <span className="feed-sym">{f.sym}<span className="feed-sym-suffix">USDT</span></span>
          <span className="feed-route">{f.buy} → {f.sell}</span>
          <span className="feed-spread">{f.sp}%</span>
        </motion.div>
      ))}
    </motion.div>
  );
}

/* ── Scroll reveal wrapper ── */
function Reveal({ children, delay = 0, y = 30 }) {
  const ref = useRef();
  const inView = useInView(ref, { once: true, margin: "-80px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {children}
    </motion.div>
  );
}

/* ── Main ── */
export default function Landing() {
  const [lang, setLang] = useState("en");
  const t = L[lang];
  const feats = [
    { t: t.f1_t, d: t.f1_d }, { t: t.f2_t, d: t.f2_d },
    { t: t.f3_t, d: t.f3_d }, { t: t.f4_t, d: t.f4_d },
    { t: t.f5_t, d: t.f5_d }, { t: t.f6_t, d: t.f6_d },
  ];

  return (
    <div className="landing-page">
      <Nav lang={lang} setLang={setLang} />

      {/* ── Hero ── */}
      <section className="hero">
        {/* Mesh gradient background */}
        <div className="mesh-wrap">
          <div className="mesh-blob mesh-blob--blue" />
          <div className="mesh-blob mesh-blob--cyan" />
          <div className="mesh-blob mesh-blob--amber" />
        </div>

        <motion.p className="hero-tag" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.1 }}>
          {t.hero_tag}
        </motion.p>

        <motion.h1 className="hero-h1" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.15 }}>
          {t.hero_h1a}<br />
          <span className="hero-grad">{t.hero_h1b}</span>
        </motion.h1>

        <motion.p className="hero-p" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.3 }}>
          {t.hero_p}
        </motion.p>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.4 }} className="hero-cta-wrap">
          <a href="#/dashboard" className="cta-btn">{t.hero_cta}</a>
        </motion.div>
        <motion.p className="hero-note" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}>
          {t.hero_note}
        </motion.p>

        <div className="hero-feed-wrap">
          <LiveFeed label={t.demo_label} />
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="stats-bar">
        <div className="stats-inner">
          {[
            { n: 700, su: "+", l: lang === "en" ? "pairs" : "пар" },
            { n: 8, su: "", l: lang === "en" ? "exchanges" : "бирж" },
            { n: 56, su: "", l: lang === "en" ? "comparisons/sym" : "сравнений/символ" },
            { n: 50, su: "ms", l: lang === "en" ? "latency" : "задержка" },
          ].map((x, i) => (
            <Reveal key={i} delay={i * 0.08}>
              <div className="stat-item">
                <span className="stat-num"><AnimN to={x.n} suf={x.su} /></span>
                <span className="stat-label">{x.l}</span>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Philosophy ── */}
      <section className="section">
        <Reveal>
          <div className="narrow">
            <h2 className="phil-h">{t.phil_h}</h2>
            <p className="phil-p">{t.phil_p}</p>
          </div>
        </Reveal>
      </section>

      {/* ── Features ── */}
      <section className="section">
        <div className="feat-grid">
          {feats.map((f, i) => (
            <Reveal key={i} delay={i * 0.06}>
              <div className="feat-card">
                <span className="feat-icon">{ICONS[ICON_KEYS[i]]}</span>
                <h3 className="feat-title">{f.t}</h3>
                <p className="feat-desc">{f.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section className="section">
        <Reveal><h2 className="section-title">{t.how_t}</h2></Reveal>
        <div className="how-grid">
          {[
            { n: "01", t: t.how_1t, d: t.how_1d },
            { n: "02", t: t.how_2t, d: t.how_2d },
            { n: "03", t: t.how_3t, d: t.how_3d },
          ].map((h, i) => (
            <Reveal key={i} delay={i * 0.1}>
              <div className="how-card">
                <span className="how-num">{h.n}</span>
                <div className="how-line" />
                <h3 className="how-title">{h.t}</h3>
                <p className="how-desc">{h.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section className="bot-cta">
        <Reveal>
          <h2 className="section-title section-title--compact">
            {t.hero_h1a}<br /><span className="hero-grad">{t.hero_h1b}</span>
          </h2>
          <p className="bot-cta-text">{t.hero_p}</p>
          <a href="#/dashboard" className="cta-btn">{t.bot_cta}</a>
        </Reveal>
      </section>

      {/* ── Footer ── */}
      <footer className="landing-footer">
        <div className="footer-inner">
          <div className="footer-logo">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            <span className="footer-logo-f">Flash</span>
            <span className="footer-logo-a">Arb</span>
          </div>
          <p className="footer-tagline">{t.foot}</p>
          <p className="footer-copy">{t.copy}</p>
        </div>
      </footer>
    </div>
  );
}

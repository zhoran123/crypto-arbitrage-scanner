import React, { useState, useEffect, useRef } from "react";
import { motion, useInView } from "framer-motion";
import Nav from "./Nav";

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
      style={s.feed}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6, duration: 0.5 }}
    >
      <div style={s.feedH}>
        <span style={s.feedDot} />
        <span style={s.feedL}>{label}</span>
      </div>
      {items.map((f, j) => (
        <motion.div
          key={f.sym + i + j}
          style={{ ...s.feedRow, opacity: j === 0 ? 1 : j === 1 ? 0.4 : 0.15 }}
          initial={j === 0 ? { opacity: 0, x: -10 } : false}
          animate={j === 0 ? { opacity: 1, x: 0 } : false}
          transition={{ duration: 0.35 }}
        >
          <span style={s.feedSym}>{f.sym}<span style={{ color: "#334155", fontSize: 11, fontWeight: 400 }}>USDT</span></span>
          <span style={{ color: "#475569", fontSize: 12, fontFamily: "'JetBrains Mono',monospace" }}>{f.buy} → {f.sell}</span>
          <span style={s.feedSp}>{f.sp}%</span>
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
    <div style={s.page}>
      <Nav lang={lang} setLang={setLang} />

      {/* ── Hero ── */}
      <section style={s.hero}>
        {/* Mesh gradient background */}
        <div style={s.meshWrap}>
          <div style={{ ...s.meshBlob, background: "radial-gradient(circle, rgba(14,165,233,0.12) 0%, transparent 70%)", top: -80, left: "30%", animation: "meshMove 20s ease-in-out infinite" }} />
          <div style={{ ...s.meshBlob, background: "radial-gradient(circle, rgba(6,182,212,0.08) 0%, transparent 70%)", top: 40, right: "20%", width: 500, height: 500, animation: "meshMove 25s ease-in-out infinite reverse" }} />
          <div style={{ ...s.meshBlob, background: "radial-gradient(circle, rgba(245,158,11,0.05) 0%, transparent 70%)", bottom: -100, left: "50%", width: 400, height: 400, animation: "meshMove 18s ease-in-out infinite" }} />
        </div>

        <motion.p
          style={s.heroTag}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          {t.hero_tag}
        </motion.p>

        <motion.h1
          style={s.heroH1}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
        >
          {t.hero_h1a}<br />
          <span style={s.heroGrad}>{t.hero_h1b}</span>
        </motion.h1>

        <motion.p
          style={s.heroP}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          {t.hero_p}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
          style={{ marginBottom: 12, position: "relative", zIndex: 1 }}
        >
          <a href="#/dashboard" style={s.ctaBtn}>{t.hero_cta}</a>
        </motion.div>
        <motion.p
          style={s.heroNote}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {t.hero_note}
        </motion.p>

        <div style={{ marginTop: 56, position: "relative", zIndex: 1 }}>
          <LiveFeed label={t.demo_label} />
        </div>
      </section>

      {/* ── Stats ── */}
      <section style={s.statsBar}>
        <div style={s.statsIn}>
          {[
            { n: 700, su: "+", l: lang === "en" ? "pairs" : "пар" },
            { n: 8, su: "", l: lang === "en" ? "exchanges" : "бирж" },
            { n: 56, su: "", l: lang === "en" ? "comparisons/sym" : "сравнений/символ" },
            { n: 50, su: "ms", l: lang === "en" ? "latency" : "задержка" },
          ].map((x, i) => (
            <Reveal key={i} delay={i * 0.08}>
              <div style={s.statItem}>
                <span style={s.statNum}><AnimN to={x.n} suf={x.su} /></span>
                <span style={s.statLbl}>{x.l}</span>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Philosophy ── */}
      <section style={s.sec}>
        <Reveal>
          <div style={s.narrow}>
            <h2 style={s.philH}>{t.phil_h}</h2>
            <p style={s.philP}>{t.phil_p}</p>
          </div>
        </Reveal>
      </section>

      {/* ── Features ── */}
      <section style={s.sec}>
        <div style={s.featGrid}>
          {feats.map((f, i) => (
            <Reveal key={i} delay={i * 0.06}>
              <div style={s.featCard}>
                <span style={s.featIcon}>{ICONS[ICON_KEYS[i]]}</span>
                <h3 style={s.featT}>{f.t}</h3>
                <p style={s.featD}>{f.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── How it works ── */}
      <section style={s.sec}>
        <Reveal><h2 style={s.secTitle}>{t.how_t}</h2></Reveal>
        <div style={s.howGrid}>
          {[
            { n: "01", t: t.how_1t, d: t.how_1d },
            { n: "02", t: t.how_2t, d: t.how_2d },
            { n: "03", t: t.how_3t, d: t.how_3d },
          ].map((h, i) => (
            <Reveal key={i} delay={i * 0.1}>
              <div style={s.howCard}>
                <span style={s.howNum}>{h.n}</span>
                <div style={s.howLine} />
                <h3 style={s.howT}>{h.t}</h3>
                <p style={s.howD}>{h.d}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── Bottom CTA ── */}
      <section style={s.botCta}>
        <Reveal>
          <h2 style={{ ...s.secTitle, marginBottom: 16 }}>
            {t.hero_h1a}<br /><span style={s.heroGrad}>{t.hero_h1b}</span>
          </h2>
          <p style={{ fontSize: 16, color: "#64748b", marginBottom: 32, lineHeight: 1.7 }}>{t.hero_p}</p>
          <a href="#/dashboard" style={s.ctaBtn}>{t.bot_cta}</a>
        </Reveal>
      </section>

      {/* ── Footer ── */}
      <footer style={s.footer}>
        <div style={{ maxWidth: 1100, margin: "0 auto", textAlign: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center" }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
            <span style={{ fontSize: 17, fontWeight: 700, color: "#e2e8f0" }}>Flash</span>
            <span style={{ fontSize: 17, fontWeight: 700, background: "linear-gradient(135deg, #0ea5e9, #06b6d4)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Arb</span>
          </div>
          <p style={{ fontSize: 14, color: "#334155", marginTop: 16 }}>{t.foot}</p>
          <p style={{ fontSize: 12, color: "#1e293b", marginTop: 8 }}>{t.copy}</p>
        </div>
      </footer>
    </div>
  );
}

/* ── Styles ── */
const s = {
  page: { background: "#08090e", color: "#e2e8f0", fontFamily: "'Inter',sans-serif", minHeight: "100vh" },

  /* Hero */
  hero: { maxWidth: 1100, margin: "0 auto", padding: "100px 32px 60px", textAlign: "center", position: "relative", overflow: "hidden" },
  meshWrap: { position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 },
  meshBlob: { position: "absolute", width: 600, height: 600, borderRadius: "50%", filter: "blur(60px)" },
  heroTag: {
    display: "inline-block", fontSize: 12, color: "#0ea5e9", letterSpacing: 3, textTransform: "uppercase",
    marginBottom: 24, fontFamily: "'JetBrains Mono',monospace", fontWeight: 500,
    position: "relative", zIndex: 1,
    padding: "6px 16px", borderRadius: 20,
    background: "rgba(14,165,233,0.06)", border: "1px solid rgba(14,165,233,0.1)",
  },
  heroH1: {
    fontSize: 60, fontWeight: 800, color: "#f1f5f9", lineHeight: 1.1,
    marginBottom: 24, letterSpacing: -2.5, position: "relative", zIndex: 1,
  },
  heroGrad: {
    background: "linear-gradient(135deg, #0ea5e9, #06b6d4, #0ea5e9)",
    backgroundSize: "200% 200%",
    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
    animation: "shimmer 6s linear infinite",
  },
  heroP: {
    fontSize: 17, color: "#64748b", lineHeight: 1.7, maxWidth: 520,
    margin: "0 auto 40px", position: "relative", zIndex: 1,
  },
  ctaBtn: {
    display: "inline-block", position: "relative",
    background: "linear-gradient(135deg, #0ea5e9, #0284c7)",
    color: "#fff", fontSize: 15, fontWeight: 600, padding: "14px 40px",
    borderRadius: 10, textDecoration: "none",
    boxShadow: "0 0 40px rgba(14,165,233,0.2), 0 4px 20px rgba(0,0,0,0.3)",
    transition: "all 0.3s", letterSpacing: -0.2, zIndex: 1,
  },
  heroNote: {
    fontSize: 13, color: "#334155", fontFamily: "'JetBrains Mono',monospace",
    position: "relative", zIndex: 1,
  },

  /* Feed */
  feed: {
    maxWidth: 460, margin: "0 auto",
    background: "rgba(12,14,24,0.7)",
    backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
    border: "1px solid rgba(14,165,233,0.08)", borderRadius: 14, overflow: "hidden",
  },
  feedH: {
    padding: "12px 20px", borderBottom: "1px solid rgba(14,165,233,0.06)",
    display: "flex", alignItems: "center", gap: 8,
  },
  feedDot: {
    width: 7, height: 7, borderRadius: "50%", background: "#10b981",
    display: "inline-block", animation: "pulse 2s infinite",
    boxShadow: "0 0 8px rgba(16,185,129,0.4)",
  },
  feedL: { fontSize: 11, color: "#334155", letterSpacing: 2, fontFamily: "'JetBrains Mono',monospace", fontWeight: 500 },
  feedRow: {
    padding: "13px 20px", display: "flex", justifyContent: "space-between",
    alignItems: "center", borderBottom: "1px solid rgba(14,165,233,0.04)",
    fontFamily: "'JetBrains Mono',monospace", fontSize: 13,
  },
  feedSym: { color: "#e2e8f0", fontWeight: 600, minWidth: 80 },
  feedSp: { color: "#10b981", fontWeight: 600, minWidth: 60, textAlign: "right" },

  /* Stats */
  statsBar: { borderTop: "1px solid rgba(14,165,233,0.06)", borderBottom: "1px solid rgba(14,165,233,0.06)" },
  statsIn: { maxWidth: 1100, margin: "0 auto", padding: "44px 32px", display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 32 },
  statItem: { textAlign: "center" },
  statNum: {
    display: "block", fontSize: 36, fontWeight: 700,
    fontFamily: "'JetBrains Mono',monospace",
    background: "linear-gradient(135deg, #e2e8f0, #0ea5e9)",
    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
  },
  statLbl: { fontSize: 12, color: "#334155", marginTop: 6, display: "block", letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 600 },

  /* Sections */
  sec: { maxWidth: 1100, margin: "0 auto", padding: "80px 32px" },
  narrow: { maxWidth: 600, margin: "0 auto" },
  secTitle: { fontSize: 32, fontWeight: 700, color: "#f1f5f9", textAlign: "center", marginBottom: 48, letterSpacing: -1 },

  /* Philosophy */
  philH: { fontSize: 28, fontWeight: 700, color: "#f1f5f9", marginBottom: 16, lineHeight: 1.3 },
  philP: { fontSize: 16, color: "#64748b", lineHeight: 1.8 },

  /* Features */
  featGrid: { display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, background: "rgba(14,165,233,0.04)", borderRadius: 16, overflow: "hidden", border: "1px solid rgba(14,165,233,0.06)" },
  featCard: { background: "rgba(8,9,14,0.95)", padding: "36px 30px", transition: "background 0.3s" },
  featIcon: { color: "#0ea5e9", marginBottom: 16, display: "block" },
  featT: { fontSize: 16, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 },
  featD: { fontSize: 14, color: "#64748b", lineHeight: 1.7 },

  /* How it works */
  howGrid: { display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 32 },
  howCard: { textAlign: "center" },
  howNum: {
    display: "inline-flex", alignItems: "center", justifyContent: "center",
    width: 40, height: 40, borderRadius: 10,
    fontSize: 14, fontFamily: "'JetBrains Mono',monospace", fontWeight: 600,
    color: "#0ea5e9", background: "rgba(14,165,233,0.06)",
    border: "1px solid rgba(14,165,233,0.1)", marginBottom: 16,
  },
  howLine: { width: 32, height: 1, background: "rgba(14,165,233,0.1)", margin: "0 auto 16px" },
  howT: { fontSize: 17, fontWeight: 600, color: "#e2e8f0", marginBottom: 8 },
  howD: { fontSize: 14, color: "#64748b", lineHeight: 1.7 },

  /* Bottom CTA */
  botCta: {
    maxWidth: 1100, margin: "0 auto", padding: "100px 32px",
    borderTop: "1px solid rgba(14,165,233,0.06)", textAlign: "center",
  },

  /* Footer */
  footer: { borderTop: "1px solid rgba(14,165,233,0.06)", padding: "48px 32px" },
};

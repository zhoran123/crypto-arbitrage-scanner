import React, { useState, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import Nav from "./Nav";

const L = {
  en: {
    title: "One plan. Full access.",
    sub: "No tiers, no hidden limits. Everything included.",
    price: "$29", per: "/mo",
    items: [
      "700+ trading pairs across 8 exchanges",
      "Real-time WebSocket price feeds",
      "Instant Telegram alerts (3 priority levels)",
      "Custom pair blacklist",
      "Full signal history & analytics",
      "Exchange health monitoring",
      "Web dashboard access",
      "Priority support",
    ],
    cta: "Get Access",
    note: "7 days free \u00b7 cancel anytime",
    faq_t: "Questions",
    q1: "What exchanges are supported?", a1: "Binance, Bybit, OKX, Bitget, Gate.io, MEXC, BingX, and KuCoin. All USDT perpetual futures.",
    q2: "How fast are the alerts?", a2: "Sub-second. We use WebSocket connections to every exchange \u2014 no polling, no REST delays.",
    q3: "Can I try it for free?", a3: "Yes. 7-day trial with full access. No card required.",
    q4: "What is net spread?", a4: "The price difference between exchanges minus trading fees on both sides. It shows your actual profit potential.",
  },
  ru: {
    title: "Один тариф. Полный доступ.",
    sub: "Без скрытых ограничений. Всё включено.",
    price: "$29", per: "/мес",
    items: [
      "700+ пар на 8 биржах",
      "WebSocket-фиды в реальном времени",
      "Мгновенные Telegram-алерты (3 уровня)",
      "Чёрный список пар",
      "Полная история и аналитика",
      "Мониторинг состояния бирж",
      "Доступ к веб-дашборду",
      "Приоритетная поддержка",
    ],
    cta: "Получить доступ",
    note: "7 дней бесплатно \u00b7 отмена в любой момент",
    faq_t: "Вопросы",
    q1: "Какие биржи поддерживаются?", a1: "Binance, Bybit, OKX, Bitget, Gate.io, MEXC, BingX и KuCoin. Все USDT-перпетуалы.",
    q2: "Как быстро приходят алерты?", a2: "Менее секунды. WebSocket-подключение к каждой бирже — без поллинга.",
    q3: "Можно попробовать бесплатно?", a3: "Да. 7 дней с полным доступом. Карта не нужна.",
    q4: "Что такое net spread?", a4: "Разница цен между биржами минус комиссии с обеих сторон. Показывает реальную прибыль.",
  },
};

function Reveal({ children, delay = 0 }) {
  const ref = useRef();
  const inView = useInView(ref, { once: true, margin: "-60px" });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 24 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.45, delay, ease: [0.25, 0.1, 0.25, 1] }}
    >
      {children}
    </motion.div>
  );
}

export default function Pricing() {
  const [lang, setLang] = useState("en");
  const [openQ, setOpenQ] = useState(null);
  const [ctaH, setCtaH] = useState(false);
  const t = L[lang];
  const faqs = [[t.q1, t.a1], [t.q2, t.a2], [t.q3, t.a3], [t.q4, t.a4]];

  return (
    <div style={S.page}>
      <Nav lang={lang} setLang={setLang} />

      <section style={S.hero}>
        {/* Mesh background */}
        <div style={S.meshWrap}>
          <div style={{ ...S.meshBlob, background: "radial-gradient(circle, rgba(14,165,233,0.1) 0%, transparent 70%)", top: -60, left: "40%" }} />
          <div style={{ ...S.meshBlob, background: "radial-gradient(circle, rgba(245,158,11,0.04) 0%, transparent 70%)", top: 100, right: "30%", width: 400, height: 400 }} />
        </div>

        <Reveal>
          <h1 style={S.title}>{t.title}</h1>
          <p style={S.sub}>{t.sub}</p>
        </Reveal>

        <Reveal delay={0.15}>
          <div style={S.card}>
            <div style={S.priceRow}>
              <span style={S.price}>{t.price}</span>
              <span style={S.per}>{t.per}</span>
            </div>

            <div style={S.items}>
              {t.items.map((item, i) => (
                <motion.div
                  key={i}
                  style={S.item}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.05, duration: 0.3 }}
                >
                  <span style={S.check}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </span>
                  {item}
                </motion.div>
              ))}
            </div>

            <a
              href="#/dashboard"
              onMouseEnter={() => setCtaH(true)}
              onMouseLeave={() => setCtaH(false)}
              style={{
                ...S.cta,
                boxShadow: ctaH
                  ? "0 0 40px rgba(14,165,233,0.3), 0 4px 20px rgba(0,0,0,0.4)"
                  : "0 0 24px rgba(14,165,233,0.15), 0 4px 16px rgba(0,0,0,0.3)",
                transform: ctaH ? "translateY(-1px)" : "none",
              }}
            >
              {t.cta}
            </a>
            <p style={S.note}>{t.note}</p>
          </div>
        </Reveal>
      </section>

      {/* FAQ */}
      <section style={S.faqSection}>
        <Reveal><h2 style={S.faqTitle}>{t.faq_t}</h2></Reveal>
        <div>
          {faqs.map(([q, a], i) => (
            <Reveal key={i} delay={i * 0.05}>
              <div style={S.faqItem} onClick={() => setOpenQ(openQ === i ? null : i)}>
                <div style={S.faqQ}>
                  <span>{q}</span>
                  <motion.span
                    style={{ color: "#0ea5e9", fontSize: 18, display: "inline-block" }}
                    animate={{ rotate: openQ === i ? 45 : 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    +
                  </motion.span>
                </div>
                <AnimatePresence>
                  {openQ === i && (
                    <motion.p
                      style={S.faqA}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25 }}
                    >
                      {a}
                    </motion.p>
                  )}
                </AnimatePresence>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <footer style={S.footer}>
        <p style={{ fontSize: 12, color: "#1e293b" }}>&copy; 2025 FlashArb</p>
      </footer>
    </div>
  );
}

const S = {
  page: { background: "#08090e", color: "#e2e8f0", fontFamily: "'Inter',sans-serif", minHeight: "100vh" },
  hero: { maxWidth: 560, margin: "0 auto", padding: "100px 32px 60px", textAlign: "center", position: "relative" },
  meshWrap: { position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 },
  meshBlob: { position: "absolute", width: 500, height: 500, borderRadius: "50%", filter: "blur(60px)" },
  title: { fontSize: 38, fontWeight: 700, color: "#f1f5f9", marginBottom: 12, letterSpacing: -1, position: "relative", zIndex: 1 },
  sub: { fontSize: 16, color: "#64748b", marginBottom: 48, position: "relative", zIndex: 1 },
  card: {
    background: "rgba(12,14,24,0.7)",
    backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)",
    border: "1px solid rgba(14,165,233,0.08)",
    borderRadius: 16, padding: "48px 40px", textAlign: "center",
    position: "relative", zIndex: 1,
    boxShadow: "0 0 60px rgba(14,165,233,0.04), 0 8px 32px rgba(0,0,0,0.3)",
  },
  priceRow: { marginBottom: 36 },
  price: {
    fontSize: 60, fontWeight: 700,
    background: "linear-gradient(135deg, #f1f5f9, #0ea5e9)",
    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
  },
  per: { fontSize: 18, color: "#334155", marginLeft: 4 },
  items: { textAlign: "left", marginBottom: 36 },
  item: {
    fontSize: 15, color: "#94a3b8", padding: "11px 0",
    borderBottom: "1px solid rgba(14,165,233,0.05)",
    display: "flex", alignItems: "center", gap: 12,
  },
  check: { display: "flex", flexShrink: 0 },
  cta: {
    display: "block",
    background: "linear-gradient(135deg, #0ea5e9, #0284c7)",
    color: "#fff", fontSize: 16, fontWeight: 600, padding: "16px 0",
    borderRadius: 10, textDecoration: "none",
    marginBottom: 14, transition: "all 0.3s",
  },
  note: { fontSize: 13, color: "#334155", fontFamily: "'JetBrains Mono',monospace" },
  faqSection: { maxWidth: 560, margin: "0 auto", padding: "60px 32px 100px" },
  faqTitle: { fontSize: 28, fontWeight: 700, color: "#f1f5f9", marginBottom: 32, textAlign: "center" },
  faqItem: {
    borderBottom: "1px solid rgba(14,165,233,0.06)", cursor: "pointer",
    padding: "16px 0", transition: "all 0.2s", overflow: "hidden",
  },
  faqQ: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    fontSize: 15, fontWeight: 500, color: "#94a3b8",
  },
  faqA: { fontSize: 14, color: "#64748b", lineHeight: 1.7, marginTop: 12, overflow: "hidden" },
  footer: { borderTop: "1px solid rgba(14,165,233,0.06)", padding: "32px", textAlign: "center" },
};

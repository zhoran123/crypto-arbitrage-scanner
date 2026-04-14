import React, { useState, useRef } from "react";
import { motion, useInView, AnimatePresence } from "framer-motion";
import Nav from "./Nav";
import "./pricing.css";

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
    title: "\u041e\u0434\u0438\u043d \u0442\u0430\u0440\u0438\u0444. \u041f\u043e\u043b\u043d\u044b\u0439 \u0434\u043e\u0441\u0442\u0443\u043f.",
    sub: "\u0411\u0435\u0437 \u0441\u043a\u0440\u044b\u0442\u044b\u0445 \u043e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u0439. \u0412\u0441\u0451 \u0432\u043a\u043b\u044e\u0447\u0435\u043d\u043e.",
    price: "$29", per: "/\u043c\u0435\u0441",
    items: [
      "700+ \u043f\u0430\u0440 \u043d\u0430 8 \u0431\u0438\u0440\u0436\u0430\u0445",
      "WebSocket-\u0444\u0438\u0434\u044b \u0432 \u0440\u0435\u0430\u043b\u044c\u043d\u043e\u043c \u0432\u0440\u0435\u043c\u0435\u043d\u0438",
      "\u041c\u0433\u043d\u043e\u0432\u0435\u043d\u043d\u044b\u0435 Telegram-\u0430\u043b\u0435\u0440\u0442\u044b (3 \u0443\u0440\u043e\u0432\u043d\u044f)",
      "\u0427\u0451\u0440\u043d\u044b\u0439 \u0441\u043f\u0438\u0441\u043e\u043a \u043f\u0430\u0440",
      "\u041f\u043e\u043b\u043d\u0430\u044f \u0438\u0441\u0442\u043e\u0440\u0438\u044f \u0438 \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0430",
      "\u041c\u043e\u043d\u0438\u0442\u043e\u0440\u0438\u043d\u0433 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044f \u0431\u0438\u0440\u0436",
      "\u0414\u043e\u0441\u0442\u0443\u043f \u043a \u0432\u0435\u0431-\u0434\u0430\u0448\u0431\u043e\u0440\u0434\u0443",
      "\u041f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442\u043d\u0430\u044f \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430",
    ],
    cta: "\u041f\u043e\u043b\u0443\u0447\u0438\u0442\u044c \u0434\u043e\u0441\u0442\u0443\u043f",
    note: "7 \u0434\u043d\u0435\u0439 \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e \u00b7 \u043e\u0442\u043c\u0435\u043d\u0430 \u0432 \u043b\u044e\u0431\u043e\u0439 \u043c\u043e\u043c\u0435\u043d\u0442",
    faq_t: "\u0412\u043e\u043f\u0440\u043e\u0441\u044b",
    q1: "\u041a\u0430\u043a\u0438\u0435 \u0431\u0438\u0440\u0436\u0438 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u044e\u0442\u0441\u044f?", a1: "Binance, Bybit, OKX, Bitget, Gate.io, MEXC, BingX \u0438 KuCoin. \u0412\u0441\u0435 USDT-\u043f\u0435\u0440\u043f\u0435\u0442\u0443\u0430\u043b\u044b.",
    q2: "\u041a\u0430\u043a \u0431\u044b\u0441\u0442\u0440\u043e \u043f\u0440\u0438\u0445\u043e\u0434\u044f\u0442 \u0430\u043b\u0435\u0440\u0442\u044b?", a2: "\u041c\u0435\u043d\u0435\u0435 \u0441\u0435\u043a\u0443\u043d\u0434\u044b. WebSocket-\u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u0435 \u043a \u043a\u0430\u0436\u0434\u043e\u0439 \u0431\u0438\u0440\u0436\u0435 \u2014 \u0431\u0435\u0437 \u043f\u043e\u043b\u043b\u0438\u043d\u0433\u0430.",
    q3: "\u041c\u043e\u0436\u043d\u043e \u043f\u043e\u043f\u0440\u043e\u0431\u043e\u0432\u0430\u0442\u044c \u0431\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u043e?", a3: "\u0414\u0430. 7 \u0434\u043d\u0435\u0439 \u0441 \u043f\u043e\u043b\u043d\u044b\u043c \u0434\u043e\u0441\u0442\u0443\u043f\u043e\u043c. \u041a\u0430\u0440\u0442\u0430 \u043d\u0435 \u043d\u0443\u0436\u043d\u0430.",
    q4: "\u0427\u0442\u043e \u0442\u0430\u043a\u043e\u0435 net spread?", a4: "\u0420\u0430\u0437\u043d\u0438\u0446\u0430 \u0446\u0435\u043d \u043c\u0435\u0436\u0434\u0443 \u0431\u0438\u0440\u0436\u0430\u043c\u0438 \u043c\u0438\u043d\u0443\u0441 \u043a\u043e\u043c\u0438\u0441\u0441\u0438\u0438 \u0441 \u043e\u0431\u0435\u0438\u0445 \u0441\u0442\u043e\u0440\u043e\u043d. \u041f\u043e\u043a\u0430\u0437\u044b\u0432\u0430\u0435\u0442 \u0440\u0435\u0430\u043b\u044c\u043d\u0443\u044e \u043f\u0440\u0438\u0431\u044b\u043b\u044c.",
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
  const t = L[lang];
  const faqs = [[t.q1, t.a1], [t.q2, t.a2], [t.q3, t.a3], [t.q4, t.a4]];

  return (
    <div className="pricing-page">
      <Nav lang={lang} setLang={setLang} />

      <section className="pricing-hero">
        {/* Mesh background */}
        <div className="pricing-mesh-wrap">
          <div className="pricing-mesh-blob pricing-mesh-blob--blue" />
          <div className="pricing-mesh-blob pricing-mesh-blob--amber" />
        </div>

        <Reveal>
          <h1 className="pricing-title">{t.title}</h1>
          <p className="pricing-sub">{t.sub}</p>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="pricing-card">
            <div className="pricing-price-row">
              <span className="pricing-price">{t.price}</span>
              <span className="pricing-per">{t.per}</span>
            </div>

            <div className="pricing-items">
              {t.items.map((item, i) => (
                <motion.div
                  key={i}
                  className="pricing-item"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.05, duration: 0.3 }}
                >
                  <span className="pricing-check">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </span>
                  {item}
                </motion.div>
              ))}
            </div>

            <a href="#/dashboard" className="pricing-cta">
              {t.cta}
            </a>
            <p className="pricing-note">{t.note}</p>
          </div>
        </Reveal>
      </section>

      {/* FAQ */}
      <section className="pricing-faq-section">
        <Reveal><h2 className="pricing-faq-title">{t.faq_t}</h2></Reveal>
        <div>
          {faqs.map(([q, a], i) => (
            <Reveal key={i} delay={i * 0.05}>
              <div className="pricing-faq-item" onClick={() => setOpenQ(openQ === i ? null : i)}>
                <div className="pricing-faq-q">
                  <span>{q}</span>
                  <motion.span
                    className="pricing-faq-toggle"
                    animate={{ rotate: openQ === i ? 45 : 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    +
                  </motion.span>
                </div>
                <AnimatePresence>
                  {openQ === i && (
                    <motion.p
                      className="pricing-faq-a"
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

      <footer className="pricing-footer">
        <p className="pricing-footer-copy">&copy; 2025 FlashArb</p>
      </footer>
    </div>
  );
}

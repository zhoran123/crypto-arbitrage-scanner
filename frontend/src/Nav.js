import React, { useState } from "react";
import { motion } from "framer-motion";

const NAV_T = {
  en: { pricing: "Pricing", dash: "Dashboard", open: "Launch App" },
  ru: { pricing: "Тарифы", dash: "Дашборд", open: "Запустить" },
};

function NavLink({ href, children }) {
  const [hov, setHov] = useState(false);
  return (
    <a
      href={href}
      onMouseEnter={() => setHov(true)}
      onMouseLeave={() => setHov(false)}
      style={{
        color: hov ? "#e2e8f0" : "#64748b",
        fontSize: 14, textDecoration: "none", fontWeight: 500,
        transition: "color 0.2s", position: "relative", padding: "4px 0",
      }}
    >
      {children}
      <motion.span
        style={{
          position: "absolute", bottom: -1, left: 0, right: 0,
          height: 1.5, background: "#0ea5e9", originX: 0, borderRadius: 1,
        }}
        initial={{ scaleX: 0 }}
        animate={{ scaleX: hov ? 1 : 0 }}
        transition={{ duration: 0.2 }}
      />
    </a>
  );
}

export default function Nav({ lang, setLang }) {
  const t = NAV_T[lang || "en"];
  const [ctaH, setCtaH] = useState(false);

  return (
    <nav style={S.nav}>
      <div style={S.inner}>
        <a href="#/" style={S.logo}>
          <span style={S.logoIcon}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </span>
          <span style={S.logoF}>Flash</span>
          <span style={S.logoA}>Arb</span>
        </a>

        <div style={S.right}>
          <NavLink href="#/pricing">{t.pricing}</NavLink>
          <NavLink href="#/dashboard">{t.dash}</NavLink>
          {setLang && (
            <button onClick={() => setLang(lang === "en" ? "ru" : "en")} style={S.langBtn}>
              {lang === "en" ? "RU" : "EN"}
            </button>
          )}
          <a
            href="#/dashboard"
            onMouseEnter={() => setCtaH(true)}
            onMouseLeave={() => setCtaH(false)}
            style={{
              ...S.cta,
              boxShadow: ctaH
                ? "0 0 28px rgba(14,165,233,0.3), 0 4px 14px rgba(0,0,0,0.3)"
                : "0 0 16px rgba(14,165,233,0.12), 0 2px 8px rgba(0,0,0,0.2)",
              transform: ctaH ? "translateY(-1px)" : "none",
            }}
          >
            {t.open}
          </a>
        </div>
      </div>
    </nav>
  );
}

const S = {
  nav: {
    position: "sticky", top: 0, zIndex: 100,
    background: "rgba(8,9,14,0.82)",
    backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)",
    borderBottom: "1px solid rgba(14,165,233,0.05)",
  },
  inner: {
    maxWidth: 1200, margin: "0 auto", padding: "14px 32px",
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  logo: { display: "flex", alignItems: "center", gap: 8, textDecoration: "none" },
  logoIcon: {
    width: 30, height: 30, borderRadius: 8,
    background: "rgba(14,165,233,0.07)",
    border: "1px solid rgba(14,165,233,0.1)",
    display: "flex", alignItems: "center", justifyContent: "center",
  },
  logoF: { fontSize: 18, fontWeight: 700, color: "#e2e8f0", letterSpacing: -0.3 },
  logoA: {
    fontSize: 18, fontWeight: 700, letterSpacing: -0.3,
    background: "linear-gradient(135deg, #0ea5e9, #06b6d4)",
    WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
  },
  right: { display: "flex", alignItems: "center", gap: 28 },
  langBtn: {
    background: "rgba(14,165,233,0.05)", border: "1px solid rgba(14,165,233,0.08)",
    borderRadius: 6, color: "#64748b", fontSize: 12, padding: "5px 12px",
    cursor: "pointer", fontFamily: "'JetBrains Mono',monospace", fontWeight: 500,
    transition: "all 0.2s",
  },
  cta: {
    background: "linear-gradient(135deg, #0ea5e9, #0284c7)",
    color: "#fff", fontSize: 13, fontWeight: 600, padding: "9px 22px",
    borderRadius: 8, textDecoration: "none", transition: "all 0.3s",
    letterSpacing: -0.2,
  },
};

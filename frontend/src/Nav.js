import React from "react";
import "./nav.css";

const NAV_T = {
  en: { pricing: "Pricing", dash: "Dashboard", open: "Launch App" },
  ru: { pricing: "Тарифы", dash: "Дашборд", open: "Запустить" },
};

function NavLink({ href, children }) {
  return (
    <a href={href} className="nav-link">
      {children}
      <span className="nav-link-underline" />
    </a>
  );
}

export default function Nav({ lang, setLang }) {
  const t = NAV_T[lang || "en"];

  return (
    <nav className="nav-bar">
      <div className="nav-inner">
        <a href="#/" className="nav-logo">
          <span className="nav-logo-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </span>
          <span className="nav-logo-f">Flash</span>
          <span className="nav-logo-a">Arb</span>
        </a>

        <div className="nav-right">
          <NavLink href="#/pricing">{t.pricing}</NavLink>
          <NavLink href="#/dashboard">{t.dash}</NavLink>
          {setLang && (
            <button onClick={() => setLang(lang === "en" ? "ru" : "en")} className="nav-lang-btn">
              {lang === "en" ? "RU" : "EN"}
            </button>
          )}
          <a href="#/dashboard" className="nav-cta">
            {t.open}
          </a>
        </div>
      </div>
    </nav>
  );
}

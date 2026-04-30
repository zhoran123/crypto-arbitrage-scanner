import React, { useEffect, useState } from "react";
import "./nav.css";

const NAV_T = {
  en: { pricing: "Pricing", dash: "Dashboard", open: "Launch App", telegram: "Telegram" },
  ru: { pricing: "Тарифы", dash: "Дашборд", open: "Запустить" },
};

const IS_FRONTEND_DEV = window.location.port === "3000";
const API = IS_FRONTEND_DEV
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : window.location.origin;

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
  const [telegramUrl, setTelegramUrl] = useState("");

  useEffect(() => {
    let active = true;
    fetch(`${API}/public-config`)
      .then(res => res.ok ? res.json() : null)
      .then(config => {
        if (active && config?.telegram_invite_url) {
          setTelegramUrl(config.telegram_invite_url);
        }
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

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
          {telegramUrl && (
            <a href={telegramUrl} className="nav-telegram" target="_blank" rel="noreferrer">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M22 2L11 13" />
                <path d="M22 2L15 22L11 13L2 9L22 2Z" />
              </svg>
              <span>{t.telegram || "Telegram"}</span>
            </a>
          )}
          <a href="#/dashboard" className="nav-cta">
            {t.open}
          </a>
        </div>
      </div>
    </nav>
  );
}

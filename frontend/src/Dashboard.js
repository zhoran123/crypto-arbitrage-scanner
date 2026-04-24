import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Nav from "./Nav";
import ChartsTab from "./ChartsTab";
import "./dashboard.css";

const _h = window.location.hostname;
const _p = window.location.port === "3000" ? "8000" : window.location.port;
const _pr = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_URL = `${_pr}//${_h}:${_p}/ws`;
const API = `${window.location.protocol}//${_h}:${_p}`;

const EX_COL = {
  binance: "#F0B90B", bybit: "#F7A600", mexc: "#00B897", bingx: "#60a5fa",
  gate: "#60a5fa", bitget: "#00c9a7", okx: "#a78bfa", kucoin: "#23AF91",
  dex: "#f472b6",
};

function fmtP(p) { return p >= 1000 ? p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p >= 1 ? p.toFixed(4) : p.toFixed(6); }
function fmtUSD(v) { if (!v || v <= 0) return "—"; if (v >= 1e6) return "$" + (v / 1e6).toFixed(1) + "M"; if (v >= 1e3) return "$" + (v / 1e3).toFixed(1) + "k"; return "$" + Math.round(v); }
function timeAgo(iso) { const d = (Date.now() - new Date(iso).getTime()) / 1000; return d < 5 ? "now" : d < 60 ? Math.floor(d) + "s" : d < 3600 ? Math.floor(d / 60) + "m" : Math.floor(d / 3600) + "h"; }
function qCol(q) { return q >= 70 ? "#0ea5e9" : q >= 40 ? "#0284c7" : "#1e3a5f"; }
function spreadCol(n) { return n > 0.3 ? "#10b981" : n > 0 ? "#6ee7b7" : n > -0.1 ? "#64748b" : "#475569"; }

export default function Dashboard() {
  const [signals, setSignals] = useState([]);
  const [wsStatus, setWsStatus] = useState("connecting");
  const [stats, setStats] = useState(null);
  const [spreads, setSpreads] = useState([]);
  const [health, setHealth] = useState([]);
  const [history, setHistory] = useState([]);
  const [hStats, setHStats] = useState(null);
  const [blacklist, setBL] = useState([]);
  const [tab, setTab] = useState("spreads");
  const [search, setSearch] = useState("");
  const [tblMin, setTblMin] = useState(-1);
  const [sigMin, setSigMin] = useState(3);
  const [showF, setShowF] = useState(true);
  const [favs, setFavs] = useState(() => {
    try { return JSON.parse(localStorage.getItem("fa_favs") || "[]"); }
    catch { return []; }
  });
  const wsRef = useRef(null); const rcRef = useRef(null);

  const toggleFav = useCallback(sym => {
    const s = sym.toUpperCase();
    setFavs(prev => {
      const next = prev.includes(s) ? prev.filter(x => x !== s) : [s, ...prev];
      try { localStorage.setItem("fa_favs", JSON.stringify(next)); } catch {}
      return next;
    });
  }, []);

  const connectWs = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState <= 1) return;
    setWsStatus("connecting");
    const ws = new WebSocket(WS_URL); wsRef.current = ws;
    ws.onopen = () => setWsStatus("connected");
    ws.onmessage = e => { try { const s = JSON.parse(e.data); setSignals(p => [s, ...p].slice(0, 200)); } catch {} };
    ws.onclose = () => { setWsStatus("disconnected"); rcRef.current = setTimeout(connectWs, 3000); };
    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => { connectWs(); return () => { clearTimeout(rcRef.current); wsRef.current?.close(); }; }, [connectWs]);

  useEffect(() => {
    let a = true;
    async function poll() {
      try {
        const [s, sp, h, b] = await Promise.all([
          fetch(`${API}/stats`), fetch(`${API}/spreads`),
          fetch(`${API}/health`), fetch(`${API}/blacklist`),
        ]);
        if (!a) return;
        setStats(await s.json()); setSpreads(await sp.json());
        setHealth(await h.json()); const bl = await b.json(); setBL(bl.symbols || []);
      } catch {}
    }
    poll(); const id = setInterval(poll, 6000);
    return () => { a = false; clearInterval(id); };
  }, []);

  useEffect(() => {
    if (tab !== "history") return;
    let a = true;
    async function load() {
      try {
        const [h, hs] = await Promise.all([fetch(`${API}/history?limit=100`), fetch(`${API}/history/stats`)]);
        if (!a) return; setHistory(await h.json()); setHStats(await hs.json());
      } catch {}
    }
    load(); const id = setInterval(load, 10000);
    return () => { a = false; clearInterval(id); };
  }, [tab]);

  const [, setTick] = useState(0);
  useEffect(() => { const id = setInterval(() => setTick(t => t + 1), 1000); return () => clearInterval(id); }, []);

  const block = async sym => {
    setBL(p => [...p, sym.toUpperCase()].sort());
    fetch(`${API}/blacklist/add`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol: sym }) })
      .catch(() => setBL(p => p.filter(s => s !== sym.toUpperCase())));
  };
  const unblock = async sym => {
    setBL(p => p.filter(s => s !== sym.toUpperCase()));
    fetch(`${API}/blacklist/remove`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ symbol: sym }) })
      .catch(() => setBL(p => [...p, sym.toUpperCase()].sort()));
  };

  const filtSig = signals.filter(s => s.net_spread_pct >= sigMin);
  const TABS = ["spreads", "charts", "signals", "health", "history", "blacklist"];
  const TAB_LABELS = {
    spreads: "Spreads",
    charts: "Charts",
    signals: `Signals (${filtSig.length})`,
    health: "Health",
    history: "History",
    blacklist: `Blacklist (${blacklist.length})`,
  };
  const TAB_ICONS = {
    spreads: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
    charts: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/><line x1="2" y1="22" x2="22" y2="22"/></svg>,
    signals: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
    health: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
    history: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
    blacklist: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  };

  return (
    <div className="dash-page">
      <Nav lang="en" />
      <div className="status-bar">
        <div className="status-inner">
          <div className="status-left">
            <span className={`dot dot--${wsStatus}`} />
            <span className={`status-text status-text--${wsStatus}`}>
              {wsStatus === "connected" ? "LIVE" : wsStatus === "connecting" ? "CONNECTING" : "OFFLINE"}
            </span>
          </div>
          {stats && (
            <div className="status-right">
              <Chip l="History" v={stats.signals_history} />
              {stats.blacklisted > 0 && <Chip l="Blocked" v={stats.blacklisted} warn />}
            </div>
          )}
        </div>
      </div>
      <div className="tab-bar">
        <div className="tab-inner">
          {TABS.map(t2 => (
            <button key={t2} onClick={() => setTab(t2)} className={`tab${tab === t2 ? " tab--active" : ""}`}>
              <span className="tab-content">
                {TAB_ICONS[t2]}{TAB_LABELS[t2]}
              </span>
              {tab === t2 && (
                <motion.div layoutId="tabIndicator" className="tab-line" transition={{ type: "spring", stiffness: 400, damping: 30 }} />
              )}
            </button>
          ))}
          {tab === "signals" && (
            <button onClick={() => setShowF(v => !v)} className={`tab tab--filter${showF ? " tab--active" : ""}`}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
              </svg>
              Filters
            </button>
          )}
        </div>
      </div>
      <AnimatePresence>
        {tab === "signals" && showF && (
          <motion.div className="filter-bar" initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }}>
            <div className="filter-inner">
              <Slider l="MIN NET SPREAD" v={sigMin} set={setSigMin} min={0} max={10} step={0.1} fmt={v => v.toFixed(1) + "%"} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <main className="dash-main">
        <AnimatePresence mode="wait">
          <motion.div key={tab} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.2 }}>
            {tab === "spreads" && <SpreadsTab spreads={spreads} search={search} setSearch={setSearch} min={tblMin} setMin={setTblMin} onBlock={block} blocked={blacklist} favs={favs} onFav={toggleFav} />}
            {tab === "charts" && <ChartsTab spreads={spreads} favs={favs} onFav={toggleFav} />}
            {tab === "signals" && (
              filtSig.length === 0
                ? <Empty t="Waiting for signals..." d={`${stats?.price_updates?.toLocaleString() || 0} updates processed. Signals appear when spreads exceed thresholds.`} />
                : <div className="signals-list">{filtSig.map((s, i) => <SigCard key={s.timestamp + i} s={s} isNew={i === 0} />)}</div>
            )}
            {tab === "health" && <HealthTab data={health} />}
            {tab === "history" && <HistoryTab data={history} stats={hStats} />}
            {tab === "blacklist" && <BLTab list={blacklist} onUnblock={unblock} />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}

function Chip({ l, v, accent, warn }) {
  return (
    <div className="chip">
      <span className="chip-label">{l}</span>
      <span className={`chip-value${warn ? " chip-value--warn" : accent ? " chip-value--accent" : ""}`}>{v}</span>
    </div>
  );
}

function Slider({ l, v, set, min, max, step, fmt }) {
  return (
    <div className="slider">
      <label className="slider-label">
        {l}<span className="slider-value">{fmt(v)}</span>
      </label>
      <input type="range" min={min} max={max} step={step} value={v} onChange={e => set(parseFloat(e.target.value))} />
    </div>
  );
}

function Empty({ t, d }) {
  return (
    <div className="empty">
      <div className="empty-title">{t}</div>
      <div className="empty-desc">{d}</div>
    </div>
  );
}

function SigCard({ s, isNew }) {
  const c = qCol(s.quality);
  return (
    <motion.div
      className="card card--accent-left"
      style={{ "--accent-color": c, "--accent-bg": `${c}12`, "--accent-border": `${c}25` }}
      initial={isNew ? { opacity: 0, x: -12 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="sig-header">
        <span className="sig-symbol">
          {s.symbol.replace("USDT", "")}<span className="sig-suffix">/USDT</span>
        </span>
        <div className="sig-meta">
          <span className="sig-quality">{s.quality}</span>
          <span className="sig-time">{timeAgo(s.timestamp)}</span>
        </div>
      </div>
      <div className="sig-body">
        <div className="sig-side">
          <div className="sig-side-label sig-side-label--buy">BUY</div>
          <div className="sig-exchange" style={{ color: EX_COL[s.buy_on] || "#94a3b8" }}>{s.buy_on}</div>
          <div className="sig-price">${fmtP(s.buy_price)}</div>
        </div>
        <div className="sig-arrow">
          <span className="sig-arrow-line sig-arrow-line--left" />
          <span className="sig-deviation">{s.deviation_pct.toFixed(3)}%</span>
          <span className="sig-arrow-line sig-arrow-line--right" />
        </div>
        <div className="sig-side">
          <div className="sig-side-label sig-side-label--sell">SELL</div>
          <div className="sig-exchange" style={{ color: EX_COL[s.sell_on] || "#94a3b8" }}>{s.sell_on}</div>
          <div className="sig-price">${fmtP(s.sell_price)}</div>
        </div>
      </div>
      <div className="sig-footer">
        <Metric l="Z-Score" v={s.z_score.toFixed(1)} h={s.z_score >= 5} />
        <Metric l="Net" v={`${s.net_spread_pct >= 0 ? "+" : ""}${s.net_spread_pct.toFixed(3)}%`} h={s.net_spread_pct > 0} />
        <Metric l="Gross" v={`${s.deviation_pct.toFixed(3)}%`} />
      </div>
    </motion.div>
  );
}

function Metric({ l, v, h }) {
  return (
    <div className="metric">
      <span className="metric-label">{l}</span>
      <span className={`metric-value${h ? " metric-value--highlight" : ""}`}>{v}</span>
    </div>
  );
}

function SpreadsTab({ spreads, search, setSearch, min, setMin, onBlock, blocked, favs, onFav }) {
  const favSet = new Set(favs);
  const f = spreads
    .filter(s => {
      if (search && !s.symbol.toLowerCase().includes(search.toLowerCase().replace(/[/usdt]/gi, ""))) return false;
      return s.net_spread >= min;
    })
    .sort((a, b) => {
      const af = favSet.has(a.symbol) ? 1 : 0;
      const bf = favSet.has(b.symbol) ? 1 : 0;
      if (af !== bf) return bf - af;
      return b.net_spread - a.net_spread;
    });
  return (
    <div>
      <div className="spreads-controls">
        <div className="search-box">
          <svg className="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input type="text" placeholder="Search pair..." value={search} onChange={e => setSearch(e.target.value)} className="search-input" />
          {search && <button onClick={() => setSearch("")} className="search-clear">&times;</button>}
        </div>
        <Slider l="MIN NET SPREAD" v={min} set={setMin} min={-1} max={5} step={0.1} fmt={v => v.toFixed(1) + "%"} />
        <div className="spreads-count">
          {f.length} shown &middot; <span className="spreads-profitable">{spreads.filter(s => s.net_spread > 0).length} profitable</span>
        </div>
      </div>
      <div className="tbl-wrap">
        <table className="tbl">
          <thead>
            <tr>
              <th className="th th--narrow"></th>
              <th className="th th--narrow">#</th>
              <th className="th th--left">Symbol</th>
              <th className="th">Buy</th><th className="th">Price</th>
              <th className="th">Sell</th><th className="th">Price</th>
              <th className="th">Gross</th><th className="th">Net</th>
              <th className="th">Max Size</th>
              <th className="th">Exch</th><th className="th th--narrow"></th>
            </tr>
          </thead>
          <tbody>
            {f.map((s, i) => {
              const nc = spreadCol(s.net_spread);
              const isFav = favSet.has(s.symbol);
              return (
                <tr key={s.symbol} className={i % 2 === 0 ? "tbl-row--even" : "tbl-row--odd"}>
                  <td className="td">
                    <button
                      onClick={() => onFav(s.symbol)}
                      className={`fav-btn${isFav ? " fav-btn--active" : ""}`}
                      title={isFav ? "Unpin" : "Pin to top"}
                    >
                      {isFav ? "★" : "☆"}
                    </button>
                  </td>
                  <td className="td td--muted">{i + 1}</td>
                  <td className="td td--left">
                    <span className="tbl-symbol">{s.symbol.replace("USDT", "")}</span>
                    <span className="tbl-suffix">/USDT</span>
                  </td>
                  <td className="td"><span className="exchange-name" style={{ color: EX_COL[s.buy_on] || "#94a3b8" }}>{s.buy_on}</span></td>
                  <td className="td td--price">${fmtP(s.buy_price)}</td>
                  <td className="td"><span className="exchange-name" style={{ color: EX_COL[s.sell_on] || "#94a3b8" }}>{s.sell_on}</span></td>
                  <td className="td td--price">${fmtP(s.sell_price)}</td>
                  <td className="td td--price">{s.gross_spread.toFixed(3)}%</td>
                  <td className="td td--emphasis" style={{ color: nc }}>{s.net_spread >= 0 ? "+" : ""}{s.net_spread.toFixed(3)}%</td>
                  <td className="td td--price" title="Max USD notional with <0.2% slippage per leg">{fmtUSD(s.max_size_usd)}</td>
                  <td className="td td--exchanges">{s.exchanges}</td>
                  <td className="td">
                    <button
                      onClick={() => onBlock(s.symbol)}
                      className={`block-btn${blocked.includes(s.symbol) ? " block-btn--muted" : ""}`}
                    >
                      &times; block
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {f.length === 0 && <Empty t="No matches" d="Adjust search or spread filter" />}
      </div>
    </div>
  );
}

function HealthTab({ data }) {
  if (!data.length) return <Empty t="Loading..." d="" />;
  return (
    <div className="health-grid">
      {data.map((h, idx) => {
        const c = h.status === "online" ? "#10b981" : h.status === "lagging" ? "#f59e0b" : "#ef4444";
        return (
          <motion.div
            key={h.exchange}
            className="card card--accent-left"
            style={{ "--accent-color": c, "--accent-bg": `${c}12`, "--accent-border": `${c}25` }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.04, duration: 0.3 }}
          >
            <div className="health-header">
              <span className="health-name" style={{ color: EX_COL[h.exchange] || "#e2e8f0" }}>{h.exchange.toUpperCase()}</span>
              <span className="health-status">{h.status}</span>
            </div>
            <div className="health-metrics">
              <Metric l="Last update" v={`${h.last_update_sec}s`} h={h.last_update_sec < 10} />
              <Metric l="Pairs" v={h.symbols_active} />
              <Metric l="Upd/sec" v={h.updates_per_sec} h={h.updates_per_sec > 10} />
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

function HistoryTab({ data, stats }) {
  return (
    <div>
      {stats && stats.total > 0 && (
        <div className="history-stats">
          <motion.div className="card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3 }}>
            <div className="history-stat-label">TOTAL</div>
            <div className="history-stat-value history-stat-value--primary">{stats.total}</div>
          </motion.div>
          {stats.top_symbols?.slice(0, 5).map((s, idx) => (
            <motion.div key={s.symbol} className="card" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.05 * (idx + 1), duration: 0.3 }}>
              <div className="history-stat-label">{s.symbol}</div>
              <div className="history-stat-value">{s.count}</div>
            </motion.div>
          ))}
        </div>
      )}
      {data.length === 0
        ? <Empty t="No history yet" d="Signals will appear as they are generated" />
        : (
          <div className="tbl-wrap">
            <table className="tbl">
              <thead>
                <tr>
                  <th className="th th--left">Symbol</th>
                  <th className="th">Buy</th><th className="th">Sell</th>
                  <th className="th">Gross</th><th className="th">Net</th>
                  <th className="th">Q</th><th className="th">Time</th>
                </tr>
              </thead>
              <tbody>
                {data.map((s, i) => (
                  <tr key={i} className={i % 2 === 0 ? "tbl-row--even" : "tbl-row--odd"}>
                    <td className="td td--left">
                      <span className="tbl-symbol">{s.symbol?.replace("USDT", "")}</span>
                      <span className="tbl-suffix">/USDT</span>
                    </td>
                    <td className="td"><span className="exchange-name" style={{ color: EX_COL[s.buy_on] || "#94a3b8" }}>{s.buy_on}</span></td>
                    <td className="td"><span className="exchange-name" style={{ color: EX_COL[s.sell_on] || "#94a3b8" }}>{s.sell_on}</span></td>
                    <td className="td td--price">{s.deviation_pct?.toFixed(3)}%</td>
                    <td className="td td--emphasis" style={{ color: spreadCol(s.net_spread_pct) }}>
                      {s.net_spread_pct >= 0 ? "+" : ""}{s.net_spread_pct?.toFixed(3)}%
                    </td>
                    <td className="td td--quality" style={{ color: qCol(s.quality) }}>{s.quality}</td>
                    <td className="td td--time">{timeAgo(s.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
    </div>
  );
}

function BLTab({ list, onUnblock }) {
  if (!list.length) return <Empty t="Blacklist is empty" d="Block symbols from the Spreads tab" />;
  return (
    <div className="bl-grid">
      {list.map((sym, idx) => (
        <motion.div key={sym} className="card bl-item" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: idx * 0.03, duration: 0.2 }}>
          <span className="bl-symbol">
            {sym.replace("USDT", "")}<span className="bl-suffix">/USDT</span>
          </span>
          <button onClick={() => onUnblock(sym)} className="unblock-btn">Unblock</button>
        </motion.div>
      ))}
    </div>
  );
}

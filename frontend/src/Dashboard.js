import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Nav from "./Nav";

const _h = window.location.hostname;
const _p = window.location.port === "3000" ? "8000" : window.location.port;
const _pr = window.location.protocol === "https:" ? "wss:" : "ws:";
const WS_URL = `${_pr}//${_h}:${_p}/ws`;
const API = `${window.location.protocol}//${_h}:${_p}`;

const EX_COL = {
  binance: "#F0B90B", bybit: "#F7A600", mexc: "#00B897", bingx: "#60a5fa",
  gate: "#60a5fa", bitget: "#00c9a7", okx: "#a78bfa", kucoin: "#23AF91",
};

function fmtP(p) { return p >= 1000 ? p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : p >= 1 ? p.toFixed(4) : p.toFixed(6); }
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
  const [sigMin, setSigMin] = useState(0);
  const [showF, setShowF] = useState(false);
  const wsRef = useRef(null); const rcRef = useRef(null);

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
  const TABS = ["spreads", "signals", "health", "history", "blacklist"];
  const TAB_LABELS = {
    spreads: "Spreads",
    signals: `Signals (${filtSig.length})`,
    health: "Health",
    history: "History",
    blacklist: `Blacklist (${blacklist.length})`,
  };
  const TAB_ICONS = {
    spreads: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
    signals: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>,
    health: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
    history: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>,
    blacklist: <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
  };

  const statusColor = wsStatus === "connected" ? "#10b981" : wsStatus === "connecting" ? "#0ea5e9" : "#ef4444";
  const statusGlow = wsStatus === "connected" ? "0 0 10px rgba(16,185,129,0.4)" : "none";

  return (
    <div style={S.page}>
      <Nav lang="en" />

      {/* Status Bar */}
      <div style={S.statusBar}>
        <div style={S.statusIn}>
          <div style={S.statusLeft}>
            <span style={{ ...S.dot, background: statusColor, boxShadow: statusGlow }} />
            <span style={{ color: statusColor, fontSize: 12, fontWeight: 600, letterSpacing: 1.5, fontFamily: "'JetBrains Mono',monospace" }}>
              {wsStatus === "connected" ? "LIVE" : wsStatus === "connecting" ? "CONNECTING" : "OFFLINE"}
            </span>
          </div>
          {stats && (
            <div style={S.statusRight}>
              <Chip l="History" v={stats.signals_history} />
              {stats.blacklisted > 0 && <Chip l="Blocked" v={stats.blacklisted} warn />}
            </div>
          )}
        </div>
      </div>

      {/* Tab Bar */}
      <div style={S.tabBar}>
        <div style={S.tabIn}>
          {TABS.map(t2 => (
            <button key={t2} onClick={() => setTab(t2)} style={{ ...S.tab, ...(tab === t2 ? S.tabA : {}) }}>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                {TAB_ICONS[t2]}{TAB_LABELS[t2]}
              </span>
              {tab === t2 && (
                <motion.div
                  layoutId="tabIndicator"
                  style={S.tabLine}
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
            </button>
          ))}
          {tab === "signals" && (
            <button
              onClick={() => setShowF(v => !v)}
              style={{ ...S.tab, marginLeft: "auto", color: showF ? "#0ea5e9" : "#334155" }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
              </svg>
              Filters
            </button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <AnimatePresence>
        {tab === "signals" && showF && (
          <motion.div
            style={S.filterBar}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div style={S.filterIn}>
              <Slider l="MIN NET SPREAD" v={sigMin} set={setSigMin} min={0} max={5} step={0.1} fmt={v => v.toFixed(1) + "%"} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main style={S.main}>
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.2 }}
          >
            {tab === "spreads" && <SpreadsTab spreads={spreads} search={search} setSearch={setSearch} min={tblMin} setMin={setTblMin} onBlock={block} blocked={blacklist} />}
            {tab === "signals" && (
              filtSig.length === 0
                ? <Empty t="Waiting for signals..." d={`${stats?.price_updates?.toLocaleString() || 0} updates processed. Signals appear when spreads exceed thresholds.`} />
                : <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{filtSig.map((s, i) => <SigCard key={s.timestamp + i} s={s} isNew={i === 0} />)}</div>
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

/* ─── Sub-components ─── */

function Chip({ l, v, accent, warn }) {
  const color = warn ? "#ef4444" : accent ? "#0ea5e9" : "#94a3b8";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end" }}>
      <span style={{ fontSize: 9, color: "#334155", letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 600, fontFamily: "'JetBrains Mono',monospace" }}>{l}</span>
      <span style={{ fontSize: 13, fontWeight: 600, color, fontFamily: "'JetBrains Mono',monospace" }}>{v}</span>
    </div>
  );
}

function Slider({ l, v, set, min, max, step, fmt }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 200, flex: 1 }}>
      <label style={{ fontSize: 9, color: "#334155", letterSpacing: 1.5, textTransform: "uppercase", display: "flex", justifyContent: "space-between", fontWeight: 600, fontFamily: "'JetBrains Mono',monospace" }}>
        {l}<span style={{ color: "#0ea5e9", fontSize: 12, fontWeight: 600 }}>{fmt(v)}</span>
      </label>
      <input type="range" min={min} max={max} step={step} value={v} onChange={e => set(parseFloat(e.target.value))} style={{ width: "100%" }} />
    </div>
  );
}

function Empty({ t, d }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: 300, textAlign: "center", gap: 12 }}>
      <div style={{ fontSize: 18, fontWeight: 600, color: "#1e3a5f" }}>{t}</div>
      <div style={{ fontSize: 13, color: "#475569", maxWidth: 420, lineHeight: 1.6 }}>{d}</div>
    </div>
  );
}

function SigCard({ s, isNew }) {
  const c = qCol(s.quality);
  return (
    <motion.div
      style={{ ...S.card, borderLeft: `3px solid ${c}` }}
      initial={isNew ? { opacity: 0, x: -12 } : false}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
        <span style={{ fontSize: 16, fontWeight: 700, color: "#e2e8f0" }}>
          {s.symbol.replace("USDT", "")}<span style={{ color: "#334155", fontSize: 12, fontWeight: 400 }}>/USDT</span>
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{
            fontSize: 11, color: c, fontWeight: 600,
            background: `${c}12`, padding: "3px 10px", borderRadius: 6,
            border: `1px solid ${c}25`,
          }}>{s.quality}</span>
          <span style={{ fontSize: 11, color: "#475569", fontFamily: "'JetBrains Mono',monospace" }}>{timeAgo(s.timestamp)}</span>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
        <div style={{ textAlign: "center", minWidth: 90 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 2, color: "#10b981" }}>BUY</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: EX_COL[s.buy_on] || "#94a3b8" }}>{s.buy_on}</div>
          <div style={{ fontSize: 12, color: "#475569", fontFamily: "'JetBrains Mono',monospace" }}>${fmtP(s.buy_price)}</div>
        </div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ flex: 1, height: 1, background: "linear-gradient(90deg, transparent, rgba(14,165,233,0.15))" }} />
          <span style={{
            fontSize: 12, fontWeight: 700, color: "#e2e8f0", whiteSpace: "nowrap",
            padding: "3px 10px", background: "rgba(14,165,233,0.08)", borderRadius: 6,
            fontFamily: "'JetBrains Mono',monospace",
          }}>{s.deviation_pct.toFixed(3)}%</span>
          <span style={{ flex: 1, height: 1, background: "linear-gradient(90deg, rgba(14,165,233,0.15), transparent)" }} />
        </div>
        <div style={{ textAlign: "center", minWidth: 90 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 2, color: "#ef4444" }}>SELL</div>
          <div style={{ fontSize: 13, fontWeight: 600, color: EX_COL[s.sell_on] || "#94a3b8" }}>{s.sell_on}</div>
          <div style={{ fontSize: 12, color: "#475569", fontFamily: "'JetBrains Mono',monospace" }}>${fmtP(s.sell_price)}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 24, paddingTop: 12, borderTop: "1px solid rgba(14,165,233,0.06)" }}>
        <Metric l="Z-Score" v={s.z_score.toFixed(1)} h={s.z_score >= 5} />
        <Metric l="Net" v={`${s.net_spread_pct >= 0 ? "+" : ""}${s.net_spread_pct.toFixed(3)}%`} h={s.net_spread_pct > 0} />
        <Metric l="Gross" v={`${s.deviation_pct.toFixed(3)}%`} />
      </div>
    </motion.div>
  );
}

function Metric({ l, v, h }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontSize: 9, color: "#334155", letterSpacing: 1.5, textTransform: "uppercase", fontWeight: 600, fontFamily: "'JetBrains Mono',monospace" }}>{l}</span>
      <span style={{ fontSize: 14, fontWeight: 600, color: h ? "#0ea5e9" : "#64748b", fontFamily: "'JetBrains Mono',monospace" }}>{v}</span>
    </div>
  );
}

function SpreadsTab({ spreads, search, setSearch, min, setMin, onBlock, blocked }) {
  const f = spreads.filter(s => {
    if (search && !s.symbol.toLowerCase().includes(search.toLowerCase().replace(/[/usdt]/gi, ""))) return false;
    return s.net_spread >= min;
  });
  return (
    <div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 20, marginBottom: 16, flexWrap: "wrap" }}>
        <div style={S.searchBox}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8, flexShrink: 0 }}>
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input type="text" placeholder="Search pair..." value={search} onChange={e => setSearch(e.target.value)} style={S.searchIn} />
          {search && <button onClick={() => setSearch("")} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 14, padding: 4 }}>&times;</button>}
        </div>
        <Slider l="MIN NET SPREAD" v={min} set={setMin} min={-1} max={5} step={0.1} fmt={v => v.toFixed(1) + "%"} />
        <div style={{ fontSize: 12, color: "#64748b", whiteSpace: "nowrap", fontFamily: "'JetBrains Mono',monospace" }}>
          {f.length} shown &middot; <span style={{ color: "#10b981" }}>{spreads.filter(s => s.net_spread > 0).length} profitable</span>
        </div>
      </div>
      <div style={S.tblWrap}>
        <table style={S.tbl}>
          <thead>
            <tr>
              <th style={{ ...S.th, width: 40 }}>#</th>
              <th style={{ ...S.th, textAlign: "left" }}>Symbol</th>
              <th style={S.th}>Buy</th><th style={S.th}>Price</th>
              <th style={S.th}>Sell</th><th style={S.th}>Price</th>
              <th style={S.th}>Gross</th><th style={S.th}>Net</th>
              <th style={S.th}>Exch</th><th style={{ ...S.th, width: 40 }}></th>
            </tr>
          </thead>
          <tbody>
            {f.map((s, i) => {
              const nc = spreadCol(s.net_spread);
              return (
                <tr key={s.symbol} style={{ background: i % 2 === 0 ? "rgba(8,9,14,0.5)" : "rgba(12,14,24,0.5)" }}>
                  <td style={{ ...S.td, color: "#1e293b" }}>{i + 1}</td>
                  <td style={{ ...S.td, textAlign: "left" }}>
                    <span style={{ fontWeight: 700, color: "#e2e8f0", fontSize: 13 }}>{s.symbol.replace("USDT", "")}</span>
                    <span style={{ color: "#334155", fontSize: 11 }}>/USDT</span>
                  </td>
                  <td style={S.td}><span style={{ color: EX_COL[s.buy_on] || "#94a3b8", fontWeight: 600 }}>{s.buy_on}</span></td>
                  <td style={{ ...S.td, color: "#64748b" }}>${fmtP(s.buy_price)}</td>
                  <td style={S.td}><span style={{ color: EX_COL[s.sell_on] || "#94a3b8", fontWeight: 600 }}>{s.sell_on}</span></td>
                  <td style={{ ...S.td, color: "#64748b" }}>${fmtP(s.sell_price)}</td>
                  <td style={{ ...S.td, color: "#64748b" }}>{s.gross_spread.toFixed(3)}%</td>
                  <td style={{ ...S.td, color: nc, fontWeight: 700 }}>{s.net_spread >= 0 ? "+" : ""}{s.net_spread.toFixed(3)}%</td>
                  <td style={{ ...S.td, color: "#334155" }}>{s.exchanges}</td>
                  <td style={S.td}>
                    <button onClick={() => onBlock(s.symbol)} style={{
                      background: "none", border: "none", cursor: "pointer", fontSize: 11,
                      opacity: blocked.includes(s.symbol) ? 0.2 : 0.5, color: "#ef4444",
                      transition: "opacity 0.2s", display: "flex", alignItems: "center", gap: 3,
                      fontFamily: "'JetBrains Mono',monospace", fontWeight: 600,
                    }}>&times; block</button>
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
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
      {data.map((h, idx) => {
        const c = h.status === "online" ? "#10b981" : h.status === "lagging" ? "#f59e0b" : "#ef4444";
        return (
          <motion.div
            key={h.exchange}
            style={{ ...S.card, borderLeft: `3px solid ${c}` }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.04, duration: 0.3 }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: EX_COL[h.exchange] || "#e2e8f0" }}>{h.exchange.toUpperCase()}</span>
              <span style={{
                fontSize: 11, color: c, fontWeight: 600,
                background: `${c}12`, padding: "3px 12px", borderRadius: 6,
                border: `1px solid ${c}25`,
              }}>{h.status}</span>
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
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
        <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
          <motion.div style={S.card} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.3 }}>
            <div style={{ fontSize: 9, color: "#334155", marginBottom: 4, letterSpacing: 1.5, fontWeight: 600, textTransform: "uppercase", fontFamily: "'JetBrains Mono',monospace" }}>TOTAL</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: "#0ea5e9", fontFamily: "'JetBrains Mono',monospace" }}>{stats.total}</div>
          </motion.div>
          {stats.top_symbols?.slice(0, 5).map((s, idx) => (
            <motion.div
              key={s.symbol}
              style={S.card}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.05 * (idx + 1), duration: 0.3 }}
            >
              <div style={{ fontSize: 9, color: "#334155", marginBottom: 4, letterSpacing: 1.5, fontWeight: 600, fontFamily: "'JetBrains Mono',monospace" }}>{s.symbol}</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#94a3b8", fontFamily: "'JetBrains Mono',monospace" }}>{s.count}</div>
            </motion.div>
          ))}
        </div>
      )}
      {data.length === 0
        ? <Empty t="No history yet" d="Signals will appear as they are generated" />
        : (
          <div style={S.tblWrap}>
            <table style={S.tbl}>
              <thead>
                <tr>
                  <th style={{ ...S.th, textAlign: "left" }}>Symbol</th>
                  <th style={S.th}>Buy</th><th style={S.th}>Sell</th>
                  <th style={S.th}>Gross</th><th style={S.th}>Net</th>
                  <th style={S.th}>Q</th><th style={S.th}>Time</th>
                </tr>
              </thead>
              <tbody>
                {data.map((s, i) => (
                  <tr key={i} style={{ background: i % 2 === 0 ? "rgba(8,9,14,0.5)" : "rgba(12,14,24,0.5)" }}>
                    <td style={{ ...S.td, textAlign: "left" }}>
                      <span style={{ fontWeight: 700, color: "#e2e8f0" }}>{s.symbol?.replace("USDT", "")}</span>
                      <span style={{ color: "#334155" }}>/USDT</span>
                    </td>
                    <td style={S.td}><span style={{ color: EX_COL[s.buy_on] || "#94a3b8", fontWeight: 600 }}>{s.buy_on}</span></td>
                    <td style={S.td}><span style={{ color: EX_COL[s.sell_on] || "#94a3b8", fontWeight: 600 }}>{s.sell_on}</span></td>
                    <td style={{ ...S.td, color: "#64748b" }}>{s.deviation_pct?.toFixed(3)}%</td>
                    <td style={{ ...S.td, color: spreadCol(s.net_spread_pct), fontWeight: 700 }}>
                      {s.net_spread_pct >= 0 ? "+" : ""}{s.net_spread_pct?.toFixed(3)}%
                    </td>
                    <td style={{ ...S.td, color: qCol(s.quality) }}>{s.quality}</td>
                    <td style={{ ...S.td, color: "#475569", fontSize: 11 }}>{timeAgo(s.timestamp)}</td>
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
    <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
      {list.map((sym, idx) => (
        <motion.div
          key={sym}
          style={{ ...S.card, display: "flex", alignItems: "center", gap: 12, padding: "10px 16px" }}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: idx * 0.03, duration: 0.2 }}
        >
          <span style={{ fontWeight: 700, color: "#e2e8f0", fontSize: 14 }}>
            {sym.replace("USDT", "")}<span style={{ color: "#334155", fontSize: 12 }}>/USDT</span>
          </span>
          <button onClick={() => onUnblock(sym)} style={{
            background: "rgba(14,165,233,0.06)", border: "1px solid rgba(14,165,233,0.1)",
            borderRadius: 6, color: "#0ea5e9", fontSize: 11, fontFamily: "inherit",
            padding: "4px 12px", cursor: "pointer", transition: "all 0.2s",
          }}>Unblock</button>
        </motion.div>
      ))}
    </div>
  );
}

/* ─── Styles ─── */

const S = {
  page: {
    background: "#08090e", color: "#e2e8f0",
    fontFamily: "'Inter',sans-serif", minHeight: "100vh",
  },
  statusBar: {
    borderBottom: "1px solid rgba(14,165,233,0.06)",
    background: "rgba(10,12,20,0.6)",
  },
  statusIn: {
    maxWidth: 1200, margin: "0 auto", padding: "10px 32px",
    display: "flex", justifyContent: "space-between", alignItems: "center",
  },
  statusLeft: { display: "flex", alignItems: "center", gap: 8 },
  statusRight: { display: "flex", alignItems: "center", gap: 20 },
  dot: { width: 8, height: 8, borderRadius: "50%", display: "inline-block" },
  tabBar: {
    borderBottom: "1px solid rgba(14,165,233,0.06)",
    background: "rgba(10,12,20,0.4)",
  },
  tabIn: {
    maxWidth: 1200, margin: "0 auto", padding: "0 32px",
    display: "flex", gap: 0, overflowX: "auto",
  },
  tab: {
    background: "none", border: "none",
    color: "#334155", fontSize: 13, fontWeight: 500,
    fontFamily: "inherit", padding: "12px 18px",
    cursor: "pointer", whiteSpace: "nowrap", transition: "color 0.2s",
    display: "flex", alignItems: "center", gap: 6,
    position: "relative",
  },
  tabA: { color: "#0ea5e9" },
  tabLine: {
    position: "absolute", bottom: 0, left: 8, right: 8,
    height: 2, background: "#0ea5e9", borderRadius: 1,
  },
  filterBar: {
    borderBottom: "1px solid rgba(14,165,233,0.06)",
    background: "rgba(10,12,20,0.4)", overflow: "hidden",
  },
  filterIn: {
    maxWidth: 1200, margin: "0 auto", padding: "12px 32px",
    display: "flex", gap: 20, flexWrap: "wrap",
  },
  main: { maxWidth: 1200, margin: "0 auto", padding: 24 },
  card: {
    background: "rgba(12,14,24,0.6)",
    backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
    borderRadius: 12, padding: "18px 22px",
    border: "1px solid rgba(14,165,233,0.06)",
    transition: "border-color 0.2s, box-shadow 0.2s",
  },
  searchBox: {
    display: "flex", alignItems: "center",
    background: "rgba(12,14,24,0.6)",
    border: "1px solid rgba(14,165,233,0.06)",
    borderRadius: 8, padding: "0 14px",
    flex: "1 1 200px", minWidth: 180,
    transition: "border-color 0.2s",
  },
  searchIn: {
    background: "none", border: "none", color: "#e2e8f0",
    fontSize: 13, fontFamily: "inherit", padding: "10px 0",
    outline: "none", width: "100%",
  },
  tblWrap: {
    overflowX: "auto", borderRadius: 10,
    border: "1px solid rgba(14,165,233,0.06)",
    background: "rgba(10,12,20,0.4)",
  },
  tbl: {
    width: "100%", borderCollapse: "collapse",
    fontSize: 12, fontFamily: "'JetBrains Mono',monospace",
  },
  th: {
    padding: "10px 12px", textAlign: "center",
    color: "#334155", fontSize: 9, fontWeight: 600,
    letterSpacing: 1.5, textTransform: "uppercase",
    borderBottom: "1px solid rgba(14,165,233,0.06)",
    background: "rgba(12,14,24,0.5)", whiteSpace: "nowrap",
    fontFamily: "'JetBrains Mono',monospace",
  },
  td: {
    padding: "9px 12px", textAlign: "center",
    borderBottom: "1px solid rgba(14,165,233,0.04)",
    whiteSpace: "nowrap", fontSize: 12,
  },
};

import React, { useState, useEffect, useRef, useCallback } from "react";
import { createChart, CrosshairMode, LineStyle } from "lightweight-charts";

const _h = window.location.hostname;
const _p = window.location.port === "3000" ? "8000" : window.location.port;
const API = `${window.location.protocol}//${_h}:${_p}`;

const EX_COL = {
  binance: "#F0B90B", bybit: "#F7A600", mexc: "#00B897", bingx: "#60a5fa",
  gate: "#60a5fa", bitget: "#00c9a7", okx: "#a78bfa", kucoin: "#23AF91",
};

const TFS = ["1m", "5m", "15m", "30m", "1h", "4h"];
const PER_PAGE = 6;

function MiniChart({ symbol, tf, height }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef({});
  const [hidden, setHidden] = useState({});
  const [exchanges, setExchanges] = useState([]);

  const fetchData = useCallback(async () => {
    try {
      const r = await fetch(`${API}/price-history?symbol=${symbol}&tf=${tf}`);
      const data = await r.json();
      const exchs = Object.keys(data).filter(ex => data[ex]?.length > 0);
      setExchanges(exchs);
      return data;
    } catch {
      return null;
    }
  }, [symbol, tf]);

  // Create chart once
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: height - 40,
      layout: {
        background: { color: "transparent" },
        textColor: "#475569",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "rgba(14,165,233,0.04)" },
        horzLines: { color: "rgba(14,165,233,0.04)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: "rgba(14,165,233,0.3)",
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: "#0c0e18",
        },
        horzLine: {
          color: "rgba(14,165,233,0.3)",
          width: 1,
          style: LineStyle.Dashed,
          labelBackgroundColor: "#0c0e18",
        },
      },
      rightPriceScale: {
        borderColor: "rgba(14,165,233,0.08)",
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: "rgba(14,165,233,0.08)",
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      handleScroll: false,
      handleScale: false,
    });
    chartRef.current = chart;

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = {};
    };
  }, [height]);

  // Fetch & update data
  useEffect(() => {
    if (!chartRef.current) return;
    let active = true;

    async function update() {
      const data = await fetchData();
      if (!data || !active || !chartRef.current) return;

      const chart = chartRef.current;

      // Remove old series
      Object.values(seriesRef.current).forEach(s => {
        try { chart.removeSeries(s); } catch {}
      });
      seriesRef.current = {};

      // Add new series
      Object.keys(data).forEach(ex => {
        if (!data[ex]?.length) return;
        const series = chart.addLineSeries({
          color: EX_COL[ex] || "#94a3b8",
          lineWidth: 1.5,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerRadius: 3,
          crosshairMarkerBorderColor: EX_COL[ex] || "#94a3b8",
          crosshairMarkerBackgroundColor: "#08090e",
        });
        const points = data[ex].map(c => ({
          time: c.t,
          value: c.c,
        }));
        series.setData(points);
        if (hidden[ex]) series.applyOptions({ visible: false });
        seriesRef.current[ex] = series;
      });

      chart.timeScale().fitContent();
    }

    update();
    const interval = tf === "1m" ? 10000 : 30000;
    const id = setInterval(update, interval);
    return () => { active = false; clearInterval(id); };
  }, [tf, fetchData, hidden]);

  // Toggle visibility without re-fetch
  const toggleExch = ex => {
    setHidden(h => {
      const next = { ...h, [ex]: !h[ex] };
      const s = seriesRef.current[ex];
      if (s) s.applyOptions({ visible: !next[ex] });
      return next;
    });
  };

  return (
    <div style={CS.chartCard}>
      {/* Header */}
      <div style={CS.chartHeader}>
        <span style={CS.chartSymbol}>
          {symbol.replace("USDT", "")}
          <span style={{ color: "#334155", fontSize: 11, fontWeight: 400 }}>/USDT</span>
        </span>
      </div>

      {/* Exchange toggles */}
      {exchanges.length > 0 && (
        <div style={CS.exchRow}>
          {exchanges.map(ex => (
            <button key={ex} onClick={() => toggleExch(ex)} style={{
              background: hidden[ex] ? "rgba(30,41,59,0.4)" : `${EX_COL[ex] || "#94a3b8"}18`,
              border: `1px solid ${hidden[ex] ? "rgba(30,41,59,0.5)" : (EX_COL[ex] || "#94a3b8") + "40"}`,
              borderRadius: 4, padding: "2px 6px", cursor: "pointer",
              color: hidden[ex] ? "#334155" : (EX_COL[ex] || "#94a3b8"),
              fontSize: 9, fontWeight: 600, fontFamily: "'JetBrains Mono',monospace",
              transition: "all 0.15s", opacity: hidden[ex] ? 0.5 : 1,
              textDecoration: hidden[ex] ? "line-through" : "none",
            }}>{ex}</button>
          ))}
        </div>
      )}

      {/* Chart container */}
      <div ref={containerRef} style={{ width: "100%", flex: 1 }} />

      {exchanges.length === 0 && (
        <div style={CS.noData}>No data yet</div>
      )}
    </div>
  );
}

export default function ChartsTab({ spreads }) {
  const [tf, setTf] = useState("1m");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  const symbols = spreads
    .map(s => s.symbol)
    .filter(s => !search || s.toLowerCase().includes(search.toLowerCase().replace(/[/usdt]/gi, "")));

  const totalPages = Math.max(1, Math.ceil(symbols.length / PER_PAGE));
  const safePage = Math.min(page, totalPages - 1);
  const pageSymbols = symbols.slice(safePage * PER_PAGE, safePage * PER_PAGE + PER_PAGE);

  // Reset page on search change
  useEffect(() => { setPage(0); }, [search]);

  return (
    <div>
      {/* Controls: search + timeframes + pagination */}
      <div style={CS.controls}>
        <div style={CS.searchBox}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 8, flexShrink: 0 }}>
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input type="text" placeholder="Search pair..." value={search} onChange={e => setSearch(e.target.value)} style={CS.searchIn} />
          {search && <button onClick={() => setSearch("")} style={{ background: "none", border: "none", color: "#64748b", cursor: "pointer", fontSize: 14, padding: 4 }}>&times;</button>}
        </div>
        <div style={CS.tfRow}>
          {TFS.map(t => (
            <button key={t} onClick={() => setTf(t)} style={{
              background: tf === t ? "rgba(14,165,233,0.15)" : "rgba(14,165,233,0.04)",
              border: tf === t ? "1px solid rgba(14,165,233,0.3)" : "1px solid rgba(14,165,233,0.08)",
              borderRadius: 6, padding: "5px 14px", cursor: "pointer",
              color: tf === t ? "#0ea5e9" : "#475569", fontSize: 12, fontWeight: 600,
              fontFamily: "'JetBrains Mono',monospace", transition: "all 0.15s",
            }}>{t}</button>
          ))}
        </div>
        <div style={{ fontSize: 12, color: "#64748b", fontFamily: "'JetBrains Mono',monospace", whiteSpace: "nowrap" }}>
          {symbols.length} pairs
        </div>
      </div>

      {/* Chart grid */}
      {pageSymbols.length === 0 ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: 300, color: "#475569", fontSize: 13 }}>
          {search ? "No matches" : "No spread data yet"}
        </div>
      ) : (
        <div style={CS.grid}>
          {pageSymbols.map(sym => (
            <MiniChart key={sym + tf} symbol={sym} tf={tf} height={280} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={CS.pagination}>
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={safePage === 0}
            style={{ ...CS.pageBtn, opacity: safePage === 0 ? 0.3 : 1 }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <span style={CS.pageInfo}>{safePage + 1} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={safePage >= totalPages - 1}
            style={{ ...CS.pageBtn, opacity: safePage >= totalPages - 1 ? 0.3 : 1 }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

const CS = {
  controls: {
    display: "flex", alignItems: "center", gap: 16, marginBottom: 16, flexWrap: "wrap",
  },
  searchBox: {
    display: "flex", alignItems: "center",
    background: "rgba(12,14,24,0.6)",
    border: "1px solid rgba(14,165,233,0.06)",
    borderRadius: 8, padding: "0 14px",
    flex: "1 1 180px", minWidth: 160,
  },
  searchIn: {
    background: "none", border: "none", color: "#e2e8f0",
    fontSize: 13, fontFamily: "inherit", padding: "10px 0",
    outline: "none", width: "100%",
  },
  tfRow: { display: "flex", gap: 4 },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: 10,
  },
  chartCard: {
    background: "rgba(12,14,24,0.6)",
    border: "1px solid rgba(14,165,233,0.06)",
    borderRadius: 10,
    padding: "12px 14px",
    display: "flex", flexDirection: "column",
    minHeight: 280,
  },
  chartHeader: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    marginBottom: 6,
  },
  chartSymbol: {
    fontSize: 14, fontWeight: 700, color: "#e2e8f0",
  },
  exchRow: {
    display: "flex", gap: 4, flexWrap: "wrap", marginBottom: 6,
  },
  noData: {
    display: "flex", alignItems: "center", justifyContent: "center",
    flex: 1, color: "#334155", fontSize: 11,
    fontFamily: "'JetBrains Mono',monospace",
  },
  pagination: {
    display: "flex", alignItems: "center", justifyContent: "center",
    gap: 16, marginTop: 16, padding: "8px 0",
  },
  pageBtn: {
    background: "rgba(14,165,233,0.06)",
    border: "1px solid rgba(14,165,233,0.1)",
    borderRadius: 8, padding: "8px 12px",
    cursor: "pointer", color: "#0ea5e9",
    display: "flex", alignItems: "center",
    transition: "all 0.15s",
  },
  pageInfo: {
    fontSize: 13, fontWeight: 600, color: "#64748b",
    fontFamily: "'JetBrains Mono',monospace",
  },
};

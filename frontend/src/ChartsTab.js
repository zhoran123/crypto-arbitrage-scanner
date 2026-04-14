import React, { useState, useEffect, useRef } from "react";
import { createChart, CrosshairMode, LineStyle, LineSeries } from "lightweight-charts";
import "./chartstab.css";

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
  const initDone = useRef(false);
  const [hidden, setHidden] = useState({});
  const [exchanges, setExchanges] = useState([]);

  // Create chart once on mount
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
        attributionLogo: false,
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
      },
      handleScroll: true,
      handleScale: true,
    });
    chartRef.current = chart;

    // Hide TradingView watermark via CSS
    const el = containerRef.current;
    const tvLogos = el.querySelectorAll("a[href*='tradingview'], div[class*='attribution']");
    tvLogos.forEach(l => { l.style.display = "none"; });

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
      initDone.current = false;
    };
  }, [height]);

  // Full data load (on mount and tf change)
  useEffect(() => {
    if (!chartRef.current) return;
    let active = true;

    async function fullLoad() {
      try {
        const r = await fetch(`${API}/price-history?symbol=${symbol}&tf=${tf}`);
        const data = await r.json();
        if (!active || !chartRef.current) return;

        const chart = chartRef.current;
        const exchs = Object.keys(data).filter(ex => data[ex]?.length > 0);
        setExchanges(exchs);

        // Remove old series
        Object.values(seriesRef.current).forEach(s => {
          try { chart.removeSeries(s); } catch {}
        });
        seriesRef.current = {};

        // Create series for each exchange
        exchs.forEach(ex => {
          const series = chart.addSeries(LineSeries, {
            color: EX_COL[ex] || "#94a3b8",
            lineWidth: 1.5,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerRadius: 3,
            crosshairMarkerBorderColor: EX_COL[ex] || "#94a3b8",
            crosshairMarkerBackgroundColor: "#08090e",
            visible: !hidden[ex],
          });
          const points = data[ex].map(c => ({ time: c.t, value: c.c }));
          series.setData(points);
          seriesRef.current[ex] = series;
        });

        chart.timeScale().fitContent();
        initDone.current = true;
      } catch {}
    }

    fullLoad();
    return () => { active = false; };
  }, [symbol, tf]); // hidden is intentionally excluded to avoid re-creating series on toggle

  // Live update every 5 seconds (only update last point, no re-create)
  useEffect(() => {
    if (!chartRef.current) return;
    let active = true;

    async function liveUpdate() {
      if (!initDone.current || !active) return;
      try {
        const r = await fetch(`${API}/price-history/live?symbol=${symbol}`);
        const live = await r.json();
        if (!active) return;

        Object.entries(live).forEach(([ex, candle]) => {
          const series = seriesRef.current[ex];
          if (series && candle) {
            series.update({ time: candle.t, value: candle.c });
          }
        });
      } catch {}
    }

    const id = setInterval(liveUpdate, 5000);
    return () => { active = false; clearInterval(id); };
  }, [symbol]);

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
    <div className="charts-card">
      <div className="charts-card-header">
        <span className="charts-card-symbol">
          {symbol.replace("USDT", "")}
          <span className="charts-card-suffix">/USDT</span>
        </span>
      </div>

      {exchanges.length > 0 && (
        <div className="charts-exchanges">
          {exchanges.map(ex => (
            <button
              key={ex}
              onClick={() => toggleExch(ex)}
              className={`charts-exchange-btn${hidden[ex] ? " is-hidden" : ""}`}
              style={{
                "--exchange-color": EX_COL[ex] || "#94a3b8",
                "--exchange-bg": `${EX_COL[ex] || "#94a3b8"}18`,
                "--exchange-border": `${EX_COL[ex] || "#94a3b8"}40`,
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      <div ref={containerRef} className="charts-canvas" />

      {exchanges.length === 0 && (
        <div className="charts-no-data">No data yet</div>
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

  useEffect(() => { setPage(0); }, [search]);

  return (
    <div className="charts-tab">
      <div className="charts-controls">
        <div className="charts-search-box">
          <svg className="charts-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#334155" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            placeholder="Search pair..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="charts-search-input"
          />
          {search && <button onClick={() => setSearch("")} className="charts-search-clear">&times;</button>}
        </div>
        <div className="charts-timeframes">
          {TFS.map(t => (
            <button
              key={t}
              onClick={() => setTf(t)}
              className={`charts-timeframe-btn${tf === t ? " is-active" : ""}`}
            >
              {t}
            </button>
          ))}
        </div>
        <div className="charts-pairs-count">
          {symbols.length} pairs
        </div>
      </div>

      {pageSymbols.length === 0 ? (
        <div className="charts-empty">
          {search ? "No matches" : "No spread data yet"}
        </div>
      ) : (
        <div className="charts-grid">
          {pageSymbols.map(sym => (
            <MiniChart key={sym + tf} symbol={sym} tf={tf} height={280} />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="charts-pagination">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={safePage === 0}
            className="charts-page-btn"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <span className="charts-page-info">{safePage + 1} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
            disabled={safePage >= totalPages - 1}
            className="charts-page-btn"
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

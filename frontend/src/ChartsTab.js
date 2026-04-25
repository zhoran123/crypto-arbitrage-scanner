import React, { useState, useEffect, useRef } from "react";
import { createChart, CrosshairMode, LineStyle, LineSeries } from "lightweight-charts";
import "./chartstab.css";

const API = window.location.port === "3000"
  ? `${window.location.protocol}//${window.location.hostname}:8000`
  : window.location.origin;
const EMPTY_ARRAY = [];
const HISTORY_RETRY_DELAYS = [15000, 30000, 60000, 120000, 120000];
const LIVE_POLL_INTERVAL = 5000;
const HISTORY_CACHE_TTL_MS = 30000;
const historyCache = new Map();

const EX_COL = {
  binance: "#F0B90B", bybit: "#F7A600", mexc: "#00B897", bingx: "#60a5fa",
  gate: "#22d3ee", bitget: "#00c9a7", okx: "#a78bfa", kucoin: "#23AF91",
  dex: "#f472b6",
};

const TFS = ["1m", "5m", "15m", "30m", "1h", "4h"];
const PER_PAGE = 6;

function getHistoryCacheKey(symbol, tf) {
  return `${symbol}|${tf}`;
}

function cloneHistoryData(data) {
  return Object.fromEntries(
    Object.entries(data).map(([exchange, candles]) => [exchange, candles.map(candle => ({ ...candle }))])
  );
}

function readHistoryCache(symbol, tf) {
  const entry = historyCache.get(getHistoryCacheKey(symbol, tf));
  if (!entry || entry.expiresAt <= Date.now()) {
    historyCache.delete(getHistoryCacheKey(symbol, tf));
    return null;
  }
  return cloneHistoryData(entry.data);
}

function writeHistoryCache(symbol, tf, data) {
  historyCache.set(getHistoryCacheKey(symbol, tf), {
    data: cloneHistoryData(data),
    expiresAt: Date.now() + HISTORY_CACHE_TTL_MS,
  });
}

function mergeLiveCandleIntoHistory(data, exchange, candle) {
  const next = cloneHistoryData(data);
  const candles = next[exchange] ? [...next[exchange]] : [];
  const existingIndex = candles.findIndex(item => item.t === candle.t);
  const normalized = { ...candle };

  if (existingIndex >= 0) {
    candles[existingIndex] = { ...candles[existingIndex], ...normalized };
  } else {
    candles.push(normalized);
    candles.sort((left, right) => left.t - right.t);
  }

  next[exchange] = candles;
  return next;
}

function MiniChart({ symbol, tf, height, hiddenExchanges, liveData }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const seriesRef = useRef({});
  const initDone = useRef(false);
  const fetchAbortRef = useRef(null);
  const retryTimeoutRef = useRef(null);
  const retryAttemptRef = useRef(0);
  const [hidden, setHidden] = useState({});
  const [exchanges, setExchanges] = useState([]);
  const hiddenRef = useRef(hidden);
  const hiddenExchangesKey = hiddenExchanges.join("|");

  useEffect(() => {
    hiddenRef.current = hidden;
  }, [hidden]);

  const removeAllSeries = chart => {
    Object.values(seriesRef.current).forEach(series => {
      try { chart.removeSeries(series); } catch {}
    });
    seriesRef.current = {};
  };

  const addSeries = (chart, ex, points = []) => {
    const series = chart.addSeries(LineSeries, {
      color: EX_COL[ex] || "#94a3b8",
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerRadius: 3,
      crosshairMarkerBorderColor: EX_COL[ex] || "#94a3b8",
      crosshairMarkerBackgroundColor: "#08090e",
      visible: !hiddenRef.current[ex] && !hiddenExchanges.includes(ex),
    });
    if (points.length) {
      series.setData(points);
    }
    seriesRef.current[ex] = series;
    return series;
  };

  const applyHistoryData = data => {
    if (!chartRef.current) return 0;
    const chart = chartRef.current;
    const exchs = Object.keys(data).filter(ex => data[ex]?.length > 0);

    removeAllSeries(chart);
    exchs.forEach(ex => {
      addSeries(chart, ex, data[ex].map(c => ({ time: c.t, value: c.c })));
    });

    setExchanges(exchs);
    if (exchs.length > 0) {
      chart.timeScale().fitContent();
    }
    return exchs.length;
  };

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
    initDone.current = false;
    retryAttemptRef.current = 0;
    const cachedData = readHistoryCache(symbol, tf);

    const clearRetry = () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
    };

    const scheduleRetry = () => {
      clearRetry();
      if (retryAttemptRef.current >= HISTORY_RETRY_DELAYS.length) {
        return;
      }
      const delay = HISTORY_RETRY_DELAYS[retryAttemptRef.current];
      retryAttemptRef.current += 1;
      retryTimeoutRef.current = setTimeout(() => {
        fullLoad();
      }, delay);
    };

    async function fullLoad() {
      fetchAbortRef.current?.abort();
      const controller = new AbortController();
      fetchAbortRef.current = controller;
      try {
        const r = await fetch(`${API}/price-history?symbol=${symbol}&tf=${tf}`, { signal: controller.signal });
        const data = await r.json();
        if (controller.signal.aborted || !chartRef.current) return;
        const seriesCount = applyHistoryData(data);
        // Mark initialized even when history is empty so live updates and retries can recover.
        initDone.current = true;
        if (seriesCount > 0) {
          writeHistoryCache(symbol, tf, data);
          retryAttemptRef.current = 0;
          clearRetry();
        } else {
          scheduleRetry();
        }
      } catch (error) {
        if (error.name !== "AbortError") {
          scheduleRetry();
        }
      }
    }

    if (cachedData) {
      const cachedSeriesCount = applyHistoryData(cachedData);
      initDone.current = cachedSeriesCount > 0;
    } else {
      fullLoad();
    }

    return () => {
      fetchAbortRef.current?.abort();
      clearRetry();
    };
  }, [symbol, tf]);

  useEffect(() => {
    if (!chartRef.current || !initDone.current || !liveData) return;

    Object.entries(liveData).forEach(([ex, candle]) => {
      if (!candle) return;

      let series = seriesRef.current[ex];
      if (!series && chartRef.current) {
        series = addSeries(chartRef.current, ex, [{ time: candle.t, value: candle.c }]);
        setExchanges(prev => (prev.includes(ex) ? prev : [...prev, ex]));
        chartRef.current.timeScale().fitContent();
      }

      if (series) {
        series.update({ time: candle.t, value: candle.c });
        const cached = readHistoryCache(symbol, tf);
        if (cached) {
          writeHistoryCache(symbol, tf, mergeLiveCandleIntoHistory(cached, ex, candle));
        }
      }
    });
  }, [liveData, symbol, tf]);

  useEffect(() => {
    Object.entries(seriesRef.current).forEach(([ex, series]) => {
      series.applyOptions({ visible: !hiddenRef.current[ex] && !hiddenExchanges.includes(ex) });
    });
  }, [hiddenExchangesKey]);

  // Toggle visibility without re-fetch
  const toggleExch = ex => {
    setHidden(h => {
      const next = { ...h, [ex]: !h[ex] };
      const s = seriesRef.current[ex];
      if (s) s.applyOptions({ visible: !next[ex] && !hiddenExchanges.includes(ex) });
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
              className={`charts-exchange-btn${hidden[ex] || hiddenExchanges.includes(ex) ? " is-hidden" : ""}`}
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

export default function ChartsTab({ spreads, hiddenExchanges = EMPTY_ARRAY }) {
  const [tf, setTf] = useState("1m");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [liveSnapshots, setLiveSnapshots] = useState({});

  const symbols = spreads
    .map(s => s.symbol)
    .filter(s => !search || s.toLowerCase().includes(search.toLowerCase().replace(/[/usdt]/gi, "")));

  const totalPages = Math.max(1, Math.ceil(symbols.length / PER_PAGE));
  const safePage = Math.min(page, totalPages - 1);
  const pageSymbols = symbols.slice(safePage * PER_PAGE, safePage * PER_PAGE + PER_PAGE);
  const pageSymbolsKey = pageSymbols.join(",");

  useEffect(() => { setPage(0); }, [search]);

  useEffect(() => {
    if (!pageSymbolsKey) {
      setLiveSnapshots({});
      return;
    }

    let alive = true;
    let currentController = null;

    async function loadLiveBatch() {
      currentController?.abort();
      const controller = new AbortController();
      currentController = controller;

      try {
        const response = await fetch(
          `${API}/price-history/live/batch?symbols=${encodeURIComponent(pageSymbolsKey)}`,
          { signal: controller.signal }
        );
        const data = await response.json();
        if (!alive || controller.signal.aborted) return;
        setLiveSnapshots(data);
      } catch (error) {
        if (error.name !== "AbortError" && alive) {
          setLiveSnapshots({});
        }
      }
    }

    loadLiveBatch();
    const intervalId = setInterval(loadLiveBatch, LIVE_POLL_INTERVAL);

    return () => {
      alive = false;
      currentController?.abort();
      clearInterval(intervalId);
    };
  }, [pageSymbolsKey]);

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
            <MiniChart
              key={sym + tf}
              symbol={sym}
              tf={tf}
              height={280}
              hiddenExchanges={hiddenExchanges}
              liveData={liveSnapshots[sym] || null}
            />
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

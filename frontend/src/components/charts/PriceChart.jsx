import { useEffect, useState } from "react";
import {
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  Cell,
  Line,
  Area,
  ReferenceLine,
  ResponsiveContainer
} from "recharts";
import { fetchOHLCV, fetchSignal } from "@/services/apiService";
import { Loader2 } from "lucide-react";

export default function PriceChart({ symbol = "AAPL" }) {
  const [range, setRange] = useState("1D");
  const [chartType, setChartType] = useState("area"); // "area" or "candles"
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showEMA, setShowEMA] = useState(false);
  const [showBBands, setShowBBands] = useState(false);
  const [showMACD, setShowMACD] = useState(false);
  const [signalInfo, setSignalInfo] = useState(null);

  useEffect(() => {
    let active = true;
    
    async function loadData() {
      try {
        const fetchedData = await fetchOHLCV(range, symbol);
        let fetchedSignal = null;
        try {
          fetchedSignal = await fetchSignal(range, symbol);
        } catch (sigErr) {
          console.error("Failed to fetch market signal:", sigErr);
        }
        
        if (active) {
          setData(fetchedData);
          if (fetchedSignal) {
            setSignalInfo(fetchedSignal);
          }
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (active) {
          setError(`Failed to fetch market data for ${symbol}.`);
          setData([]);
          setLoading(false);
        }
      }
    }

    setLoading(true);
    setError(null);
    setData([]);
    loadData();

    // Setup polling every 5 seconds
    const interval = setInterval(() => {
      loadData();
    }, 5000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [range, symbol]);

  if (loading && data.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-card text-muted-foreground" data-testid="chart-loading">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="text-xs font-mono">Fetching Market Feed...</span>
        </div>
      </div>
    );
  }

  if (error && data.length === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-card text-destructive text-xs font-semibold p-4 text-center" data-testid="chart-error">
        {error}
      </div>
    );
  }

  // Format data for floating candlestick bars
  const chartData = data.map((item) => ({
    ...item,
    highLow: [item.low, item.high],
    openClose: [item.open, item.close],
    isUp: item.close >= item.open
  }));

  // Calculate domains
  const priceValues = data.flatMap((d) => [d.low, d.high]);
  const minPrice = priceValues.length ? Math.min(...priceValues) - 0.5 : 100;
  const maxPrice = priceValues.length ? Math.max(...priceValues) + 0.5 : 110;

  // Determine trend color (green for positive returns, red for negative returns)
  const firstPrice = data[0]?.close ?? 0;
  const lastPrice = data[data.length - 1]?.close ?? 0;
  const isPositive = lastPrice >= firstPrice;
  const trendColor = isPositive ? "hsl(var(--primary))" : "hsl(var(--destructive))";
  const gradientId = isPositive ? "greenGradient" : "redGradient";

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const d = payload[0].payload;
      const isUp = d.close >= d.open;
      return (
        <div className="rounded-xl border border-border bg-card/95 backdrop-blur-md p-3 shadow-lg text-[10px] space-y-1 font-mono text-foreground z-50">
          <div className="text-muted-foreground font-bold border-b border-border/55 pb-0.5 mb-1">
            Time: {d.time}
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
            <span className="text-muted-foreground">Open:</span>
            <span className="font-semibold text-right">${d.open.toFixed(2)}</span>
            <span className="text-muted-foreground">Close:</span>
            <span className={`font-semibold text-right ${isUp ? "text-emerald-500" : "text-rose-500"}`}>
              ${d.close.toFixed(2)}
            </span>
            <span className="text-muted-foreground">High:</span>
            <span className="text-emerald-500 font-semibold text-right">${d.high.toFixed(2)}</span>
            <span className="text-muted-foreground">Low:</span>
            <span className="text-rose-500 font-semibold text-right">${d.low.toFixed(2)}</span>
            <span className="text-muted-foreground">RSI:</span>
            <span className="text-primary font-semibold text-right">{d.rsi ? d.rsi.toFixed(2) : ""}</span>
          </div>
        </div>
      );
    }
    return null;
  };

  const priceChartHeight = showMACD ? "h-[45%]" : "h-[62%]";
  const rsiChartHeight = showMACD ? "h-[20%]" : "h-[28%]";

  return (
    <div className="w-full h-full flex flex-col justify-between" data-testid="price-chart-container">
      {/* Chart Type & Time-Range Selector Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-2 mb-2 flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold font-mono tracking-wide text-foreground uppercase">{symbol}</span>
          
          {/* Glowing recommendation badge */}
          {signalInfo && signalInfo.signal && (
            <span 
              className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider transition duration-300 ${
                signalInfo.signal === "BUY" 
                  ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/20 shadow-[0_0_8px_rgba(34,211,238,0.15)] animate-pulse" 
                  : signalInfo.signal === "SELL"
                    ? "bg-rose-500/10 text-rose-400 border-rose-500/20 shadow-[0_0_8px_rgba(244,63,94,0.15)]"
                    : "bg-muted text-muted-foreground border-border/40"
              }`}
              data-testid="signal-badge"
            >
              Signal: {signalInfo.signal}
            </span>
          )}
        </div>

        {/* Action Controls toolbar */}
        <div className="flex items-center gap-2">
          {/* Indicator toggles */}
          <div className="flex items-center gap-1 bg-secondary/30 p-0.5 rounded-lg border border-border/40 text-[9px] font-bold text-muted-foreground select-none">
            <label className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md cursor-pointer transition ${showEMA ? "bg-card text-foreground border border-border/20" : "hover:text-foreground"}`}>
              <input type="checkbox" checked={showEMA} onChange={(e) => setShowEMA(e.target.checked)} className="sr-only" />
              <span>EMA</span>
            </label>
            <label className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md cursor-pointer transition ${showBBands ? "bg-card text-foreground border border-border/20" : "hover:text-foreground"}`}>
              <input type="checkbox" checked={showBBands} onChange={(e) => setShowBBands(e.target.checked)} className="sr-only" />
              <span>BB</span>
            </label>
            <label className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md cursor-pointer transition ${showMACD ? "bg-card text-foreground border border-border/20" : "hover:text-foreground"}`}>
              <input type="checkbox" checked={showMACD} onChange={(e) => setShowMACD(e.target.checked)} className="sr-only" />
              <span>MACD</span>
            </label>
          </div>

          {/* Chart Type Toggle */}
          <div className="flex gap-1 bg-secondary/30 p-0.5 rounded-lg border border-border/40">
          <button
            onClick={() => setChartType("area")}
            type="button"
            className={`p-1 rounded-md transition duration-200 ${
              chartType === "area"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="Area Chart"
            data-testid="toggle-chart-area"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5">
              <path d="M3 3v18h18" />
              <path d="m18.7 8-5.1 5.2-2.8-2.7L7 14.3" />
            </svg>
          </button>
          <button
            onClick={() => setChartType("candles")}
            type="button"
            className={`p-1 rounded-md transition duration-200 ${
              chartType === "candles"
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            }`}
            title="Candlestick Chart"
            data-testid="toggle-chart-candles"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5">
              <path d="M6 3v18M6 8h4v6H6zM18 3v18M14 6h4v10h-4z" />
            </svg>
          </button>
        </div>

        {/* Interval Selector */}
        <div className="flex gap-1 bg-secondary/30 p-0.5 rounded-lg border border-border/40">
          {["1D", "1W", "1M"].map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              type="button"
              className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition duration-200 ${
                range === r
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              data-testid={`range-${r}`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
    </div>

      {/* Main Subplot (approx 65% height) */}
      <div className={`${priceChartHeight} w-full min-h-[140px]`} data-testid={`chart-display-${chartType}`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: -25, bottom: 5 }}>
            <defs>
              <linearGradient id="greenGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.25}/>
                <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="redGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.25}/>
                <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis dataKey="time" fontSize={8} tickLine={false} axisLine={false} className="text-muted-foreground/60" />
            <YAxis
              domain={[minPrice, maxPrice]}
              fontSize={8}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground/60"
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(34, 211, 238, 0.08)", strokeWidth: 1 }} />
            
            {chartType === "area" ? (
              <Area
                type="monotone"
                dataKey="close"
                stroke={trendColor}
                strokeWidth={2}
                fill={`url(#${gradientId})`}
                dot={false}
                legendType="none"
              />
            ) : (
              <>
                {/* Candlestick Wicks */}
                <Bar dataKey="highLow" barSize={1.2} legendType="none">
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`wick-${index}`}
                      fill={entry.isUp ? "hsl(var(--primary)/40%)" : "hsl(var(--destructive)/40%)"}
                    />
                  ))}
                </Bar>
 
                {/* Candlestick Bodies */}
                <Bar dataKey="openClose" barSize={7} legendType="none">
                  {chartData.map((entry, index) => (
                    <Cell
                      key={`body-${index}`}
                      fill={entry.isUp ? "hsl(var(--primary))" : "hsl(var(--destructive))"}
                    />
                  ))}
                </Bar>
              </>
            )}

            {/* EMA Overlay */}
            {showEMA && (
              <Line
                type="monotone"
                dataKey="ema"
                stroke="#f59e0b"
                strokeWidth={1.5}
                dot={false}
                legendType="none"
                connectNulls
              />
            )}

            {/* Bollinger Bands Overlay */}
            {showBBands && (
              <>
                <Line
                  type="monotone"
                  dataKey="bbands_upper"
                  stroke="#8b5cf6"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  dot={false}
                  legendType="none"
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="bbands_middle"
                  stroke="#8b5cf6"
                  strokeWidth={0.8}
                  strokeDasharray="5 5"
                  dot={false}
                  legendType="none"
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="bbands_lower"
                  stroke="#8b5cf6"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  dot={false}
                  legendType="none"
                  connectNulls
                />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* RSI Subplot (approx 30% height) */}
      <div className={`${rsiChartHeight} w-full border-t border-border/40 pt-2 mt-1`}>
        <div className="text-[8px] font-bold text-muted-foreground uppercase tracking-widest mb-1 select-none">
          Relative Strength Index (RSI)
        </div>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 0, right: 10, left: -25, bottom: 5 }}>
            <XAxis dataKey="time" hide />
            <YAxis
              domain={[10, 90]}
              fontSize={7}
              tickLine={false}
              axisLine={false}
              className="text-muted-foreground/60"
              ticks={[30, 50, 70]}
            />
            
            {/* Overbought / Oversold reference guides */}
            <ReferenceLine y={70} stroke="hsl(var(--destructive)/35%)" strokeDasharray="3 3" strokeWidth={1} />
            <ReferenceLine y={30} stroke="hsl(var(--primary)/35%)" strokeDasharray="3 3" strokeWidth={1} />
            
            <Line
              type="monotone"
              dataKey="rsi"
              stroke="hsl(var(--primary))"
              strokeWidth={1.5}
              dot={false}
              legendType="none"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* MACD Subplot */}
      {showMACD && (
        <div className="h-[20%] w-full border-t border-border/40 pt-2 mt-1" data-testid="macd-subplot">
          <div className="text-[8px] font-bold text-muted-foreground uppercase tracking-widest mb-1 select-none flex justify-between">
            <span>MACD (12, 26, 9)</span>
            {data.length > 0 && (
              <span className="font-mono text-muted-foreground/60">
                L: {data[data.length - 1].macd_line?.toFixed(2) ?? ""} | S: {data[data.length - 1].macd_signal?.toFixed(2) ?? ""} | H: {data[data.length - 1].macd_histogram?.toFixed(2) ?? ""}
              </span>
            )}
          </div>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 0, right: 10, left: -25, bottom: 5 }}>
              <XAxis dataKey="time" hide />
              <YAxis
                fontSize={7}
                tickLine={false}
                axisLine={false}
                className="text-muted-foreground/60"
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(34, 211, 238, 0.08)", strokeWidth: 1 }} />
              
              <Bar dataKey="macd_histogram" barSize={3} legendType="none">
                {chartData.map((entry, index) => {
                  const val = entry.macd_histogram ?? 0;
                  return (
                    <Cell
                      key={`macd-hist-${index}`}
                      fill={val >= 0 ? "hsl(var(--primary))" : "hsl(var(--destructive))"}
                    />
                  );
                })}
              </Bar>

              <Line
                type="monotone"
                dataKey="macd_line"
                stroke="#38bdf8"
                strokeWidth={1.2}
                dot={false}
                legendType="none"
                connectNulls
              />

              <Line
                type="monotone"
                dataKey="macd_signal"
                stroke="#f472b6"
                strokeWidth={1.2}
                dot={false}
                legendType="none"
                connectNulls
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

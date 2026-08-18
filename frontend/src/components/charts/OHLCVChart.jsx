import {
  ComposedChart,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  Cell,
  ResponsiveContainer,
  ReferenceLine
} from "recharts";

// Beautiful static mock OHLCV + Volume data for demonstration
const defaultMockData = [
  { time: "09:30", open: 150.2, high: 152.5, low: 149.8, close: 151.6, volume: 12000 },
  { time: "10:00", open: 151.6, high: 153.1, low: 151.0, close: 152.8, volume: 9500 },
  { time: "10:30", open: 152.8, high: 154.5, low: 152.2, close: 154.1, volume: 14000 },
  { time: "11:00", open: 154.1, high: 154.2, low: 151.5, close: 152.0, volume: 11000 },
  { time: "11:30", open: 152.0, high: 153.5, low: 151.8, close: 153.2, volume: 8000 },
  { time: "12:00", open: 153.2, high: 155.0, low: 153.0, close: 154.8, volume: 16000 },
  { time: "12:30", open: 154.8, high: 156.2, low: 154.1, close: 155.9, volume: 13000 },
  { time: "13:00", open: 155.9, high: 157.0, low: 155.5, close: 156.4, volume: 10500 },
  { time: "13:30", open: 156.4, high: 156.5, low: 153.8, close: 154.2, volume: 15000 },
  { time: "14:00", open: 154.2, high: 155.8, low: 153.9, close: 155.1, volume: 9800 },
  { time: "14:30", open: 155.1, high: 157.5, low: 154.8, close: 157.2, volume: 18500 },
  { time: "15:00", open: 157.2, high: 158.4, low: 156.5, close: 158.1, volume: 22000 }
];

const CustomTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isUp = data.close >= data.open;
    return (
      <div className="rounded-xl border border-border bg-card/95 backdrop-blur-md p-3.5 shadow-lg text-[11px] space-y-1.5 font-mono">
        <div className="text-muted-foreground font-bold border-b border-border/60 pb-1 mb-1">
          Time: {data.time}
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          <span className="text-muted-foreground">Open:</span>
          <span className="text-foreground font-semibold text-right">${data.open.toFixed(2)}</span>
          
          <span className="text-muted-foreground">High:</span>
          <span className="text-emerald-500 font-semibold text-right">${data.high.toFixed(2)}</span>
          
          <span className="text-muted-foreground">Low:</span>
          <span className="text-destructive font-semibold text-right">${data.low.toFixed(2)}</span>
          
          <span className="text-muted-foreground">Close:</span>
          <span className={`font-semibold text-right ${isUp ? "text-primary" : "text-destructive"}`}>
            ${data.close.toFixed(2)}
          </span>
          
          <span className="text-muted-foreground">Volume:</span>
          <span className="text-foreground font-semibold text-right">{data.volume.toLocaleString()}</span>
        </div>
      </div>
    );
  }
  return null;
};

export default function OHLCVChart({ data = defaultMockData, stopLoss, takeProfit }) {
  // Format data for floating bars
  const chartData = data.map((item) => ({
    ...item,
    highLow: [item.low, item.high],
    openClose: [item.open, item.close],
    isUp: item.close >= item.open
  }));

  // Calculate domain automatically
  const allValues = data.flatMap((d) => [d.low, d.high]);
  const minY = allValues.length ? Math.min(...allValues) - 0.5 : 100;
  const maxY = allValues.length ? Math.max(...allValues) + 0.5 : 110;

  return (
    <div className="w-full h-full flex flex-col justify-between">
      <div className="flex-1 w-full min-h-[160px]">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
          >
            <XAxis 
              dataKey="time" 
              stroke="currentColor" 
              className="text-muted-foreground/60"
              fontSize={9} 
              tickLine={false} 
              axisLine={false}
            />
            <YAxis 
              domain={[minY, maxY]} 
              stroke="currentColor" 
              className="text-muted-foreground/60"
              fontSize={9} 
              tickLine={false} 
              axisLine={false}
              tickFormatter={(v) => `$${v}`}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(16, 185, 129, 0.1)", strokeWidth: 1 }} />
            
            {/* Take Profit target reference line */}
            {takeProfit && (
              <ReferenceLine 
                y={takeProfit} 
                stroke="hsl(var(--primary))" 
                strokeDasharray="3 3" 
                strokeWidth={1}
                label={{ value: `TP $${takeProfit}`, fill: "hsl(var(--primary))", fontSize: 8, position: "top" }} 
              />
            )}

            {/* Stop Loss target reference line */}
            {stopLoss && (
              <ReferenceLine 
                y={stopLoss} 
                stroke="hsl(var(--destructive))" 
                strokeDasharray="3 3" 
                strokeWidth={1}
                label={{ value: `SL $${stopLoss}`, fill: "hsl(var(--destructive))", fontSize: 8, position: "bottom" }} 
              />
            )}

            {/* Candlestick Wicks (High-Low) */}
            <Bar 
              dataKey="highLow" 
              fill="currentColor" 
              className="text-muted-foreground/40"
              barSize={1.5}
              legendType="none"
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`wick-${index}`} 
                  fill={entry.isUp ? "hsl(var(--primary)/40%)" : "hsl(var(--destructive)/40%)"} 
                />
              ))}
            </Bar>

            {/* Candlestick Bodies (Open-Close) */}
            <Bar 
              dataKey="openClose" 
              barSize={8}
              legendType="none"
            >
              {chartData.map((entry, index) => (
                <Cell 
                  key={`body-${index}`} 
                  fill={entry.isUp ? "hsl(var(--primary))" : "hsl(var(--destructive))"} 
                />
              ))}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Mini Volume Bar Chart */}
      <div className="h-10 w-full border-t border-border/40 pt-1.5 mt-1">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 0, right: 10, left: -20, bottom: 0 }}
          >
            <XAxis dataKey="time" hide />
            <YAxis hide />
            <Bar dataKey="volume">
              {chartData.map((entry, index) => (
                <Cell 
                  key={`vol-${index}`} 
                  fill={entry.isUp ? "hsl(var(--primary)/20%)" : "hsl(var(--destructive)/20%)"} 
                />
              ))}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

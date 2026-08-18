import { TrendingUp, TrendingDown, Percent, Hash } from "lucide-react";
import { Card } from "@/components/ui/card";
import { ResponsiveContainer, AreaChart, Area } from "recharts";

export default function PnLCard({ dailyPnl = 0, winRate = 68.5, tradeCount = 12 }) {
  const isPositive = dailyPnl >= 0;

  // Generate a mock equity curve trajectory for the sparkline ending at dailyPnl
  const curveData = Array.from({ length: 10 }, (_, i) => {
    if (i === 0) return { val: 0 };
    if (i === 9) return { val: dailyPnl };

    // Create a random walk towards the dailyPnl target
    const targetFraction = i / 9;
    const randomFactor = Math.sin(i * 1.5) * 0.15 * Math.abs(dailyPnl);
    const val = dailyPnl * targetFraction + randomFactor;
    return { val: parseFloat(val.toFixed(2)) };
  });

  return (
    <Card className="rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between hover:border-primary/30 transition duration-200" data-testid="pnl-card">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Daily Performance</span>
        <div className={`h-8 w-8 rounded-lg grid place-items-center ${isPositive
            ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-500"
            : "bg-rose-500/10 border border-rose-500/20 text-rose-500"
          }`}>
          {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
        </div>
      </div>

      <div className="mt-4 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h3
              className={`text-2xl font-bold tracking-tight font-sans ${isPositive ? "text-emerald-500" : "text-rose-500"}`}
              data-testid="pnl-value"
            >
              {isPositive ? "+" : "-"}${Math.abs(dailyPnl).toFixed(2)}
            </h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">Daily P&L</p>
          </div>

          {/* Mini Sparkline Chart */}
          <div className="h-[40px] w-[100px]" data-testid="pnl-sparkline">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={curveData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                <defs>
                  <linearGradient id="pnlSparklineGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={isPositive ? "hsl(var(--primary))" : "hsl(var(--destructive))"} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={isPositive ? "hsl(var(--primary))" : "hsl(var(--destructive))"} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="val"
                  stroke={isPositive ? "hsl(var(--primary))" : "hsl(var(--destructive))"}
                  strokeWidth={1.5}
                  fill="url(#pnlSparklineGrad)"
                  dot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 border-t border-border/40 pt-3">
          <div className="space-y-0.5">
            <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider block">Win Rate</span>
            <div
              className="text-sm font-bold text-foreground font-sans flex items-center gap-1"
              data-testid="win-rate"
            >
              <Percent className="h-3.5 w-3.5 text-primary/80" />
              {typeof winRate === "number" ? `${winRate.toFixed(1)}%` : winRate}
            </div>
          </div>
          <div className="space-y-0.5">
            <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider block">Trades Count</span>
            <div
              className="text-sm font-bold text-foreground font-sans flex items-center gap-1"
              data-testid="trade-count"
            >
              <Hash className="h-3.5 w-3.5 text-primary/80" />
              {tradeCount}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

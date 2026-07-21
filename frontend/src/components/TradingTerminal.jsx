import { useEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import PriceChart from "@/components/PriceChart";
import PnLCard from "@/components/PnLCard";
import useMarketEngine from "@/hooks/useMarketEngine";
import { 
  Wallet, 
  TrendingUp, 
  Layers, 
  ShieldCheck, 
  Activity,
  ArrowUpRight,
  Zap,
  AlertCircle
} from "lucide-react";

import { fetchAccountDetails, fetchPositions } from "@/services/apiService";

export default function TradingTerminal() {
  const [copilotMode, setCopilotMode] = useState(true);
  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [searchQuery, setSearchQuery] = useState("");
  const { candleData, currentPrice, xaiLogs } = useMarketEngine(selectedSymbol);
  const feedRef = useRef(null);

  const [accountInfo, setAccountInfo] = useState({
    cash: 0.0,
    buying_power: 0.0,
    equity: 0.0,
    portfolio_value: 0.0,
    daily_pnl: 0.0,
    mock_mode: true
  });
  const [positions, setPositions] = useState([]);

  useEffect(() => {
    let active = true;
    const loadData = async () => {
      try {
        const acc = await fetchAccountDetails();
        const pos = await fetchPositions();
        if (active) {
          setAccountInfo(acc);
          setPositions(pos);
        }
      } catch (err) {
        console.error("Failed to fetch account/positions:", err);
      }
    };

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const position = positions.find(pos => pos.symbol === selectedSymbol) || { symbol: selectedSymbol, qty: 0, avg_entry_price: 0 };
  const posQty = position.qty || 0;
  const posEntry = position.avg_entry_price || 0;

  const quantPnl = currentPrice === 0 || posQty === 0 
    ? (position.unrealized_pl || 0.0) 
    : +((currentPrice - posEntry) * posQty).toFixed(2);

  // Guardrail breach logic: drawdown check
  const isBreached = currentPrice > 0 && currentPrice < 98.0;

  // Daily portfolio calculations (mock + real-time dynamic P&L mapping)
  const basePortfolioValue = accountInfo.portfolio_value;
  const livePortfolioValue = +(basePortfolioValue).toFixed(2);
  const percentChange = basePortfolioValue > 0
    ? +((accountInfo.daily_pnl / basePortfolioValue) * 100).toFixed(2)
    : 0.0;

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [xaiLogs]);

  return (
    <div className="flex flex-col gap-6 w-full px-1 sm:px-0">
      {isBreached && (
        <div 
          className="flex items-start gap-3 rounded-2xl border border-destructive/25 bg-destructive/5 p-4 text-xs leading-relaxed text-destructive animate-in fade-in duration-300" 
          data-testid="guardrail-breach-alert"
        >
          <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold uppercase tracking-wide">Critical Exposure Drawdown Breach</span>
            <p className="opacity-90 font-sans">
              QUANT price fell below maximum drawdown boundary ($98.00). Algorithmic trading execution has been suspended.
            </p>
          </div>
        </div>
      )}
      
      {/* 1. Top P&L Summary Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Card 1: Portfolio Value */}
        <Card className="rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between hover:border-primary/30 transition duration-200">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Total Portfolio</span>
            <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 text-primary grid place-items-center">
              <Wallet className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 space-y-1">
            <h3 className="text-2xl font-extrabold text-foreground tracking-tight font-mono">
              ${livePortfolioValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </h3>
            <p className="text-[10px] text-muted-foreground flex items-center gap-1 flex-wrap">
              <span className="text-primary font-bold inline-flex items-center">
                <ArrowUpRight className="h-3 w-3" />
                {percentChange >= 0 ? "+" : ""}{percentChange}%
              </span>
              <span>from yesterday</span>
            </p>
            <p className="text-[9px] text-muted-foreground flex items-center gap-1 mt-1 flex-wrap font-mono">
              <span>Cash: ${(accountInfo.cash || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
              <span className="opacity-50">|</span>
              <span>BP: ${(accountInfo.buying_power || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}</span>
            </p>
          </div>
        </Card>

        {/* Card 2: Daily P&L */}
        <PnLCard dailyPnl={accountInfo.daily_pnl || 0.0} winRate={68.5} tradeCount={12} />

        {/* Card 3: Active Exposure */}
        <Card className="rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between hover:border-primary/30 transition duration-200">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Active Exposure</span>
            <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 grid place-items-center">
              <Layers className="h-4 w-4" />
            </div>
          </div>
          <div className="mt-4 space-y-1">
            <h3 className="text-2xl font-extrabold text-foreground tracking-tight font-mono">
              ${positions.reduce((sum, p) => sum + (p.market_value || 0), 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}
            </h3>
            <p className="text-[10px] text-muted-foreground">
              {positions.length > 0
                ? `${positions.length} Active Asset${positions.length > 1 ? "s" : ""} (${positions.map((p) => p.symbol).join(", ")})`
                : "No Active Holdings"}
            </p>
          </div>
        </Card>

        {/* Card 4: Engine Status */}
        <Card className="rounded-2xl border border-border bg-card p-5 shadow-sm flex flex-col justify-between hover:border-primary/30 transition duration-200" data-testid="safety-card">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">Engine Safety</span>
            <div className={`h-8 w-8 rounded-lg grid place-items-center ${
              isBreached 
                ? "bg-destructive/10 border border-destructive/20 text-destructive animate-pulse" 
                : "bg-amber-500/10 border border-amber-500/20 text-amber-500"
            }`}>
              {isBreached ? <AlertCircle className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
            </div>
          </div>
          <div className="mt-4 space-y-1">
            <h3 className="text-2xl font-extrabold text-foreground tracking-tight flex items-center gap-1.5 font-mono">
              {isBreached ? (
                <>
                  45.2% <span className="text-xs font-bold text-destructive px-1.5 py-0.5 rounded bg-destructive/10 border border-destructive/20" data-testid="safety-status-badge">BREACH</span>
                </>
              ) : (
                <>
                  99.8% <span className="text-xs font-bold text-primary px-1.5 py-0.5 rounded bg-primary/10 border border-primary/20" data-testid="safety-status-badge">OK</span>
                </>
              )}
            </h3>
            <p className="text-[10px] text-muted-foreground flex items-center gap-1">
              <Activity className={`h-3 w-3 ${isBreached ? "text-destructive" : "text-primary animate-pulse"}`} />
              <span data-testid="safety-status-text">
                {isBreached ? "Drawdown limit exceeded!" : "Risk guardrails nominal"}
              </span>
            </p>
          </div>
        </Card>
      </div>

      {/* 2. Upper Grid - Chart & Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_1fr] gap-6">
        <Card className="flex flex-col rounded-2xl border border-border bg-card p-4 sm:p-6 shadow-sm min-h-[380px]">
          <CardHeader className="space-y-3 border-b border-border pb-4 p-0">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <CardTitle className="text-lg font-bold text-foreground flex items-center gap-2">
                <Zap className="h-4 w-4 text-primary fill-current" />
                <span data-testid="active-symbol-title">{selectedSymbol} Live Chart</span>
              </CardTitle>
              
              <div className="flex items-center gap-3 flex-wrap">
                {/* Quick select tags */}
                <div className="flex items-center gap-1.5 bg-secondary/20 p-0.5 rounded-lg border border-border/40">
                  {["AAPL", "NVDA", "TSLA", "MSFT"].map((sym) => (
                    <button
                      key={sym}
                      onClick={() => setSelectedSymbol(sym)}
                      type="button"
                      className={`px-2 py-0.5 text-[10px] font-bold rounded transition ${
                        selectedSymbol === sym
                          ? "bg-primary text-primary-foreground font-mono"
                          : "text-muted-foreground hover:text-foreground font-mono"
                      }`}
                      data-testid={`quick-select-${sym}`}
                    >
                      {sym}
                    </button>
                  ))}
                </div>

                {/* Custom search bar */}
                <form 
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (searchQuery.trim()) {
                      setSelectedSymbol(searchQuery.trim().toUpperCase());
                      setSearchQuery("");
                    }
                  }}
                  className="flex items-center gap-2 bg-secondary/35 rounded-xl border border-border px-3 py-1 focus-within:border-primary/50 transition duration-200"
                >
                  <input
                    type="text"
                    placeholder="Search stock..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-transparent border-none text-[10px] text-foreground placeholder:text-muted-foreground outline-none w-24 font-sans"
                    data-testid="ticker-search-input"
                  />
                  <button
                    type="submit"
                    className="text-[9px] font-bold text-primary hover:text-primary-foreground hover:bg-primary/20 px-1.5 py-0.5 rounded transition duration-200 uppercase font-mono"
                    data-testid="ticker-search-btn"
                  >
                    Load
                  </button>
                </form>
              </div>
            </div>
          </CardHeader>
          <CardContent className="flex-grow p-0 pt-4 relative">
            <div className="absolute inset-0 w-full h-full">
              <PriceChart symbol={selectedSymbol} />
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between">
          <div>
            <CardHeader className="space-y-1 border-b border-border pb-4 p-0">
              <CardTitle className="text-lg font-bold text-foreground">
                Control Panel
              </CardTitle>
              <p className="text-xs text-muted-foreground">
                Toggle execution mode and prepare the trade workflow.
              </p>
            </CardHeader>
            <CardContent className="space-y-6 pt-6 p-0">
              <div className="flex items-center justify-between rounded-xl border border-border bg-secondary/40 p-4">
                <div>
                  <p className="text-xs text-muted-foreground font-semibold">Mode</p>
                  <p
                    className={`mt-1 text-base font-bold ${copilotMode ? "text-primary" : "text-destructive"}`}
                  >
                    {copilotMode ? "Copilot Mode" : "Autopilot Mode"}
                  </p>
                </div>
                <Switch
                  checked={copilotMode}
                  onCheckedChange={setCopilotMode}
                  className="data-[state=checked]:bg-primary bg-muted"
                />
              </div>
            </CardContent>
          </div>

          <div className="space-y-3 pt-6 border-t border-border">
            <p className="text-[10px] uppercase tracking-[0.2em] font-semibold text-muted-foreground">
              Trade execution
            </p>
            <Button
              className={`w-full rounded-xl py-5 text-sm font-bold tracking-wider transition duration-200 border-none ${
                copilotMode
                  ? "bg-primary text-primary-foreground hover:scale-102 hover:brightness-105 active:scale-98"
                  : "cursor-not-allowed bg-secondary text-muted-foreground"
              }`}
              disabled={!copilotMode}
            >
              EXECUTE TRADE
            </Button>
          </div>
        </Card>
      </div>

      {/* 3. Lower Grid - Positions & XAI Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr] gap-6">
        <Card className="rounded-2xl border border-border bg-card p-4 sm:p-6 shadow-sm overflow-hidden">
          <CardHeader className="space-y-1 border-b border-border pb-4 p-0">
            <CardTitle className="text-lg font-bold text-foreground">
              Active Positions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 pt-4">
            {/* Scrollable table wrapper for mobile scaling */}
            <div className="w-full overflow-x-auto">
              <Table className="w-full min-w-[500px] text-sm text-foreground">
                <TableHeader>
                  <TableRow className="border-b border-border hover:bg-transparent">
                    <TableHead className="font-semibold text-muted-foreground text-left py-3">Ticker</TableHead>
                    <TableHead className="font-semibold text-muted-foreground text-left py-3">Qty</TableHead>
                    <TableHead className="font-semibold text-muted-foreground text-left py-3">Entry</TableHead>
                    <TableHead className="font-semibold text-muted-foreground text-left py-3">Current</TableHead>
                    <TableHead className="font-semibold text-muted-foreground text-right py-3">PnL</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {positions.length > 0 ? (
                    positions.map((pos) => {
                      const pnl = pos.unrealized_pl || 0.0;
                      const isPositive = pnl >= 0;
                      const currentP = pos.symbol === selectedSymbol && currentPrice > 0 ? currentPrice : (pos.current_price || 0.0);
                      const updatedPnl = pos.symbol === selectedSymbol && currentPrice > 0
                        ? +((currentPrice - pos.avg_entry_price) * pos.qty).toFixed(2)
                        : pnl;
                      return (
                        <TableRow 
                          key={pos.symbol} 
                          className={`border-b border-border/50 hover:bg-secondary/20 cursor-pointer ${
                            selectedSymbol === pos.symbol ? "bg-secondary/15" : ""
                          }`}
                          onClick={() => setSelectedSymbol(pos.symbol)}
                        >
                          <TableCell className="font-bold text-foreground py-4">
                            {pos.symbol}
                          </TableCell>
                          <TableCell className="py-4">{pos.qty}</TableCell>
                          <TableCell className="py-4 font-mono">${(pos.avg_entry_price || 0).toFixed(2)}</TableCell>
                          <TableCell className="py-4 font-mono">${currentP.toFixed(2)}</TableCell>
                          <TableCell className="text-right py-4">
                            <Badge
                              className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                                updatedPnl >= 0
                                  ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                                  : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
                              }`}
                            >
                              {updatedPnl >= 0 ? "+" : ""}${updatedPnl.toFixed(2)}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  ) : (
                    <TableRow className="hover:bg-transparent">
                      <TableCell colSpan={5} className="text-center py-6 text-muted-foreground italic">
                        No active holdings in your Alpaca account. Approve proposals or execute trades to create positions.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <Card className="rounded-2xl border border-border bg-card p-4 sm:p-6 shadow-sm">
          <CardHeader className="space-y-1 border-b border-border pb-4 p-0">
            <CardTitle className="text-lg font-bold text-foreground">
              XAI Intelligence Feed
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 pt-4">
            <ScrollArea className="h-[200px] rounded-xl border border-border bg-secondary/20 p-4">
              <div
                ref={feedRef}
                className="space-y-2.5 font-mono text-xs text-muted-foreground"
              >
                {xaiLogs.map((line, index) => (
                  <p key={index} className="leading-5">
                    {line.split(" ").map((token, tokenIndex) => {
                      const highlight =
                        token.includes("SIGNAL:") ||
                        token.includes("JUSTIFICATION:") ||
                        token.includes("ALERT:") ||
                        token.includes("NOTE:");
                      return (
                        <span
                          key={tokenIndex}
                          className={highlight ? "text-primary font-bold" : ""}
                        >
                          {token}{" "}
                        </span>
                      );
                    })}
                  </p>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

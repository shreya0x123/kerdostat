import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { 
  Check, 
  X, 
  BrainCircuit, 
  TrendingUp, 
  TrendingDown, 
  Info,
  DollarSign,
  Briefcase,
  Terminal
} from "lucide-react";
import OHLCVChart from "./OHLCVChart";
import { useAuth } from "@/hooks/useAuth";

export default function ProposalCard({
  symbol = "QUANT",
  signal = "BUY",
  XAIReason = "Neural network detected double bottom formation with high volume support. Short-term momentum indicators show bullish crossover.",
  qty = 100,
  SL = 148.0,
  TP = 158.0,
  status: propStatus,
  actions = {},
  chartData
}) {
  const navigate = useNavigate();
  const { systemMode } = useAuth();
  const isAutopilot = systemMode === "autopilot";
  const [localStatus, setLocalStatus] = useState("pending");
  const status = propStatus !== undefined ? propStatus : localStatus;
  const [isProcessing, setIsProcessing] = useState(false);

  const onApprove = actions.onApprove;
  const onReject = actions.onReject;

  const handleApprove = async () => {
    setIsProcessing(true);
    try {
      if (onApprove) {
        await onApprove();
      } else {
        await new Promise((resolve) => setTimeout(resolve, 800));
        setLocalStatus("approved");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReject = async () => {
    setIsProcessing(true);
    try {
      if (onReject) {
        await onReject();
      } else {
        await new Promise((resolve) => setTimeout(resolve, 800));
        setLocalStatus("rejected");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsProcessing(false);
    }
  };

  const isBuy = signal.toUpperCase() === "BUY";

  return (
    <div className={`rounded-2xl border bg-card text-card-foreground shadow-md transition-all duration-300 overflow-hidden ${
      status === "approved" ? "border-primary/40 shadow-primary/5 bg-primary/[0.01]" : 
      status === "rejected" ? "border-destructive/30 opacity-75 bg-destructive/[0.01]" : 
      "border-border hover:border-primary/20 hover:shadow-lg"
    }`}>
      {/* Top Banner / Header */}
      <div className="flex items-center justify-between border-b border-border/60 bg-muted/20 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-secondary border border-border text-foreground font-bold flex items-center justify-center text-sm font-mono tracking-wide">
            {symbol.slice(0, 3)}
          </div>
          <div>
            <h3 className="font-extrabold text-foreground font-sans text-sm flex items-center gap-2">
              {symbol}
              <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                isBuy 
                  ? "bg-primary/15 text-primary border border-primary/20" 
                  : "bg-destructive/15 text-destructive border border-destructive/20"
              }`}>
                {isBuy ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {signal.toUpperCase()}
              </span>
            </h3>
            <span className="text-[10px] text-muted-foreground font-mono">Proposal ID: P-{symbol}-{qty}</span>
          </div>
        </div>

        {/* Status indicator */}
        <div className="text-right">
          {status === "pending" && (
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/20">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
              Awaiting HITL Approval
            </span>
          )}
          {status === "approved" && (
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold bg-primary/20 text-primary border border-primary/30">
              <Check className="h-3 w-3" />
              Approved & Dispatched
            </span>
          )}
          {status === "rejected" && (
            <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold bg-destructive/10 text-destructive border border-destructive/20">
              <X className="h-3 w-3" />
              Rejected / Cancelled
            </span>
          )}
        </div>
      </div>

      {/* Main Content Body */}
      {!isAutopilot && (
        <div className="p-6 space-y-6">
          
          {/* Core parameters metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-secondary/20 rounded-xl border border-border/40 p-4">
            <div className="space-y-1">
              <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider block">Quantity</span>
              <div className="text-sm font-extrabold text-foreground font-mono flex items-center gap-1">
                <Briefcase className="h-3.5 w-3.5 text-muted-foreground" />
                {qty}
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider block">Stop Loss</span>
              <div className="text-sm font-extrabold text-destructive font-mono flex items-center gap-0.5">
                <DollarSign className="h-3.5 w-3.5 text-destructive/80" />
                {SL.toFixed(2)}
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider block">Take Profit</span>
              <div className="text-sm font-extrabold text-primary font-mono flex items-center gap-0.5">
                <DollarSign className="h-3.5 w-3.5 text-primary/80" />
                {TP.toFixed(2)}
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider block">Est. Risk/Reward</span>
              <div className="text-sm font-extrabold text-foreground font-mono">
                {Math.abs((TP - (isBuy ? SL : TP)) / ((isBuy ? SL : TP) - SL) || 2.5).toFixed(1)}x
              </div>
            </div>
          </div>

          {/* Explainable AI (XAI) Reason box */}
          <div className="rounded-xl border border-primary/10 bg-primary/[0.02] p-4.5 space-y-2 relative overflow-hidden group">
            <div className="absolute top-0 right-0 h-16 w-16 bg-primary/5 rounded-full blur-xl -mr-4 -mt-4" />
            <div className="flex items-center gap-2">
              <div className="h-6 w-6 rounded-lg bg-primary/10 border border-primary/20 text-primary grid place-items-center">
                <BrainCircuit className="h-3.5 w-3.5" />
              </div>
              <span className="text-xs font-bold text-foreground">Explainable AI Reasoning (XAI)</span>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed font-sans">
              {XAIReason}
            </p>
          </div>

          {/* Price chart container */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-foreground flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5 text-muted-foreground" />
                Live Price Snapshot
              </span>
              <span className="text-muted-foreground font-mono text-[10px]">OHLCV + Target Boundaries</span>
            </div>
            
            <div className="h-52 w-full rounded-xl border border-border/80 bg-background/50 p-4">
              <OHLCVChart data={chartData} stopLoss={SL} takeProfit={TP} />
            </div>
          </div>
        </div>
      )}

      {/* Action panel */}
      {status === "pending" && (
        <div className="flex border-t border-border/60">
          {isAutopilot ? (
            <button
              onClick={() => {
                const entry_price = chartData && chartData.length > 0 ? chartData[chartData.length - 1].close : 151.60;
                navigate("/override", { 
                  state: { 
                    proposal: { 
                      id: `prop-${symbol.toLowerCase()}`,
                      symbol, 
                      qty, 
                      SL, 
                      TP, 
                      entry_price 
                    } 
                  } 
                });
              }}
              disabled={isProcessing}
              type="button"
              className="w-full inline-flex items-center justify-center gap-2 py-4 px-6 text-xs font-bold text-amber-500 hover:bg-amber-500/5 active:bg-amber-500/10 transition disabled:opacity-50"
              data-testid="override-btn"
            >
              <Terminal className="h-4 w-4" />
              <span>Override</span>
            </button>
          ) : (
            <>
              <button
                onClick={handleReject}
                disabled={isProcessing}
                type="button"
                className="flex-1 inline-flex items-center justify-center gap-2 py-4 px-6 text-xs font-bold text-destructive hover:bg-destructive/5 active:bg-destructive/10 border-r border-border/60 transition disabled:opacity-50"
              >
                {isProcessing ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-destructive border-t-transparent" />
                ) : (
                  <>
                    <X className="h-4 w-4" />
                    <span>Reject & Cancel</span>
                  </>
                )}
              </button>
              
              <button
                onClick={() => {
                  const entry_price = chartData && chartData.length > 0 ? chartData[chartData.length - 1].close : 151.60;
                  navigate("/override", { 
                    state: { 
                      proposal: { 
                        id: `prop-${symbol.toLowerCase()}`,
                        symbol, 
                        qty, 
                        SL, 
                        TP, 
                        entry_price 
                      } 
                    } 
                  });
                }}
                disabled={isProcessing}
                type="button"
                className="flex-1 inline-flex items-center justify-center gap-2 py-4 px-6 text-xs font-bold text-amber-500 hover:bg-amber-500/5 active:bg-amber-500/10 border-r border-border/60 transition disabled:opacity-50"
                data-testid="hijack-btn"
              >
                <Terminal className="h-4 w-4" />
                <span>Manual Override</span>
              </button>
              
              <button
                onClick={handleApprove}
                disabled={isProcessing}
                type="button"
                className="flex-1 inline-flex items-center justify-center gap-2 py-4 px-6 text-xs font-bold text-primary hover:bg-primary/5 active:bg-primary/10 transition disabled:opacity-50"
              >
                {isProcessing ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    <span>Approve & Execute</span>
                  </>
                )}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

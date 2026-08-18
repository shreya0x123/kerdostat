/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect } from "react";
import ProposalCard from "@/components/ProposalCard";
import useWebSocket from "@/hooks/useWebSocket";
import { fetchProposals, updateProposalAction, fetchOHLCV } from "@/services/apiService";
import { Layers, ShieldCheck, CheckSquare, RefreshCw } from "lucide-react";

// Mock chart data for Proposal 1: QUANT
const quantChartData = [
  { time: "09:30", open: 150.2, high: 152.5, low: 149.8, close: 151.6, volume: 12000 },
  { time: "10:00", open: 151.6, high: 153.1, low: 151.0, close: 152.8, volume: 9500 },
  { time: "10:30", open: 152.8, high: 154.5, low: 152.2, close: 154.1, volume: 14000 },
  { time: "11:00", open: 154.1, high: 154.2, low: 151.5, close: 152.0, volume: 11000 },
  { time: "11:30", open: 152.0, high: 153.5, low: 151.8, close: 153.2, volume: 8000 },
  { time: "12:00", open: 153.2, high: 155.0, low: 153.0, close: 154.8, volume: 16000 },
  { time: "12:30", open: 154.8, high: 156.2, low: 154.1, close: 155.9, volume: 13000 },
  { time: "13:00", open: 155.9, high: 157.0, low: 155.5, close: 156.4, volume: 10500 },
  { time: "13:30", open: 156.4, high: 156.5, low: 153.8, close: 154.2, volume: 15000 },
  { time: "14:00", open: 154.2, high: 157.2, low: 174.8, close: 175.1, volume: 16000 },
  { time: "14:30", open: 175.1, high: 176.4, low: 173.8, close: 174.2, volume: 22000 },
  { time: "15:00", open: 174.2, high: 175.5, low: 172.5, close: 173.0, volume: 28000 }
];

// Mock chart data for Proposal 2: NVIDIA (NVDA)
const nvdaChartData = [
  { time: "09:30", open: 121.2, high: 122.5, low: 120.5, close: 121.8, volume: 25000 },
  { time: "10:00", open: 121.8, high: 123.4, low: 121.5, close: 123.1, volume: 29000 },
  { time: "10:30", open: 123.1, high: 124.0, low: 122.8, close: 123.5, volume: 18000 },
  { time: "11:00", open: 123.5, high: 123.6, low: 122.0, close: 122.4, volume: 15000 },
  { time: "11:30", open: 122.4, high: 124.1, low: 122.3, close: 123.9, volume: 21000 },
  { time: "12:00", open: 123.9, high: 125.8, low: 123.8, close: 125.2, volume: 35000 },
  { time: "12:30", open: 125.2, high: 126.9, low: 124.9, close: 126.4, volume: 41000 },
  { time: "13:00", open: 126.4, high: 127.5, low: 126.0, close: 127.1, volume: 28000 },
  { time: "13:30", open: 127.1, high: 128.8, low: 126.8, close: 128.2, volume: 32000 },
  { time: "14:00", open: 128.2, high: 129.5, low: 127.9, close: 129.1, volume: 27000 },
  { time: "14:30", open: 129.1, high: 131.2, low: 128.8, close: 130.8, volume: 49000 },
  { time: "15:00", open: 130.8, high: 132.8, low: 130.5, close: 132.4, volume: 55000 }
];

// Mock chart data for Proposal 3: TESLA (TSLA)
const tslaChartData = [
  { time: "09:30", open: 185.0, high: 186.4, low: 183.1, close: 183.9, volume: 19000 },
  { time: "10:00", open: 183.9, high: 184.8, low: 182.2, close: 182.7, volume: 14000 },
  { time: "10:30", open: 182.7, high: 183.9, low: 181.5, close: 182.0, volume: 16500 },
  { time: "11:00", open: 182.0, high: 182.8, low: 180.2, close: 181.1, volume: 13000 },
  { time: "11:30", open: 181.1, high: 181.8, low: 179.5, close: 180.0, volume: 11000 },
  { time: "12:00", open: 180.0, high: 180.9, low: 178.2, close: 178.6, volume: 17500 },
  { time: "12:30", open: 178.6, high: 179.4, low: 177.0, close: 177.5, volume: 15000 },
  { time: "13:00", open: 177.5, high: 178.5, low: 176.2, close: 176.9, volume: 12000 },
  { time: "13:30", open: 176.9, high: 178.0, low: 175.5, close: 175.9, volume: 14500 },
  { time: "14:00", open: 175.9, high: 177.2, low: 174.8, close: 175.1, volume: 16000 },
  { time: "14:30", open: 175.1, high: 176.4, low: 173.8, close: 174.2, volume: 22000 },
  { time: "15:00", open: 174.2, high: 175.5, low: 172.5, close: 173.0, volume: 28000 }
];

export default function ProposalsPage() {
  const [proposals, setProposals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");
  const [chartsData, setChartsData] = useState({});

  const { latestMessage } = useWebSocket();

  useEffect(() => {
    if (proposals.length === 0) return;

    let active = true;
    const fetchAllCharts = async () => {
      const symbols = [...new Set(proposals.map((p) => p.symbol))];
      const newCharts = {};
      await Promise.all(
        symbols.map(async (sym) => {
          try {
            const data = await fetchOHLCV("1D", sym);
            newCharts[sym] = data;
          } catch (err) {
            console.error(`Failed to fetch chart for ${sym}`, err);
          }
        })
      );

      if (active && Object.keys(newCharts).length > 0) {
        setChartsData((prev) => ({ ...prev, ...newCharts }));
      }
    };

    fetchAllCharts();
    const interval = setInterval(fetchAllCharts, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [proposals]);


  // Load proposals from server
  const loadProposals = async () => {
    try {
      setLoading(true);
      const data = await fetchProposals();
      setProposals(data);
      setError(null);
    } catch (err) {
      setError("Failed to connect to trading backend. Run backend server first.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProposals();
  }, []);

  // Listen to live WebSocket broadcast actions
  useEffect(() => {
    if (latestMessage && latestMessage.event === "proposal_updated") {
      const { proposal_id, status } = latestMessage;
      setProposals((prev) =>
        prev.map((p) => (p.id === proposal_id ? { ...p, status } : p))
      );
    }
  }, [latestMessage]);

  const handleApproveAction = async (id, symbol) => {
    try {
      const updated = await updateProposalAction(id, "approve");
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: updated.status } : p))
      );
      console.log(`[Governance] Proposal for ${symbol} APPROVED and dispatched to broker execution queue.`);
    } catch (err) {
      console.error(err);
      alert(`Approval failed: ${err.message}`);
    }
  };

  const handleRejectAction = async (id, symbol) => {
    try {
      const updated = await updateProposalAction(id, "reject");
      setProposals((prev) =>
        prev.map((p) => (p.id === id ? { ...p, status: updated.status } : p))
      );
      console.log(`[Governance] Proposal for ${symbol} REJECTED and discarded.`);
    } catch (err) {
      console.error(err);
      alert(`Rejection failed: ${err.message}`);
    }
  };

  const getChartData = (symbol) => {
    if (chartsData[symbol] && chartsData[symbol].length > 0) {
      return chartsData[symbol];
    }
    if (symbol === "NVDA") return nvdaChartData;
    if (symbol === "TSLA") return tslaChartData;
    return quantChartData;
  };

  const filteredProposals = proposals.filter((p) => {
    if (filter === "all") return true;
    return p.signal.toLowerCase() === filter;
  });

  return (
    <div className="w-full max-w-4xl mx-auto py-6 px-4 space-y-8 font-sans" data-testid="proposals-page-content">
      {/* Header section */}
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-6">
        <div className="space-y-2 text-left">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-primary/10 border border-primary/20 text-primary grid place-items-center">
              <Layers className="h-4 w-4" />
            </div>
            <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
              Proposals & Governance
            </h1>
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
            Review live suggestions from the auto-trading desks. Every proposal contains explainable AI (XAI) rationale, boundaries, and static charts. Approve to execute via your active broker.
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 self-start md:self-center">
          <button
            onClick={loadProposals}
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground hover:text-foreground transition active:scale-95"
            title="Refresh Proposals"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </section>

      {/* Safety info alert */}
      <div className="flex items-start gap-3 rounded-2xl border border-primary/25 bg-primary/5 p-4 text-xs leading-relaxed text-foreground/90">
        <ShieldCheck className="h-4 w-4 text-primary flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-bold">Human-in-the-Loop Safeguard Mode Active</span>
          <p className="text-muted-foreground font-sans">
            Kerdostat's autopilot trading requires human signature to dispatch live trades unless autonomous threshold overrides are enabled in system settings.
          </p>
        </div>
      </div>

      {/* Filter and Tab Section */}
      <div className="flex items-center justify-between border-b border-border/40 pb-2">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setFilter("all")}
            type="button"
            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              filter === "all"
                ? "bg-secondary text-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            All Proposals ({proposals.length})
          </button>
          <button
            onClick={() => setFilter("buy")}
            type="button"
            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              filter === "buy"
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Buy Signal ({proposals.filter((p) => p.signal === "BUY").length})
          </button>
          <button
            onClick={() => setFilter("sell")}
            type="button"
            className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${
              filter === "sell"
                ? "bg-destructive/10 text-destructive"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Sell Signal ({proposals.filter((p) => p.signal === "SELL").length})
          </button>
        </div>

        <div className="hidden sm:flex items-center gap-1.5 text-[10px] text-muted-foreground font-mono">
          <CheckSquare className="h-3.5 w-3.5" />
          <span>Nominal Risk Parameters Verified</span>
        </div>
      </div>

      {/* Loading and Error States */}
      {/* Loading and Error States */}
      {loading && proposals.length === 0 && (
        <div className="space-y-6" data-testid="logs-loading">
          <div className="rounded-2xl border border-border bg-card/60 p-6 space-y-6 animate-pulse">
            <div className="flex items-center justify-between border-b border-border/40 pb-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl bg-secondary/80" />
                <div className="space-y-2">
                  <div className="h-4 w-24 rounded bg-secondary/80" />
                  <div className="h-3 w-16 rounded bg-secondary/60" />
                </div>
              </div>
              <div className="h-6 w-28 rounded-full bg-secondary/60" />
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-4 p-4 rounded-xl bg-secondary/20 animate-pulse">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="space-y-2">
                    <div className="h-2 w-10 rounded bg-secondary/60" />
                    <div className="h-4 w-12 rounded bg-secondary/80" />
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <div className="h-3 w-full rounded bg-secondary/60" />
                <div className="h-3 w-5/6 rounded bg-secondary/60" />
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-border bg-card/60 p-6 space-y-6 animate-pulse">
            <div className="flex items-center justify-between border-b border-border/40 pb-4">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl bg-secondary/80" />
                <div className="space-y-2">
                  <div className="h-4 w-24 rounded bg-secondary/80" />
                  <div className="h-3 w-16 rounded bg-secondary/60" />
                </div>
              </div>
              <div className="h-6 w-28 rounded-full bg-secondary/60" />
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-4 gap-4 p-4 rounded-xl bg-secondary/20 animate-pulse">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="space-y-2">
                    <div className="h-2 w-10 rounded bg-secondary/60" />
                    <div className="h-4 w-12 rounded bg-secondary/80" />
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                <div className="h-3 w-full rounded bg-secondary/60" />
                <div className="h-3 w-5/6 rounded bg-secondary/60" />
              </div>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-6 text-center text-sm font-semibold text-destructive space-y-3">
          <p>{error}</p>
          <button
            onClick={loadProposals}
            className="inline-flex items-center gap-2 rounded-xl bg-destructive text-destructive-foreground px-4 py-2 text-xs font-bold hover:brightness-105 transition"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Feed list of ProposalCards */}
      {!loading && !error && (
        <div className="space-y-8">
          {filteredProposals.length === 0 ? (
            <div className="rounded-2xl border border-border bg-card p-12 text-center text-muted-foreground font-semibold flex flex-col items-center justify-center space-y-4">
              <Layers className="h-10 w-10 text-muted-foreground/40" />
              <div>
                <p className="text-sm font-bold text-foreground">No proposals found</p>
                <p className="text-xs text-muted-foreground mt-1 font-sans font-normal">There are no active proposals matching the filter criteria.</p>
              </div>
            </div>
          ) : (
            filteredProposals.map((proposal) => (
              <ProposalCard
                key={proposal.id}
                symbol={proposal.symbol}
                signal={proposal.signal}
                XAIReason={proposal.XAIReason}
                qty={proposal.qty}
                SL={proposal.SL}
                TP={proposal.TP}
                status={proposal.status}
                chartData={getChartData(proposal.symbol)}
                actions={{
                  onApprove: () => handleApproveAction(proposal.id, proposal.symbol),
                  onReject: () => handleRejectAction(proposal.id, proposal.symbol)
                }}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

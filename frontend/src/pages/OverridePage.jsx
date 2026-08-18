import { useLocation, useNavigate } from "react-router-dom";
import QuickTradePanel from "@/components/trading/QuickTradePanel";
import OverridePanel from "@/components/trading/OverridePanel";

export default function OverridePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const proposal = location.state?.proposal;

  const handleSuccess = () => {
    setTimeout(() => {
      navigate("/dashboard");
    }, 1500);
  };

  return (
    <div className="w-full max-w-5xl mx-auto py-8 space-y-6 px-4">
      <div className="text-center md:text-left">
        <h2 className="text-3xl font-extrabold text-foreground tracking-tight">Manual Override Console</h2>
        <p className="text-xs text-muted-foreground mt-1 max-w-2xl font-sans">
          This workstation lets you execute manual orders directly to Alpaca, or hijack and override active algorithm proposals.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        {/* Left Column: Direct Alpaca execution */}
        <div className="space-y-4">
          <div className="bg-card border border-border/60 rounded-2xl p-4 shadow-sm">
            <h3 className="text-sm font-bold text-foreground">Quick Market Execution</h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Directly buy or sell assets on your Alpaca brokerage account.
            </p>
          </div>
          <QuickTradePanel proposal={proposal} onSuccess={handleSuccess} />
        </div>

        {/* Right Column: Signal Takeover */}
        <div className="space-y-4">
          <div className="bg-card border border-border/60 rounded-2xl p-4 shadow-sm">
            <h3 className="text-sm font-bold text-foreground">Proposal Override Engine</h3>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Override an active algo proposal's stop-loss, take-profit, or quantities.
            </p>
          </div>
          <OverridePanel proposal={proposal} onSuccess={handleSuccess} />
        </div>
      </div>
    </div>
  );
}

import { useForm } from "react-hook-form";
import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Loader2, RefreshCw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { overrideProposal, fetchProposals } from "@/services/apiService";

export default function OverridePanel({ proposal: initialProposal, onSuccess }) {
  const [proposals, setProposals] = useState([]);
  const [selectedProposal, setSelectedProposal] = useState(null);
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    formState: { errors, isValid },
  } = useForm({
    defaultValues: {
      symbol: "",
      qty: 1,
      entryPrice: 100.0,
      sl: 95.0,
      tp: 110.0,
      side: "BUY"
    },
    mode: "onChange"
  });

  const watchSymbol = watch("symbol");
  const watchQty = watch("qty");
  const watchEntryPrice = watch("entryPrice");
  const watchSl = watch("sl");
  const watchTp = watch("tp");
  const watchSide = watch("side");

  // Load active proposals
  const loadProposals = async () => {
    try {
      const data = await fetchProposals();
      // Only include pending proposals for override
      const pending = data.filter((p) => p.status === "pending" || p.status === "active");
      setProposals(pending);
    } catch (err) {
      console.error("Failed to load proposals for override:", err);
    }
  };

  useEffect(() => {
    loadProposals();
  }, []);

  // Pre-populate if initial proposal was passed via route state
  useEffect(() => {
    if (initialProposal) {
      setSelectedProposal(initialProposal);
      setValue("symbol", initialProposal.symbol);
      setValue("qty", initialProposal.qty || 1);
      setValue("entryPrice", initialProposal.entry_price || 100.0);
      setValue("sl", initialProposal.SL || (initialProposal.entry_price * 0.95));
      setValue("tp", initialProposal.TP || (initialProposal.entry_price * 1.05));
      setValue("side", initialProposal.signal?.toUpperCase() || "BUY");
      trigger();
    }
  }, [initialProposal, setValue, trigger]);

  // Handle dropdown proposal selection change
  const handleSelectChange = (e) => {
    const propId = e.target.value;
    const prop = proposals.find((p) => p.id === propId);
    if (prop) {
      setSelectedProposal(prop);
      setValue("symbol", prop.symbol);
      setValue("qty", prop.qty || 1);
      setValue("entryPrice", prop.entry_price || 100.0);
      setValue("sl", prop.SL || (prop.entry_price * 0.95));
      setValue("tp", prop.TP || (prop.entry_price * 1.05));
      setValue("side", prop.signal?.toUpperCase() || "BUY");
      trigger();
    } else {
      setSelectedProposal(null);
      setValue("symbol", "");
    }
  };

  // Perform validations
  const isBuy = watchSide === "BUY";
  const slValidation = (v) => {
    const val = parseFloat(v);
    const entry = parseFloat(watchEntryPrice) || 0;
    if (isBuy) {
      return val < entry || "Buy Stop Loss must be less than Entry Price";
    } else {
      return val > entry || "Sell Stop Loss must be greater than Entry Price";
    }
  };

  const tpValidation = (v) => {
    const val = parseFloat(v);
    const entry = parseFloat(watchEntryPrice) || 0;
    if (isBuy) {
      return val > entry || "Buy Take Profit must be greater than Entry Price";
    } else {
      return val < entry || "Sell Take Profit must be less than Entry Price";
    }
  };

  // Compute Risk / Reward Metrics
  const qty = parseFloat(watchQty) || 0;
  const entry = parseFloat(watchEntryPrice) || 0;
  const sl = parseFloat(watchSl) || 0;
  const tp = parseFloat(watchTp) || 0;

  const maxRisk = qty > 0 ? Math.abs(entry - sl) * qty : 0;
  const maxReward = qty > 0 ? Math.abs(entry - tp) * qty : 0;
  const rrMultiplier = maxRisk > 0 ? (maxReward / maxRisk).toFixed(2) : "0.00";

  const onSubmit = async (data) => {
    setLoading(true);
    setToast(null);
    try {
      const payload = {
        symbol: data.symbol.toUpperCase(),
        qty: parseInt(data.qty),
        SL: parseFloat(data.sl),
        TP: parseFloat(data.tp),
        entry_price: parseFloat(data.entryPrice),
        proposal_id: selectedProposal?.id || null,
        side: data.side.toUpperCase()
      };

      await overrideProposal(selectedProposal?.id || "manual", payload);
      setToast({ type: "success", message: `Successfully executed override trade for ${data.symbol.toUpperCase()}!` });
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setToast({ type: "error", message: err.message || "Failed to execute override." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="w-full max-w-sm mx-auto bg-card border border-border rounded-2xl shadow-xl overflow-hidden p-6 space-y-4" data-testid="override-panel">
      {toast && (
        <div
          data-testid={toast.type === "success" ? "success-alert" : "error-alert"}
          className={`fixed top-6 right-6 z-50 flex items-start gap-3 max-w-md rounded-2xl border p-4 shadow-2xl transition-all duration-300 transform translate-y-0 scale-100 ${toast.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-destructive/10 border-destructive/20 text-destructive"
            }`}
        >
          {toast.type === "success" ? (
            <CheckCircle className="h-5 w-5 flex-shrink-0 mt-0.5 text-emerald-400" />
          ) : (
            <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5 text-destructive" />
          )}
          <div className="space-y-1">
            <span className="text-xs font-bold block uppercase tracking-wide">
              {toast.type === "success" ? "Override Success" : "Override Failed"}
            </span>
            <p className="text-[11px] font-medium leading-normal opacity-90">{toast.message}</p>
          </div>
        </div>
      )}

      {/* Select Proposal to Override */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="prop-select" className="text-xs font-bold text-foreground">
            Select Active Proposal
          </Label>
          <button
            type="button"
            onClick={loadProposals}
            className="text-muted-foreground hover:text-foreground transition duration-150"
            title="Refresh proposals list"
          >
            <RefreshCw className="h-3 w-3" />
          </button>
        </div>
        <select
          id="prop-select"
          onChange={handleSelectChange}
          value={selectedProposal?.id || ""}
          className="w-full border border-border bg-secondary/25 text-foreground rounded-xl px-3 py-2 text-xs font-medium focus-visible:ring-primary focus-visible:border-primary focus:outline-none"
        >
          <option value="">-- Choose Proposal --</option>
          {proposals.map((p) => (
            <option key={p.id} value={p.id}>
              {p.symbol} ({p.signal?.toUpperCase()}) - Risk: {p.risk_score?.toFixed(1) || "N/A"}
            </option>
          ))}
        </select>
      </div>

      {/* Ticker Symbol display */}
      <div className="space-y-1.5">
        <Label htmlFor="override-symbol" className="text-xs font-bold text-foreground">
          Asset Symbol
        </Label>
        <Input
          id="override-symbol"
          type="text"
          disabled={!!selectedProposal}
          className="border-border bg-secondary/25 disabled:opacity-50 text-foreground rounded-xl font-mono text-sm"
          {...register("symbol", { required: "Symbol is required" })}
        />
      </div>

      {/* Direction & Qty */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="override-side" className="text-xs font-bold text-foreground">
            Direction
          </Label>
          <select
            id="override-side"
            className="w-full border border-border bg-secondary/25 text-foreground rounded-xl px-3 py-2 text-xs font-medium focus:outline-none"
            {...register("side")}
          >
            <option value="BUY">BUY (Long)</option>
            <option value="SELL">SELL (Short)</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="override-qty" className="text-xs font-bold text-foreground">
            Quantity
          </Label>
          <Input
            id="override-qty"
            type="number"
            className="border-border bg-secondary/25 text-foreground rounded-xl font-mono text-sm"
            {...register("qty", {
              required: "Quantity is required",
              validate: (v) => parseInt(v) > 0 || "Must be positive"
            })}
          />
        </div>
      </div>

      {/* Entry Price */}
      <div className="space-y-1.5">
        <Label htmlFor="override-entry" className="text-xs font-bold text-foreground">
          Entry Price ($)
        </Label>
        <Input
          id="override-entry"
          type="number"
          step="any"
          className="border-border bg-secondary/25 text-foreground rounded-xl font-mono text-sm"
          {...register("entryPrice", {
            required: "Entry Price is required",
            validate: (v) => parseFloat(v) > 0 || "Must be positive"
          })}
        />
      </div>

      {/* SL / TP */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="override-sl" className="text-xs font-bold text-foreground">
            Stop Loss ($)
          </Label>
          <Input
            id="override-sl"
            type="number"
            step="any"
            className="border-border bg-secondary/25 text-foreground rounded-xl font-mono text-sm"
            {...register("sl", {
              required: "Stop loss is required",
              validate: slValidation
            })}
          />
          {errors.sl && (
            <span className="text-[9px] font-bold text-destructive block leading-tight">{errors.sl.message}</span>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="override-tp" className="text-xs font-bold text-foreground">
            Take Profit ($)
          </Label>
          <Input
            id="override-tp"
            type="number"
            step="any"
            className="border-border bg-secondary/25 text-foreground rounded-xl font-mono text-sm"
            {...register("tp", {
              required: "Take profit is required",
              validate: tpValidation
            })}
          />
          {errors.tp && (
            <span className="text-[9px] font-bold text-destructive block leading-tight">{errors.tp.message}</span>
          )}
        </div>
      </div>

      {/* Risk Metrics Card */}
      <div className="pt-2 border-t border-border/40 space-y-1 text-xs">
        <div className="flex justify-between font-semibold text-muted-foreground">
          <span>Max Risk:</span>
          <span className="font-mono font-bold text-foreground">${maxRisk.toFixed(2)}</span>
        </div>
        <div className="flex justify-between font-semibold text-muted-foreground">
          <span>Max Reward:</span>
          <span className="font-mono font-bold text-foreground">${maxReward.toFixed(2)}</span>
        </div>
        <div className="flex justify-between font-semibold text-muted-foreground pt-0.5">
          <span>Reward-to-Risk Ratio:</span>
          <span className="font-mono font-bold text-foreground">
            Risk : Reward = 1 : {rrMultiplier}
          </span>
        </div>
      </div>

      {/* Execution Button */}
      <Button
        type="submit"
        disabled={!isValid || loading}
        className="w-full mt-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 font-bold py-3 text-xs shadow-md transition-all active:scale-95 disabled:opacity-30 border-none"
      >
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Apply Override"}
      </Button>
    </form>
  );
}

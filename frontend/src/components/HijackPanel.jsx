import { useForm } from "react-hook-form";
import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { overrideProposal } from "@/services/apiService";

export default function HijackPanel({ proposal, onSuccess }) {
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(false);

  // Auto-dismiss toast timer
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Set default values based on proposal or generic mock values
  const defaultValues = {
    symbol: proposal?.symbol || "QUANT",
    entryPrice: proposal?.entry_price || 151.60,
    qty: proposal?.qty || 100,
    SL: proposal?.SL || 149.00,
    TP: proposal?.TP || 157.50,
  };

  const {
    register,
    handleSubmit,
    watch,
    trigger,
    formState: { errors, isValid },
  } = useForm({
    defaultValues,
    mode: "onChange"
  });

  // Trigger initial validation to check validity of pre-filled defaults
  useEffect(() => {
    trigger();
  }, [trigger]);

  const watchEntryPrice = watch("entryPrice");

  const onSubmit = async (data) => {
    setLoading(true);
    setToast(null);
    
    try {
      const payload = {
        symbol: data.symbol,
        qty: parseInt(data.qty, 10),
        SL: parseFloat(data.SL),
        TP: parseFloat(data.TP),
        entry_price: parseFloat(data.entryPrice),
        proposal_id: proposal?.id || null
      };

      await overrideProposal(proposal?.id || "manual", payload);
      setToast({ type: "success", message: "Hijack execution dispatched successfully!" });
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setToast({ type: "error", message: err.message || "Hijack execution failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto bg-card border border-border rounded-2xl shadow-xl overflow-hidden" data-testid="hijack-panel">
      <div className="border-b border-border bg-secondary/15 px-6 py-4">
        <h3 className="text-base font-bold text-foreground flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-destructive animate-pulse" />
          Override Parameters Form
        </h3>
        <p className="text-[11px] text-muted-foreground mt-0.5">
          Execute direct override control over the execution loop parameters.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-4" noValidate>
        {toast && (
          <div
            data-testid={toast.type === "success" ? "success-alert" : "error-alert"}
            className={`fixed top-6 right-6 z-50 flex items-start gap-3 max-w-md rounded-2xl border p-4 shadow-2xl transition-all duration-300 transform translate-y-0 scale-100 ${
              toast.type === "success"
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
                {toast.type === "success" ? "Execution Dispatched" : "Execution Failed"}
              </span>
              <p className="text-[11px] font-medium leading-normal opacity-90">{toast.message}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          {/* Symbol */}
          <div className="space-y-1.5 col-span-2">
            <Label htmlFor="hijack-symbol" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Asset Symbol
            </Label>
            <Input
              id="hijack-symbol"
              type="text"
              className="border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary"
              {...register("symbol", { required: "Symbol is required" })}
            />
            {errors.symbol && (
              <span className="text-[10px] font-bold text-destructive block mt-1" data-testid="symbol-error">{errors.symbol.message}</span>
            )}
          </div>

          {/* Entry Price */}
          <div className="space-y-1.5">
            <Label htmlFor="hijack-entryPrice" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Entry Price ($)
            </Label>
            <Input
              id="hijack-entryPrice"
              type="number"
              step="any"
              className="border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary font-mono"
              {...register("entryPrice", {
                required: "Entry price is required",
                validate: {
                  positive: (v) => parseFloat(v) > 0 || "Must be a positive number"
                }
              })}
            />
            {errors.entryPrice && (
              <span className="text-[10px] font-bold text-destructive block mt-1" data-testid="entryPrice-error">{errors.entryPrice.message}</span>
            )}
          </div>

          {/* Quantity */}
          <div className="space-y-1.5">
            <Label htmlFor="hijack-qty" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Quantity
            </Label>
            <Input
              id="hijack-qty"
              type="number"
              step="1"
              className="border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary font-mono"
              {...register("qty", {
                required: "Quantity is required",
                validate: {
                  positive: (v) => parseInt(v, 10) > 0 || "Must be positive integer"
                }
              })}
            />
            {errors.qty && (
              <span className="text-[10px] font-bold text-destructive block mt-1" data-testid="qty-error">{errors.qty.message}</span>
            )}
          </div>

          {/* Stop Loss (SL) */}
          <div className="space-y-1.5">
            <Label htmlFor="hijack-SL" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Stop Loss (SL)
            </Label>
            <Input
              id="hijack-SL"
              type="number"
              step="any"
              className="border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary font-mono"
              {...register("SL", {
                required: "Stop loss is required",
                validate: {
                  positive: (v) => parseFloat(v) > 0 || "Must be a positive number",
                  lessThanEntry: (v) => parseFloat(v) < parseFloat(watchEntryPrice) || "SL must be < entry price"
                }
              })}
            />
            {errors.SL && (
              <span className="text-[10px] font-bold text-destructive block mt-1" data-testid="SL-error">{errors.SL.message}</span>
            )}
          </div>

          {/* Take Profit (TP) */}
          <div className="space-y-1.5">
            <Label htmlFor="hijack-TP" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Take Profit (TP)
            </Label>
            <Input
              id="hijack-TP"
              type="number"
              step="any"
              className="border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary font-mono"
              {...register("TP", {
                required: "Take profit is required",
                validate: {
                  positive: (v) => parseFloat(v) > 0 || "Must be a positive number"
                }
              })}
            />
            {errors.TP && (
              <span className="text-[10px] font-bold text-destructive block mt-1" data-testid="TP-error">{errors.TP.message}</span>
            )}
          </div>
        </div>

        <Button
          type="submit"
          disabled={!isValid || loading}
          className="w-full rounded-xl bg-destructive text-destructive-foreground px-4 py-3 text-xs font-bold transition hover:brightness-105 active:scale-98 shadow-md border-none mt-4 disabled:opacity-50"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-1.5">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Executing Override...
            </span>
          ) : (
            <span>EXECUTE HIJACK OVERRIDE</span>
          )}
        </Button>
      </form>
    </div>
  );
}

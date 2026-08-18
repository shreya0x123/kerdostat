import { useForm } from "react-hook-form";
import { useState, useEffect } from "react";
import { AlertCircle, CheckCircle, Loader2, Search, ChevronDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { overrideProposal, fetchAccountDetails, fetchOHLCV, searchAssets } from "@/services/apiService";

export default function HijackPanel({ proposal, onSuccess }) {
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(false);
  const [buyingPower, setBuyingPower] = useState(82980.27);
  const [livePrice, setLivePrice] = useState(150.00);
  const [unit, setUnit] = useState("#"); // "#" = Shares, "$" = Dollars
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Load actual Alpaca Buying Power
  useEffect(() => {
    async function loadAccount() {
      try {
        const data = await fetchAccountDetails();
        if (data && data.buying_power !== undefined) {
          setBuyingPower(data.buying_power);
        }
      } catch (err) {
        console.error("Failed to load buying power:", err);
      }
    }
    loadAccount();
  }, []);

  // Set default values based on proposal or generic mock values
  const defaultValues = {
    symbol: proposal?.symbol || "QUANT",
    qty: proposal?.qty || 1,
    orderType: "Market",
    limitPrice: proposal?.entry_price || 151.60,
    timeInForce: "DAY"
  };

  const {
    register,
    handleSubmit,
    watch,
    trigger,
    setValue,
    formState: { errors, isValid },
  } = useForm({
    defaultValues,
    mode: "onChange"
  });

  const watchSymbol = watch("symbol");
  const watchQty = watch("qty");
  const watchOrderType = watch("orderType");
  const watchLimitPrice = watch("limitPrice");

  // Fetch search suggestions
  useEffect(() => {
    const delayDebounce = setTimeout(async () => {
      if (watchSymbol && watchSymbol.trim().length > 0) {
        if (proposal && proposal.symbol === watchSymbol) {
          setSuggestions([]);
          setShowSuggestions(false);
          return;
        }
        try {
          const res = await searchAssets(watchSymbol);
          setSuggestions(res || []);
          setShowSuggestions(true);
        } catch (e) {
          console.error("Failed to search assets:", e);
        }
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 200);
    return () => clearTimeout(delayDebounce);
  }, [watchSymbol, proposal]);

  // Handle click outside suggestions
  useEffect(() => {
    const handleClickOutside = () => setShowSuggestions(false);
    window.addEventListener("click", handleClickOutside);
    return () => window.removeEventListener("click", handleClickOutside);
  }, []);

  const handleSelectSuggestion = (asset) => {
    setValue("symbol", asset.symbol, { shouldValidate: true, shouldDirty: true });
    setLivePrice(asset.price);
    setValue("limitPrice", asset.price, { shouldValidate: true });
    setShowSuggestions(false);
  };

  // Fetch live price for the typed symbol
  useEffect(() => {
    if (proposal && proposal.symbol === watchSymbol) {
      setLivePrice(proposal.entry_price || 150.00);
      return;
    }
    const delayDebounce = setTimeout(async () => {
      if (watchSymbol && watchSymbol.trim().length > 0) {
        try {
          const data = await fetchOHLCV("1D", watchSymbol.toUpperCase());
          if (data && data.length > 0) {
            const lastClose = data[data.length - 1].close;
            setLivePrice(lastClose);
            setValue("limitPrice", lastClose);
          }
        } catch (e) {
          console.error("Failed to fetch live price:", e);
        }
      }
    }, 800);
    return () => clearTimeout(delayDebounce);
  }, [watchSymbol, proposal, setValue]);

  // Trigger initial validation to check validity of pre-filled defaults
  useEffect(() => {
    trigger();
  }, [trigger]);

  // Calculate estimated cost
  const qtyVal = parseFloat(watchQty) || 0;
  const currentPriceReference = watchOrderType === "Limit" ? (parseFloat(watchLimitPrice) || livePrice) : livePrice;
  const estimatedCost = unit === "#" ? qtyVal * currentPriceReference : qtyVal;

  // Execute Order Submission
  const submitOrder = async (side) => {
    setLoading(true);
    setToast(null);

    const targetPrice = watchOrderType === "Limit" ? parseFloat(watchLimitPrice) : livePrice;
    const finalQty = unit === "#" ? Math.round(qtyVal) : Math.round(qtyVal / livePrice);

    if (finalQty <= 0) {
      setToast({ type: "error", message: "Calculated share quantity must be greater than zero." });
      setLoading(false);
      return;
    }

    // Dynamic SL/TP safety defaults to satisfy backend schema
    const slVal = side === "SELL" ? +(targetPrice * 1.05).toFixed(2) : +(targetPrice * 0.95).toFixed(2);
    const tpVal = side === "SELL" ? +(targetPrice * 0.95).toFixed(2) : +(targetPrice * 1.05).toFixed(2);

    try {
      const payload = {
        symbol: watchSymbol.toUpperCase(),
        qty: finalQty,
        SL: slVal,
        TP: tpVal,
        entry_price: targetPrice,
        proposal_id: proposal?.id || null,
        side: side,
        order_type: watchOrderType
      };

      await overrideProposal(proposal?.id || "manual", payload);
      setToast({ type: "success", message: `Order dispatched successfully: ${side} ${finalQty} ${watchSymbol.toUpperCase()}` });
      if (onSuccess) {
        onSuccess();
      }
    } catch (err) {
      setToast({ type: "error", message: err.message || "Order execution failed." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-sm mx-auto bg-card border border-border rounded-2xl shadow-xl overflow-hidden p-6 space-y-4" data-testid="hijack-panel">
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
              {toast.type === "success" ? "Execution Dispatched" : "Execution Failed"}
            </span>
            <p className="text-[11px] font-medium leading-normal opacity-90">{toast.message}</p>
          </div>
        </div>
      )}

      {/* Asset Ticker Search */}
      <div className="relative" onClick={(e) => e.stopPropagation()}>
        <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted-foreground">
          <Search className="h-4 w-4" />
        </span>
        <Input
          id="hijack-symbol"
          aria-label="Asset Symbol"
          type="text"
          placeholder="Search by symbol..."
          autoComplete="off"
          className="pl-9 border-border bg-secondary/25 text-foreground rounded-xl placeholder:text-muted-foreground/40 font-mono text-sm focus-visible:ring-primary focus-visible:border-primary"
          {...register("symbol", { required: "Symbol is required" })}
        />
        {showSuggestions && suggestions.length > 0 && (
          <div className="absolute z-50 left-0 right-0 top-full mt-1.5 bg-card border border-border rounded-xl shadow-2xl overflow-hidden max-h-60 overflow-y-auto divide-y divide-border/30">
            {suggestions.map((asset) => (
              <div
                key={asset.symbol}
                onClick={() => handleSelectSuggestion(asset)}
                className="flex items-center justify-between px-3 py-2.5 hover:bg-secondary/40 cursor-pointer transition duration-150"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-7 h-7 rounded-lg bg-muted flex items-center justify-center font-extrabold text-[10px] text-muted-foreground uppercase flex-shrink-0">
                    {asset.symbol.slice(0, 2)}
                  </div>
                  <div className="flex flex-col text-left truncate">
                    <span className="font-extrabold text-xs text-foreground uppercase tracking-wider">{asset.symbol}</span>
                    <span className="text-[9px] text-muted-foreground truncate max-w-[150px] font-medium mt-0.5">{asset.name}</span>
                  </div>
                </div>
                <div className="text-right flex flex-col justify-center flex-shrink-0">
                  <span className="font-mono font-bold text-xs text-foreground">
                    ${asset.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span className={`text-[9px] font-bold leading-none mt-0.5 ${
                    asset.change >= 0 ? "text-emerald-500" : "text-rose-500"
                  }`}>
                    {asset.change >= 0 ? "+" : ""}${asset.change.toFixed(2)} ({asset.change >= 0 ? "+" : ""}{asset.change_percent.toFixed(2)}%)
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quantity & Unit Selector */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <Label htmlFor="hijack-qty" className="text-xs font-bold text-foreground">
            Quantity
          </Label>
          <div className="flex bg-secondary/35 p-0.5 rounded-lg border border-border/30">
            <button
              type="button"
              onClick={() => setUnit("#")}
              className={`px-2.5 py-0.5 text-[10px] font-bold rounded-md transition ${
                unit === "#" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              #
            </button>
            <button
              type="button"
              onClick={() => setUnit("$")}
              className={`px-2.5 py-0.5 text-[10px] font-bold rounded-md transition ${
                unit === "$" ? "bg-primary text-primary-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              $
            </button>
          </div>
        </div>
        <Input
          id="hijack-qty"
          aria-label="Quantity"
          type="number"
          step="any"
          className="border-border bg-secondary/25 text-foreground rounded-xl font-mono text-sm focus-visible:ring-primary focus-visible:border-primary"
          {...register("qty", {
            required: "Quantity is required",
            validate: {
              positive: (v) => parseFloat(v) > 0 || "Must be positive"
            }
          })}
        />
        {errors.qty && (
          <span className="text-[10px] font-bold text-destructive block" data-testid="qty-error">{errors.qty.message}</span>
        )}
      </div>

      {/* Order Type Dropdown */}
      <div className="space-y-1.5">
        <Label htmlFor="order-type" className="text-xs font-bold text-foreground">
          Order Type
        </Label>
        <div className="relative">
          <select
            id="order-type"
            className="w-full appearance-none border border-border bg-secondary/25 text-foreground rounded-xl px-3 py-2 text-xs font-medium focus-visible:ring-primary focus-visible:border-primary focus:outline-none"
            {...register("orderType")}
          >
            <option value="Market">Market</option>
            <option value="Limit">Limit</option>
          </select>
          <span className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-muted-foreground">
            <ChevronDown className="h-3.5 w-3.5" />
          </span>
        </div>
      </div>

      {/* Limit Price - Dynamically Visible */}
      {watchOrderType === "Limit" && (
        <div className="space-y-1.5 animate-in slide-in-from-top-1 duration-200">
          <Label htmlFor="hijack-entryPrice" className="text-xs font-bold text-foreground">
            Limit Price ($)
          </Label>
          <Input
            id="hijack-entryPrice"
            aria-label="Limit Price"
            type="number"
            step="any"
            className="border-border bg-secondary/25 text-foreground rounded-xl font-mono text-sm focus-visible:ring-primary focus-visible:border-primary"
            {...register("limitPrice", {
              required: "Limit price is required",
              validate: {
                positive: (v) => parseFloat(v) > 0 || "Must be positive"
              }
            })}
          />
          {errors.limitPrice && (
            <span className="text-[10px] font-bold text-destructive block" data-testid="entryPrice-error">{errors.limitPrice.message}</span>
          )}
        </div>
      )}

      {/* Time in Force Dropdown */}
      <div className="space-y-1.5">
        <Label htmlFor="time-in-force" className="text-xs font-bold text-foreground">
          Time In Force
        </Label>
        <div className="relative">
          <select
            id="time-in-force"
            className="w-full appearance-none border border-border bg-secondary/25 text-foreground rounded-xl px-3 py-2 text-xs font-medium focus-visible:ring-primary focus-visible:border-primary focus:outline-none"
            {...register("timeInForce")}
          >
            <option value="DAY">DAY (Expires 4:00 PM ET)</option>
            <option value="GTC">GTC (Good 'Til Cancelled)</option>
          </select>
          <span className="absolute inset-y-0 right-3 flex items-center pointer-events-none text-muted-foreground">
            <ChevronDown className="h-3.5 w-3.5" />
          </span>
        </div>
      </div>

      {/* Cost & Buying Power Metrics Summary */}
      <div className="pt-2 border-t border-border/40 space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-muted-foreground">Estimated Cost</span>
          <span className="font-mono font-bold text-foreground">
            {estimatedCost > 0 ? `$${estimatedCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "-"}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold text-muted-foreground">Buying Power</span>
          <span className="font-mono font-bold text-foreground">
            ${buyingPower.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
      </div>

      {/* Dual Submission Buttons */}
      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button
          type="button"
          onClick={() => submitOrder("BUY")}
          disabled={!isValid || loading || (estimatedCost > buyingPower)}
          className="rounded-xl bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-white py-3 text-xs font-bold shadow-md transition-all active:scale-95 disabled:opacity-30 border-none"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Buy"}
        </Button>
        <Button
          type="button"
          onClick={() => submitOrder("SELL")}
          disabled={!isValid || loading}
          className="rounded-xl bg-rose-500 hover:bg-rose-600 active:bg-rose-700 text-white py-3 text-xs font-bold shadow-md transition-all active:scale-95 disabled:opacity-30 border-none"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Sell"}
        </Button>
      </div>
    </div>
  );
}

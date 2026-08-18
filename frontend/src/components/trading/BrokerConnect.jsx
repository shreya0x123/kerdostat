import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Server } from "lucide-react";

import { Button } from "./ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

const brokers = [
  { id: "zerodha", name: "Zerodha Kite" },
  { id: "alpaca", name: "Alpaca (Paper Trading)" },
];

const BrokerConnect = () => {
  const navigate = useNavigate();
  const [selectedBroker, setSelectedBroker] = useState("zerodha");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");

  const canProceed = apiKey.trim().length > 0 && apiSecret.trim().length > 0;

  return (
    <Card className="max-w-2xl rounded-3xl border-slate-800 bg-slate-950/95 text-slate-100 shadow-[0_20px_80px_rgba(15,23,42,0.7)]">
      <CardHeader className="space-y-3 border-b border-slate-800 pb-5">
        <CardTitle className="text-3xl text-slate-100">
          Connect Execution Venue
        </CardTitle>
        <CardDescription className="max-w-2xl text-slate-400">
          Link your brokerage account for live or paper trading execution. API
          credentials are encrypted and stored locally in your browser.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6 pt-6">
        <div className="space-y-2">
          <Label className="text-slate-300">Select broker</Label>
          <div className="flex flex-col gap-3 sm:flex-row">
            {brokers.map((broker) => {
              const active = selectedBroker === broker.id;
              return (
                <button
                  key={broker.id}
                  type="button"
                  onClick={() => setSelectedBroker(broker.id)}
                  className={`flex-1 rounded-2xl border px-4 py-3 text-left text-sm transition-all duration-200 ${
                    active
                      ? "border-cyan-400 bg-slate-900/90 text-cyan-200 shadow-[0_0_0_1px_rgba(56,189,248,0.4)]"
                      : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700 hover:bg-slate-900/95"
                  }`}
                >
                  <span className="font-medium">{broker.name}</span>
                  <span className="mt-1 block text-xs text-slate-500">
                    {broker.id === "alpaca"
                      ? "Paper trading mode"
                      : "Live execution"}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="api-key" className="text-slate-300">
              API Key / Client ID
            </Label>
            <Input
              id="api-key"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Enter API key"
              className="bg-slate-900 border-slate-800 text-slate-100 placeholder:text-slate-500"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="api-secret" className="text-slate-300">
              API Secret
            </Label>
            <Input
              id="api-secret"
              type="password"
              value={apiSecret}
              onChange={(event) => setApiSecret(event.target.value)}
              placeholder="Enter API secret"
              className="bg-slate-900 border-slate-800 text-slate-100 placeholder:text-slate-500"
            />
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex flex-col gap-3 border-t border-slate-800 pt-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <p className="text-sm text-slate-500">
            API keys remain local and are never sent to external servers. Keep
            in mind your broker’s rate limits may apply during rapid order
            testing.
          </p>
          <p className="text-xs text-slate-600">
            Note: Frequent polling or repeated test calls can trigger rate limit
            throttling.
          </p>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button
            variant="default"
            className="inline-flex items-center gap-2 rounded-2xl bg-cyan-500 px-5 py-3 text-slate-950 shadow-lg shadow-cyan-500/20 hover:bg-cyan-400"
            type="button"
          >
            <Server className="h-4 w-4" />
            Test Connection
          </Button>
          <Button
            type="button"
            onClick={() => navigate("/dashboard")}
            disabled={!canProceed}
            className={`inline-flex items-center justify-center rounded-2xl px-5 py-3 text-slate-100 transition ${
              canProceed
                ? "bg-slate-800 text-cyan-300 hover:bg-slate-700"
                : "cursor-not-allowed bg-slate-950/60 text-slate-600"
            }`}
          >
            Proceed to Dashboard
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
};

export default BrokerConnect;

import { useState } from "react";
import { 
  Terminal, 
  Copy, 
  Check, 
  BookOpen, 
  Lock, 
  ShieldAlert, 
  Activity, 
  Code,
  FileCode,
  RefreshCw,
  Cpu
} from "lucide-react";

const codeSnippets = {
  auth: {
    title: "User Authentication",
    description: "Submit trader credentials to establish an authenticated session. Upon successful validation, the server sets a secure, HTTP-only cookie (`access_token`) used for all compliance-wrapped endpoints.",
    method: "POST",
    path: "/auth/login",
    requestBody: [
      { name: "email", type: "string", required: true, desc: "Account email address (e.g. trader@kerdostat.com)." },
      { name: "password", type: "string", required: true, desc: "Cleartext account password." }
    ],
    response: `{
  "id": "user-1",
  "name": "Alex Mercer",
  "email": "trader@kerdostat.com"
}`,
    python: `import requests

url = "http://localhost:8000/auth/login"
payload = {
    "email": "trader@kerdostat.com",
    "password": "password123"
}

response = requests.post(url, json=payload)
print(response.json())`,
    javascript: `const payload = {
  email: "trader@kerdostat.com",
  password: "password123"
};

fetch("http://localhost:8000/auth/login", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify(payload)
})
.then(res => res.json())
.then(data => console.log(data));`,
    curl: `curl -X POST "http://localhost:8000/auth/login" \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "trader@kerdostat.com",
    "password": "password123"
  }'`
  },
  ohlcv: {
    title: "Market Candlestick Stream",
    description: "Fetch high-fidelity historical market candles. Includes open, high, low, close, volume, and an authentic rolling 14-period Relative Strength Index (RSI) computed dynamically.",
    method: "GET",
    path: "/market/ohlcv",
    queryParams: [
      { name: "range", type: "string", required: false, default: "1D", desc: "Duration window: '1D' (hourly), '1W' (4-hour intervals), or '1M' (daily)." }
    ],
    response: `[
  {
    "time": "14:00",
    "open": 151.60,
    "high": 153.10,
    "low": 151.00,
    "close": 152.80,
    "volume": 9500,
    "rsi": 48.20
  }
]`,
    python: `import requests

url = "http://localhost:8000/market/ohlcv"
params = {"range": "1D"}

response = requests.get(url, params=params)
print(response.json())`,
    javascript: `fetch("http://localhost:8000/market/ohlcv?range=1D")
  .then(res => res.json())
  .then(data => console.log(data));`,
    curl: `curl -X GET "http://localhost:8000/market/ohlcv?range=1D"`
  },
  proposals: {
    title: "Fetch Strategic Proposals",
    description: "Retrieve active buying and selling order proposals formulated by AI quantitative models currently awaiting human-in-the-loop (HITL) review.",
    method: "GET",
    path: "/trade/proposals",
    response: `[
  {
    "id": "prop-1",
    "symbol": "QUANT",
    "signal": "BUY",
    "qty": 150,
    "SL": 149.00,
    "TP": 157.50,
    "status": "pending",
    "XAIReason": "Neural network double bottom formation."
  }
]`,
    python: `import requests

url = "http://localhost:8000/trade/proposals"
response = requests.get(url)
print(response.json())`,
    javascript: `fetch("http://localhost:8000/trade/proposals")
  .then(res => res.json())
  .then(data => console.log(data));`,
    curl: `curl -X GET "http://localhost:8000/trade/proposals"`
  },
  action: {
    title: "Approve/Reject Order",
    description: "Dispatch human-in-the-loop approval or rejection for a pending AI proposal. Approving a proposal triggers broker routing and appends to audit logs.",
    method: "PATCH",
    path: "/trade/{proposal_id}/action",
    requestBody: [
      { name: "action", type: "string", required: true, desc: "Action value: either 'approve' or 'reject'." }
    ],
    response: `{
  "id": "prop-1",
  "symbol": "QUANT",
  "status": "approved",
  "qty": 150,
  "SL": 149.00,
  "TP": 157.50
}`,
    python: `import requests

url = "http://localhost:8000/trade/prop-1/action"
payload = {"action": "approve"}

response = requests.patch(url, json=payload)
print(response.json())`,
    javascript: `fetch("http://localhost:8000/trade/prop-1/action", {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ action: "approve" })
})
.then(res => res.json())
.then(data => console.log(data));`,
    curl: `curl -X PATCH "http://localhost:8000/trade/prop-1/action" \\
  -H "Content-Type: application/json" \\
  -d '{"action": "approve"}'`
  },
  hijack: {
    title: "Direct Execution Hijack",
    description: "Bypass typical model pipeline parameters to directly override order quantities, entry trigger lines, and risk stop/target boundaries.",
    method: "POST",
    path: "/trade/hijack",
    requestBody: [
      { name: "symbol", type: "string", required: true, desc: "Asset identifier ticker." },
      { name: "qty", type: "integer", required: true, desc: "Size of position order." },
      { name: "entry_price", type: "float", required: true, desc: "Direct override execution entry price." },
      { name: "SL", type: "float", required: true, desc: "Custom stop loss price (must be < entry price)." },
      { name: "TP", type: "float", required: true, desc: "Custom take profit target price." },
      { name: "proposal_id", type: "string", required: false, desc: "Optionally bind hijack override to terminate a pending proposal ID." }
    ],
    response: `{
  "status": "success",
  "message": "Hijack executed and logged successfully"
}`,
    python: `import requests

url = "http://localhost:8000/trade/hijack"
payload = {
    "symbol": "QUANT",
    "qty": 100,
    "entry_price": 150.00,
    "SL": 145.00,
    "TP": 157.50,
    "proposal_id": "prop-1"
}

response = requests.post(url, json=payload)
print(response.json())`,
    javascript: `const payload = {
  symbol: "QUANT",
  qty: 100,
  entry_price: 150.00,
  SL: 145.00,
  TP: 157.50,
  proposal_id: "prop-1"
};

fetch("http://localhost:8000/trade/hijack", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(payload)
})
.then(res => res.json())
.then(data => console.log(data));`,
    curl: `curl -X POST "http://localhost:8000/trade/hijack" \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "QUANT",
    "qty": 100,
    "entry_price": 150.00,
    "SL": 145.00,
    "TP": 157.50,
    "proposal_id": "prop-1"
  }'`
  },
  websocket: {
    title: "WebSockets Live Gateway",
    description: "Establish a persistent duplex communication link. Stream server updates in real-time such as immediate proposal updates, system actions, or connection logs.",
    method: "WS",
    path: "/ws",
    response: `{
  "event": "proposal_updated",
  "proposal_id": "prop-1",
  "status": "approved",
  "symbol": "QUANT",
  "signal": "BUY"
}`,
    python: `# Python WebSocket connection example using websocket-client
import websocket
import json

def on_message(ws, message):
    print("Received event:", json.loads(message))

ws = websocket.WebSocketApp(
    "ws://localhost:8000/ws",
    on_message=on_message
)
ws.run_forever()`,
    javascript: `const ws = new WebSocket("ws://localhost:8000/ws");

ws.onopen = () => {
  console.log("WebSocket connected.");
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Live stream update:", data);
};`,
    curl: `# Connect using websocat tool
websocat ws://localhost:8000/ws`
  }
};

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState("auth");
  const [codeLang, setCodeLang] = useState("python"); // python | javascript | curl
  const [copied, setCopied] = useState(false);
  const [liveResponse, setLiveResponse] = useState(null);
  const [playgroundLoading, setPlaygroundLoading] = useState(false);

  const currentSnippet = codeSnippets[activeTab];

  const handleCopy = (code) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePlaygroundRun = async () => {
    setPlaygroundLoading(true);
    setLiveResponse(null);
    try {
      let url = (window.location.port === "80" || window.location.port === "") ? `/api${currentSnippet.path}` : `http://localhost:8000${currentSnippet.path}`;
      let options = {
        credentials: "include",
      };

      if (currentSnippet.method === "POST") {
        options.method = "POST";
        options.headers = { "Content-Type": "application/json" };
        if (activeTab === "auth") {
          options.body = JSON.stringify({ email: "trader@kerdostat.com", password: "password123" });
        } else if (activeTab === "hijack") {
          options.body = JSON.stringify({
            symbol: "QUANT",
            qty: 100,
            entry_price: 150.00,
            SL: 145.00,
            TP: 157.50,
            proposal_id: "prop-1"
          });
        }
      } else if (currentSnippet.method === "PATCH") {
        options.method = "PATCH";
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify({ action: "approve" });
        url = url.replace("{proposal_id}", "prop-1");
      } else if (currentSnippet.method === "GET") {
        options.method = "GET";
        if (activeTab === "ohlcv") {
          url += "?range=1D&symbol=QUANT";
        }
      } else if (currentSnippet.method === "WS") {
        setLiveResponse("WebSocket client initiated connection at: ws://localhost:8000/ws\nListening for live streams...");
        setPlaygroundLoading(false);
        return;
      }

      const res = await fetch(url, options);
      const data = await res.json();
      setLiveResponse(JSON.stringify(data, null, 2));
    } catch (err) {
      setLiveResponse(JSON.stringify({ error: err.message || "Failed to contact local sandbox server." }, null, 2));
    } finally {
      setPlaygroundLoading(false);
    }
  };

  const getMethodColor = (method) => {
    switch (method) {
      case "GET":
        return "bg-sky-500/10 text-sky-400 border-sky-500/20";
      case "POST":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "PATCH":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "WS":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      default:
        return "bg-primary/10 text-primary border-primary/20";
    }
  };

  const currentCode = currentSnippet[codeLang] || currentSnippet.python;

  return (
    <div className="w-full max-w-7xl mx-auto py-4 px-2 md:px-4 space-y-8">
      {/* Sub-header Banner */}
      <section className="space-y-3 max-w-4xl text-left">
        <div className="flex items-center gap-2">
          <span className="inline-block rounded-full bg-primary/10 text-primary border border-primary/20 px-3 py-1 text-xs font-semibold uppercase tracking-wider">
            API Documentation
          </span>
          <span className="h-px w-8 bg-border" />
          <span className="text-xs text-muted-foreground">Sandbox Gateway v1.0.0</span>
        </div>
        <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-foreground">
          Kerdostat Platform <span className="text-primary">Integrations Desk</span>
        </h2>
        <p className="text-sm md:text-base text-muted-foreground leading-relaxed">
          Interact with Kerdostat's live broker routes, monitor machine learning signals, and establish manual override hijack triggers using our REST endpoints and WebSocket relays.
        </p>
      </section>

      {/* Docs Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-8 pt-4">
        {/* Navigation Sidebar */}
        <aside className="space-y-2 lg:border-r lg:border-border/55 lg:pr-6">
          <h3 className="text-xs font-bold text-muted-foreground uppercase tracking-widest px-3 mb-4 flex items-center gap-2">
            <BookOpen className="h-3.5 w-3.5" /> Reference API
          </h3>
          <nav className="flex flex-row lg:flex-col overflow-x-auto lg:overflow-x-visible gap-1 pb-3 lg:pb-0 scrollbar-none">
            {Object.entries(codeSnippets).map(([key, item]) => {
              const isActive = activeTab === key;
              return (
                <button
                  key={key}
                  onClick={() => {
                    setActiveTab(key);
                    setCopied(false);
                  }}
                  className={`flex items-center gap-2 px-3 py-2 text-xs font-semibold rounded-xl border transition-all whitespace-nowrap text-left w-full ${
                    isActive
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-transparent text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
                  }`}
                >
                  <span className={`h-1.5 w-1.5 rounded-full ${
                    item.method === "GET" ? "bg-sky-400" :
                    item.method === "POST" ? "bg-emerald-400" :
                    item.method === "PATCH" ? "bg-amber-400" : "bg-purple-400"
                  }`} />
                  <span className="flex-1">{item.title}</span>
                  <span className="text-[9px] opacity-70 px-1.5 py-0.5 rounded border border-current font-mono">
                    {item.method}
                  </span>
                </button>
              );
            })}
          </nav>
        </aside>

        {/* Documentation Content & Code Split */}
        <div className="grid grid-cols-1 xl:grid-cols-[1.1fr_1fr] gap-8">
          {/* Detailed Endpoint Description */}
          <div className="space-y-6">
            <div className="space-y-3 border-b border-border/50 pb-5">
              <div className="flex flex-wrap items-center gap-3">
                <span className={`px-2.5 py-1 text-xs font-bold border rounded-lg font-mono tracking-wider ${getMethodColor(currentSnippet.method)}`}>
                  {currentSnippet.method}
                </span>
                <span className="font-mono text-sm font-semibold bg-secondary/40 border border-border/60 px-3 py-1 rounded-lg text-foreground">
                  {currentSnippet.path}
                </span>
              </div>
              <h3 className="text-xl font-bold text-foreground">{currentSnippet.title}</h3>
              <p className="text-xs md:text-sm text-muted-foreground leading-relaxed">
                {currentSnippet.description}
              </p>
            </div>

            {/* Request Schema Table if present */}
            {currentSnippet.requestBody && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <Lock className="h-3.5 w-3.5 text-primary" /> Request Body Structure
                </h4>
                <div className="overflow-x-auto rounded-xl border border-border bg-card">
                  <table className="min-w-full divide-y divide-border text-left">
                    <thead className="bg-secondary/15">
                      <tr>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Parameter</th>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Type</th>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Requirement</th>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-xs">
                      {currentSnippet.requestBody.map((param) => (
                        <tr key={param.name}>
                          <td className="px-4 py-2.5 font-mono font-bold text-foreground">{param.name}</td>
                          <td className="px-4 py-2.5 font-mono text-primary">{param.type}</td>
                          <td className="px-4 py-2.5">
                            {param.required ? (
                              <span className="text-[10px] font-bold text-destructive bg-destructive/5 border border-destructive/15 px-1.5 py-0.5 rounded">Required</span>
                            ) : (
                              <span className="text-[10px] font-semibold text-muted-foreground">Optional</span>
                            )}
                          </td>
                          <td className="px-4 py-2.5 text-muted-foreground">{param.desc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Query Params table if present */}
            {currentSnippet.queryParams && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <RefreshCw className="h-3.5 w-3.5 text-primary animate-spin-slow" /> Query Parameters
                </h4>
                <div className="overflow-x-auto rounded-xl border border-border bg-card">
                  <table className="min-w-full divide-y divide-border text-left">
                    <thead className="bg-secondary/15">
                      <tr>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Parameter</th>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Type</th>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Default</th>
                        <th className="px-4 py-2 text-[10px] font-bold text-muted-foreground uppercase">Description</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-xs">
                      {currentSnippet.queryParams.map((param) => (
                        <tr key={param.name}>
                          <td className="px-4 py-2.5 font-mono font-bold text-foreground">{param.name}</td>
                          <td className="px-4 py-2.5 font-mono text-primary">{param.type}</td>
                          <td className="px-4 py-2.5 font-mono text-muted-foreground">{param.default || "—"}</td>
                          <td className="px-4 py-2.5 text-muted-foreground">{param.desc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Safety & Compliance notice */}
            <div className="flex gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-xs text-amber-500 leading-relaxed max-w-lg">
              <ShieldAlert className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">Compliance Directive: </span>
                All post-registration loop operations are subject to standard human-in-the-loop audit validation. Executing manual hijacks appends logs directly to audit trails.
              </div>
            </div>
          </div>

          {/* Interactive Code Pane */}
          <div className="rounded-2xl border border-border bg-card shadow-lg flex flex-col overflow-hidden h-fit">
            <div className="border-b border-border bg-secondary/15 px-4 py-3 flex items-center justify-between">
              <span className="text-xs font-bold text-muted-foreground flex items-center gap-1.5">
                <FileCode className="h-3.5 w-3.5" /> Request Snippet
              </span>
              <div className="flex gap-1.5">
                {["python", "javascript", "curl"].map((lang) => (
                  <button
                    key={lang}
                    onClick={() => setCodeLang(lang)}
                    className={`px-2 py-1 text-[10px] font-bold rounded border uppercase transition ${
                      codeLang === lang
                        ? "bg-primary/15 text-primary border-primary/20"
                        : "bg-transparent text-muted-foreground border-transparent hover:text-foreground"
                    }`}
                  >
                    {lang === "javascript" ? "NodeJS" : lang}
                  </button>
                ))}
              </div>
            </div>

            {/* Code Highlight Block */}
            <div className="p-4 bg-secondary/10 relative group">
              <button
                onClick={() => handleCopy(currentCode)}
                className="absolute top-3 right-3 h-8 w-8 rounded-lg border border-border bg-card flex items-center justify-center text-muted-foreground hover:text-foreground active:scale-95 transition opacity-0 group-hover:opacity-100 focus:opacity-100"
                title="Copy code to clipboard"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
              <pre className="text-left text-xs font-mono overflow-x-auto text-foreground leading-relaxed select-all">
                <code>{currentCode}</code>
              </pre>
            </div>

            {/* Response Preview Header */}
            <div className="border-t border-b border-border bg-secondary/15 px-4 py-2 flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider font-bold text-muted-foreground flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5" /> Expected Response JSON (200 OK)
              </span>
              <button
                data-testid="try-it-btn"
                onClick={handlePlaygroundRun}
                disabled={playgroundLoading}
                className="flex items-center gap-1.5 px-3 py-1 text-[11px] font-bold text-primary bg-primary/10 hover:bg-primary/20 disabled:opacity-50 border border-primary/25 rounded-lg transition"
              >
                {playgroundLoading ? (
                  <>
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    Executing...
                  </>
                ) : (
                  <>
                    <Terminal className="h-3 w-3" />
                    Try It Out
                  </>
                )}
              </button>
            </div>

            {/* Response content */}
            <div className="p-4 bg-secondary/5">
              <pre className="text-left text-xs font-mono overflow-x-auto text-foreground leading-relaxed">
                <code>{currentSnippet.response}</code>
              </pre>
            </div>

            {/* Live Response Container */}
            {liveResponse && (
              <div className="border-t border-border bg-black/20">
                <div className="bg-secondary/10 px-4 py-2.5 flex items-center justify-between border-b border-border">
                  <span className="text-[10px] uppercase tracking-wider font-bold text-primary flex items-center gap-1.5">
                    <Activity className="h-3.5 w-3.5" /> Live Sandbox Response
                  </span>
                  <button
                    onClick={() => setLiveResponse(null)}
                    className="text-[9px] text-muted-foreground hover:text-foreground font-bold px-2 py-0.5 rounded border border-border bg-card transition"
                  >
                    Clear
                  </button>
                </div>
                <div className="p-4">
                  <pre
                    data-testid="live-response-output"
                    className="text-left text-xs font-mono overflow-x-auto text-emerald-400 bg-secondary/10 p-3 rounded-xl border border-border/50 max-h-[250px]"
                  >
                    <code>{liveResponse}</code>
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

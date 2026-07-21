import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Play,
  BookOpen,
  Briefcase,
  TrendingUp,
  Terminal,
  Copy,
  Check,
  Shield,
  Activity,
  Cpu,
  RefreshCw,
  Moon,
  Sun
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useTheme } from "@/hooks/useTheme";
import Footer from "@/components/Footer";

const codeSnippets = {
  python: `import kerdostat

# Authenticate client
client = kerdostat.Client(
    api_key="krdst_live_948f2a...",
    api_secret="sec_821a..."
)

# Retrieve current price
ticker = client.market.get_price("QUANT")
print(f"Current price: \${ticker.price}")

# Execute limit order via Zerodha / Alpaca
order = client.orders.create(
    symbol="QUANT",
    qty=50,
    side="BUY",
    type="LIMIT",
    price=ticker.price - 0.05
)
print(f"Dispatched: {order.id} | {order.status}")`,
  javascript: `import { KerdostatClient } from "@kerdostat/sdk";

const client = new KerdostatClient({
  apiKey: "krdst_live_948f2a...",
  apiSecret: "sec_821a..."
});

// Stream real-time engine logs
client.stream.on("signal", (signal) => {
  console.log(\`Signal: \${signal.type} | Conf: \${signal.confidence}\`);
  
  if (signal.confidence > 0.85) {
    client.orders.execute({
      symbol: signal.symbol,
      qty: signal.qty,
      side: signal.direction
    });
  }
});`,
  curl: `curl -X POST "https://api.kerdostat.com/v1/orders" \\
  -H "Authorization: Bearer krdst_live_948f2a..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "QUANT",
    "qty": 50,
    "side": "BUY",
    "type": "MARKET"
  }'`
};

export default function LandingPage() {
  const { isAuthenticated } = useAuth();
  const { theme, setTheme } = useTheme();
  const [activeTab, setActiveTab] = useState("python");
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(codeSnippets[activeTab]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-background text-foreground transition-colors duration-300 font-sans relative overflow-hidden selection:bg-primary/20 selection:text-primary">
      {/* Visual background lights */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/5 dark:bg-primary/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-500/5 dark:bg-indigo-500/10 blur-[150px] pointer-events-none" />

      {/* Tech Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(128,128,128,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(128,128,128,0.03)_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,rgba(128,128,128,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(128,128,128,0.05)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none opacity-80" />

      {/* Standalone Visitor Header Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/80 backdrop-blur-xl transition-all duration-300">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="h-9 w-9 border border-primary/30 rounded-xl bg-primary/10 text-primary grid place-items-center text-sm font-bold tracking-[0.15em] group-hover:scale-103 transition duration-200">
                K
              </div>
              <span className="text-lg font-extrabold tracking-widest text-foreground font-mono">
                KERDOSTAT
              </span>
              <span className="text-[9px] font-bold px-2 py-0.5 rounded-md bg-primary/10 text-primary border border-primary/20">
                v1.0
              </span>
            </Link>

            <nav className="hidden md:flex items-center gap-6 text-xs font-bold uppercase tracking-wider text-muted-foreground">
              <a href="#use-cases" className="hover:text-foreground transition-colors">Use Cases</a>
              <a href="#features" className="hover:text-foreground transition-colors">Capabilities</a>
              <Link to="/docs" className="hover:text-foreground transition-colors">API Docs</Link>
              <Link to="/contact" className="hover:text-foreground transition-colors">Contact Desk</Link>
            </nav>
          </div>

          <div className="flex items-center gap-3">
            {/* Theme Toggle Button */}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card text-foreground transition hover:border-primary/50 hover:text-primary active:scale-95"
              aria-label="Toggle theme"
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-indigo-500" />
              )}
            </button>

            <Link
              to="/docs"
              className="hidden sm:inline-flex items-center gap-1.5 rounded-xl border border-border bg-card px-4 h-9 text-xs font-bold text-muted-foreground hover:border-primary/30 hover:text-foreground transition"
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Reference API</span>
            </Link>

            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-5 h-9 text-xs font-bold text-primary-foreground hover:scale-102 transition shadow-lg shadow-primary/10 hover:shadow-primary/20"
              data-testid="landing-cta-btn"
            >
              <Play className="h-3 w-3 fill-current" />
              <span>{isAuthenticated ? "Launch Terminal" : "Access Terminal"}</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Body Grid */}
      <div className="w-full max-w-6xl mx-auto py-12 px-6 md:px-0 space-y-24">
        {/* 1. Hero Section */}
        <section className="flex flex-col lg:flex-row items-center justify-between gap-12 pt-4 lg:pt-8 text-left">
          <div className="flex-1 space-y-6 max-w-xl">
            <span className="inline-block rounded-full bg-primary/10 text-primary border border-primary/20 py-1 px-4 text-xs font-semibold uppercase tracking-wider">
              Infrastructure v1.0
            </span>
            <h1 className="text-4xl md:text-5xl lg:text-[52px] leading-tight font-extrabold tracking-tight text-foreground font-sans">
              The infrastructure <br/>
              powering <span className="text-primary">algorithmic assets</span>
            </h1>
            <p className="text-muted-foreground text-sm sm:text-base leading-relaxed">
              Deploy, execute, and govern quantitative strategies with zero friction. Connect Kerdostat’s direct brokerage pipes to scale compliance, automated risk management, and order routing.
            </p>
            <div className="flex flex-wrap items-center gap-4 pt-2">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-xs font-extrabold text-primary-foreground hover:brightness-105 active:scale-98 transition shadow-lg shadow-primary/5"
              >
                <Play className="h-4 w-4 fill-current" />
                <span>Launch Terminal</span>
              </Link>
              <Link
                to="/docs"
                className="inline-flex items-center gap-2 rounded-xl border border-border bg-card hover:bg-secondary/40 px-6 py-3.5 text-xs font-extrabold text-muted-foreground hover:text-foreground active:scale-98 transition"
              >
                <BookOpen className="h-4 w-4" />
                <span>Explore Docs</span>
              </Link>
            </div>
          </div>

          {/* Hero Interactive Code Pane */}
          <div className="flex-1 w-full max-w-lg">
            <div className="rounded-2xl border border-border bg-card shadow-xl overflow-hidden font-mono text-xs">
              {/* Code Tabs Header */}
              <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-3">
                <div className="flex items-center gap-2">
                  {["python", "javascript", "curl"].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => {
                        setActiveTab(tab);
                        setCopied(false);
                      }}
                      type="button"
                      className={`rounded-lg px-3 py-1.5 font-bold uppercase transition duration-150 ${
                        activeTab === tab
                          ? "bg-primary/10 text-primary border border-primary/25"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                      data-testid={`code-tab-${tab}`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleCopy}
                  type="button"
                  className="flex items-center gap-1 rounded-lg border border-border bg-card px-2.5 py-1.5 text-muted-foreground hover:text-foreground transition active:scale-95"
                  title="Copy code"
                  data-testid="copy-code-btn"
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                      <span className="text-[10px] text-emerald-500 font-bold">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" />
                    </>
                  )}
                </button>
              </div>

              {/* Code body block */}
              <div className="p-5 overflow-x-auto bg-[#0a101d] dark:bg-[#080d17] text-slate-300 leading-6 min-h-[300px] flex items-center">
                <pre className="w-full text-left font-mono">
                  <code>
                    {codeSnippets[activeTab].split("\n").map((line, idx) => {
                      const isComment = line.trim().startsWith("#") || line.trim().startsWith("//");
                      const colorClass = isComment 
                        ? "text-slate-500 italic" 
                        : line.includes("import") || line.includes("new")
                        ? "text-cyan-400"
                        : line.includes("class") || line.includes("Client")
                        ? "text-amber-400"
                        : line.includes('"') || line.includes("'")
                        ? "text-emerald-400"
                        : "text-slate-300";

                      return (
                        <div key={idx} className={colorClass}>
                          {line}
                        </div>
                      );
                    })}
                  </code>
                </pre>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Use Cases Section */}
        <section id="use-cases" className="space-y-12 text-left">
          <div className="space-y-3">
            <span className="inline-block rounded-full bg-indigo-500/10 text-indigo-500 border border-indigo-500/20 py-0.5 px-4 text-xs font-semibold uppercase tracking-wider">
              Use Cases
            </span>
            <h2 className="text-2xl md:text-3xl font-extrabold text-foreground">
              Modular connectivity built for modern quant desks
            </h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {/* Card 1 */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between hover:border-primary/50 transition duration-300">
              <div className="space-y-4">
                <div className="h-10 w-10 rounded-xl bg-primary/10 border border-primary/20 text-primary grid place-items-center">
                  <Briefcase className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-bold text-foreground">Brokers & Wealth Managers</h3>
                <p className="text-sm text-muted-foreground leading-relaxed font-sans">
                  Upscale retail investing workflows. Provide high-fidelity broker integrations and compliant trading pipes to your mobile and web customers with zero maintenance overhead.
                </p>
              </div>
              <Link
                to="/use-cases/brokers"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:gap-2 transition pt-6 mt-auto"
              >
                <span>Learn more</span>
                <span>&rarr;</span>
              </Link>
            </div>

            {/* Card 2 */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between hover:border-primary/50 transition duration-300">
              <div className="space-y-4">
                <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 grid place-items-center">
                  <TrendingUp className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-bold text-foreground">Banks & EMIs</h3>
                <p className="text-sm text-muted-foreground leading-relaxed font-sans">
                  Embed automated investment strategies. Unlock superior customer touchpoints by offering secure, compliant, and automated cash sweep features with absolute security.
                </p>
              </div>
              <Link
                to="/use-cases/banks"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-indigo-500 hover:gap-2 transition pt-6 mt-auto"
              >
                <span>Learn more</span>
                <span>&rarr;</span>
              </Link>
            </div>

            {/* Card 3 */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between hover:border-primary/50 transition duration-300">
              <div className="space-y-4">
                <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 grid place-items-center">
                  <Terminal className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-bold text-foreground">Software Companies</h3>
                <p className="text-sm text-muted-foreground leading-relaxed font-sans">
                  Launch automated trading capabilities inside your software ecosystem. Create API pipelines, custom webhooks, and sandbox execution layers within SaaS products.
                </p>
              </div>
              <Link
                to="/use-cases/software"
                className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-500 hover:gap-2 transition pt-6 mt-auto"
              >
                <span>Learn more</span>
                <span>&rarr;</span>
              </Link>
            </div>
          </div>
        </section>

        {/* 3. Core Capabilities Grid */}
        <section id="features" className="space-y-12 text-left">
          <div className="space-y-3">
            <span className="inline-block rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 py-0.5 px-4 text-xs font-semibold uppercase tracking-wider">
              Capabilities
            </span>
            <h2 className="text-2xl md:text-3xl font-extrabold text-foreground">
              Complete compliance and safety out of the box
            </h2>
          </div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-border bg-card/60 p-6 space-y-3 hover:-translate-y-1 transition duration-300 shadow-sm">
              <Shield className="h-6 w-6 text-primary" />
              <h4 className="font-bold text-foreground text-sm">Security & Audits</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                State locked safety keys stored exclusively within local cookies or client environments. Zero data custody leakage.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card/60 p-6 space-y-3 hover:-translate-y-1 transition duration-300 shadow-sm">
              <Activity className="h-6 w-6 text-indigo-500" />
              <h4 className="font-bold text-foreground text-sm">Real-time Telemetry</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Interactive high-precision charting and live log feeds from target execution platforms and order books.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card/60 p-6 space-y-3 hover:-translate-y-1 transition duration-300 shadow-sm">
              <Cpu className="h-6 w-6 text-emerald-500" />
              <h4 className="font-bold text-foreground text-sm">Modular Execution</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Integrate with premium execution venues including Zerodha, Alpaca Paper Trading, and custom API endpoints.
              </p>
            </div>

            <div className="rounded-xl border border-border bg-card/60 p-6 space-y-3 hover:-translate-y-1 transition duration-300 shadow-sm">
              <RefreshCw className="h-6 w-6 text-amber-500" />
              <h4 className="font-bold text-foreground text-sm">Low-latency Feeds</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Live updates with responsive micro-polling structures ensuring high data consistency on charts and metrics.
              </p>
            </div>
          </div>
        </section>
      </div>

      <Footer />
    </div>
  );
}

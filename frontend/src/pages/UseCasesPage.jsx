import { useParams, Link } from "react-router-dom";
import { 
  Briefcase, 
  TrendingUp, 
  Terminal, 
  ShieldCheck, 
  Cpu, 
  ArrowRight,
  Database,
  Layers
} from "lucide-react";

const useCaseContent = {
  brokers: {
    title: "Brokers & Wealth Managers",
    tagline: "Build the next generation of algorithmic wealth management.",
    subtitle: "Upscale your retail trading offering. Integrate direct brokerage execution API access into your mobile or web app with zero operational friction.",
    icon: Briefcase,
    badges: ["Brokerage API", "Automated Rebalancing", "Slippage Shield"],
    description: "Maximize value proposition for your asset managers and retail clients by providing pre-validated execution pipelines. Kerdostat abstracts the complexity of connecting directly to execution venues (Zerodha, Alpaca, etc.), handling order routing, rate limits, and fills in the background.",
    features: [
      {
        title: "Direct Venue Connectivity",
        desc: "Native integration with leading brokers supporting live execution and low-latency paper trading.",
        icon: Cpu
      },
      {
        title: "Custom Basket Rebalancing",
        desc: "Enable clients to auto-allocate capital into custom-indexed strategies with single-click triggers.",
        icon: Layers
      },
      {
        title: "Compliance-First Architecture",
        desc: "All trade proposals pass through an automated check before dispatch, reducing execution errors.",
        icon: ShieldCheck
      }
    ]
  },
  banks: {
    title: "Banks & EMIs",
    tagline: "Embed automated investment strategies into your banking infrastructure.",
    subtitle: "Unlock superior customer touchpoints by offering secure, compliant, and automated cash sweep features.",
    icon: TrendingUp,
    badges: ["Deposit Sweeps", "ACID Audit Logs", "HITL Safety Gates"],
    description: "Offer depositors automated cash yield routing with absolute safety. Kerdostat's Human-In-The-Loop (HITL) architecture ensures that autonomous algorithms operate within strict, institutionally approved boundaries, making deployment fully auditable and compliant.",
    features: [
      {
        title: "Yield Deposit Sweeps",
        desc: "Automatically route excess cash deposits into predefined low-volatility algorithmic portfolios.",
        icon: Database
      },
      {
        title: "Immutable Auditing",
        desc: "PostgreSQL-backed append-only audit trail logging every bot proposal, human decision, and API response.",
        icon: ShieldCheck
      },
      {
        title: "Hard-Limit Safety Gates",
        desc: "Configurable daily drawdown caps and maximum position limits enforced at the database execution level.",
        icon: Terminal
      }
    ]
  },
  software: {
    title: "Software Companies",
    tagline: "Launch automated trading capabilities inside your software ecosystem.",
    subtitle: "Add direct algorithmic execution and real-time market data to your SaaS platform with our developer-first API.",
    icon: Terminal,
    badges: ["REST & WebSockets", "Sandbox Testing", "Webhooks Engine"],
    description: "Create new financial use cases inside your software. Leverage Kerdostat's developer-friendly REST and WebSocket APIs to let your users stream signals, build trading dashboards, and trigger order executions with low latency.",
    features: [
      {
        title: "Developer Sandbox",
        desc: "Zero-configuration paper trading environment to test strategy integrations and rate limits.",
        icon: Terminal
      },
      {
        title: "WebSocket Streams",
        desc: "Real-time market feeds and trade alerts delivered with less than 50ms latency.",
        icon: Cpu
      },
      {
        title: "Flexible Webhooks",
        desc: "Receive instant notifications for trade execution updates, signal triggers, and risk exceptions.",
        icon: Layers
      }
    ]
  }
};

export default function UseCasesPage({ type }) {
  const { type: paramType } = useParams();
  const activeType = type || paramType || "brokers";
  const content = useCaseContent[activeType];

  if (!content) {
    return (
      <div className="text-center py-20">
        <h2 className="text-2xl font-bold text-foreground">Use Case Not Found</h2>
        <Link to="/" className="text-primary hover:underline mt-4 inline-block">Back to Home</Link>
      </div>
    );
  }

  const IconComponent = content.icon;

  return (
    <div className="w-full max-w-5xl mx-auto py-8 px-4 font-sans space-y-16">
      {/* Hero Header */}
      <section className="space-y-6 text-left max-w-3xl">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-primary/10 border border-primary/20 text-primary grid place-items-center">
            <IconComponent className="h-5 w-5" />
          </div>
          <div className="flex flex-wrap gap-2">
            {content.badges.map((badge, idx) => (
              <span 
                key={idx} 
                className="inline-block rounded-full bg-secondary text-secondary-foreground border border-border px-3 py-0.5 text-xs font-semibold"
              >
                {badge}
              </span>
            ))}
          </div>
        </div>
        
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-foreground">
          {content.tagline}
        </h1>
        
        <p className="text-lg text-muted-foreground leading-relaxed">
          {content.subtitle}
        </p>
      </section>

      {/* Description block */}
      <section className="grid grid-cols-1 md:grid-cols-[1.5fr_1fr] gap-12 border-t border-border/60 pt-10">
        <div className="space-y-6">
          <h2 className="text-xl font-bold text-foreground">How it works</h2>
          <p className="text-muted-foreground leading-relaxed font-sans">
            {content.description}
          </p>
          <div className="pt-4">
            <Link
              to="/contact"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-primary-foreground hover:brightness-105 active:scale-98 transition shadow-lg shadow-primary/10"
            >
              <span>Schedule Integration Consultation</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Dynamic Card showcasing the core solution */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm flex flex-col justify-between h-fit space-y-6">
          <div className="space-y-2">
            <span className="text-[10px] uppercase tracking-[0.2em] text-primary font-bold">Kerdostat Core</span>
            <h3 className="text-lg font-bold text-foreground">Explainable & Safe</h3>
            <p className="text-xs text-muted-foreground leading-relaxed font-sans">
              Deploy secure trading software using our HMT design. Run loops on Autopilot while retaining full ability to edit parameters or hit the emergency override.
            </p>
          </div>
          <div className="h-px bg-border w-full" />
          <div className="flex items-center justify-between text-xs text-muted-foreground font-mono">
            <span>Execution Status: Active</span>
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
        </div>
      </section>

      {/* Features Detail Grid */}
      <section className="space-y-8 border-t border-border/60 pt-10">
        <h2 className="text-xl font-bold text-foreground">Key Capabilities</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {content.features.map((feature, idx) => {
            const FeatureIcon = feature.icon;
            return (
              <div key={idx} className="rounded-xl border border-border bg-card/60 p-6 space-y-3 hover:border-primary/30 transition duration-200">
                <div className="h-8 w-8 rounded-lg bg-secondary/80 text-primary grid place-items-center">
                  <FeatureIcon className="h-4 w-4" />
                </div>
                <h4 className="font-bold text-foreground text-sm">{feature.title}</h4>
                <p className="text-xs text-muted-foreground font-sans leading-relaxed">
                  {feature.desc}
                </p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

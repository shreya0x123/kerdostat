import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, ChevronLeft, X, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

const tourSteps = [
  // Dashboard Steps
  {
    target: '[data-testid="mode-badge"]',
    title: "System Execution Mode",
    content: "Kerdostat operates in two modes: Copilot (requires human approval for all proposals) and Autopilot (models execute trades autonomously). Switch modes using the Autopilot toggle.",
    path: "/dashboard"
  },
  {
    target: '[data-testid="stats-summary-row"]',
    title: "Account Metrics",
    content: "View your real-time Alpaca portfolio value, cash, buying power, daily profit/loss, and safety indicators in this header stats row.",
    path: "/dashboard"
  },
  {
    target: '[data-testid="chart-section-card"]',
    title: "Interactive Charts & Custom Search",
    content: "View live candlestick charts and technical indicators. Switch quickly between core assets (AAPL, NVDA, TSLA) or search for custom symbols.",
    path: "/dashboard"
  },
  {
    target: '[data-testid="positions-section-card"]',
    title: "Active Positions Portfolio",
    content: "Keep track of your current asset holdings, including share quantity, average entry price, live market valuation, and real-time P&L.",
    path: "/dashboard"
  },
  {
    target: '[data-testid="xai-feed-card"]',
    title: "Explainable AI (XAI) Feed",
    content: "Read the real-time AI intelligence feed explaining why signals are generated, ensuring you have transparency on algorithmic decisions.",
    path: "/dashboard"
  },
  
  // Sidebar Proposals Icon step
  {
    target: '[aria-label="Proposals"]',
    title: "Proposals & Governance",
    content: "This icon links to the Proposals panel. Click here to inspect live trade suggestions, review their ML success probabilities, and manually approve or reject pending signals.",
    path: "/dashboard"
  },

  // Sidebar Manual Override Icon step
  {
    target: '[aria-label="Manual Override"]',
    title: "Manual Override Console",
    content: "This icon links to the Manual Override console. Click here in case of emergencies to enter custom Stop-Loss, Take-Profit bounds, and direct BUY/SELL trades, bypassing the automated loop.",
    path: "/dashboard"
  },

  // Sidebar Audit Log Icon step
  {
    target: '[aria-label="Audit Log"]',
    title: "Audit History Logs",
    content: "This icon links to the Audit Log. Click here to audit the complete history of model signals, execution fills, manual overrides, and guardrail breaches.",
    path: "/dashboard"
  }
];

export default function GuidedTour({ forceStart = false, onTourEnd, isAuthenticated = false }) {
  const navigate = useNavigate();
  const [active, setActive] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [coords, setCoords] = useState(null);
  const [showWelcome, setShowWelcome] = useState(false);

  // Check if tour should auto-start (first-time login)
  useEffect(() => {
    if (!isAuthenticated) {
      setShowWelcome(false);
      setActive(false);
      return;
    }

    const status = localStorage.getItem("kerdostat_tour_status");
    if (forceStart) {
      setActive(true);
      setCurrentStep(0);
      setShowWelcome(false);
    } else if (!status) {
      setShowWelcome(true);
    }
  }, [forceStart, isAuthenticated]);
  
  // Add temporary bottom padding to body during tour to allow scroll space
  useEffect(() => {
    if (active) {
      document.body.style.paddingBottom = "450px";
    } else {
      document.body.style.paddingBottom = "0px";
    }
    return () => {
      document.body.style.paddingBottom = "0px";
    };
  }, [active]);

  // Track coordinates of the current targeted element
  useEffect(() => {
    if (!active) {
      setCoords(null);
      return;
    }

    const updateCoords = () => {
      const step = tourSteps[currentStep];
      if (!step) return;

      const element = document.querySelector(step.target);
      if (element) {
        // Scroll the element to top of screen to guarantee visibility and space below
        if (typeof element.scrollIntoView === "function") {
          element.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        
        // Let scroll/render finish then update coordinates
        const timer = setTimeout(() => {
          const rect = element.getBoundingClientRect();
          setCoords({
            top: rect.top + window.scrollY,
            left: rect.left + window.scrollX,
            width: rect.width,
            height: rect.height,
          });
        }, 150);
        return () => clearTimeout(timer);
      } else {
        setCoords(null);
      }
    };

    const cleanup = updateCoords();
    window.addEventListener("resize", updateCoords);
    window.addEventListener("scroll", updateCoords);

    return () => {
      if (cleanup) cleanup();
      window.removeEventListener("resize", updateCoords);
      window.removeEventListener("scroll", updateCoords);
    };
  }, [active, currentStep, window.location.pathname]); // Hook dependency includes path to re-trigger coordinates query on route change

  const handleStartTour = () => {
    setShowWelcome(false);
    setActive(true);
    setCurrentStep(0);
    navigate("/dashboard");
  };

  const handleSkipWelcome = () => {
    setShowWelcome(false);
    localStorage.setItem("kerdostat_tour_status", "completed");
    if (onTourEnd) onTourEnd();
  };

  const handleNext = () => {
    const nextStep = currentStep + 1;
    if (nextStep < tourSteps.length) {
      const currentStepData = tourSteps[currentStep];
      const nextStepData = tourSteps[nextStep];

      // If the next step requires a different route, navigate first
      if (currentStepData.path !== nextStepData.path) {
        navigate(nextStepData.path);
        // Wait for router render transition before highlighting the new target
        setTimeout(() => {
          setCurrentStep(nextStep);
        }, 200);
      } else {
        setCurrentStep(nextStep);
      }
    } else {
      handleComplete();
    }
  };

  const handlePrev = () => {
    const prevStep = currentStep - 1;
    if (prevStep >= 0) {
      const currentStepData = tourSteps[currentStep];
      const prevStepData = tourSteps[prevStep];

      // If the previous step requires a different route, navigate first
      if (currentStepData.path !== prevStepData.path) {
        navigate(prevStepData.path);
        setTimeout(() => {
          setCurrentStep(prevStep);
        }, 200);
      } else {
        setCurrentStep(prevStep);
      }
    }
  };

  const handleComplete = () => {
    setActive(false);
    localStorage.setItem("kerdostat_tour_status", "completed");
    navigate("/dashboard");
    if (onTourEnd) onTourEnd();
  };

  if (showWelcome) {
    return (
      <div className="fixed inset-0 z-[99999] flex items-center justify-center bg-background/85 backdrop-blur-md animate-in fade-in duration-300">
        <div className="w-full max-w-md rounded-3xl border border-border bg-card p-6 shadow-2xl scale-100 transition-all duration-300 relative overflow-hidden">
          {/* Accent decoration */}
          <div className="absolute -top-12 -right-12 h-24 w-24 rounded-full bg-primary/10 blur-xl" />
          
          <div className="flex items-center gap-3 mb-4">
            <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center border border-primary/20">
              <Sparkles className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <h2 className="text-lg font-bold tracking-wide text-foreground">Welcome to Kerdostat!</h2>
              <p className="text-xs text-muted-foreground">Let's set up your trading workspace.</p>
            </div>
          </div>

          <p className="text-sm text-muted-foreground leading-relaxed mb-6">
            Would you like a quick 1-minute guided tour of your live terminal layout, algorithmic controls, and safety metrics?
          </p>

          <div className="flex items-center justify-end gap-3 border-t border-border/50 pt-4">
            <button
              onClick={handleSkipWelcome}
              className="px-4 py-2 text-xs font-bold rounded-xl border border-border bg-transparent text-muted-foreground hover:bg-secondary/40 hover:text-foreground transition duration-200"
            >
              Maybe Later
            </button>
            <Button
              onClick={handleStartTour}
              className="px-4 py-2 text-xs font-bold rounded-xl bg-primary text-primary-foreground hover:scale-102 hover:brightness-105 active:scale-98 shadow-md"
            >
              Start Tour
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!active || !coords) return null;

  const currentStepData = tourSteps[currentStep];
  const isBelow = coords.top - window.scrollY < window.innerHeight / 2;

  // Calculate dynamic floating position for tooltip
  const tooltipStyle = {
    position: "absolute",
    left: Math.max(16, Math.min(window.innerWidth - 396, coords.left + (coords.width / 2) - 190)),
    width: "360px",
    zIndex: 99999,
    transition: "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
  };

  if (isBelow) {
    tooltipStyle.top = coords.top + coords.height + 16;
  } else {
    tooltipStyle.top = coords.top - 200 - 16;
  }

  return (
    <>
      {/* Dimmed backdrop spotlight */}
      <div
        style={{
          position: "absolute",
          top: coords.top - 6,
          left: coords.left - 6,
          width: coords.width + 12,
          height: coords.height + 12,
          borderRadius: "20px",
          boxShadow: "0 0 0 9999px rgba(8, 8, 10, 0.78)",
          border: "2px solid hsl(var(--primary))",
          pointerEvents: "none",
          zIndex: 99998,
          transition: "all 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        }}
        data-testid="tour-spotlight"
      />

      {/* Floating Tutorial card */}
      <div
        style={tooltipStyle}
        className="bg-card/95 border border-border rounded-2xl p-5 shadow-2xl backdrop-blur animate-in fade-in slide-in-from-bottom-5 duration-300"
        data-testid="tour-tooltip"
      >
        <div className="flex items-center justify-between border-b border-border/50 pb-3 mb-3">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5 font-sans">
            <Sparkles className="h-4 w-4 text-primary" />
            {currentStepData.title}
          </h3>
          <button
            onClick={handleComplete}
            className="text-muted-foreground hover:text-foreground transition rounded-full p-1 hover:bg-secondary/40"
            aria-label="Close Tour"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <p className="text-xs text-muted-foreground leading-relaxed mb-5 font-sans">
          {currentStepData.content}
        </p>

        <div className="flex items-center justify-between">
          {/* Progress dots */}
          <div className="flex items-center gap-1.5">
            {tourSteps.map((_, idx) => (
              <span
                key={idx}
                className={`h-1.5 w-1.5 rounded-full transition-all duration-300 ${
                  currentStep === idx ? "bg-primary w-3" : "bg-muted-foreground/30"
                }`}
              />
            ))}
          </div>

          {/* Navigation Controls */}
          <div className="flex items-center gap-2">
            {currentStep > 0 && (
              <button
                onClick={handlePrev}
                className="flex items-center justify-center h-8 px-2 text-xs font-bold text-muted-foreground hover:text-foreground hover:bg-secondary/40 rounded-lg transition duration-200"
              >
                <ChevronLeft className="h-4 w-4" />
                Back
              </button>
            )}
            <Button
              onClick={handleNext}
              size="sm"
              className="flex items-center justify-center h-8 px-3 text-xs font-bold rounded-lg bg-primary text-primary-foreground hover:brightness-105 transition duration-200"
            >
              {currentStep === tourSteps.length - 1 ? "Finish" : "Next"}
              {currentStep < tourSteps.length - 1 && <ChevronRight className="h-4 w-4 ml-0.5" />}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}

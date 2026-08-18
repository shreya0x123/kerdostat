import { useState, useEffect } from "react";
import { Link, useLocation, Outlet } from "react-router-dom";
import { 
  Home, 
  LayoutDashboard, 
  Layers, 
  Terminal, 
  Sun, 
  Moon, 
  LogOut, 
  LogIn, 
  Wifi, 
  WifiOff,
  MessageSquare,
  FileText,
  BookOpen
} from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useAuth } from "@/hooks/useAuth";
import Footer from "@/components/Footer";
import GuidedTour from "@/components/GuidedTour";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { label: "Proposals", path: "/proposals", icon: Layers },
  { label: "Manual Override", path: "/override", icon: Terminal },
  { label: "Audit Log", path: "/audit-log", icon: FileText },
  { label: "API Docs", path: "/docs", icon: BookOpen },
];

export default function DashboardLayout({ children }) {
  const location = useLocation();
  const { theme, setTheme } = useTheme();
  const { isAuthenticated, isBrokerConnected, systemMode, toggleSystemMode, signOut } = useAuth();
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [runTour, setRunTour] = useState(false);

  useEffect(() => {
    const handleStart = () => {
      setRunTour(true);
    };
    window.addEventListener("start-kerdostat-tour", handleStart);
    return () => {
      window.removeEventListener("start-kerdostat-tour", handleStart);
    };
  }, []);

  const getPageTitle = (pathname) => {
    if (pathname.startsWith("/use-cases/")) {
      const segment = pathname.split("/").pop();
      return `Use Cases: ${segment.charAt(0).toUpperCase() + segment.slice(1)}`;
    }
    switch (pathname) {
      case "/dashboard":
        return "Trading Dashboard";
      case "/proposals":
        return "Proposals & Governance";
      case "/override":
        return "Manual Override Console";
      case "/audit-log":
        return "Audit History";
      case "/contact":
        return "Contact Desk";
      case "/docs":
        return "Developer Docs";
      default:
        return "Kerdostat Platform";
    }
  };

  const currentTitle = getPageTitle(location.pathname);

  return (
    <div className="min-h-screen grid grid-cols-[60px_1fr] md:grid-cols-[80px_1fr] bg-background text-foreground transition-colors duration-300">
      <GuidedTour forceStart={runTour} onTourEnd={() => setRunTour(false)} isAuthenticated={isAuthenticated} />
      {/* Sidebar navigation */}
      <aside className="flex flex-col items-center border-r border-border bg-card/40 backdrop-blur-md px-1 md:px-2 py-4 md:py-6 z-10">
        {/* Brand logo */}
        <Link 
          to={isAuthenticated ? "/dashboard" : "/"} 
          className="mb-6 md:mb-10 flex h-10 w-10 md:h-12 md:w-12 items-center justify-center rounded-xl md:rounded-2xl border-2 border-primary text-primary text-lg md:text-xl font-bold tracking-[0.2em] hover:scale-105 transition-transform duration-200"
        >
          K
        </Link>

        {/* Navigation links */}
        <nav className="flex flex-1 flex-col items-center gap-3 md:gap-4 w-full">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.label}
                to={item.path}
                className={`group flex h-10 w-10 md:h-12 md:w-12 items-center justify-center rounded-xl md:rounded-2xl border transition-all duration-200 ${
                  isActive
                    ? "border-primary bg-primary/10 text-primary shadow-[0_0_15px_rgba(34,211,238,0.25)]"
                    : "border-border bg-card/60 text-muted-foreground hover:border-primary/50 hover:text-primary"
                }`}
                aria-label={item.label}
                title={item.label}
              >
                <Icon className="h-4 w-4 md:h-5 md:w-5 transition group-hover:scale-110" />
              </Link>
            );
          })}
        </nav>

        {/* Footer label */}
        <div className="mt-auto flex flex-col items-center pt-4 md:pt-6">
          <div className="h-px w-6 md:h-px md:w-8 bg-border mb-2 md:mb-3" />
          <span className="text-[8px] md:text-[9px] uppercase tracking-[0.2em] text-muted-foreground font-semibold">
            KRDST
          </span>
        </div>
      </aside>

      {/* Main container with TopBar */}
      <div className="flex flex-col min-h-screen overflow-hidden">
        {/* TopBar component */}
        <header className="flex h-16 items-center justify-between border-b border-border bg-card/30 backdrop-blur-md px-4 md:px-8 py-4 z-10 transition-colors duration-300">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-bold tracking-wide text-foreground">
              {currentTitle}
            </h1>
          </div>

          <div className="flex items-center gap-4">
            {/* Broker Status Badge */}
            <div 
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${
                isBrokerConnected 
                  ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" 
                  : "bg-amber-500/10 text-amber-500 border-amber-500/20"
              }`}
            >
              {isBrokerConnected ? (
                <>
                  <Wifi className="h-3.5 w-3.5 animate-pulse" />
                  <span>Broker Active</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-3.5 w-3.5" />
                  <span>No Broker</span>
                </>
              )}
            </div>

            {/* COPILOT vs AUTOPILOT Badge */}
            {systemMode === "copilot" ? (
              <div 
                className="flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold border bg-cyan-500/10 text-cyan-400 border-cyan-500/20 tracking-wider uppercase"
                data-testid="mode-badge"
              >
                COPILOT
              </div>
            ) : (
              <div 
                className="flex items-center gap-1 rounded-full px-3 py-1 text-xs font-bold border bg-amber-500/10 text-amber-400 border-amber-500/20 tracking-wider uppercase"
                data-testid="mode-badge"
              >
                AUTOPILOT
              </div>
            )}

            {/* Autopilot toggle switch */}
            <div className="flex items-center gap-2 border-l border-border pl-4">
              <Label htmlFor="autopilot-mode" className="text-xs font-bold text-muted-foreground uppercase cursor-pointer hidden sm:inline">
                Autopilot
              </Label>
              <Switch
                id="autopilot-mode"
                checked={systemMode === "autopilot"}
                onCheckedChange={() => setShowConfirmModal(true)}
                data-testid="mode-switch"
              />
            </div>

            {/* Contact Desk button */}
            <Link
              to="/contact"
              className={`flex h-9 items-center gap-1.5 rounded-xl border border-border px-3 text-xs font-bold transition hover:border-primary/50 hover:text-primary ${
                location.pathname === "/contact"
                  ? "border-primary bg-primary/10 text-primary"
                  : "bg-card/50 text-foreground"
              }`}
              title="Contact Support & Integrations Desk"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Contact Desk</span>
            </Link>

            {/* Dark/Light mode toggle */}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card/50 text-foreground transition hover:border-primary/50 hover:text-primary"
              aria-label="Toggle theme"
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4 text-amber-400" />
              ) : (
                <Moon className="h-4 w-4 text-indigo-500" />
              )}
            </button>

            {/* Auth Indicator */}
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/20 border border-primary/30 text-primary text-xs font-bold uppercase">
                  TR
                </div>
                <button
                  onClick={signOut}
                  type="button"
                  className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card/50 text-muted-foreground hover:border-destructive/50 hover:text-destructive transition"
                  title="Sign Out"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <Link
                to="/auth"
                className="flex items-center gap-1.5 rounded-xl bg-primary px-4 py-1.5 text-xs font-bold text-primary-foreground hover:scale-102 hover:brightness-105 active:scale-98 transition"
              >
                <LogIn className="h-3.5 w-3.5" />
                <span>Access Terminal</span>
              </Link>
            )}
          </div>
        </header>

        {/* Page content main wrapper */}
        <main className="flex-1 overflow-y-auto bg-background p-4 md:p-8 transition-colors duration-300">
          <div className="flex flex-col min-h-full justify-between">
            <div className="flex-1 pb-8">
              {children || <Outlet />}
            </div>
            <Footer />
          </div>
        </main>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm transition-opacity duration-300">
          <div className="w-full max-w-md scale-100 rounded-2xl border border-border bg-card p-6 shadow-2xl transition-all duration-300">
            <h2 className="text-lg font-bold tracking-wide text-foreground mb-3 flex items-center gap-2">
              <span>Confirm Mode Switch</span>
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed mb-6">
              {systemMode === "copilot" ? (
                <span>
                  You are switching to <strong className="text-amber-400">Autopilot Mode</strong>. In this mode, trade proposals will be executed automatically without requiring manual governance approval. Are you sure you want to proceed?
                </span>
              ) : (
                <span>
                  You are switching to <strong className="text-cyan-400">Copilot Mode</strong>. In this mode, all trade proposals will require manual approval, rejection, or parameter overrides. Are you sure you want to proceed?
                </span>
              )}
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                className="px-4 py-2 text-xs font-bold rounded-xl border border-border bg-transparent text-muted-foreground hover:bg-secondary/40 hover:text-foreground transition duration-200"
                data-testid="cancel-mode-btn"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={async () => {
                  await toggleSystemMode();
                  setShowConfirmModal(false);
                }}
                className={`px-4 py-2 text-xs font-bold rounded-xl text-primary-foreground shadow-sm transition duration-200 ${
                  systemMode === "copilot"
                    ? "bg-amber-500 hover:bg-amber-600 shadow-amber-500/20"
                    : "bg-cyan-500 hover:bg-cyan-600 shadow-cyan-500/20"
                }`}
                data-testid="confirm-mode-btn"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

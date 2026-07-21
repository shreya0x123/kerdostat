import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-card/20 py-10 text-left transition-colors duration-300 w-full mt-auto" data-testid="official-footer">
      <div className="max-w-7xl mx-auto px-6 grid sm:grid-cols-2 md:grid-cols-4 gap-8">
        {/* Brand Column */}
        <div className="space-y-3">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-7 w-7 border border-primary/45 rounded-lg bg-primary/10 text-primary grid place-items-center text-xs font-bold tracking-[0.15em]">
              K
            </div>
            <span className="font-extrabold font-mono text-foreground tracking-widest text-xs">
              KERDOSTAT
            </span>
          </Link>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            Institutional-grade automated execution engine designed for digital wealth platforms. Zero platform custody of broker credentials.
          </p>
        </div>

        {/* Platform Links */}
        <div>
          <h5 className="font-bold text-[10px] uppercase tracking-wider text-foreground mb-3 font-sans">
            Trading Platform
          </h5>
          <ul className="space-y-2 text-xs text-muted-foreground">
            <li>
              <Link to="/dashboard" className="hover:text-primary transition-colors duration-200">
                Dashboard Terminal
              </Link>
            </li>
            <li>
              <Link to="/proposals" className="hover:text-primary transition-colors duration-200">
                Proposals Feed
              </Link>
            </li>
            <li>
              <Link to="/hijack" className="hover:text-primary transition-colors duration-200">
                Hijack Console
              </Link>
            </li>
            <li>
              <Link to="/audit-log" className="hover:text-primary transition-colors duration-200">
                Execution Audits
              </Link>
            </li>
          </ul>
        </div>

        {/* Resources & Docs */}
        <div>
          <h5 className="font-bold text-[10px] uppercase tracking-wider text-foreground mb-3 font-sans">
            Developers & Help
          </h5>
          <ul className="space-y-2 text-xs text-muted-foreground">
            <li>
              <Link to="/docs" className="hover:text-primary transition-colors duration-200">
                Developer API Docs
              </Link>
            </li>
            <li>
              <Link to="/contact" className="hover:text-primary transition-colors duration-200">
                Contact Desk
              </Link>
            </li>
            <li>
              <a href="#" className="hover:text-primary transition-colors duration-200">
                Platform Status
              </a>
            </li>
          </ul>
        </div>

        {/* Compliance Column */}
        <div>
          <h5 className="font-bold text-[10px] uppercase tracking-wider text-foreground mb-3 font-sans">
            Security & Standards
          </h5>
          <ul className="space-y-2 text-xs text-muted-foreground font-mono text-[10px]">
            <li className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-emerald-500" />
              <span>Alpaca Sandbox Integration</span>
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-emerald-500" />
              <span>Zero-Key Custody Architecture</span>
            </li>
            <li className="flex items-center gap-1.5">
              <span className="h-1 w-1 rounded-full bg-emerald-500" />
              <span>Cryptographically Secured SSL</span>
            </li>
          </ul>
        </div>
      </div>

      {/* Bottom Sub-footer */}
      <div className="max-w-7xl mx-auto px-6 pt-6 mt-6 border-t border-border/40 flex flex-col sm:flex-row justify-between items-center gap-4 text-[10px] text-muted-foreground">
        <span>
          &copy; {new Date().getFullYear()} Kerdostat Technologies Inc. All rights reserved.
        </span>
        <div className="flex gap-4">
          <a href="#" className="hover:text-foreground transition-colors duration-200">
            Privacy Policy
          </a>
          <a href="#" className="hover:text-foreground transition-colors duration-200">
            Terms of Service
          </a>
          <a href="#" className="hover:text-foreground transition-colors duration-200">
            Security Disclosures
          </a>
        </div>
      </div>
    </footer>
  );
}

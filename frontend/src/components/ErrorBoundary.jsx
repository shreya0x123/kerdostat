import React from "react";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "./ui/button";

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("[ErrorBoundary] Caught error:", error, errorInfo);
    if (error && (error.name === "ChunkLoadError" || error.message?.includes("dynamically imported module") || error.message?.includes("Loading chunk"))) {
      const isReloaded = sessionStorage.getItem("chunk_reload_attempted");
      if (!isReloaded) {
        sessionStorage.setItem("chunk_reload_attempted", "true");
        window.location.reload();
      }
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full max-w-lg mx-auto my-12 p-8 rounded-2xl border border-destructive/20 bg-destructive/5 text-center space-y-6">
          <div className="flex justify-center">
            <div className="h-12 w-12 rounded-full bg-destructive/15 text-destructive grid place-items-center">
              <AlertCircle className="h-6 w-6" />
            </div>
          </div>
          <div className="space-y-2">
            <h2 className="text-lg font-bold text-foreground">System Exception Caught</h2>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto font-sans">
              An unexpected UI rendering crash occurred in this component viewport. Execution telemetry has been logged.
            </p>
          </div>
          {this.state.error && (
            <pre className="text-[10px] font-mono bg-background/50 text-destructive/80 p-3 rounded-xl border border-border text-left overflow-x-auto max-h-40">
              {this.state.error.toString()}
            </pre>
          )}
          <Button
            onClick={this.handleReset}
            className="inline-flex items-center gap-1.5 rounded-xl bg-destructive text-destructive-foreground px-4 py-2 text-xs font-bold hover:brightness-105 active:scale-98 transition shadow-md border-none"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Viewport</span>
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

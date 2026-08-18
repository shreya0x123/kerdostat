import { useEffect, useState } from "react";
import { fetchAuditLogs } from "@/services/apiService";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FileDown, RefreshCw, Filter } from "lucide-react";

export default function AuditLogPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Filter states
  const [symbolFilter, setSymbolFilter] = useState("all");
  const [actionFilter, setActionFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("");

  const loadLogs = async () => {
    try {
      setLoading(true);
      const data = await fetchAuditLogs();
      setLogs(data);
      setError(null);
    } catch (err) {
      setError("Failed to load audit logs.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  // Filter logic
  const filteredLogs = logs.filter((log) => {
    // 1. Symbol Filter
    if (symbolFilter !== "all" && log.symbol.toUpperCase() !== symbolFilter.toUpperCase()) {
      return false;
    }
    // 2. Action Type Filter
    if (actionFilter !== "all" && log.action_type.toUpperCase() !== actionFilter.toUpperCase()) {
      return false;
    }
    // 3. Date Filter
    if (dateFilter) {
      const logDate = log.timestamp.split("T")[0];
      if (logDate !== dateFilter) {
        return false;
      }
    }
    return true;
  });

  // Client-side CSV export
  const handleCSVExport = () => {
    const headers = ["ID", "Timestamp", "Symbol", "Action Type", "Quantity", "Price", "Status", "User"];
    const rows = filteredLogs.map((log) => [
      log.id,
      log.timestamp,
      log.symbol,
      log.action_type,
      log.qty,
      log.price,
      log.status,
      log.user
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `audit_log_export_${new Date().toISOString().split("T")[0]}.csv`);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getActionBadgeColor = (actionType) => {
    switch (actionType.toUpperCase()) {
      case "APPROVE":
        return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      case "REJECT":
        return "bg-rose-500/10 text-rose-500 border-rose-500/20";
      case "HIJACK_EXECUTE":
        return "bg-amber-500/10 text-amber-500 border-amber-500/20";
      default:
        return "bg-secondary text-secondary-foreground border-border";
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto py-6 px-4 space-y-6 font-sans" data-testid="audit-log-page">
      {/* Header section */}
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/60 pb-6">
        <div className="space-y-2 text-left">
          <h1 className="text-2xl font-extrabold tracking-tight text-foreground">
            Audit History & Governance Logs
          </h1>
          <p className="text-sm text-muted-foreground max-w-2xl leading-relaxed">
            Trace execution records, overrides, and multi-sig permissions. Filter history or download direct execution archives.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start md:self-center">
          <button
            onClick={loadLogs}
            type="button"
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground hover:text-foreground transition active:scale-95"
            title="Refresh logs"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          
          <Button
            onClick={handleCSVExport}
            disabled={filteredLogs.length === 0}
            className="flex h-9 items-center gap-2 rounded-xl bg-primary px-4 text-xs font-bold text-primary-foreground hover:brightness-105 transition disabled:opacity-50"
            data-testid="export-csv-btn"
          >
            <FileDown className="h-4 w-4" />
            <span>Export CSV</span>
          </Button>
        </div>
      </section>

      {/* Filters section */}
      <Card className="rounded-2xl border border-border bg-card p-5 shadow-sm">
        <CardHeader className="p-0 pb-4 border-b border-border/50">
          <CardTitle className="text-sm font-bold text-foreground flex items-center gap-2">
            <Filter className="h-4 w-4 text-primary" />
            Filters Panel
          </CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-5 p-0">
          {/* Symbol Selector */}
          <div className="space-y-1.5">
            <Label htmlFor="filter-symbol" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Symbol
            </Label>
            <select
              id="filter-symbol"
              value={symbolFilter}
              onChange={(e) => setSymbolFilter(e.target.value)}
              className="w-full rounded-xl border border-border bg-secondary/30 text-foreground px-3 py-2 text-xs font-medium focus-visible:ring-primary focus-visible:border-primary outline-none"
              data-testid="filter-symbol"
            >
              <option value="all">All Symbols</option>
              <option value="QUANT">QUANT</option>
              <option value="NVDA">NVDA</option>
              <option value="TSLA">TSLA</option>
            </select>
          </div>

          {/* Action Type Selector */}
          <div className="space-y-1.5">
            <Label htmlFor="filter-action" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Action Type
            </Label>
            <select
              id="filter-action"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full rounded-xl border border-border bg-secondary/30 text-foreground px-3 py-2 text-xs font-medium focus-visible:ring-primary focus-visible:border-primary outline-none"
              data-testid="filter-action"
            >
              <option value="all">All Actions</option>
              <option value="APPROVE">APPROVE</option>
              <option value="REJECT">REJECT</option>
              <option value="HIJACK_EXECUTE">HIJACK OVERRIDE</option>
            </select>
          </div>

          {/* Date Picker */}
          <div className="space-y-1.5">
            <Label htmlFor="filter-date" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Date Select
            </Label>
            <Input
              id="filter-date"
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              className="w-full border-border bg-secondary/30 text-foreground rounded-xl text-xs font-medium focus-visible:ring-primary focus-visible:border-primary outline-none"
              data-testid="filter-date"
            />
          </div>
        </CardContent>
      </Card>

      {/* Main Table section */}
      <Card className="rounded-2xl border border-border bg-card p-4 sm:p-6 shadow-sm overflow-hidden">
        {loading ? (
          <div data-testid="logs-loading" className="w-full overflow-x-auto">
            <Table className="w-full min-w-[700px] text-sm text-foreground">
              <TableHeader>
                <TableRow className="border-b border-border hover:bg-transparent">
                  <TableHead className="font-semibold text-muted-foreground text-left py-3 w-[80px]">ID</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Timestamp</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Symbol</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Action Type</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Qty</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Price</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">User</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-right py-3">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {[1, 2, 3, 4].map((i) => (
                  <TableRow key={i} className="animate-pulse">
                    {[1, 2, 3, 4, 5, 6, 7, 8].map((j) => (
                      <TableCell key={j} className="py-4">
                        <div className="h-4 w-5/6 rounded bg-secondary/60" />
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-6 text-center text-sm font-semibold text-destructive">
            {error}
          </div>
        ) : (
          <div className="w-full overflow-x-auto">
            <Table className="w-full min-w-[700px] text-sm text-foreground">
              <TableHeader>
                <TableRow className="border-b border-border hover:bg-transparent">
                  <TableHead className="font-semibold text-muted-foreground text-left py-3 w-[80px]">ID</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Timestamp</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Symbol</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Action Type</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Qty</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">Price</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-left py-3">User</TableHead>
                  <TableHead className="font-semibold text-muted-foreground text-right py-3">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredLogs.length === 0 ? (
                  <TableRow data-testid="no-logs-row">
                    <TableCell colSpan={8} className="py-12 text-center">
                      <div className="flex flex-col items-center justify-center space-y-3">
                        <FileDown className="h-8 w-8 text-muted-foreground/30" />
                        <div>
                          <p className="text-xs font-bold text-foreground">No records found</p>
                          <p className="text-[11px] text-muted-foreground mt-0.5 font-sans font-normal">Try adjusting the filter criteria or refreshing the log.</p>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredLogs.map((log) => (
                    <TableRow key={log.id} className="border-b border-border/50 hover:bg-secondary/15" data-testid="log-row">
                      <TableCell className="font-bold text-foreground py-4">{log.id}</TableCell>
                      <TableCell className="py-4 text-xs font-mono">
                        {new Date(log.timestamp).toLocaleString("en-US", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                          hour12: false
                        })}
                      </TableCell>
                      <TableCell className="font-bold py-4">{log.symbol}</TableCell>
                      <TableCell className="py-4">
                        <Badge className={`rounded-full px-2 py-0.5 text-[10px] font-bold border ${getActionBadgeColor(log.action_type)}`}>
                          {log.action_type === "HIJACK_EXECUTE" ? "HIJACK" : log.action_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="py-4 font-mono">{log.qty}</TableCell>
                      <TableCell className="py-4 font-mono">${log.price.toFixed(2)}</TableCell>
                      <TableCell className="py-4 text-xs text-muted-foreground">{log.user}</TableCell>
                      <TableCell className="text-right py-4">
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-500">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                          {log.status}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}

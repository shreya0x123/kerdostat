#!/usr/bin/env python3
"""
Kerdostat — Evaluator Terminal Demo
=====================================
Runs the Signal Engine + XDI Engine and displays results
in a clean, color-coded terminal UI using Rich.

Usage:
    ./venv/bin/python scripts/demo.py
    ./venv/bin/python scripts/demo.py --symbol AAPL --interval 1day
    ./venv/bin/python scripts/demo.py --source csv --filepath data/sample_ohlcv.csv
"""

from __future__ import annotations
import os, sys, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Rich imports ──────────────────────────────────────────────────────────────
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.rule import Rule
from rich.padding import Padding
from rich.align import Align
from rich.progress import Progress, SpinnerColumn, TextColumn
import time

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def signal_color(signal: str) -> str:
    return {"BUY": "bold green", "SELL": "bold red", "HOLD": "bold yellow"}.get(signal, "white")

def signal_icon(signal: str) -> str:
    return {"BUY": "▲", "SELL": "▼", "HOLD": "●"}.get(signal, "?")

def risk_color(risk: str) -> str:
    return {"LOW": "green", "MODERATE": "yellow", "HIGH": "red", "EXTREME": "bold red"}.get(risk, "white")

def impact_icon(impact: str) -> str:
    return {"bullish": "[green]▲[/green]", "bearish": "[red]▼[/red]", "neutral": "[yellow]●[/yellow]"}.get(impact, "?")

def conf_bar(conf: float, width: int = 20) -> str:
    filled = int(conf * width)
    bar = "█" * filled + "░" * (width - filled)
    pct = f"{conf:.0%}"
    if conf >= 0.75:
        color = "green"
    elif conf >= 0.50:
        color = "yellow"
    else:
        color = "red"
    return f"[{color}]{bar}[/{color}] {pct}"

def agreement_color(ag: str) -> str:
    return {
        "STRONG_AGREEMENT":  "bold green",
        "PARTIAL_AGREEMENT": "yellow",
        "NEUTRAL":           "cyan",
        "CONFLICT":          "bold red",
    }.get(ag, "white")


# ─────────────────────────────────────────────────────────────────────────────
# Render functions
# ─────────────────────────────────────────────────────────────────────────────

def render_header():
    title = Text("  K E R D O S T A T", style="bold white", justify="center")
    sub   = Text("  Explainable AI Trading Signal System", style="dim cyan", justify="center")
    grid  = Table.grid(expand=True)
    grid.add_row(title)
    grid.add_row(sub)
    console.print(Panel(grid, style="bold blue", padding=(1, 4)))
    console.print()


def render_signal_card(result: dict):
    signal     = result["signal"]
    conf       = result["confidence"]
    rule_conf  = result.get("rule_confidence", conf)
    ml_conf    = result.get("ml_confidence")
    close      = result["indicators"]["close"]
    rsi        = result["indicators"]["rsi"]
    data_as_of = result.get("data_as_of", "—")
    horizon    = result.get("prediction_horizon", "—")
    sc         = signal_color(signal)
    icon       = signal_icon(signal)

    # Signal + confidence table
    t = Table.grid(padding=(0, 2))
    t.add_column(style="dim", width=22)
    t.add_column()

    t.add_row("Signal",
              Text(f"{icon}  {signal}", style=sc))
    t.add_row("Close Price",
              Text(f"${close:,.2f}"))
    t.add_row("RSI",
              Text(f"{rsi:.1f}  {'(oversold)' if rsi < 30 else '(overbought)' if rsi > 70 else '(neutral)'}",
                   style="green" if rsi < 30 else "red" if rsi > 70 else "yellow"))
    t.add_row("Combined Conf", conf_bar(conf))
    t.add_row("Rule Conf",    conf_bar(rule_conf))
    if ml_conf is not None:
        t.add_row("ML Conf",  conf_bar(ml_conf))
    t.add_row("Data As Of",  Text(str(data_as_of) if data_as_of else "—", style="dim"))
    # horizon can be a string, dict, or None depending on the source
    if isinstance(horizon, dict):
        horizon_str = horizon.get("display") or horizon.get("timeframe") or "—"
    else:
        horizon_str = str(horizon) if horizon else "—"
    t.add_row("Horizon",     Text(horizon_str, style="italic cyan"))

    console.print(Panel(
        t,
        title=f"[bold]MODULE 1 — Signal Engine[/bold]",
        title_align="left",
        border_style=sc.replace("bold ", ""),
        padding=(1, 2),
    ))


def render_indicators(indicators: dict):
    t = Table(show_header=True, header_style="bold cyan",
              box=box.SIMPLE_HEAVY, padding=(0, 1))
    t.add_column("Indicator", style="bold", width=20)
    t.add_column("Value", justify="right", width=14)
    t.add_column("Reading", width=30)

    rsi  = indicators["rsi"]
    ema  = indicators["ema_20"]
    macd = indicators["macd_histogram"]
    close = indicators["close"]
    bbu  = indicators["bb_upper"]
    bbl  = indicators["bb_lower"]

    rsi_read = ("[green]Oversold — potential reversal[/green]" if rsi < 30
                else "[red]Overbought — potential correction[/red]" if rsi > 70
                else "[yellow]Neutral zone[/yellow]")

    t.add_row("RSI (14)",        f"{rsi:.2f}",       rsi_read)
    t.add_row("EMA (20)",        f"{ema:.2f}",
              "[green]Price above trend[/green]" if close > ema else "[red]Price below trend[/red]")
    t.add_row("MACD Histogram",  f"{macd:+.4f}",
              "[green]Bullish momentum[/green]" if macd > 0 else "[red]Bearish momentum[/red]")
    t.add_row("BB Upper",        f"{indicators['bb_upper']:.2f}", "")
    t.add_row("BB Middle",       f"{indicators['bb_middle']:.2f}", "")
    t.add_row("BB Lower",        f"{indicators['bb_lower']:.2f}",
              "[green]Price below lower band[/green]" if close < bbl
              else "[red]Price above upper band[/red]" if close > bbu else "")

    console.print(Panel(
        t,
        title="[bold]Technical Indicators[/bold]",
        title_align="left",
        border_style="blue",
        padding=(1, 2),
    ))


def render_rules(rules_triggered: list):
    if not rules_triggered:
        console.print(Panel(
            "[dim]No primary signal rules fired — HOLD[/dim]",
            title="[bold]Rules Triggered[/bold]",
            title_align="left",
            border_style="yellow",
            padding=(0, 2),
        ))
        return

    t = Table.grid(padding=(0, 1))
    for rule in rules_triggered:
        t.add_row("[green]✔[/green]", rule)

    console.print(Panel(
        t,
        title=f"[bold]Rules Triggered ({len(rules_triggered)})[/bold]",
        title_align="left",
        border_style="green",
        padding=(1, 2),
    ))


def render_xdi(explanation: dict, hybrid: dict | None = None):
    # ── Summary ──────────────────────────────────────────────────────────────
    console.print(Panel(
        Padding(Text(explanation["summary"], style="white"), (1, 2)),
        title="[bold]MODULE 2 — XDI Explanation  ·  Summary[/bold]",
        title_align="left",
        border_style="magenta",
        padding=(0, 0),
    ))

    # ── Key Factors ───────────────────────────────────────────────────────────
    t = Table(show_header=True, header_style="bold cyan",
              box=box.SIMPLE_HEAVY, padding=(0, 1))
    t.add_column("Indicator", style="bold", width=16)
    t.add_column("Value",     justify="right", width=10)
    t.add_column("Impact",    width=10)
    t.add_column("Analysis")

    for f in explanation.get("key_factors", []):
        t.add_row(
            f["indicator"],
            str(f["value"]),
            impact_icon(f["impact"]),
            f["interpretation"],
        )

    console.print(Panel(
        t,
        title="[bold]Key Factors[/bold]",
        title_align="left",
        border_style="magenta",
        padding=(1, 2),
    ))

    # ── Risk + Horizon (side by side) ─────────────────────────────────────────
    risk   = explanation["risk_level"]
    rc     = risk_color(risk)
    h      = explanation["prediction_horizon"]

    risk_panel = Panel(
        Padding(
            Text(explanation["risk_reasoning"], style="dim"),
            (1, 2)
        ),
        title=f"[{rc}]Risk Level: {risk}[/{rc}]",
        title_align="left",
        border_style=rc.replace("bold ", ""),
    )
    horizon_panel = Panel(
        Padding(
            Text(h.get("reasoning", h.get("display", "")), style="dim"),
            (1, 2)
        ),
        title=f"[cyan]Horizon: {h.get('display', '')} ({h.get('timeframe', '')})[/cyan]",
        title_align="left",
        border_style="cyan",
    )
    console.print(Columns([risk_panel, horizon_panel], equal=True))

    # ── Confidence Reasoning ──────────────────────────────────────────────────
    console.print(Panel(
        Padding(Text(explanation["confidence_reasoning"], style="dim"), (0, 2)),
        title="[bold]Confidence Reasoning[/bold]",
        title_align="left",
        border_style="blue",
        padding=(1, 0),
    ))

    # ── Actionable Insight ────────────────────────────────────────────────────
    console.print(Panel(
        Padding(Text(explanation["actionable_insight"], style="bold white"), (1, 2)),
        title="[bold green]Actionable Insight[/bold green]",
        title_align="left",
        border_style="green",
        padding=(0, 0),
    ))

    # ── Hybrid Decision ───────────────────────────────────────────────────────
    if hybrid:
        ag    = hybrid.get("agreement", "NEUTRAL")
        ag_c  = agreement_color(ag)
        fs    = hybrid.get("final_signal", "—")
        fs_c  = signal_color(fs)
        reasoning = hybrid.get("reasoning", "")

        hg = Table.grid(padding=(0, 2))
        hg.add_column(style="dim", width=20)
        hg.add_column()
        hg.add_row("Final Signal",  Text(f"{signal_icon(fs)}  {fs}", style=fs_c))
        hg.add_row("ML Agreement",  Text(ag.replace("_", " "), style=ag_c))
        hg.add_row("Reasoning",     Text(reasoning, style="dim"))

        console.print(Panel(
            hg,
            title="[bold]Hybrid Decision (TA + ML)[/bold]",
            title_align="left",
            border_style=ag_c.replace("bold ", ""),
            padding=(1, 2),
        ))


def render_detailed_reasoning(explanation: dict):
    console.print(Panel(
        Padding(Text(explanation["detailed_reasoning"], style="dim white"), (1, 2)),
        title="[bold]Detailed Reasoning (Full Analysis)[/bold]",
        title_align="left",
        border_style="blue",
        padding=(0, 0),
    ))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Kerdostat — Terminal Demo")
    p.add_argument("--source",   default="csv",    choices=["csv", "alpaca", "yahoo"])
    p.add_argument("--filepath", default=os.path.join(ROOT, "data", "sample_ohlcv.csv"))
    p.add_argument("--symbol",   default="AAPL")
    p.add_argument("--interval", default="1day",
                   choices=["1min","5min","15min","1hour","1day"])
    p.add_argument("--start",    default="2020-01-01")
    p.add_argument("--end",      default="2025-01-01")
    p.add_argument("--verbose",  action="store_true",
                   help="Show detailed reasoning section")
    return p.parse_args()


def run_with_spinner(args) -> dict:
    from ml.pipeline import run_analysis

    with Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[cyan]{task.description}"),
        console=console,
        transient=True,
    ) as prog:
        task = prog.add_task("Running Signal Engine + XDI Engine …", total=None)

        if args.source == "yahoo":
            # Use the engine/yahoo_loader directly
            from engine.yahoo_loader import fetch_ohlcv
            df = fetch_ohlcv(symbol=args.symbol, period="3mo")
            from ml.indicators.technical_indicators import compute_all_indicators
            from ml.signals.signal_engine import SignalEngine
            from ml.xdi.xdi_engine import XDIEngine
            from ml.decision.hybrid_decision_engine import HybridDecisionEngine
            from ml.pipeline import _disabled_ml_placeholder, _candle_horizon_label, _compute_combined_confidence
            from datetime import datetime, timezone

            indicators = compute_all_indicators(df)
            result     = SignalEngine().generate_signal(indicators)
            result["candle_interval"] = args.interval
            result["ml_prediction"]   = _disabled_ml_placeholder()
            result["hybrid_decision"] = HybridDecisionEngine().combine(result, result["ml_prediction"])
            result["generated_at"]    = datetime.now(timezone.utc).isoformat()
            result["data_as_of"]      = str(df.index[-1].date())
            result["prediction_horizon"] = _candle_horizon_label(args.interval)
            rule_conf = result["confidence"]
            result["rule_confidence"] = rule_conf
            result["ml_confidence"]   = None
            result["confidence"]      = _compute_combined_confidence(rule_conf, result["ml_prediction"])
            result["explanation"]     = XDIEngine().generate_explanation(result)
            result["source"]          = "yahoo"
            result["symbol"]          = args.symbol
        else:
            result = run_analysis(
                source=args.source,
                filepath=args.filepath if args.source == "csv" else None,
                symbol=args.symbol     if args.source != "csv" else None,
                start=args.start,
                end=args.end,
                candle_interval=args.interval,
            )

        prog.update(task, description="Done.")

    return result


def main():
    args = parse_args()

    render_header()

    # Source info line
    src_info = (
        f"[dim]Source:[/dim] [bold]{args.source.upper()}[/bold]  "
        f"[dim]Symbol:[/dim] [bold]{args.symbol}[/bold]  "
        f"[dim]Interval:[/dim] [bold]{args.interval}[/bold]"
    )
    console.print(Align(src_info, align="center"))
    console.print()

    try:
        result = run_with_spinner(args)
    except Exception as exc:
        console.print_exception()
        console.print(f"\n[bold red]Error:[/bold red] {exc}")
        sys.exit(1)

    explanation = result.get("explanation", {})
    hybrid      = result.get("hybrid_decision")

    # ── Render all sections ───────────────────────────────────────────────────
    render_signal_card(result)
    console.print()
    render_indicators(result["indicators"])
    console.print()
    render_rules(result.get("rules_triggered", []))
    console.print()
    console.print(Rule("[bold magenta]MODULE 2  —  XDI Explainability Engine[/bold magenta]"))
    console.print()
    render_xdi(explanation, hybrid)
    console.print()

    if args.verbose:
        render_detailed_reasoning(explanation)
        console.print()

    # ── Footer ────────────────────────────────────────────────────────────────
    console.print(Rule(style="dim"))
    console.print(
        f"[dim]  Generated: {result.get('generated_at', '—')}  |  "
        f"Data as of: {result.get('data_as_of', '—')}[/dim]"
    )
    console.print()


if __name__ == "__main__":
    main()

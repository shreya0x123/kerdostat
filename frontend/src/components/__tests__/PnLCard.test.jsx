import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import PnLCard from "../PnLCard";

describe("PnLCard Component", () => {
  it("renders positive daily P&L correctly with correct signs and classes", () => {
    render(<PnLCard dailyPnl={150.25} winRate={72.4} tradeCount={15} />);
    
    expect(screen.getByTestId("pnl-card")).toBeInTheDocument();
    expect(screen.getByTestId("pnl-value")).toHaveTextContent("+$150.25");
    expect(screen.getByTestId("pnl-value")).toHaveClass("text-emerald-500");
    expect(screen.getByTestId("pnl-sparkline")).toBeInTheDocument();
    expect(screen.getByTestId("win-rate")).toHaveTextContent("72.4%");
    expect(screen.getByTestId("trade-count")).toHaveTextContent("15");
  });

  it("renders negative daily P&L correctly", () => {
    render(<PnLCard dailyPnl={-85.50} winRate={45.0} tradeCount={8} />);
    
    expect(screen.getByTestId("pnl-value")).toHaveTextContent("-$85.50");
    expect(screen.getByTestId("pnl-value")).toHaveClass("text-rose-500");
    expect(screen.getByTestId("win-rate")).toHaveTextContent("45.0%");
    expect(screen.getByTestId("trade-count")).toHaveTextContent("8");
  });
});

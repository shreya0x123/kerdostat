import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import TradingTerminal from "../TradingTerminal";
import * as useMarketEngineModule from "@/hooks/useMarketEngine";

// Mock PriceChart and OHLCVChart to avoid canvas rendering issues in test environment
vi.mock("../PriceChart", () => ({
  default: () => <div data-testid="price-chart">Price Chart</div>,
}));

vi.mock("@/hooks/useMarketEngine", () => ({
  default: vi.fn(),
}));

vi.mock("@/services/apiService", () => ({
  fetchAccountDetails: vi.fn(() => Promise.resolve({
    cash: 40000.0,
    buying_power: 160000.0,
    equity: 40000.0,
    portfolio_value: 40000.0,
    daily_pnl: 0.0,
    mock_mode: true
  })),
  fetchPositions: vi.fn(() => Promise.resolve([
    {
      symbol: "QUANT",
      qty: 50,
      avg_entry_price: 103.75,
      current_price: 105.00,
      market_value: 5250.00,
      unrealized_pl: 62.50
    }
  ])),
}));

describe("TradingTerminal Guardrail Breach (TC-08)", () => {
  it("renders nominal state when price is above drawdown threshold", () => {
    // Mock normal price of 105.00
    vi.mocked(useMarketEngineModule.default).mockReturnValue({
      candleData: [{ time: 12345, open: 104, high: 106, low: 103, close: 105 }],
      currentPrice: 105.00,
      xaiLogs: ["[10:00:00] Live algo loop running nominal."],
    });

    render(
      <MemoryRouter>
        <TradingTerminal />
      </MemoryRouter>
    );

    // Safety card details should be nominal
    expect(screen.getByTestId("safety-card")).toBeInTheDocument();
    expect(screen.getByTestId("safety-status-badge")).toHaveTextContent("OK");
    expect(screen.getByTestId("safety-status-text")).toHaveTextContent("Risk guardrails nominal");

    // Guardrail breach alert should NOT be present
    expect(screen.queryByTestId("guardrail-breach-alert")).not.toBeInTheDocument();
  });

  it("renders breach state and error banner when price falls below drawdown boundary ($98.00)", () => {
    // Mock price of 95.00 (which triggers currentPrice < 98.0)
    vi.mocked(useMarketEngineModule.default).mockReturnValue({
      candleData: [{ time: 12345, open: 104, high: 106, low: 93, close: 95 }],
      currentPrice: 95.00,
      xaiLogs: ["[10:00:00] Critical exposure breach warning."],
    });

    render(
      <MemoryRouter>
        <TradingTerminal />
      </MemoryRouter>
    );

    // Safety card details should show BREACH details
    expect(screen.getByTestId("safety-card")).toBeInTheDocument();
    expect(screen.getByTestId("safety-status-badge")).toHaveTextContent("BREACH");
    expect(screen.getByTestId("safety-status-text")).toHaveTextContent("Drawdown limit exceeded!");

    // Guardrail breach alert banner MUST be present
    const alertBanner = screen.getByTestId("guardrail-breach-alert");
    expect(alertBanner).toBeInTheDocument();
    expect(alertBanner).toHaveTextContent(/Critical Exposure Drawdown Breach/i);
    expect(alertBanner).toHaveTextContent(/QUANT price fell below maximum drawdown boundary/i);
  });
});

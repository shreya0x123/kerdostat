import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import HijackPanel from "../HijackPanel";
import * as apiService from "@/services/apiService";

vi.mock("@/services/apiService", () => ({
  overrideProposal: vi.fn(),
  fetchAccountDetails: vi.fn(() => Promise.resolve({ buying_power: 82980.27 })),
  fetchOHLCV: vi.fn(() => Promise.resolve([{ close: 150.00 }])),
  searchAssets: vi.fn(() => Promise.resolve([
    { symbol: "AAPL", name: "Apple Inc.", price: 150.00, change: 1.25, change_percent: 0.83 }
  ])),
}));

describe("HijackPanel Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form fields with default values", async () => {
    const mockProposal = {
      id: "prop-1",
      symbol: "QUANT",
      qty: 150,
      entry_price: 151.60
    };

    render(<HijackPanel proposal={mockProposal} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Asset Symbol/i)).toHaveValue("QUANT");
      expect(screen.getByLabelText(/Quantity/i)).toHaveValue(150);
      expect(screen.getByLabelText(/Order Type/i)).toHaveValue("Market");
      // Limit Price input is hidden by default under Market type
      expect(screen.queryByLabelText(/Limit Price/i)).not.toBeInTheDocument();
    });
  });

  it("displays limit price field only when limit order type is selected", async () => {
    const user = userEvent.setup();
    render(<HijackPanel />);

    const orderTypeSelect = screen.getByLabelText(/Order Type/i);
    expect(screen.queryByLabelText(/Limit Price/i)).not.toBeInTheDocument();

    // Toggle to Limit
    await user.selectOptions(orderTypeSelect, "Limit");

    await waitFor(() => {
      expect(screen.getByLabelText(/Limit Price/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Limit Price/i)).toHaveValue(150);
    });

    // Toggle back to Market
    await user.selectOptions(orderTypeSelect, "Market");

    await waitFor(() => {
      expect(screen.queryByLabelText(/Limit Price/i)).not.toBeInTheDocument();
    });
  });

  it("submits the buy order with correct params and handle success callback", async () => {
    const user = userEvent.setup();
    const handleSuccess = vi.fn();
    apiService.overrideProposal.mockResolvedValue({ status: "success" });

    render(<HijackPanel onSuccess={handleSuccess} />);

    const symbolInput = screen.getByLabelText(/Asset Symbol/i);
    const qtyInput = screen.getByLabelText(/Quantity/i);
    const buyBtn = screen.getByRole("button", { name: /^Buy$/i });

    // Modify Symbol
    await user.clear(symbolInput);
    await user.type(symbolInput, "AAPL");

    // Modify Quantity
    await user.clear(qtyInput);
    await user.type(qtyInput, "10");

    await waitFor(() => {
      expect(buyBtn).not.toBeDisabled();
    });

    await user.click(buyBtn);

    await waitFor(() => {
      expect(apiService.overrideProposal).toHaveBeenCalledWith("manual", {
        symbol: "AAPL",
        qty: 10,
        SL: 142.5,  // 150 * 0.95 (default)
        TP: 157.5,  // 150 * 1.05 (default)
        entry_price: 150.00,
        proposal_id: null,
        side: "BUY",
        order_type: "Market"
      });
      expect(handleSuccess).toHaveBeenCalled();
    });
  });

  it("submits the sell order with correct calculated params", async () => {
    const user = userEvent.setup();
    const handleSuccess = vi.fn();
    apiService.overrideProposal.mockResolvedValue({ status: "success" });

    render(<HijackPanel onSuccess={handleSuccess} />);

    const qtyInput = screen.getByLabelText(/Quantity/i);
    const sellBtn = screen.getByRole("button", { name: /^Sell$/i });

    // Set Quantity
    await user.clear(qtyInput);
    await user.type(qtyInput, "5");

    await waitFor(() => {
      expect(sellBtn).not.toBeDisabled();
    });

    await user.click(sellBtn);

    await waitFor(() => {
      expect(apiService.overrideProposal).toHaveBeenCalledWith("manual", {
        symbol: "QUANT",
        qty: 5,
        SL: 157.5,  // 150 * 1.05
        TP: 142.5,  // 150 * 0.95
        entry_price: 150.00,
        proposal_id: null,
        side: "SELL",
        order_type: "Market"
      });
      expect(handleSuccess).toHaveBeenCalled();
    });
  });
});

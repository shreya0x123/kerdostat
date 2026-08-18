import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import OverridePanel from "../OverridePanel";
import * as apiService from "@/services/apiService";

vi.mock("@/services/apiService", () => ({
  overrideProposal: vi.fn(),
  fetchProposals: vi.fn(() => Promise.resolve([
    { id: "prop-123", symbol: "TSLA", qty: 10, entry_price: 200.0, SL: 190.0, TP: 220.0, signal: "buy", status: "pending" }
  ])),
}));

describe("OverridePanel Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with nominal selector options and default input values", async () => {
    render(<OverridePanel />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Select Active Proposal/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Asset Symbol/i)).toHaveValue("");
    });
  });

  it("populates fields when an active proposal is selected from the dropdown", async () => {
    const user = userEvent.setup();
    render(<OverridePanel />);

    const select = screen.getByLabelText(/Select Active Proposal/i);
    
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /TSLA/i })).toBeInTheDocument();
    });

    await user.selectOptions(select, "prop-123");

    await waitFor(() => {
      expect(screen.getByLabelText(/Asset Symbol/i)).toHaveValue("TSLA");
      expect(screen.getByLabelText(/Quantity/i)).toHaveValue(10);
      expect(screen.getByLabelText(/Entry Price/i)).toHaveValue(200);
      expect(screen.getByLabelText(/Stop Loss/i)).toHaveValue(190);
      expect(screen.getByLabelText(/Take Profit/i)).toHaveValue(220);
    });
  });

  it("displays direction-aware stop-loss error validations", async () => {
    const user = userEvent.setup();
    render(<OverridePanel />);

    const select = screen.getByLabelText(/Select Active Proposal/i);
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /TSLA/i })).toBeInTheDocument();
    });

    await user.selectOptions(select, "prop-123");

    const slInput = screen.getByLabelText(/Stop Loss/i);

    // Set Stop loss above entry price for a BUY (invalid)
    await user.clear(slInput);
    await user.type(slInput, "210");

    await waitFor(() => {
      expect(screen.getByText(/must be less than Entry Price/i)).toBeInTheDocument();
    });
  });

  it("successfully dispatches override data upon form submission", async () => {
    const user = userEvent.setup();
    const handleSuccess = vi.fn();
    apiService.overrideProposal.mockResolvedValue({ status: "success" });

    render(<OverridePanel onSuccess={handleSuccess} />);

    const select = screen.getByLabelText(/Select Active Proposal/i);
    await waitFor(() => {
      expect(screen.getByRole("option", { name: /TSLA/i })).toBeInTheDocument();
    });

    await user.selectOptions(select, "prop-123");

    const submitBtn = screen.getByRole("button", { name: /Apply Override/i });
    expect(submitBtn).not.toBeDisabled();

    await user.click(submitBtn);

    await waitFor(() => {
      expect(apiService.overrideProposal).toHaveBeenCalledWith("prop-123", {
        symbol: "TSLA",
        qty: 10,
        SL: 190.0,
        TP: 220.0,
        entry_price: 200.0,
        proposal_id: "prop-123",
        side: "BUY"
      });
      expect(handleSuccess).toHaveBeenCalled();
    });
  });
});

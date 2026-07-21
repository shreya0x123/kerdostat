import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import HijackPanel from "../HijackPanel";
import * as apiService from "@/services/apiService";

vi.mock("@/services/apiService", () => ({
  overrideProposal: vi.fn(),
}));

describe("HijackPanel Component", () => {
  it("renders form fields with default values", async () => {
    const mockProposal = {
      id: "prop-1",
      symbol: "QUANT",
      qty: 150,
      SL: 149.0,
      TP: 157.5,
      entry_price: 151.60
    };

    render(<HijackPanel proposal={mockProposal} />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Asset Symbol/i)).toHaveValue("QUANT");
      expect(screen.getByLabelText(/Entry Price/i)).toHaveValue(151.60);
      expect(screen.getByLabelText(/Quantity/i)).toHaveValue(150);
      expect(screen.getByLabelText(/Stop Loss/i)).toHaveValue(149.0);
      expect(screen.getByLabelText(/Take Profit/i)).toHaveValue(157.5);
    });
  });

  it("validates that SL must be less than entry price and shows error", async () => {
    const user = userEvent.setup();
    render(<HijackPanel proposal={{ entry_price: 100, SL: 95 }} />);

    const entryInput = screen.getByLabelText(/Entry Price/i);
    const slInput = screen.getByLabelText(/Stop Loss/i);
    const submitBtn = screen.getByRole("button", { name: /EXECUTE HIJACK OVERRIDE/i });

    // Clear and set Entry Price to 100
    await user.clear(entryInput);
    await user.type(entryInput, "100");

    // Clear and set SL to 105 (greater than Entry)
    await user.clear(slInput);
    await user.type(slInput, "105");

    await waitFor(() => {
      expect(screen.getByTestId("SL-error")).toHaveTextContent("SL must be < entry price");
      expect(submitBtn).toBeDisabled();
    });
  });

  it("enables submit button only when form is valid and handles submit", async () => {
    const user = userEvent.setup();
    const handleSuccess = vi.fn();
    apiService.overrideProposal.mockResolvedValue({ status: "success" });

    render(<HijackPanel onSuccess={handleSuccess} />);

    const entryInput = screen.getByLabelText(/Entry Price/i);
    const slInput = screen.getByLabelText(/Stop Loss/i);
    const submitBtn = screen.getByRole("button", { name: /EXECUTE HIJACK OVERRIDE/i });

    // Modify fields to be valid (Entry = 150, SL = 145)
    await user.clear(entryInput);
    await user.type(entryInput, "150");

    await user.clear(slInput);
    await user.type(slInput, "145");

    await waitFor(() => {
      expect(submitBtn).not.toBeDisabled();
    });

    await user.click(submitBtn);

    await waitFor(() => {
      expect(apiService.overrideProposal).toHaveBeenCalledWith("manual", {
        symbol: "QUANT",
        qty: 100,
        SL: 145,
        TP: 157.5,
        entry_price: 150,
        proposal_id: null
      });
      expect(handleSuccess).toHaveBeenCalled();
    });
  });
});

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import ProposalCard from "../ProposalCard";

// Mock chart component to isolate ProposalCard component tests
vi.mock("../OHLCVChart", () => {
  return {
    default: () => <div data-testid="mock-chart">OHLCV Mock Chart</div>
  };
});

let mockSystemMode = "copilot";
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    systemMode: mockSystemMode,
  }),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe("ProposalCard Component", () => {
  const defaultProps = {
    symbol: "QUANT",
    signal: "BUY",
    qty: 150,
    SL: 149.0,
    TP: 157.5,
    XAIReason: "Bullish divergence indicator crossover."
  };

  beforeEach(() => {
    mockSystemMode = "copilot";
    mockNavigate.mockClear();
  });

  it("should render proposal details correctly", () => {
    render(<ProposalCard {...defaultProps} />);
    
    // Check header details
    expect(screen.getByText("QUANT")).toBeInTheDocument();
    expect(screen.getByText("BUY")).toBeInTheDocument();
    expect(screen.getByText("Proposal ID: P-QUANT-150")).toBeInTheDocument();

    // Check parameters metrics
    expect(screen.getByText("150")).toBeInTheDocument();
    expect(screen.getByText("149.00")).toBeInTheDocument();
    expect(screen.getByText("157.50")).toBeInTheDocument();

    // Check XAI block
    expect(screen.getByText("Bullish divergence indicator crossover.")).toBeInTheDocument();
    
    // Check chart component renders
    expect(screen.getByTestId("mock-chart")).toBeInTheDocument();
  });

  it("should invoke onApprove callback when clicking Approve button", async () => {
    const onApprove = vi.fn();
    const actions = { onApprove };

    render(<ProposalCard {...defaultProps} actions={actions} />);
    
    const approveBtn = screen.getByText("Approve & Execute");
    expect(approveBtn).toBeInTheDocument();

    fireEvent.click(approveBtn);
    
    // Wait for the simulated async timer or execution to complete
    await waitFor(() => {
      expect(onApprove).toHaveBeenCalledTimes(1);
    });
  });

  it("should invoke onReject callback when clicking Reject button", async () => {
    const onReject = vi.fn();
    const actions = { onReject };

    render(<ProposalCard {...defaultProps} actions={actions} />);
    
    const rejectBtn = screen.getByText("Reject & Cancel");
    expect(rejectBtn).toBeInTheDocument();

    fireEvent.click(rejectBtn);
    
    // Wait for the simulated async timer or execution to complete
    await waitFor(() => {
      expect(onReject).toHaveBeenCalledTimes(1);
    });
  });

  it("should render override button and navigate in autopilot mode", async () => {
    mockSystemMode = "autopilot";
    render(<ProposalCard {...defaultProps} />);

    const overrideBtn = screen.getByTestId("override-btn");
    expect(overrideBtn).toBeInTheDocument();
    expect(screen.queryByText("Approve & Execute")).not.toBeInTheDocument();

    fireEvent.click(overrideBtn);

    expect(mockNavigate).toHaveBeenCalledWith("/hijack", {
      state: {
        proposal: {
          id: "prop-quant",
          symbol: "QUANT",
          qty: 150,
          SL: 149.0,
          TP: 157.5,
          entry_price: 151.60
        }
      }
    });
  });
});

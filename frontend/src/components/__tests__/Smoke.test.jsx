import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import App from "../../App";

// Mock the Recharts and OHLCV chart since JSDOM doesn't support canvas/SVG measurement
vi.mock("../OHLCVChart", () => {
  return {
    default: () => <div data-testid="mock-chart">OHLCV Chart Mock</div>
  };
});

// Mock lightweight charts in case dashboard loads it
vi.mock("../PriceChart", () => {
  return {
    default: () => <div data-testid="mock-price-chart">Price Chart Mock</div>
  };
});


describe("End-to-end Auth and Proposals Smoke Test", () => {
  let mockLoggedIn = false;

  beforeEach(() => {
    vi.clearAllMocks();
    mockLoggedIn = false;
    
    // Clear local storage to ensure fresh session
    localStorage.clear();
    localStorage.setItem("kerdostat_tour_status", "completed");

    // Mock global WebSocket to prevent connection errors
    class MockWebSocket {
      constructor(url) {
        this.url = url;
        this.readyState = 0; // CONNECTING
        this.send = vi.fn();
        this.close = vi.fn();
        this.onopen = null;
        this.onmessage = null;
        this.onclose = null;
        this.onerror = null;

        // Simulate open trigger
        setTimeout(() => {
          this.readyState = 1; // OPEN
          if (this.onopen) this.onopen();
        }, 50);
      }
    }
    MockWebSocket.OPEN = 1;
    globalThis.WebSocket = MockWebSocket;

    // Mock API fetch requests with dynamic mockLoggedIn state
    const mockFetch = vi.fn().mockImplementation((url) => {
      // 1. Auth status check on load
      if (url.includes("/auth/me")) {
        if (mockLoggedIn) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({
              id: "user-1",
              name: "Alex Mercer",
              email: "trader@kerdostat.com"
            })
          });
        }
        return Promise.resolve({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ detail: "Session token missing" })
        });
      }
      // 2. Authentication Submit -> successful token generation
      if (url.includes("/auth/login")) {
        mockLoggedIn = true;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: "user-1",
            name: "Alex Mercer",
            email: "trader@kerdostat.com"
          })
        });
      }
      // 3. Retrieve Proposals List
      if (url.includes("/trade/proposals")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            {
              id: "prop-1",
              symbol: "QUANT",
              signal: "BUY",
              qty: 150,
              SL: 149.0,
              TP: 157.5,
              status: "pending",
              XAIReason: "Neural network double bottom formation."
            }
          ])
        });
      }
      // 4. Dispatch Proposal Action Update
      if (url.includes("/action")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: "prop-1",
            symbol: "QUANT",
            signal: "BUY",
            qty: 150,
            SL: 149.0,
            TP: 157.5,
            status: "approved",
            XAIReason: "Neural network double bottom formation."
          })
        });
      }
      // 5. Direct Hijack execution
      if (url.includes("/trade/hijack") || url.includes("/override")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: "success", message: "Hijack executed and logged successfully" })
        });
      }
      // 6. Market OHLCV
      if (url.includes("/market/ohlcv")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { time: "09:30", open: 150.2, high: 152.5, low: 149.8, close: 151.6, volume: 12000, rsi: 45.5 },
            { time: "10:00", open: 151.6, high: 153.1, low: 151.0, close: 152.8, volume: 9500, rsi: 48.2 }
          ])
        });
      }
      // 7. System Mode settings
      if (url.includes("/trade/mode")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ mode: "copilot" })
        });
      }
      // 7a. Account details
      if (url.includes("/trade/account")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            cash: 40000.0,
            buying_power: 160000.0,
            equity: 40000.0,
            portfolio_value: 40000.0,
            daily_pnl: 0.0,
            mock_mode: true
          })
        });
      }
      // 7b. Positions list
      if (url.includes("/trade/positions")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            {
              symbol: "QUANT",
              qty: 50,
              avg_entry_price: 103.75,
              current_price: 105.00,
              market_value: 5250.00,
              unrealized_pl: 62.50
            }
          ])
        });
      }
      // 8. Audit Logs list
      if (url.includes("/trade/audit-logs")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([
            { id: "log-1", timestamp: "2026-06-15T09:30:00Z", symbol: "QUANT", action_type: "APPROVE", qty: 150, price: 151.60, status: "SUCCESS", user: "trader@kerdostat.com" }
          ])
        });
      }
      return Promise.reject(new Error(`Unhandled request URL: ${url}`));
    });

    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("should login successfully, navigate to proposals, and approve a proposal card", async () => {
    window.history.pushState({}, "Test Page", "/dashboard");
    const user = userEvent.setup();
    render(<App />);

    // --- PHASE 1: Verify Initial Redirect to Auth Login Gateway ---
    await waitFor(() => {
      expect(screen.getByText("Kerdostat Access")).toBeInTheDocument();
    }, { timeout: 10000 });

    const emailInput = screen.getByLabelText(/^email$/i);
    const passwordInput = screen.getByLabelText(/^password$/i);
    const signInBtn = screen.getByRole("button", { name: /^sign in$/i });

    // --- PHASE 2: Submit Valid Credentials ---
    await user.type(emailInput, "trader@kerdostat.com");
    await user.type(passwordInput, "password123");
    await user.click(signInBtn);

    // --- PHASE 3: Navigate to Dashboard and transition to Proposals Feed ---
    await waitFor(() => {
      expect(screen.getByText("Trading Dashboard")).toBeInTheDocument();
    }, { timeout: 15000 });

    // Find and click the Proposals link in the Sidebar navigation
    const proposalsLink = screen.getByTitle("Proposals");
    expect(proposalsLink).toBeInTheDocument();
    await user.click(proposalsLink);

    // --- PHASE 4: Check Proposals Load & Approve proposal ---
    await waitFor(() => {
      expect(screen.getAllByText("Proposals & Governance").length).toBe(2);
      expect(screen.getByText("QUANT")).toBeInTheDocument();
      expect(screen.getByText("Awaiting HITL Approval")).toBeInTheDocument();
    }, { timeout: 10000 });

    const approveBtn = screen.getByRole("button", { name: "Approve & Execute" });
    expect(approveBtn).toBeInTheDocument();
    await user.click(approveBtn);

    // --- PHASE 5: Verify status changes to Approved ---
    await waitFor(() => {
      expect(screen.getByText("Approved & Dispatched")).toBeInTheDocument();
    });
  }, 30000);

  it("should execute the full Copilot parameter hijack and execution flow", async () => {
    window.history.pushState({}, "Test Page", "/dashboard");
    const user = userEvent.setup();
    render(<App />);

    // --- PHASE 1: Verify Initial Redirect to Auth Login Gateway ---
    await waitFor(() => {
      expect(screen.getByText("Kerdostat Access")).toBeInTheDocument();
    }, { timeout: 10000 });

    const emailInput = screen.getByLabelText(/^email$/i);
    const passwordInput = screen.getByLabelText(/^password$/i);
    const signInBtn = screen.getByRole("button", { name: /^sign in$/i });

    // --- PHASE 2: Submit Valid Credentials ---
    await user.type(emailInput, "trader@kerdostat.com");
    await user.type(passwordInput, "password123");
    await user.click(signInBtn);

    // --- PHASE 3: Navigate to Dashboard and transition to Proposals Feed ---
    await waitFor(() => {
      expect(screen.getByText("Trading Dashboard")).toBeInTheDocument();
    }, { timeout: 15000 });

    const proposalsLink = screen.getByTitle("Proposals");
    expect(proposalsLink).toBeInTheDocument();
    await user.click(proposalsLink);

    // --- PHASE 4: Find proposal and click Hijack Trade ---
    await waitFor(() => {
      expect(screen.getByText("Awaiting HITL Approval")).toBeInTheDocument();
      expect(screen.getByTestId("hijack-btn")).toBeInTheDocument();
    }, { timeout: 10000 });

    const hijackBtn = screen.getByTestId("hijack-btn");
    await user.click(hijackBtn);

    // --- PHASE 5: Wait for Hijack Page & Modify Parameters ---
    await waitFor(() => {
      expect(screen.getAllByText("Manual Override Console").length).toBeGreaterThan(0);
      expect(screen.getByTestId("hijack-panel")).toBeInTheDocument();
    });

    const qtyInput = within(screen.getByTestId("hijack-panel")).getByLabelText(/Quantity/i);
    const buyBtn = screen.getByRole("button", { name: /^Buy$/i });

    // Verify quantity is pre-filled with proposal qty (150)
    expect(qtyInput).toHaveValue(150);

    // Modify quantity to 100
    await user.clear(qtyInput);
    await user.type(qtyInput, "100");

    await waitFor(() => {
      expect(buyBtn).not.toBeDisabled();
    });

    // --- PHASE 6: Submit Order ---
    await user.click(buyBtn);

    // --- PHASE 7: Verify success message ---
    await waitFor(() => {
      expect(screen.getByTestId("success-alert")).toBeInTheDocument();
    });
  }, 30000);
});

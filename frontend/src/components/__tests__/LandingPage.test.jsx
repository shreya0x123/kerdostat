import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LandingPage from "@/pages/LandingPage";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    isAuthenticated: false,
  }),
}));

vi.mock("@/hooks/useTheme", () => ({
  useTheme: () => ({
    theme: "dark",
    setTheme: vi.fn(),
  }),
}));

describe("Reverted LandingPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock navigator.clipboard
    Object.defineProperty(navigator, "clipboard", {
      value: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
      configurable: true,
    });
  });

  it("should render landing page visitor header, brand logos, use cases, and capabilities", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );

    // Verify Brand Logo (header and footer)
    expect(screen.getAllByText(/KERDOSTAT/i).length).toBeGreaterThan(0);

    // Verify Main Headers
    expect(screen.getByText(/algorithmic assets/i)).toBeInTheDocument();

    // Verify Use Cases section
    expect(screen.getByText("Brokers & Wealth Managers")).toBeInTheDocument();
    expect(screen.getByText("Banks & EMIs")).toBeInTheDocument();
    expect(screen.getByText("Software Companies")).toBeInTheDocument();

    // Verify Capabilities grid elements
    expect(screen.getByText("Security & Audits")).toBeInTheDocument();
    expect(screen.getByText("Real-time Telemetry")).toBeInTheDocument();
    expect(screen.getByText("Modular Execution")).toBeInTheDocument();
  });

  it("should toggle code snippets between Python, JavaScript, and cURL tabs", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );

    // Initial state check - Python is default active tab
    const pythonTab = screen.getByTestId("code-tab-python");
    expect(pythonTab).toHaveClass("bg-primary/10");
    expect(screen.getByText(/client = kerdostat\.Client/i)).toBeInTheDocument();

    // Switch to javascript
    const jsTab = screen.getByTestId("code-tab-javascript");
    fireEvent.click(jsTab);
    expect(jsTab).toHaveClass("bg-primary/10");
    expect(screen.queryByText(/client = kerdostat\.Client/i)).not.toBeInTheDocument();
    expect(screen.getByText(/new KerdostatClient/i)).toBeInTheDocument();

    // Switch to curl
    const curlTab = screen.getByTestId("code-tab-curl");
    fireEvent.click(curlTab);
    expect(curlTab).toHaveClass("bg-primary/10");
    expect(screen.queryByText(/new KerdostatClient/i)).not.toBeInTheDocument();
    expect(screen.getByText(/curl -X POST/i)).toBeInTheDocument();
  });

  it("should trigger copy to clipboard when copy button is clicked", async () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );

    const copyBtn = screen.getByTestId("copy-code-btn");
    expect(copyBtn).toBeInTheDocument();

    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledTimes(1);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining("client = kerdostat.Client")
    );
  });
});

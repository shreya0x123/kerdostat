import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import DocsPage from "../../pages/DocsPage";

describe("DocsPage Component", () => {
  it("renders side navigation and default auth endpoint details", () => {
    render(<DocsPage />);

    // Verify side navigation headers and items exist
    expect(screen.getByText("Reference API")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /User Authentication/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Market Candlestick Stream/i })).toBeInTheDocument();

    // Verify default auth documentation displays
    expect(screen.getAllByText("User Authentication").length).toBeGreaterThan(0);
    expect(screen.getByText("/auth/login")).toBeInTheDocument();
    expect(screen.getByText("email")).toBeInTheDocument();
    expect(screen.getByText("password")).toBeInTheDocument();
  });

  it("switches displayed endpoint on side navigation click", async () => {
    const user = userEvent.setup();
    render(<DocsPage />);

    const marketBtn = screen.getByRole("button", { name: /Market Candlestick Stream/i });
    await user.click(marketBtn);

    // Verify path and description updates to OHLCV endpoint
    await waitFor(() => {
      expect(screen.getByText("/market/ohlcv")).toBeInTheDocument();
      expect(screen.getByRole("heading", { name: "Market Candlestick Stream" })).toBeInTheDocument();
      expect(screen.getByText("range")).toBeInTheDocument();
    });
  });

  it("updates code block language tab correctly", async () => {
    const user = userEvent.setup();
    render(<DocsPage />);

    // Default code block is Python for /auth/login
    expect(screen.getByText(/url = "http:\/\/localhost:8000\/auth\/login"/)).toBeInTheDocument();

    // Switch to cURL
    const curlTab = screen.getByRole("button", { name: /CURL/i });
    await user.click(curlTab);

    await waitFor(() => {
      expect(screen.getByText(/curl -X POST "http:\/\/localhost:8000\/auth\/login"/)).toBeInTheDocument();
    });

    // Switch to NodeJS
    const nodeTab = screen.getByRole("button", { name: /NodeJS/i });
    await user.click(nodeTab);

    await waitFor(() => {
      expect(screen.getByText(/fetch\("http:\/\/localhost:8000\/auth\/login"/)).toBeInTheDocument();
    });
  });

  it("executes API playground request when clicking Try It Out and renders response", async () => {
    const user = userEvent.setup();
    
    // Mock successful login call response
    const mockResponse = { id: "user-1", name: "Alex Mercer", email: "trader@kerdostat.com" };
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse)
    });
    vi.stubGlobal("fetch", mockFetch);

    render(<DocsPage />);

    // Get Try It Out button and click it
    const tryItBtn = screen.getByTestId("try-it-btn");
    expect(tryItBtn).toBeInTheDocument();
    await user.click(tryItBtn);

    // Verify loading and response display
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/auth/login",
        expect.objectContaining({
          method: "POST",
          credentials: "include",
          body: JSON.stringify({ email: "trader@kerdostat.com", password: "password123" })
        })
      );
      const responseOutput = screen.getByTestId("live-response-output");
      expect(responseOutput).toBeInTheDocument();
      expect(responseOutput.textContent).toContain("Alex Mercer");
    });

    vi.unstubAllGlobals();
  });
});

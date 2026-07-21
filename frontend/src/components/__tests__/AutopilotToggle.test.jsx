import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/hooks/useAuth";
import { ThemeProvider } from "@/hooks/useTheme";
import DashboardLayout from "../DashboardLayout";

describe("Autopilot Mode Toggle", () => {
  let mockMode = "copilot";

  beforeEach(() => {
    mockMode = "copilot";
    vi.clearAllMocks();

    const mockFetch = vi.fn().mockImplementation((url, options) => {
      // 1. Session check
      if (url.includes("/auth/me")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: "user-1",
            name: "Alex Mercer",
            email: "trader@kerdostat.com"
          })
        });
      }
      // 2. Mode GET
      if (url.includes("/trade/mode") && (!options || !options.method || options.method.toUpperCase() === "GET")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ mode: mockMode })
        });
      }
      // 3. Mode POST
      if (url.includes("/trade/mode") && options && options.method === "POST") {
        const body = JSON.parse(options.body);
        mockMode = body.mode;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ mode: mockMode })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([])
      });
    });

    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders with default COPILOT mode and updates badge when switch toggled", async () => {
    render(
      <ThemeProvider>
        <AuthProvider>
          <MemoryRouter>
            <DashboardLayout />
          </MemoryRouter>
        </AuthProvider>
      </ThemeProvider>
    );

    // Verify loading and initial COPILOT badge
    await waitFor(() => {
      expect(screen.getByTestId("mode-badge")).toHaveTextContent("COPILOT");
    });

    const modeSwitch = screen.getByTestId("mode-switch");
    expect(modeSwitch).not.toBeChecked();

    // Toggle to Autopilot (opens modal)
    fireEvent.click(modeSwitch);

    // Click confirm in modal
    const confirmBtn1 = await screen.findByTestId("confirm-mode-btn");
    fireEvent.click(confirmBtn1);

    // Verify badge updates to AUTOPILOT and switch is checked
    await waitFor(() => {
      expect(screen.getByTestId("mode-badge")).toHaveTextContent("AUTOPILOT");
      expect(modeSwitch).toBeChecked();
    });

    // Toggle back to Copilot (opens modal)
    fireEvent.click(modeSwitch);

    // Click confirm in modal
    const confirmBtn2 = await screen.findByTestId("confirm-mode-btn");
    fireEvent.click(confirmBtn2);

    // Verify badge updates back to COPILOT
    await waitFor(() => {
      expect(screen.getByTestId("mode-badge")).toHaveTextContent("COPILOT");
      expect(modeSwitch).not.toBeChecked();
    });
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GuidedTour from "../GuidedTour";

describe("GuidedTour Component", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    
    // Create elements that tour will target
    const badge = document.createElement("div");
    badge.setAttribute("data-testid", "mode-badge");
    document.body.appendChild(badge);

    const stats = document.createElement("div");
    stats.setAttribute("data-testid", "stats-summary-row");
    document.body.appendChild(stats);
  });

  it("should show welcome dialog if first-time visitor", () => {
    render(
      <MemoryRouter>
        <GuidedTour isAuthenticated={true} />
      </MemoryRouter>
    );
    expect(screen.getByText("Welcome to Kerdostat!")).toBeInTheDocument();
    expect(screen.getByText("Start Tour")).toBeInTheDocument();
  });

  it("should skip tour and write completed to localStorage when Maybe Later clicked", () => {
    const endSpy = vi.fn();
    render(
      <MemoryRouter>
        <GuidedTour onTourEnd={endSpy} isAuthenticated={true} />
      </MemoryRouter>
    );
    
    const skipBtn = screen.getByText("Maybe Later");
    fireEvent.click(skipBtn);
    
    expect(localStorage.getItem("kerdostat_tour_status")).toBe("completed");
    expect(screen.queryByText("Welcome to Kerdostat!")).not.toBeInTheDocument();
    expect(endSpy).toHaveBeenCalled();
  });

  it("should start the step-by-step tour when Start Tour is clicked", async () => {
    render(
      <MemoryRouter>
        <GuidedTour isAuthenticated={true} />
      </MemoryRouter>
    );
    
    const startBtn = screen.getByText("Start Tour");
    fireEvent.click(startBtn);
    
    await waitFor(() => {
      expect(screen.getByTestId("tour-tooltip")).toBeInTheDocument();
    });
    
    expect(screen.getByText("System Execution Mode")).toBeInTheDocument();
  });

  it("should navigate steps using Next and Back controls", async () => {
    render(
      <MemoryRouter>
        <GuidedTour isAuthenticated={true} />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByText("Start Tour"));
    
    await waitFor(() => {
      expect(screen.getByText("System Execution Mode")).toBeInTheDocument();
    });

    const nextBtn = screen.getByRole("button", { name: /Next/i });
    fireEvent.click(nextBtn);

    await waitFor(() => {
      expect(screen.getByText(/Account metrics/i)).toBeInTheDocument();
    });

    const backBtn = screen.getByRole("button", { name: /Back/i });
    fireEvent.click(backBtn);

    await waitFor(() => {
      expect(screen.getByText("System Execution Mode")).toBeInTheDocument();
    });
  });

  it("should force start tour when forceStart prop is true", async () => {
    render(
      <MemoryRouter>
        <GuidedTour forceStart={true} isAuthenticated={true} />
      </MemoryRouter>
    );
    
    await waitFor(() => {
      expect(screen.getByTestId("tour-tooltip")).toBeInTheDocument();
    });
    expect(screen.getByText("System Execution Mode")).toBeInTheDocument();
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import PriceChart from "../PriceChart";
import * as apiService from "@/services/apiService";

vi.mock("@/services/apiService", () => ({
  fetchOHLCV: vi.fn(),
  fetchSignal: vi.fn(),
}));

const mockOHLCVData = Array.from({ length: 30 }, (_, i) => ({
  time: `10:${i.toString().padStart(2, "0")}`,
  open: 100 + i,
  high: 102 + i,
  low: 99 + i,
  close: 101 + i,
  volume: 1000 * (i + 1),
  rsi: 30 + (i * 2) % 40
}));

describe("PriceChart Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiService.fetchSignal.mockResolvedValue({ signal: "BUY" });
  });

  it("shows loading indicator initially, then renders chart when data loaded", async () => {
    apiService.fetchOHLCV.mockResolvedValue(mockOHLCVData);

    render(<PriceChart />);

    expect(screen.getByTestId("chart-loading")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("price-chart-container")).toBeInTheDocument();
      expect(screen.queryByTestId("chart-loading")).not.toBeInTheDocument();
    });

    expect(apiService.fetchOHLCV).toHaveBeenCalledWith("1D", "AAPL");
  });

  it("handles time range selection changes and queries new values", async () => {
    const user = userEvent.setup();
    apiService.fetchOHLCV.mockResolvedValue(mockOHLCVData);

    render(<PriceChart />);

    await waitFor(() => {
      expect(screen.getByTestId("price-chart-container")).toBeInTheDocument();
    });

    // Click 1W selector
    const oneWeekBtn = screen.getByTestId("range-1W");
    await user.click(oneWeekBtn);

    await waitFor(() => {
      expect(apiService.fetchOHLCV).toHaveBeenLastCalledWith("1W", "AAPL");
    });

    // Click 1M selector
    const oneMonthBtn = screen.getByTestId("range-1M");
    await user.click(oneMonthBtn);

    await waitFor(() => {
      expect(apiService.fetchOHLCV).toHaveBeenLastCalledWith("1M", "AAPL");
    });
  });

  it("toggles between area and candlestick chart types", async () => {
    const user = userEvent.setup();
    apiService.fetchOHLCV.mockResolvedValue(mockOHLCVData);

    render(<PriceChart />);

    await waitFor(() => {
      expect(screen.getByTestId("price-chart-container")).toBeInTheDocument();
    });

    // Default chart type should be 'area'
    expect(screen.getByTestId("chart-display-area")).toBeInTheDocument();
    expect(screen.queryByTestId("chart-display-candles")).not.toBeInTheDocument();

    // Click candlestick toggle
    const candlesToggleBtn = screen.getByTestId("toggle-chart-candles");
    await user.click(candlesToggleBtn);

    // Chart display should update to 'candles'
    expect(screen.getByTestId("chart-display-candles")).toBeInTheDocument();
    expect(screen.queryByTestId("chart-display-area")).not.toBeInTheDocument();

    // Click area toggle back
    const areaToggleBtn = screen.getByTestId("toggle-chart-area");
    await user.click(areaToggleBtn);

    // Chart display should update back to 'area'
    expect(screen.getByTestId("chart-display-area")).toBeInTheDocument();
    expect(screen.queryByTestId("chart-display-candles")).not.toBeInTheDocument();
  });

  it("renders live signal badge and toggles MACD subplot", async () => {
    const user = userEvent.setup();
    apiService.fetchOHLCV.mockResolvedValue(mockOHLCVData);
    apiService.fetchSignal.mockResolvedValue({ signal: "BUY" });

    render(<PriceChart symbol="AAPL" />);

    await waitFor(() => {
      expect(screen.getByTestId("price-chart-container")).toBeInTheDocument();
      expect(screen.getByTestId("signal-badge")).toHaveTextContent("Signal: BUY");
    });

    // MACD subplot should NOT be visible by default
    expect(screen.queryByTestId("macd-subplot")).not.toBeInTheDocument();

    // Toggle MACD
    const macdLabel = screen.getByText("MACD");
    await user.click(macdLabel);

    // MACD subplot should now be visible
    expect(screen.getByTestId("macd-subplot")).toBeInTheDocument();
  });
});

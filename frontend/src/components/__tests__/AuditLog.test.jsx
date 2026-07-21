import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AuditLogPage from "../../pages/AuditLogPage";
import * as apiService from "@/services/apiService";

vi.mock("@/services/apiService", () => ({
  fetchAuditLogs: vi.fn(),
}));

const mockAuditLogs = [
  {
    id: "log-1",
    timestamp: "2026-06-15T09:30:00Z",
    symbol: "QUANT",
    action_type: "APPROVE",
    qty: 150,
    price: 151.60,
    status: "SUCCESS",
    user: "trader@kerdostat.com"
  },
  {
    id: "log-2",
    timestamp: "2026-06-14T11:00:00Z",
    symbol: "TSLA",
    action_type: "REJECT",
    qty: 120,
    price: 183.00,
    status: "SUCCESS",
    user: "trader@kerdostat.com"
  },
  {
    id: "log-3",
    timestamp: "2026-06-15T13:45:00Z",
    symbol: "NVDA",
    action_type: "HIJACK_EXECUTE",
    qty: 100,
    price: 125.50,
    status: "SUCCESS",
    user: "trader@kerdostat.com"
  }
];

describe("AuditLogPage Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    globalThis.URL.createObjectURL = vi.fn().mockReturnValue("blob:mock-url");
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  });

  it("renders table with mock audit logs", async () => {
    apiService.fetchAuditLogs.mockResolvedValue(mockAuditLogs);

    render(<AuditLogPage />);

    expect(screen.getByTestId("logs-loading")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("audit-log-page")).toBeInTheDocument();
    });

    const rows = screen.getAllByTestId("log-row");
    expect(rows).toHaveLength(3);
    expect(screen.getAllByText("QUANT").length).toBeGreaterThan(0);
    expect(screen.getAllByText("TSLA").length).toBeGreaterThan(0);
    expect(screen.getAllByText("NVDA").length).toBeGreaterThan(0);
  });

  it("filters logs by symbol correctly", async () => {
    const user = userEvent.setup();
    apiService.fetchAuditLogs.mockResolvedValue(mockAuditLogs);

    render(<AuditLogPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId("log-row")).toHaveLength(3);
    });

    const symbolSelect = screen.getByTestId("filter-symbol");
    await user.selectOptions(symbolSelect, "QUANT");

    await waitFor(() => {
      const rows = screen.getAllByTestId("log-row");
      expect(rows).toHaveLength(1);
      expect(screen.getAllByText("QUANT").length).toBe(2);
      expect(screen.getAllByText("TSLA").length).toBe(1);
    });
  });

  it("filters logs by action type correctly", async () => {
    const user = userEvent.setup();
    apiService.fetchAuditLogs.mockResolvedValue(mockAuditLogs);

    render(<AuditLogPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId("log-row")).toHaveLength(3);
    });

    const actionSelect = screen.getByTestId("filter-action");
    await user.selectOptions(actionSelect, "HIJACK_EXECUTE");

    await waitFor(() => {
      const rows = screen.getAllByTestId("log-row");
      expect(rows).toHaveLength(1);
      expect(screen.getAllByText("NVDA").length).toBe(2);
      expect(screen.getAllByText("QUANT").length).toBe(1);
    });
  });

  it("filters logs by date correctly", async () => {
    const user = userEvent.setup();
    apiService.fetchAuditLogs.mockResolvedValue(mockAuditLogs);

    render(<AuditLogPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId("log-row")).toHaveLength(3);
    });

    const dateInput = screen.getByTestId("filter-date");
    await user.type(dateInput, "2026-06-14");

    await waitFor(() => {
      const rows = screen.getAllByTestId("log-row");
      expect(rows).toHaveLength(1);
      expect(screen.getAllByText("TSLA").length).toBe(2);
    });
  });

  it("exports filtered logs as CSV client-side", async () => {
    const user = userEvent.setup();
    apiService.fetchAuditLogs.mockResolvedValue(mockAuditLogs);

    render(<AuditLogPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId("log-row")).toHaveLength(3);
    });

    // Filter by QUANT first
    const symbolSelect = screen.getByTestId("filter-symbol");
    await user.selectOptions(symbolSelect, "QUANT");

    const exportBtn = screen.getByTestId("export-csv-btn");
    await user.click(exportBtn);

    expect(globalThis.URL.createObjectURL).toHaveBeenCalled();
    expect(HTMLAnchorElement.prototype.click).toHaveBeenCalled();
  });
});

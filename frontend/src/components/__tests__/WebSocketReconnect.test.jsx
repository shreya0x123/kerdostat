import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import useWebSocket from "../../hooks/useWebSocket";

// Test component that renders connection state
function TestComponent() {
  const { connected, latestMessage } = useWebSocket("ws://localhost:8000/ws");
  return (
    <div>
      <div data-testid="status">{connected ? "Connected" : "Disconnected"}</div>
      {latestMessage && <div data-testid="message">{JSON.stringify(latestMessage)}</div>}
    </div>
  );
}

describe("WebSocket Reconnection Logic (TC-07)", () => {
  let mockSocketInstances = [];
  let originalWebSocket;

  beforeEach(() => {
    vi.useFakeTimers();
    mockSocketInstances = [];
    originalWebSocket = globalThis.WebSocket;

    // Mock WebSocket class
    globalThis.WebSocket = class MockWebSocket {
      constructor(url) {
        this.url = url;
        this.readyState = 0; // CONNECTING
        mockSocketInstances.push(this);

        // Simulate successful connection after a brief delay
        setTimeout(() => {
          this.readyState = 1; // OPEN
          if (this.onopen) this.onopen();
        }, 10);
      }
      close() {
        if (this.onclose) {
          this.onclose({ code: 1000 });
        }
      }
      send(data) {}
    };
  });

  afterEach(() => {
    globalThis.WebSocket = originalWebSocket;
    vi.useRealTimers();
  });

  it("should connect initially and then attempt to reconnect on disconnect", async () => {
    render(<TestComponent />);

    // Verify initially disconnected
    expect(screen.getByTestId("status")).toHaveTextContent("Disconnected");

    // Advance timers for initial connection
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20);
    });

    // Verify connected status
    expect(screen.getByTestId("status")).toHaveTextContent("Connected");
    expect(mockSocketInstances).toHaveLength(1);

    // Simulate connection close
    await act(async () => {
      mockSocketInstances[0].onclose({ code: 1006 });
    });

    // Verify disconnected status
    expect(screen.getByTestId("status")).toHaveTextContent("Disconnected");

    // Reconnection is scheduled (exponential backoff: 1000ms initially)
    // Advance time by 500ms -> should not have reconnected yet
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500);
    });
    expect(mockSocketInstances).toHaveLength(1);

    // Advance time to 1000ms -> reconnect attempt starts
    await act(async () => {
      await vi.advanceTimersByTimeAsync(550);
    });
    
    // A second socket should have been instantiated
    expect(mockSocketInstances).toHaveLength(2);

    // Advance time for second connection to succeed
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20);
    });

    // Should be connected again
    expect(screen.getByTestId("status")).toHaveTextContent("Connected");
  });
});

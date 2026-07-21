import "@testing-library/jest-dom";
import React from "react";
import { vi } from "vitest";

// Mock ResponsiveContainer and ResizeObserver since jsdom doesn't support them
class MockResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = MockResizeObserver;

// Mock Recharts responsive container to render its children
vi.mock("recharts", async () => {
  const original = await vi.importActual("recharts");
  return {
    ...original,
    ResponsiveContainer: ({ children }) => 
      React.createElement("div", { style: { width: "100%", height: "100%" } }, children)
  };
});

// Mock BrowserRouter with MemoryRouter dynamically in JSDOM tests
vi.mock("react-router-dom", async () => {
  const original = await vi.importActual("react-router-dom");
  return {
    ...original,
    BrowserRouter: ({ children }) => {
      const [initialPath] = React.useState(() => window.location.pathname);
      return React.createElement(
        original.MemoryRouter,
        { initialEntries: [initialPath] },
        children
      );
    },
  };
});

import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import ProtectedRoute from "../ProtectedRoute";
import { useAuth } from "@/hooks/useAuth";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

describe("ProtectedRoute Component", () => {
  it("renders verifying session loader when loading is true", () => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      loading: true,
    });

    render(
      <MemoryRouter>
        <ProtectedRoute />
      </MemoryRouter>
    );

    expect(screen.getByText("Verifying Session...")).toBeInTheDocument();
  });

  it("renders child route Outlet when authenticated and not loading", () => {
    useAuth.mockReturnValue({
      isAuthenticated: true,
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div>Protected Dashboard Content</div>} />
          </Route>
          <Route path="/auth" element={<div>Auth Gateway Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Protected Dashboard Content")).toBeInTheDocument();
    expect(screen.queryByText("Auth Gateway Page")).not.toBeInTheDocument();
  });

  it("redirects to /auth when unauthenticated and not loading", () => {
    useAuth.mockReturnValue({
      isAuthenticated: false,
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={["/protected"]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/protected" element={<div>Protected Dashboard Content</div>} />
          </Route>
          <Route path="/auth" element={<div>Auth Gateway Page</div>} />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.queryByText("Protected Dashboard Content")).not.toBeInTheDocument();
    expect(screen.getByText("Auth Gateway Page")).toBeInTheDocument();
  });
});

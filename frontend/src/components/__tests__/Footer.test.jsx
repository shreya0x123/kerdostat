import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import Footer from "../Footer";

describe("Footer Component", () => {
  it("renders brand information, columns of links, and copyright notice", () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>
    );

    // Verify footer is rendered
    expect(screen.getByTestId("official-footer")).toBeInTheDocument();

    // Verify brand logo and text
    expect(screen.getByText("KERDOSTAT")).toBeInTheDocument();
    expect(screen.getByText(/Institutional-grade automated execution engine/i)).toBeInTheDocument();

    // Verify main platform links
    expect(screen.getByRole("link", { name: /Dashboard Terminal/i })).toHaveAttribute("href", "/dashboard");
    expect(screen.getByRole("link", { name: /Proposals Feed/i })).toHaveAttribute("href", "/proposals");
    expect(screen.getByRole("link", { name: /Manual Override/i })).toHaveAttribute("href", "/override");
    expect(screen.getByRole("link", { name: /Execution Audits/i })).toHaveAttribute("href", "/audit-log");

    // Verify resources links
    expect(screen.getByRole("link", { name: /Developer API Docs/i })).toHaveAttribute("href", "/docs");
    expect(screen.getByRole("link", { name: /Contact Desk/i })).toHaveAttribute("href", "/contact");

    // Verify compliance indicators
    expect(screen.getByText("Alpaca Sandbox Integration")).toBeInTheDocument();
    expect(screen.getByText("Zero-Key Custody Architecture")).toBeInTheDocument();

    // Verify copyright and legal links
    expect(screen.getByText(/Kerdostat Technologies Inc. All rights reserved./i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Privacy Policy/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Terms of Service/i })).toBeInTheDocument();
  });
});

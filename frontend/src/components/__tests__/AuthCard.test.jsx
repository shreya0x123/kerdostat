import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthCard } from "../AuthCard";
import { BrowserRouter } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

// Mock the useAuth hook
vi.mock("@/hooks/useAuth", () => ({
  useAuth: vi.fn(),
}));

describe("AuthCard Component Form Validation", () => {
  const mockSignIn = vi.fn();
  const mockSignUp = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({
      isAuthenticated: false,
      signIn: mockSignIn,
      signUp: mockSignUp,
    });
  });

  const renderComponent = () => {
    const user = userEvent.setup();
    const result = render(
      <BrowserRouter>
        <AuthCard />
      </BrowserRouter>
    );
    return { ...result, user };
  };

  it("should render sign in panel by default", () => {
    renderComponent();
    expect(screen.getByText("Kerdostat Access")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /create account/i })).toBeInTheDocument();
    
    // Check that sign in inputs exist
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
  });

  it("should show validation errors when signing in with empty inputs", async () => {
    renderComponent();
    
    const signInBtn = screen.getByRole("button", { name: /^sign in$/i });
    fireEvent.click(signInBtn);

    await waitFor(() => {
      expect(screen.getByText("Email is required")).toBeInTheDocument();
      expect(screen.getByText("Password is required")).toBeInTheDocument();
    });
    
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("should validate email format on sign in", async () => {
    renderComponent();
    
    const emailInput = screen.getByLabelText(/^email$/i);
    const passwordInput = screen.getByLabelText(/^password$/i);
    const signInBtn = screen.getByRole("button", { name: /^sign in$/i });

    fireEvent.change(emailInput, { target: { value: "invalidemail" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    
    fireEvent.click(signInBtn);

    await waitFor(() => {
      expect(screen.getByText("Invalid email format")).toBeInTheDocument();
    });
    
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("should validate password length on sign in", async () => {
    renderComponent();
    
    const emailInput = screen.getByLabelText(/^email$/i);
    const passwordInput = screen.getByLabelText(/^password$/i);
    const signInBtn = screen.getByRole("button", { name: /^sign in$/i });

    fireEvent.change(emailInput, { target: { value: "trader@kerdostat.com" } });
    fireEvent.change(passwordInput, { target: { value: "123" } }); // less than 6 chars
    
    fireEvent.click(signInBtn);

    await waitFor(() => {
      expect(screen.getByText("Password must be at least 6 characters")).toBeInTheDocument();
    });
    
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("should show create account tab and validate mismatched passwords", async () => {
    const { user } = renderComponent();
    
    // Click on Create Account tab using user-event
    const registerTab = screen.getByRole("tab", { name: /create account/i });
    await user.click(registerTab);

    // Verify registration inputs exist
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();

    const nameInput = screen.getByLabelText(/full name/i);
    const emailInput = screen.getAllByLabelText(/^email$/i)[0]; // Since register email exists now
    const passwordInput = screen.getAllByLabelText(/^password$/i)[0];
    const confirmInput = screen.getByLabelText(/confirm password/i);
    const registerBtn = screen.getByRole("button", { name: /create account/i });

    // Fill in inputs with mismatched passwords
    fireEvent.change(nameInput, { target: { value: "Jane Doe" } });
    fireEvent.change(emailInput, { target: { value: "jane@kerdostat.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.change(confirmInput, { target: { value: "different_password" } });

    fireEvent.click(registerBtn);

    await waitFor(() => {
      expect(screen.getByText("Passwords do not match")).toBeInTheDocument();
    });
    
    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it("should call signIn on successful login", async () => {
    mockSignIn.mockResolvedValue({ id: "user-1", name: "Alex Mercer" });
    renderComponent();

    const emailInput = screen.getByLabelText(/^email$/i);
    const passwordInput = screen.getByLabelText(/^password$/i);
    const signInBtn = screen.getByRole("button", { name: /^sign in$/i });

    fireEvent.change(emailInput, { target: { value: "trader@kerdostat.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.click(signInBtn);

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("trader@kerdostat.com", "password123");
    });
  });

  it("should render error message on login failure", async () => {
    mockSignIn.mockRejectedValue(new Error("Invalid email or password"));
    renderComponent();

    const emailInput = screen.getByLabelText(/^email$/i);
    const passwordInput = screen.getByLabelText(/^password$/i);
    const signInBtn = screen.getByRole("button", { name: /^sign in$/i });

    fireEvent.change(emailInput, { target: { value: "trader@kerdostat.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.click(signInBtn);

    await waitFor(() => {
      expect(screen.getByText("Invalid email or password")).toBeInTheDocument();
    });
  });

  it("should call signUp on successful registration", async () => {
    const { user } = renderComponent();
    mockSignUp.mockResolvedValue({ id: "user-2", name: "Jane Doe" });

    const registerTab = screen.getByRole("tab", { name: /create account/i });
    await user.click(registerTab);

    const nameInput = screen.getByLabelText(/full name/i);
    const emailInput = screen.getAllByLabelText(/^email$/i)[0];
    const passwordInput = screen.getAllByLabelText(/^password$/i)[0];
    const confirmInput = screen.getByLabelText(/confirm password/i);
    const registerBtn = screen.getByRole("button", { name: /create account/i });

    fireEvent.change(nameInput, { target: { value: "Jane Doe" } });
    fireEvent.change(emailInput, { target: { value: "jane@kerdostat.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.change(confirmInput, { target: { value: "password123" } });
    fireEvent.click(registerBtn);

    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith("Jane Doe", "jane@kerdostat.com", "password123");
    });
  });

  it("should render error message on registration failure", async () => {
    const { user } = renderComponent();
    mockSignUp.mockRejectedValue(new Error("Email already registered"));

    const registerTab = screen.getByRole("tab", { name: /create account/i });
    await user.click(registerTab);

    const nameInput = screen.getByLabelText(/full name/i);
    const emailInput = screen.getAllByLabelText(/^email$/i)[0];
    const passwordInput = screen.getAllByLabelText(/^password$/i)[0];
    const confirmInput = screen.getByLabelText(/confirm password/i);
    const registerBtn = screen.getByRole("button", { name: /create account/i });

    fireEvent.change(nameInput, { target: { value: "Jane Doe" } });
    fireEvent.change(emailInput, { target: { value: "jane@kerdostat.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });
    fireEvent.change(confirmInput, { target: { value: "password123" } });
    fireEvent.click(registerBtn);

    await waitFor(() => {
      expect(screen.getByText("Email already registered")).toBeInTheDocument();
    });
  });
});

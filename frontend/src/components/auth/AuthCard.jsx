/* eslint-disable react-hooks/incompatible-library */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { useAuth } from "@/hooks/useAuth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { AlertCircle, Eye, EyeOff, Loader2 } from "lucide-react";
import Footer from "@/components/Footer";

export function AuthCard() {
  const navigate = useNavigate();
  const { isAuthenticated, signIn, signUp } = useAuth();
  
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // react-hook-form configurations
  const {
    register: registerSignIn,
    handleSubmit: handleSignInSubmit,
    formState: { errors: signInErrors },
    reset: resetSignIn
  } = useForm();

  const {
    register: registerSignUp,
    handleSubmit: handleSignUpSubmit,
    watch: watchSignUp,
    formState: { errors: signUpErrors },
    reset: resetSignUp
  } = useForm();

  // Watch password field to validate match on confirmation
  const registerPassword = watchSignUp("password");

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onSignIn = async (data) => {
    setApiError("");
    setIsSubmitting(true);
    try {
      await signIn(data.email, data.password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setApiError(err.message || "Sign in failed. Verify your credentials.");
      setIsSubmitting(false);
    }
  };

  const onSignUp = async (data) => {
    setApiError("");
    setIsSubmitting(true);
    try {
      await signUp(data.name, data.email, data.password);
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setApiError(err.message || "Registration failed. Try a different email.");
      setIsSubmitting(false);
    }
  };

  const clearErrorsAndReset = () => {
    setApiError("");
    resetSignIn();
    resetSignUp();
  };

  return (
    <div className="min-h-screen bg-background flex flex-col justify-between transition-colors duration-300 relative overflow-hidden selection:bg-primary/20 selection:text-primary">
      {/* Visual background lights */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] rounded-full bg-primary/5 dark:bg-primary/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[60%] h-[60%] rounded-full bg-indigo-500/5 dark:bg-indigo-500/10 blur-[150px] pointer-events-none" />

      {/* Tech Grid Pattern */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(128,128,128,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(128,128,128,0.03)_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,rgba(128,128,128,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(128,128,128,0.05)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none opacity-80 z-0" />

      {/* Card Wrapper */}
      <div className="flex-1 flex items-center justify-center px-4 py-12 z-10 w-full">
        <Card className="w-full max-w-md rounded-2xl border border-border bg-card text-foreground shadow-2xl transition-colors duration-300">
        <CardHeader className="space-y-2 border-b border-border px-8 py-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 border border-primary/30 rounded-xl bg-primary/10 text-primary grid place-items-center text-sm font-bold tracking-[0.15em]">
              K
            </div>
            <div>
              <CardTitle className="text-2xl font-bold tracking-tight text-foreground font-sans">
                Kerdostat Access
              </CardTitle>
              <CardDescription className="text-xs text-muted-foreground font-sans">
                Institutional-grade access to the strategy execution engine.
              </CardDescription>
            </div>
          </div>
        </CardHeader>

        <CardContent className="px-8 pb-8 pt-6">
          {/* API error alert */}
          {apiError && (
            <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 p-3.5 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span className="font-semibold leading-relaxed">{apiError}</span>
            </div>
          )}

          <Tabs defaultValue="sign-in" className="space-y-6" onValueChange={clearErrorsAndReset}>
            <TabsList className="rounded-xl border border-border bg-secondary/40 p-1 w-full grid grid-cols-2">
              <TabsTrigger
                value="sign-in"
                className="rounded-lg px-4 py-2 text-xs font-bold transition-all data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-sm text-muted-foreground"
              >
                Sign In
              </TabsTrigger>
              <TabsTrigger
                value="create-account"
                className="rounded-lg px-4 py-2 text-xs font-bold transition-all data-[state=active]:bg-background data-[state=active]:text-primary data-[state=active]:shadow-sm text-muted-foreground"
              >
                Create Account
              </TabsTrigger>
            </TabsList>

            {/* TAB: Sign In */}
            <TabsContent value="sign-in" className="space-y-5 outline-none">
              <form className="space-y-4" onSubmit={handleSignInSubmit(onSignIn)} noValidate>
                {/* Email */}
                <div className="space-y-1.5">
                  <Label htmlFor="sign-in-email" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Email
                  </Label>
                  <Input
                    id="sign-in-email"
                    type="email"
                    placeholder="trader@kerdostat.com"
                    className={`border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary ${
                      signInErrors.email ? "border-destructive/50 focus-visible:ring-destructive" : ""
                    }`}
                    {...registerSignIn("email", {
                      required: "Email is required",
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: "Invalid email format"
                      }
                    })}
                  />
                  {signInErrors.email && (
                    <span className="text-[10px] font-bold text-destructive block mt-1">
                      {signInErrors.email.message}
                    </span>
                  )}
                </div>

                {/* Password */}
                <div className="space-y-1.5 relative">
                  <Label htmlFor="sign-in-password" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Password
                  </Label>
                  <div className="relative">
                    <Input
                      id="sign-in-password"
                      type={showPassword ? "text" : "password"}
                      placeholder="••••••••••••"
                      className={`border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 pr-10 focus-visible:ring-primary focus-visible:border-primary ${
                        signInErrors.password ? "border-destructive/50 focus-visible:ring-destructive" : ""
                      }`}
                      {...registerSignIn("password", {
                        required: "Password is required",
                        minLength: {
                          value: 6,
                          message: "Password must be at least 6 characters"
                        }
                      })}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {signInErrors.password && (
                    <span className="text-[10px] font-bold text-destructive block mt-1">
                      {signInErrors.password.message}
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-[10px] text-muted-foreground font-mono">
                  <span>SSL encrypted connection</span>
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      alert("Auth endpoints simulate database check. Registered: trader@kerdostat.com / password123");
                    }}
                    className="text-primary hover:text-primary/80 transition-colors font-semibold"
                  >
                    Forgot password?
                  </a>
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded-xl bg-primary px-4 py-3 text-xs font-bold text-primary-foreground transition hover:brightness-105 active:scale-98 shadow-md shadow-primary/10 border-none mt-2"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-1.5">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Checking accounts...
                    </span>
                  ) : (
                    <span>Sign In</span>
                  )}
                </Button>
              </form>
            </TabsContent>

            {/* TAB: Register */}
            <TabsContent value="create-account" className="space-y-5 outline-none">
              <form className="space-y-4" onSubmit={handleSignUpSubmit(onSignUp)} noValidate>
                {/* Full Name */}
                <div className="space-y-1.5">
                  <Label htmlFor="register-name" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Full Name
                  </Label>
                  <Input
                    id="register-name"
                    type="text"
                    placeholder="Alex Mercer"
                    className={`border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary ${
                      signUpErrors.name ? "border-destructive/50 focus-visible:ring-destructive" : ""
                    }`}
                    {...registerSignUp("name", {
                      required: "Name is required",
                      minLength: {
                        value: 2,
                        message: "Name must be at least 2 characters"
                      }
                    })}
                  />
                  {signUpErrors.name && (
                    <span className="text-[10px] font-bold text-destructive block mt-1">
                      {signUpErrors.name.message}
                    </span>
                  )}
                </div>

                {/* Email */}
                <div className="space-y-1.5">
                  <Label htmlFor="register-email" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Email
                  </Label>
                  <Input
                    id="register-email"
                    type="email"
                    placeholder="trader@kerdostat.com"
                    className={`border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary ${
                      signUpErrors.email ? "border-destructive/50 focus-visible:ring-destructive" : ""
                    }`}
                    {...registerSignUp("email", {
                      required: "Email is required",
                      pattern: {
                        value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                        message: "Invalid email format"
                      }
                    })}
                  />
                  {signUpErrors.email && (
                    <span className="text-[10px] font-bold text-destructive block mt-1">
                      {signUpErrors.email.message}
                    </span>
                  )}
                </div>

                {/* Password */}
                <div className="space-y-1.5">
                  <Label htmlFor="register-password" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Password
                  </Label>
                  <Input
                    id="register-password"
                    type="password"
                    placeholder="••••••••••••"
                    className={`border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary ${
                      signUpErrors.password ? "border-destructive/50 focus-visible:ring-destructive" : ""
                    }`}
                    {...registerSignUp("password", {
                      required: "Password is required",
                      minLength: {
                        value: 6,
                        message: "Password must be at least 6 characters"
                      }
                    })}
                  />
                  {signUpErrors.password && (
                    <span className="text-[10px] font-bold text-destructive block mt-1">
                      {signUpErrors.password.message}
                    </span>
                  )}
                </div>

                {/* Confirm Password */}
                <div className="space-y-1.5">
                  <Label htmlFor="register-confirm" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Confirm Password
                  </Label>
                  <Input
                    id="register-confirm"
                    type="password"
                    placeholder="••••••••••••"
                    className={`border-border bg-secondary/30 text-foreground rounded-xl placeholder:text-muted-foreground/30 focus-visible:ring-primary focus-visible:border-primary ${
                      signUpErrors.confirmPassword ? "border-destructive/50 focus-visible:ring-destructive" : ""
                    }`}
                    {...registerSignUp("confirmPassword", {
                      required: "Please confirm your password",
                      validate: (val) => val === registerPassword || "Passwords do not match"
                    })}
                  />
                  {signUpErrors.confirmPassword && (
                    <span className="text-[10px] font-bold text-destructive block mt-1">
                      {signUpErrors.confirmPassword.message}
                    </span>
                  )}
                </div>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full rounded-xl bg-primary px-4 py-3 text-xs font-bold text-primary-foreground transition hover:brightness-105 active:scale-98 shadow-md shadow-primary/10 border-none mt-2"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-1.5">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Generating keypairs...
                    </span>
                  ) : (
                    <span>Create Account</span>
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
        </Card>
      </div>

      <Footer />
    </div>
  );
}

import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "@/hooks/useTheme";
import { AuthProvider } from "@/hooks/useAuth";
import DashboardLayout from "@/components/DashboardLayout";
import ProtectedRoute from "@/components/ProtectedRoute";
import ErrorBoundary from "@/components/ErrorBoundary";

const LandingPage = lazy(() => import("@/pages/LandingPage"));
const DashboardPage = lazy(() => import("@/pages/DashboardPage"));
const ProposalsPage = lazy(() => import("@/pages/ProposalsPage"));
const HijackPage = lazy(() => import("@/pages/HijackPage"));
const AuditLogPage = lazy(() => import("@/pages/AuditLogPage"));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));
const UseCasesPage = lazy(() => import("@/pages/UseCasesPage"));
const ContactPage = lazy(() => import("@/pages/ContactPage"));
const DocsPage = lazy(() => import("@/pages/DocsPage"));
const AuthPage = lazy(() =>
  import("@/components/AuthCard").then((module) => ({ default: module.AuthCard }))
);

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <ErrorBoundary>
            <div className="min-h-screen bg-background text-foreground font-sans selection:bg-primary selection:text-primary-foreground transition-colors duration-300">
              <Suspense
                fallback = {
                  <div className="flex min-h-screen items-center justify-center bg-background text-muted-foreground">
                    <div className="flex flex-col items-center gap-3">
                      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                      <span>Loading session...</span>
                    </div>
                  </div>
                }
              >
                <Routes>
                  {/* Fullscreen pages (no sidebar/topbar) */}
                  <Route path="/" element={<LandingPage />} />
                  <Route path="/auth" element={<AuthPage />} />

                  {/* Dashboard layout routes */}
                  <Route element={<DashboardLayout />}>
                    <Route path="/use-cases/:type" element={<UseCasesPage />} />
                    <Route path="/contact" element={<ContactPage />} />
                    <Route path="/docs" element={<DocsPage />} />
                    
                    {/* Guarded platform routes */}
                    <Route element={<ProtectedRoute />}>
                      <Route path="/dashboard" element={<DashboardPage />} />
                      <Route path="/proposals" element={<ProposalsPage />} />
                      <Route path="/hijack" element={<HijackPage />} />
                      <Route path="/audit-log" element={<AuditLogPage />} />
                    </Route>

                    <Route path="*" element={<NotFoundPage />} />
                  </Route>
                </Routes>
              </Suspense>
            </div>
          </ErrorBoundary>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

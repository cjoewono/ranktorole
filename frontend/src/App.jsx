import { lazy, Suspense, useEffect, useState } from "react";
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ResumeProvider } from "./context/ResumeContext";
import { ContactsProvider } from "./context/ContactsContext";
import ErrorBoundary from "./components/ErrorBoundary";
import NavBar from "./components/NavBar";
import UpgradeModal from "./components/UpgradeModal";

const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const GoogleCallback = lazy(() => import("./pages/GoogleCallback"));
const ForgeSetup = lazy(() => import("./pages/ForgeSetup"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const ResumeBuilder = lazy(() => import("./pages/ResumeBuilder"));
const CareerRecon = lazy(() => import("./pages/CareerRecon"));
const Contacts = lazy(() => import("./pages/Contacts"));
const BillingSuccess = lazy(() => import("./pages/BillingSuccess"));
const BillingCancel = lazy(() => import("./pages/BillingCancel"));

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center text-on-surface-variant font-label text-xs tracking-widest uppercase">
      Loading...
    </div>
  );
}

function AppShell() {
  const { token, user, hydrating } = useAuth();
  const location = useLocation();
  const [fullscreen, setFullscreen] = useState(false);
  const [dailyLimit, setDailyLimit] = useState(null); // { retryAfterSeconds } | null
  const path = location.pathname;

  useEffect(() => {
    const handler = (e) => {
      setDailyLimit({ retryAfterSeconds: e.detail?.retryAfterSeconds ?? null });
    };
    window.addEventListener("daily-limit", handler);
    return () => window.removeEventListener("daily-limit", handler);
  }, []);

  useEffect(() => {
    if (path !== "/resume-builder") setFullscreen(false);
  }, [path]);

  if (hydrating) return <Spinner />;
  if (!token) return <Navigate to="/login" replace />;

  // Profile gate — require profile completion before accessing any page except /profile
  if (
    user &&
    !user.profile_context &&
    path !== "/profile" &&
    path !== "/billing/success" &&
    path !== "/billing/cancel"
  ) {
    return <Navigate to="/profile" replace />;
  }

  // Redirect unknown paths to dashboard
  if (
    path !== "/dashboard" &&
    path !== "/resume-builder" &&
    path !== "/profile" &&
    path !== "/recon" &&
    path !== "/contacts" &&
    path !== "/billing/success" &&
    path !== "/billing/cancel"
  ) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div
      className={`min-h-screen bg-background${fullscreen ? " overflow-hidden" : ""}`}
    >
      <NavBar />
      <div className={path === "/profile" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <ForgeSetup />
        </Suspense>
      </div>
      <div className={path === "/recon" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <CareerRecon />
        </Suspense>
      </div>
      <div className={path === "/dashboard" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <Dashboard />
        </Suspense>
      </div>
      <div className={path === "/resume-builder" ? "" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <ResumeBuilder setFullscreen={setFullscreen} />
        </Suspense>
      </div>
      <div className={path === "/contacts" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <Contacts />
        </Suspense>
      </div>
      <div className={path === "/billing/success" ? "" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <BillingSuccess />
        </Suspense>
      </div>
      <div className={path === "/billing/cancel" ? "" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <BillingCancel />
        </Suspense>
      </div>
      <UpgradeModal
        open={dailyLimit !== null}
        onClose={() => setDailyLimit(null)}
        variant="wait"
        retryAfterSeconds={dailyLimit?.retryAfterSeconds ?? null}
      />
    </div>
  );
}

function DefaultRedirect() {
  const { token, hydrating } = useAuth();
  if (hydrating) return <Spinner />;
  return <Navigate to={token ? "/dashboard" : "/login"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <AuthProvider>
          <ResumeProvider>
            <ContactsProvider>
              <Suspense fallback={<Spinner />}>
                <Routes>
                  <Route path="/" element={<Landing />} />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route
                    path="/auth/google/callback"
                    element={<GoogleCallback />}
                  />
                  <Route path="/profile" element={<AppShell />} />
                  <Route path="/dashboard" element={<AppShell />} />
                  <Route path="/resume-builder" element={<AppShell />} />
                  <Route path="/recon" element={<AppShell />} />
                  <Route path="/contacts" element={<AppShell />} />
                  <Route path="/billing/success" element={<AppShell />} />
                  <Route path="/billing/cancel" element={<AppShell />} />
                  <Route path="*" element={<DefaultRedirect />} />
                </Routes>
              </Suspense>
            </ContactsProvider>
          </ResumeProvider>
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

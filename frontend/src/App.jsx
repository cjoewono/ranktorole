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
import ErrorBoundary from "./components/ErrorBoundary";
import NavBar from "./components/NavBar";

const Landing = lazy(() => import("./pages/Landing"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const ForgeSetup = lazy(() => import("./pages/ForgeSetup"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Contacts = lazy(() => import("./pages/Contacts"));
const ResumeBuilder = lazy(() => import("./pages/ResumeBuilder"));

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
  const path = location.pathname;

  useEffect(() => {
    if (path !== "/resume-builder") setFullscreen(false);
  }, [path]);

  if (hydrating) return <Spinner />;
  if (!token) return <Navigate to="/login" replace />;

  // Profile gate — require profile completion before accessing any page except /profile
  if (user && !user.profile_context && path !== "/profile") {
    return <Navigate to="/profile" replace />;
  }

  // Redirect unknown paths to dashboard
  if (
    path !== "/dashboard" &&
    path !== "/contacts" &&
    path !== "/resume-builder" &&
    path !== "/profile"
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
      <div className={path === "/dashboard" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <Dashboard />
        </Suspense>
      </div>
      <div className={path === "/contacts" ? "pb-20 md:pb-0" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <Contacts />
        </Suspense>
      </div>
      <div className={path === "/resume-builder" ? "" : "hidden"}>
        <Suspense fallback={<Spinner />}>
          <ResumeBuilder setFullscreen={setFullscreen} />
        </Suspense>
      </div>
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
            <Suspense fallback={<Spinner />}>
              <Routes>
                <Route path="/" element={<Landing />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="/profile" element={<AppShell />} />
                <Route path="/dashboard" element={<AppShell />} />
                <Route path="/contacts" element={<AppShell />} />
                <Route path="/resume-builder" element={<AppShell />} />
                <Route path="*" element={<DefaultRedirect />} />
              </Routes>
            </Suspense>
          </ResumeProvider>
        </AuthProvider>
      </ErrorBoundary>
    </BrowserRouter>
  );
}

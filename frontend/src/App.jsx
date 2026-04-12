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
import NavBar from "./components/NavBar";
import ProtectedRoute from "./components/ProtectedRoute";

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
  const { token, hydrating } = useAuth();
  const location = useLocation();
  const [fullscreen, setFullscreen] = useState(false);
  const path = location.pathname;

  useEffect(() => {
    if (path !== "/resume-builder") setFullscreen(false);
  }, [path]);

  if (hydrating) return <Spinner />;
  if (!token) return <Navigate to="/login" replace />;

  // Redirect unknown paths to dashboard
  if (
    path !== "/dashboard" &&
    path !== "/contacts" &&
    path !== "/resume-builder"
  ) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div
      className={`min-h-screen bg-background${fullscreen ? " overflow-hidden" : ""}`}
    >
      <NavBar />
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

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ResumeProvider>
          <Suspense fallback={<Spinner />}>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              <Route element={<ProtectedRoute />}>
                <Route path="/forge-setup" element={<ForgeSetup />} />
                <Route path="*" element={<AppShell />} />
              </Route>
            </Routes>
          </Suspense>
        </ResumeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

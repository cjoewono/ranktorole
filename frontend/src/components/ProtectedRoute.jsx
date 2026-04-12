import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute() {
  const { token, user, hydrating } = useAuth();
  const location = useLocation();

  // Wait for rehydration to complete before making auth decisions
  if (hydrating) return null;

  if (!token) return <Navigate to="/login" replace />;

  // Allow access to forge-setup even without profile_context
  if (location.pathname === "/forge-setup") return <Outlet />;

  // Redirect to forge-setup if profile not completed
  // user may be null during initial refresh — don't redirect until we know
  if (user && !user.profile_context) {
    return <Navigate to="/forge-setup" replace />;
  }

  return <Outlet />;
}

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { useNavigate } from "react-router-dom";
import { loginRequest } from "../api/auth";
import { setAccessToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null);
  const navigate = useNavigate();

  const logout = useCallback(() => {
    setToken(null);
    setAccessToken(null);
    navigate("/login");
  }, [navigate]);

  const login = useCallback(
    async (email, password) => {
      const data = await loginRequest(email, password);
      setToken(data.access);
      setAccessToken(data.access);
      navigate("/dashboard");
    },
    [navigate],
  );

  // Silent rehydration on mount — reads httpOnly refresh cookie server-side
  useEffect(() => {
    fetch("/api/v1/auth/refresh/", {
      method: "POST",
      credentials: "include",
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        setToken(data.access);
        setAccessToken(data.access);
      })
      .catch(() => {
        // No valid session — stay logged out
      });
  }, []);

  useEffect(() => {
    const handler = () => logout();
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, [logout]);

  return (
    <AuthContext.Provider value={{ isAuthenticated: !!token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

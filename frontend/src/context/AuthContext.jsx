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
  const [user, setUser] = useState(null);
  const [hydrating, setHydrating] = useState(true);
  const navigate = useNavigate();

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setAccessToken(null);
    navigate("/login");
  }, [navigate]);

  const login = useCallback(
    async (email, password) => {
      const data = await loginRequest(email, password);
      setToken(data.access);
      setAccessToken(data.access);
      setUser(data.user);
      navigate(data.user?.profile_context ? "/dashboard" : "/profile");
    },
    [navigate],
  );

  const updateUser = useCallback((updatedUser) => {
    setUser(updatedUser);
  }, []);

  const loginWithToken = useCallback((accessToken, userData) => {
    setToken(accessToken);
    setAccessToken(accessToken);
    setUser(userData);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return null;
    try {
      const res = await fetch("/api/v1/auth/profile/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return null;
      const userData = await res.json();
      setUser(userData);
      return userData;
    } catch {
      return null;
    }
  }, [token]);

  // Silent rehydration on mount — reads httpOnly refresh cookie server-side
  // then fetches user profile to get profile_context
  useEffect(() => {
    fetch("/api/v1/auth/refresh/", {
      method: "POST",
      credentials: "include",
    })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => {
        setToken(data.access);
        setAccessToken(data.access);
        return fetch("/api/v1/auth/profile/", {
          headers: { Authorization: `Bearer ${data.access}` },
        });
      })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((userData) => {
        setUser(userData);
      })
      .catch(() => {
        // No valid session — stay logged out
      })
      .finally(() => {
        setHydrating(false);
      });
  }, []);

  useEffect(() => {
    const handler = () => logout();
    window.addEventListener("auth:logout", handler);
    return () => window.removeEventListener("auth:logout", handler);
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        hydrating,
        login,
        loginWithToken,
        logout,
        updateUser,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

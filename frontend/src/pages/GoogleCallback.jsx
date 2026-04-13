import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function GoogleCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code) {
      setError("No authorization code received from Google.");
      return;
    }

    let cancelled = false;

    async function exchangeCode() {
      try {
        const res = await fetch("/api/v1/auth/google/callback/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ code, state }),
        });

        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "Google authentication failed.");
        }

        const data = await res.json();

        if (!cancelled) {
          loginWithToken(data.access, data.user);
          navigate(data.user?.profile_context ? "/dashboard" : "/profile", {
            replace: true,
          });
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      }
    }

    exchangeCode();

    return () => {
      cancelled = true;
    };
  }, [searchParams, navigate, loginWithToken]);

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="bg-surface-container-low p-8 max-w-md w-full mx-4 space-y-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-error inline-block" />
            <span className="font-label text-xs tracking-widest uppercase text-error">
              Authentication Failed
            </span>
          </div>
          <p className="font-body text-sm text-on-surface-variant">{error}</p>
          <button
            onClick={() => navigate("/login", { replace: true })}
            className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md transition-opacity"
          >
            RETURN TO LOGIN
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="flex justify-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse [animation-delay:150ms]" />
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse [animation-delay:300ms]" />
        </div>
        <p className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
          Completing Authentication...
        </p>
      </div>
    </div>
  );
}

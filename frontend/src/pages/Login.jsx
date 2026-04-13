import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen bg-background flex flex-col">
      {/* Dot-grid overlay */}
      <div className="tactical-grid absolute inset-0" />

      {/* Top bar */}
      <div className="relative z-10 flex items-center justify-between px-6 py-3 bg-surface-container-low border-b border-outline-variant">
        <Link
          to="/"
          className="font-headline font-bold text-primary text-sm hover:opacity-80 transition-opacity"
        >
          ▣ RankToRole
        </Link>
        <span className="font-label text-xs tracking-widest text-secondary uppercase">
          AUTH_SERVICE: ACTIVE
        </span>
      </div>

      {/* Center card */}
      <div className="relative z-10 flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-sm bg-surface-container-low p-8 space-y-6">
          {/* Status chip */}
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-secondary inline-block" />
            <span className="font-label text-xs tracking-widest uppercase text-secondary">
              SECURE TERMINAL CONNECTED
            </span>
          </div>

          {/* Headline */}
          <div>
            <h1 className="font-headline font-bold text-5xl uppercase text-on-surface leading-tight">
              COMMANDER
              <br />
              ACCESS
            </h1>
            <p className="font-body text-sm text-on-surface-variant mt-2">
              Initialize biometric bypass or enter tactical credentials below.
            </p>
          </div>

          {error && (
            <div className="bg-error-container text-on-error-container text-sm font-body px-4 py-3">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div className="relative">
              <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                Email
              </label>
              <input
                type="email"
                required
                autoComplete="email"
                placeholder="C-ALPHA@VANGUARD.SYS"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="tactical-input"
              />
            </div>

            {/* Password */}
            <div className="relative">
              <label className="block font-label text-xs tracking-widest uppercase text-on-surface-variant mb-1">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="tactical-input pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface text-xs font-label tracking-widest transition-colors"
                >
                  {showPassword ? "HIDE" : "SHOW"}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md disabled:opacity-50 transition-opacity"
            >
              {loading ? "AUTHENTICATING..." : "SIGN IN ›"}
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-outline-variant" />
            <span className="font-label text-xs tracking-widest text-outline uppercase">
              External Protocols
            </span>
            <div className="flex-1 h-px bg-outline-variant" />
          </div>

          {/* Google SSO */}
          <button
            type="button"
            onClick={async () => {
              try {
                const res = await fetch("/api/v1/auth/google/", {
                  credentials: "include",
                });
                const data = await res.json();
                if (data.auth_url) {
                  window.location.href = data.auth_url;
                }
              } catch (err) {
                console.error("Google SSO redirect failed:", err);
              }
            }}
            className="block w-full bg-surface-container-highest text-on-surface-variant font-label font-semibold tracking-widest uppercase text-xs py-3 text-center rounded-md hover:text-on-surface transition-colors"
          >
            ACCESS VIA GOOGLE SSO
          </button>

          {/* Footer links */}
          <div className="flex items-center justify-between">
            <button
              type="button"
              className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
            >
              FORGOT PROTOCOL?
            </button>
            <Link
              to="/register"
              className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
            >
              ENLIST NEW AGENT
            </Link>
          </div>

          {/* Bottom bar */}
          <div className="flex items-center justify-between pt-2 border-t border-outline-variant">
            <span className="font-label text-xs tracking-widest text-outline uppercase">
              AES-256 VALIDATED
            </span>
            <span className="font-label text-xs tracking-widest text-outline uppercase">
              TIER 1 ENCRYPTION
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerRequest } from "../api/auth";
import { useAuth } from "../context/AuthContext";
import TacticalLabel from "../components/forms/TacticalLabel";

export default function Register() {
  const navigate = useNavigate();
  const { loginWithToken } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await registerRequest(email, password);
      // Clear fields before navigating so Chrome password manager can't capture them
      setEmail("");
      setPassword("");
      loginWithToken(data.access, data.user);
      navigate(data.user?.profile_context ? "/dashboard" : "/profile");
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
              ENLIST NEW
              <br />
              AGENT
            </h1>
            <p className="font-body text-sm text-on-surface-variant mt-2">
              Initialize your operator profile to begin deployment.
            </p>
          </div>

          {error && (
            <div className="bg-error-container text-on-error-container text-sm font-body px-4 py-3">
              {error}
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="space-y-5"
            autoComplete="off"
          >
            {/* Email */}
            <div>
              <TacticalLabel>Email</TacticalLabel>
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
            <div>
              <TacticalLabel>Security Key</TacticalLabel>
              <input
                type="password"
                required
                autoComplete="new-password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="tactical-input"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="mission-gradient w-full text-on-primary font-label font-semibold tracking-widest uppercase text-sm py-3 rounded-md disabled:opacity-50 transition-opacity"
            >
              {loading ? "ENLISTING..." : "CREATE PROFILE ›"}
            </button>
          </form>

          {/* Footer link */}
          <div className="text-center">
            <Link
              to="/login"
              className="font-label text-xs tracking-widest uppercase text-tertiary hover:text-tertiary-fixed transition-colors"
            >
              ALREADY ENLISTED? SIGN IN
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

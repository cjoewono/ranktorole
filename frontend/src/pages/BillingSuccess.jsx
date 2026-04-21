import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const POLL_DELAYS_MS = [1000, 2000, 4000, 8000, 10000];

export default function BillingSuccess() {
  const [params] = useSearchParams();
  const { user, refreshUser } = useAuth();
  const [status, setStatus] = useState("processing"); // processing | confirmed | timeout

  // Diagnostic only — never sent to backend, never used for authorization.
  const sessionId = params.get("session_id") || "";

  useEffect(() => {
    let cancelled = false;
    let timeoutId = null;

    async function poll(attempt) {
      if (cancelled) return;
      const fresh = await refreshUser();
      if (cancelled) return;
      if (fresh?.tier === "pro") {
        setStatus("confirmed");
        return;
      }
      if (attempt >= POLL_DELAYS_MS.length) {
        setStatus("timeout");
        return;
      }
      timeoutId = setTimeout(() => poll(attempt + 1), POLL_DELAYS_MS[attempt]);
    }

    if (user?.tier === "pro") {
      setStatus("confirmed");
    } else {
      poll(0);
    }

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-surface-container-low p-8 rounded-md">
        {status === "processing" && (
          <>
            <h1 className="font-headline font-bold text-2xl uppercase text-on-surface mb-3">
              Activating Pro
            </h1>
            <p className="text-on-surface-variant text-sm mb-6">
              Payment received. Activating your account — this usually takes
              just a moment.
            </p>
            <div className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
              Processing...
            </div>
          </>
        )}

        {status === "confirmed" && (
          <>
            <h1 className="font-headline font-bold text-2xl uppercase text-on-surface mb-3">
              Pro Activated
            </h1>
            <p className="text-on-surface-variant text-sm mb-6">
              You're now on the Pro plan. Unlimited tailoring and refinement
              chat.
            </p>
            <Link
              to="/dashboard"
              className="inline-block mission-gradient text-on-primary font-label font-semibold tracking-widest uppercase text-sm px-6 py-2.5 rounded-md"
            >
              Continue to Dashboard
            </Link>
          </>
        )}

        {status === "timeout" && (
          <>
            <h1 className="font-headline font-bold text-2xl uppercase text-on-surface mb-3">
              Payment Received
            </h1>
            <p className="text-on-surface-variant text-sm mb-6">
              Your payment was successful. Activation is taking a bit longer
              than usual — it will complete automatically. You can refresh in a
              moment, or head back to the dashboard.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 text-sm font-medium text-on-surface bg-surface-container rounded-md"
              >
                Refresh
              </button>
              <Link
                to="/dashboard"
                className="px-4 py-2 text-sm font-medium text-on-primary bg-primary rounded-md"
              >
                Dashboard
              </Link>
            </div>
          </>
        )}

        {sessionId && (
          <p className="mt-6 text-xs text-on-surface-variant/60 font-mono break-all">
            Ref: {sessionId}
          </p>
        )}
      </div>
    </div>
  );
}

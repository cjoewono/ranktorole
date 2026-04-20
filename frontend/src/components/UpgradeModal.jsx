import { useState } from "react";
import { createCheckoutSession } from "../api/billing";

/**
 * Upgrade gate + daily-limit notice.
 *
 * Two variants:
 *   variant="upgrade"  (default) — free-tier limit hit. Shows Stripe
 *                      checkout CTA. PCI scope: no card fields here;
 *                      backend creates a Checkout Session and we
 *                      redirect (SAQ A).
 *   variant="wait"     — pro-tier daily cap hit. No checkout CTA.
 *                      Shows reset time (from retryAfterSeconds) and
 *                      a dismiss button.
 *
 * Props:
 *   open              – boolean
 *   onClose           – () => void
 *   variant           – "upgrade" | "wait" (default: "upgrade")
 *   title             – heading override
 *   description       – body copy override
 *   retryAfterSeconds – number | null (used only by variant="wait")
 */
export default function UpgradeModal({
  open,
  onClose,
  variant = "upgrade",
  title,
  description,
  retryAfterSeconds = null,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const defaultTitle =
    variant === "wait" ? "Daily limit reached" : "Upgrade to Pro";
  const defaultDescription =
    variant === "wait"
      ? "You've reached your daily limit on Pro. Your quota resets automatically."
      : "You've hit the Free plan daily limit. Upgrade to Pro for expanded access — $10/month, cancel anytime.";

  const effectiveTitle = title || defaultTitle;
  const effectiveDescription = description || defaultDescription;

  async function handleUpgrade() {
    setError("");
    setLoading(true);
    try {
      const { url } = await createCheckoutSession();
      if (!url) throw new Error("Checkout URL missing.");
      window.location.assign(url);
    } catch (err) {
      setError(err?.message || "Could not start checkout. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upgrade-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="max-w-md w-full rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2
          id="upgrade-modal-title"
          className="text-xl font-semibold text-gray-900"
        >
          {effectiveTitle}
        </h2>
        <p className="mt-2 text-sm text-gray-600">{effectiveDescription}</p>

        {variant === "wait" && retryAfterSeconds != null && (
          <p className="mt-3 text-sm text-gray-500">
            Resets in {formatDuration(retryAfterSeconds)}.
          </p>
        )}

        {variant === "upgrade" && error && (
          <p className="mt-3 text-sm text-red-600">{error}</p>
        )}

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
          >
            {variant === "wait" ? "Got it" : "Maybe later"}
          </button>
          {variant === "upgrade" && (
            <button
              type="button"
              onClick={handleUpgrade}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Redirecting..." : "Upgrade — $10/month"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function formatDuration(seconds) {
  if (seconds < 60) return "less than a minute";
  if (seconds < 3600) {
    const mins = Math.round(seconds / 60);
    return `${mins} minute${mins === 1 ? "" : "s"}`;
  }
  const hours = Math.round(seconds / 3600);
  return `${hours} hour${hours === 1 ? "" : "s"}`;
}

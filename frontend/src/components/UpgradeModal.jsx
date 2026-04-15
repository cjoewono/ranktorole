import { useState } from "react";
import { createCheckoutSession } from "../api/billing";

/**
 * Upgrade gate — redirects to Stripe Hosted Checkout.
 *
 * PCI scope: no card fields are rendered here. We call our backend, which
 * creates a Checkout Session server-side (SAQ A). We then window.location
 * the user onto Stripe's hosted page.
 *
 * Props:
 *   open        – boolean
 *   onClose     – () => void
 *   title       – heading override (e.g. "Chat limit reached")
 *   description – body copy override
 */
export default function UpgradeModal({
  open,
  onClose,
  title = "Upgrade to Pro",
  description = "You've hit the Free plan daily limit. Upgrade to Pro for expanded access — $10/month, cancel anytime.",
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

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
          {title}
        </h2>
        <p className="mt-2 text-sm text-gray-600">{description}</p>

        <ul className="mt-4 space-y-1 text-sm text-gray-700">
          <li>- Unlimited resume tailoring</li>
          <li>- Unlimited refinement chat</li>
          <li>- Priority AI processing</li>
        </ul>

        {error && (
          <p className="mt-3 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
          >
            Not now
          </button>
          <button
            type="button"
            onClick={handleUpgrade}
            disabled={loading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
          >
            {loading ? "Redirecting..." : "Upgrade for $10/mo"}
          </button>
        </div>

        <p className="mt-4 text-xs text-gray-400">
          Payment handled securely by Stripe. We never see or store your card
          details.
        </p>
      </div>
    </div>
  );
}

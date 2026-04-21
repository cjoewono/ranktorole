import { Link } from "react-router-dom";

export default function BillingCancel() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-surface-container-low p-8 rounded-md">
        <h1 className="font-headline font-bold text-2xl uppercase text-on-surface mb-3">
          Checkout Cancelled
        </h1>
        <p className="text-on-surface-variant text-sm mb-6">
          No charges were made. You can upgrade to Pro any time from the
          dashboard or your profile.
        </p>
        <div className="flex gap-3">
          <Link
            to="/dashboard"
            className="px-4 py-2 text-sm font-medium text-on-primary bg-primary rounded-md"
          >
            Back to Dashboard
          </Link>
          <Link
            to="/profile"
            className="px-4 py-2 text-sm font-medium text-on-surface bg-surface-container rounded-md"
          >
            Profile
          </Link>
        </div>
      </div>
    </div>
  );
}

import { apiFetch } from "./client";

export async function createCheckoutSession() {
  return await apiFetch("/api/v1/billing/checkout/", { method: "POST" });
}

export async function createPortalSession(returnUrl) {
  return await apiFetch("/api/v1/billing/portal/", {
    method: "POST",
    body: JSON.stringify({ return_url: returnUrl }),
  });
}

export async function getBillingStatus() {
  return await apiFetch("/api/v1/billing/status/");
}

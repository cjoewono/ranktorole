import { apiFetch } from "./client";

/**
 * POST /api/v1/recon/brainstorm/
 *
 * Submits the multi-field Recon form. Returns:
 *   { best_match: {...}, also_consider: [...], degraded: boolean }
 *
 * Throws on non-2xx. Caller handles 429 (throttled), 502 (O*NET down),
 * 503 (global ceiling), and 400 (validation error) distinctly.
 */
export async function submitBrainstorm(formPayload) {
  return apiFetch("/api/v1/recon/brainstorm/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(formPayload),
  });
}

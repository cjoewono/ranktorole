import { apiFetch } from "./client";

export async function loginRequest(email, password) {
  return await apiFetch("/api/v1/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function registerRequest(email, username, password) {
  return await apiFetch("/api/v1/auth/register/", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
}

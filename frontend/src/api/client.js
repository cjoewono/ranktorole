const BASE = "";

let _accessToken = null;

export function setAccessToken(token) {
  _accessToken = token;
}

async function refreshTokens() {
  const res = await fetch(`${BASE}/api/v1/auth/refresh/`, {
    method: "POST",
    credentials: "include",
  });

  if (!res.ok) {
    _accessToken = null;
    return null;
  }

  const data = await res.json();
  _accessToken = data.access;
  return data.access;
}

export async function apiFetch(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...options.headers };
  if (_accessToken) headers["Authorization"] = `Bearer ${_accessToken}`;

  let res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    const newAccess = await refreshTokens();
    if (!newAccess) {
      window.dispatchEvent(new CustomEvent("auth:logout"));
      throw new Error("Session expired. Please log in again.");
    }
    headers["Authorization"] = `Bearer ${newAccess}`;
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  }

  return res;
}

const BASE = "";

export class APIError extends Error {
  constructor(message, data, status) {
    super(message);
    this.name = "APIError";
    this.data = data;
    this.status = status;
  }
}

async function handleResponse(res) {
  let data = {};
  try {
    data = await res.json();
  } catch (_) {
    // non-JSON or empty body (e.g. 204 No Content)
  }
  if (!res.ok) {
    let message = data.error || data.detail || "An unexpected error occurred";

    // Friendlier generic message for any 429 not specifically routed
    // by the caller. Callers that WANT to handle 429 specifically
    // should still check err.status === 429 and err.data?.code.
    if (res.status === 429 && !data.code) {
      message = "You've hit a daily limit. Try again later.";
    }

    throw new APIError(message, data, res.status);
  }
  return data;
}

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
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }

  if (_accessToken) {
    headers["Authorization"] = `Bearer ${_accessToken}`;
  }

  let res = await fetch(`${BASE}${path}`, { ...options, headers });

  // Handle transparent token rotation
  if (res.status === 401) {
    const newAccess = await refreshTokens();

    if (!newAccess) {
      window.dispatchEvent(new CustomEvent("auth:logout"));
      throw new Error("Session expired. Please log in again.");
    }

    headers["Authorization"] = `Bearer ${newAccess}`;
    res = await fetch(`${BASE}${path}`, { ...options, headers });
  }

  return handleResponse(res);
}

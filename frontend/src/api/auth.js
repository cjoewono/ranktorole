export async function loginRequest(email, password) {
  const res = await fetch("/api/v1/auth/login/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Login failed");
  return data;
}

export async function registerRequest(email, password) {
  const res = await fetch("/api/v1/auth/register/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json();
  if (!res.ok) {
    const msg =
      data.email?.[0] ||
      data.password?.[0] ||
      data.detail ||
      "Registration failed";
    throw new Error(msg);
  }
  return data;
}

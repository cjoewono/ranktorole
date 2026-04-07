import { apiFetch } from "./client";

export async function listContacts() {
  const res = await apiFetch("/api/v1/contacts/");
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to load contacts");
  return data;
}

export async function createContact(payload) {
  const res = await apiFetch("/api/v1/contacts/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to create contact");
  return data;
}

export async function updateContact(id, payload) {
  const res = await apiFetch(`/api/v1/contacts/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to update contact");
  return data;
}

export async function deleteContact(id) {
  const res = await apiFetch(`/api/v1/contacts/${id}/`, { method: "DELETE" });
  if (!res.ok && res.status !== 204)
    throw new Error("Failed to delete contact");
}

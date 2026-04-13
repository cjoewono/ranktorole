import { apiFetch } from "./client";

export async function listContacts() {
  return await apiFetch("/api/v1/contacts/");
}

export async function createContact(payload) {
  return await apiFetch("/api/v1/contacts/", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateContact(id, payload) {
  return await apiFetch(`/api/v1/contacts/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteContact(id) {
  return await apiFetch(`/api/v1/contacts/${id}/`, { method: "DELETE" });
}

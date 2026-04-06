import { apiFetch } from "./client";

export async function createTranslation(militaryText, jobDescription) {
  const res = await apiFetch("/api/v1/translations/", {
    method: "POST",
    body: JSON.stringify({
      military_text: militaryText,
      job_description: jobDescription,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    const msg =
      data.military_text?.[0] ||
      data.job_description?.[0] ||
      data.detail ||
      "Translation failed";
    throw new Error(msg);
  }
  return data;
}

export async function listTranslations() {
  const res = await apiFetch("/api/v1/translations/");
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Failed to load translations");
  return data;
}

export async function deleteTranslation(id) {
  const res = await apiFetch(`/api/v1/resumes/${id}/`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) throw new Error("Failed to delete");
}

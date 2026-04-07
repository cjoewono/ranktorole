import { apiFetch } from "./client";

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  // Pass Content-Type: undefined so apiFetch's default "application/json" is
  // overridden — browser then sets multipart/form-data with correct boundary.
  const res = await apiFetch("/api/v1/resumes/upload/", {
    method: "POST",
    headers: { "Content-Type": undefined },
    body: formData,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Upload failed");
  return data; // { id, created_at }
}

export async function generateDraft(resumeId, jobDescription) {
  const res = await apiFetch(`/api/v1/resumes/${resumeId}/draft/`, {
    method: "POST",
    body: JSON.stringify({ job_description: jobDescription }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Draft generation failed");
  return data; // { civilian_title, summary, bullets, clarifying_questions }
}

export async function sendChatMessage(resumeId, message, history) {
  const res = await apiFetch(`/api/v1/resumes/${resumeId}/chat/`, {
    method: "POST",
    body: JSON.stringify({ message, history }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Chat request failed");
  return data; // { civilian_title, summary, bullets, assistant_reply }
}

export async function finalizeResume(
  resumeId,
  { civilian_title, summary, bullets },
) {
  const res = await apiFetch(`/api/v1/resumes/${resumeId}/finalize/`, {
    method: "PATCH",
    body: JSON.stringify({ civilian_title, summary, bullets }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Finalize failed");
  return data; // full Resume object
}

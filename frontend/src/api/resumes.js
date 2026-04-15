import { apiFetch } from "./client";

export async function listResumes() {
  return await apiFetch("/api/v1/resumes/");
}

export async function uploadResume(file) {
  const formData = new FormData();
  formData.append("file", file);
  // Pass Content-Type: undefined so apiFetch's default "application/json" is
  // overridden — browser then sets multipart/form-data with correct boundary.
  return await apiFetch("/api/v1/resumes/upload/", {
    method: "POST",
    headers: { "Content-Type": undefined },
    body: formData,
  }); // { id, created_at }
}

export async function generateDraft(
  resumeId,
  jobDescription,
  jobTitle = "",
  company = "",
) {
  return await apiFetch(`/api/v1/resumes/${resumeId}/draft/`, {
    method: "POST",
    body: JSON.stringify({
      job_description: jobDescription,
      ...(jobTitle && { job_title: jobTitle }),
      ...(company && { company }),
    }),
  });
}

export async function sendChatMessage(resumeId, message) {
  return await apiFetch(`/api/v1/resumes/${resumeId}/chat/`, {
    method: "POST",
    body: JSON.stringify({ message }),
  }); // { civilian_title, summary, roles[], assistant_reply }
}

export async function finalizeResume(
  resumeId,
  { civilian_title, summary, roles },
) {
  return await apiFetch(`/api/v1/resumes/${resumeId}/finalize/`, {
    method: "PATCH",
    body: JSON.stringify({ civilian_title, summary, roles }),
  }); // full Resume object
}

export async function getResume(resumeId) {
  return await apiFetch(`/api/v1/resumes/${resumeId}/`, {
    method: "GET",
  }); // full resume object including roles[], chat_history[], ai_initial_draft
}

export async function deleteResume(id) {
  return await apiFetch(`/api/v1/resumes/${id}/`, { method: "DELETE" });
}

import { apiFetch } from "./client";

export async function searchMilitaryCareers(keyword, branch = "all") {
  return apiFetch(
    `/api/v1/onet/military/?keyword=${encodeURIComponent(keyword)}&branch=${encodeURIComponent(branch)}`,
  );
}

export async function getCareerDetail(onetCode) {
  return apiFetch(`/api/v1/onet/career/${encodeURIComponent(onetCode)}/`);
}

import { getFreshToken } from "../auth/keycloak";

export interface Campaign {
  id: string;
  name: string;
  district: string;
  target_beneficiaries: number;
  status: "planned" | "active" | "completed";
  created_by: string;
  created_at: string;
}

export interface Beneficiary {
  id: string;
  campaign_id: string;
  full_name: string;
  age_months: number;
  district: string;
  registered_by: string;
  created_at: string;
}

export interface Vaccination {
  id: string;
  beneficiary_id: string;
  vaccine_name: string;
  dose_number: number;
  administered_by: string;
  administered_at: string;
}

export interface AnalyticsSummary {
  total_campaigns: number;
  total_target_beneficiaries: number;
  total_beneficiaries: number;
  total_vaccinations: number;
  unique_vaccinated_beneficiaries: number;
  coverage_percentage: number;
}

export interface DistrictMetric {
  district: string;
  target_beneficiaries: number;
  registered_beneficiaries: number;
  vaccinated_beneficiaries: number;
  coverage_percentage: number;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getFreshToken();
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getSummary: () => apiFetch<AnalyticsSummary>("/api/v1/analytics/summary"),
  getDistrictMetrics: () =>
    apiFetch<{ districts: DistrictMetric[] }>("/api/v1/metrics/coverage"),

  listCampaigns: () => apiFetch<Campaign[]>("/api/v1/campaigns"),
  createCampaign: (payload: {
    name: string;
    district: string;
    target_beneficiaries: number;
    status?: "planned" | "active" | "completed";
  }) =>
    apiFetch<Campaign>("/api/v1/campaigns", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listBeneficiaries: () => apiFetch<Beneficiary[]>("/api/v1/beneficiaries"),
  createBeneficiary: (payload: {
    campaign_id: string;
    full_name: string;
    age_months: number;
    district: string;
  }) =>
    apiFetch<Beneficiary>("/api/v1/beneficiaries", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listVaccinations: () => apiFetch<Vaccination[]>("/api/v1/vaccinations"),
  logVaccination: (payload: {
    beneficiary_id: string;
    vaccine_name: string;
    dose_number: number;
  }) =>
    apiFetch<Vaccination>("/api/v1/vaccinations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
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

export interface Round {
  round_id: string;
  name: string;
  start_date: string;
  end_date: string;
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

export interface TransitionedChild {
  child_id: string;
  confirmation_method: string | null;
}

export interface RoundTransition {
  from_round: string;
  to_round: string;
  transitioned_count: number;
  remaining_zero_dose_count: number;
  transitioned_children: TransitionedChild[];
}

export interface TransitionsResponse {
  total_children: number;
  total_encounters: number;
  rounds: string[];
  transitions: RoundTransition[];
}

export interface RoundState {
  round_id: string;
  zero_dose: boolean | null;
  confirmation_method: string | null;
}

export interface AuditTrailEntry {
  event_id: string;
  round_id: string;
  recorded_at: string;
  type: string;
  zero_dose_after: boolean | null;
  confirmation_method: string | null;
  state_changed: boolean;
  comment: string | null;
}

export interface ChildTimeline {
  child_id: string;
  current_zero_dose: boolean | null;
  confirmation_method: string | null;
  round_states: Record<string, RoundState>;
  audit_trail: AuditTrailEntry[];
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
  getTransitions: () =>
    apiFetch<TransitionsResponse>("/api/v1/analytics/transitions"),
  getChildTimeline: (childId: string) =>
    apiFetch<ChildTimeline>(`/api/v1/analytics/children/${encodeURIComponent(childId)}/timeline`),

  listRounds: () => apiFetch<Round[]>("/api/v1/rounds"),
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
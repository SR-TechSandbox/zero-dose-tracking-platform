import { FormEvent, useEffect, useState } from "react";
import {
  AnalyticsSummary,
  api,
  Beneficiary,
  Campaign,
  ChildTimeline,
  DistrictMetric,
  Round,
  TransitionsResponse,
  Vaccination,
} from "./api/client";
import { getUsername, hasRole, keycloak } from "./auth/keycloak";

type Tab = "dashboard" | "transitions" | "campaigns" | "tracking";
type EncounterOutcome =
  | "campaign_vax"
  | "external_vax"
  | "still_zero_dose"
  | "not_home";

function formatZeroDoseStatus(val: boolean | null): string {
  if (val === true) return "Zero-Dose";
  if (val === false) return "Vaccinated";
  return "Unknown";
}

export default function App() {
  const isAdmin = hasRole("admin");
  const username = getUsername();
  const roleLabel = isAdmin ? "admin" : "field_worker";

  const [tab, setTab] = useState<Tab>("dashboard");
  const [error, setError] = useState<string | null>(null);

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [metrics, setMetrics] = useState<DistrictMetric[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [transitions, setTransitions] = useState<TransitionsResponse | null>(
    null
  );
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [vaccinations, setVaccinations] = useState<Vaccination[]>([]);

  // Child timeline inspector state
  const [selectedChildId, setSelectedChildId] = useState("");
  const [timeline, setTimeline] = useState<ChildTimeline | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Campaign form state
  const [campName, setCampName] = useState("");
  const [campDistrict, setCampDistrict] = useState("");
  const [campTarget, setCampTarget] = useState("500");

  // Beneficiary form state
  const [benCampaignId, setBenCampaignId] = useState("");
  const [benName, setBenName] = useState("");
  const [benAge, setBenAge] = useState("12");
  const [benDistrict, setBenDistrict] = useState("");

  // Vaccination dose form state (1-3 sequential)
  const [vaxBenId, setVaxBenId] = useState("");
  const [vaxName, setVaxName] = useState("DTP1");
  const [vaxDose, setVaxDose] = useState("1");

  // Field encounter form state
  const [encChildId, setEncChildId] = useState("");
  const [encRoundId, setEncRoundId] = useState("");
  const [encOutcome, setEncOutcome] =
    useState<EncounterOutcome>("campaign_vax");
  const [encComment, setEncComment] = useState("");
  const [encSuccess, setEncSuccess] = useState<string | null>(null);

  async function refreshAll() {
    try {
      setError(null);
      const [s, c, b, v, r, t] = await Promise.all([
        api.getSummary(),
        api.listCampaigns(),
        api.listBeneficiaries(),
        api.listVaccinations(),
        api.listRounds(),
        api.getTransitions(),
      ]);
      setSummary(s);
      setCampaigns(c);
      setBeneficiaries(b);
      setVaccinations(v);
      setRounds(r);
      setTransitions(t);

      if (isAdmin) {
        const m = await api.getDistrictMetrics();
        setMetrics(m.districts);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  async function inspectChild(childId: string) {
    setSelectedChildId(childId);
    if (!childId) {
      setTimeline(null);
      return;
    }
    try {
      setError(null);
      setTimelineLoading(true);
      const tl = await api.getChildTimeline(childId);
      setTimeline(tl);
    } catch (err) {
      setTimeline(null);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setTimelineLoading(false);
    }
  }

  async function handleCreateCampaign(e: FormEvent) {
    e.preventDefault();
    try {
      setError(null);
      await api.createCampaign({
        name: campName,
        district: campDistrict,
        target_beneficiaries: Number(campTarget),
      });
      setCampName("");
      setCampDistrict("");
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleCreateBeneficiary(e: FormEvent) {
    e.preventDefault();
    try {
      setError(null);
      await api.createBeneficiary({
        campaign_id: benCampaignId,
        full_name: benName,
        age_months: Number(benAge),
        district: benDistrict,
      });
      setBenName("");
      setBenDistrict("");
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleLogVaccination(e: FormEvent) {
    e.preventDefault();
    try {
      setError(null);
      await api.logVaccination({
        beneficiary_id: vaxBenId,
        vaccine_name: vaxName,
        dose_number: Number(vaxDose),
      });
      await refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleLogEncounter(e: FormEvent) {
    e.preventDefault();
    try {
      setError(null);
      setEncSuccess(null);

      const outcomeFields =
        encOutcome === "campaign_vax"
          ? { vaccinated_since_last: "yes" as const, vaccinated_elsewhere: false }
          : encOutcome === "external_vax"
          ? { vaccinated_since_last: "yes" as const, vaccinated_elsewhere: true }
          : encOutcome === "still_zero_dose"
          ? { vaccinated_since_last: "no" as const, vaccinated_elsewhere: false }
          : { vaccinated_since_last: null, vaccinated_elsewhere: null };

      const eventId = `evt-${Date.now()}-${Math.random()
        .toString(36)
        .slice(2, 6)}`;

      await api.logEncounter({
        event_id: eventId,
        child_id: encChildId,
        round_id: encRoundId,
        recorded_at: new Date().toISOString(),
        type: "revisit",
        ...outcomeFields,
        comment: encComment.trim() || null,
      });

      setEncComment("");
      setEncSuccess(`Logged encounter for ${encChildId} in ${encRoundId}.`);
      await refreshAll();

      if (selectedChildId === encChildId) {
        await inspectChild(encChildId);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const beneficiaryMap = new Map(beneficiaries.map((b) => [b.id, b]));

  const maxCompletedDose = vaccinations
    .filter((v) => v.beneficiary_id === vaxBenId && v.vaccine_name === vaxName)
    .reduce((max, v) => Math.max(max, v.dose_number), 0);

  const isSeriesComplete = Boolean(vaxBenId) && maxCompletedDose >= 3;
  const nextDose = Math.min(maxCompletedDose + 1, 3);

  return (
    <>
      <header className="topbar">
        <h1>Zero-Dose Tracking Platform</h1>
        <div className="topbar-right">
          <span>{username}</span>
          <span className="badge">{roleLabel}</span>
          <button
            className="secondary"
            onClick={() =>
              keycloak.logout({ redirectUri: window.location.origin })
            }
          >
            Logout
          </button>
        </div>
      </header>

      <main className="container">
        <div className="tabs">
          <button
            className={`tab ${tab === "dashboard" ? "active" : ""}`}
            onClick={() => setTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`tab ${tab === "transitions" ? "active" : ""}`}
            onClick={() => setTab("transitions")}
          >
            Round Transitions ({rounds.length})
          </button>
          <button
            className={`tab ${tab === "campaigns" ? "active" : ""}`}
            onClick={() => setTab("campaigns")}
          >
            Campaigns ({campaigns.length})
          </button>
          <button
            className={`tab ${tab === "tracking" ? "active" : ""}`}
            onClick={() => setTab("tracking")}
          >
            Field Tracking ({beneficiaries.length})
          </button>
        </div>

        {error && <div className="error">{error}</div>}

        {tab === "dashboard" && (
          <>
            <div className="grid">
              <div className="card">
                <div className="kpi-label">Active Campaigns</div>
                <div className="kpi-value">{summary?.total_campaigns ?? 0}</div>
              </div>
              <div className="card">
                <div className="kpi-label">Registered Beneficiaries</div>
                <div className="kpi-value">
                  {summary?.total_beneficiaries ?? 0}
                </div>
              </div>
              <div className="card">
                <div className="kpi-label">Doses Administered</div>
                <div className="kpi-value">
                  {summary?.total_vaccinations ?? 0}
                </div>
              </div>
              <div className="card">
                <div className="kpi-label">Coverage</div>
                <div className="kpi-value">
                  {summary?.coverage_percentage ?? 0}%
                </div>
              </div>
            </div>

            {transitions && transitions.transitions.length > 0 && (
              <div className="card">
                <h3>Zero-Dose Children Reached Between Rounds</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Transition</th>
                      <th>Zero-Dose Reached</th>
                      <th>Remaining Zero-Dose</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transitions.transitions.map((tr) => (
                      <tr key={`${tr.from_round}-${tr.to_round}`}>
                        <td>
                          <strong>
                            {tr.from_round} → {tr.to_round}
                          </strong>
                        </td>
                        <td>{tr.transitioned_count}</td>
                        <td>{tr.remaining_zero_dose_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {isAdmin && (
              <div className="card">
                <h3>District Coverage Breakdown (Admin Only)</h3>
                <table>
                  <thead>
                    <tr>
                      <th>District</th>
                      <th>Target</th>
                      <th>Registered</th>
                      <th>Vaccinated</th>
                      <th>Coverage %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((m) => (
                      <tr key={m.district}>
                        <td>{m.district}</td>
                        <td>{m.target_beneficiaries}</td>
                        <td>{m.registered_beneficiaries}</td>
                        <td>{m.vaccinated_beneficiaries}</td>
                        <td>{m.coverage_percentage}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {tab === "transitions" && (
          <>
            <div className="grid">
              <div className="card">
                <div className="kpi-label">Rounds Tracked</div>
                <div className="kpi-value">
                  {transitions?.rounds.join(" → ") || "—"}
                </div>
              </div>
              <div className="card">
                <div className="kpi-label">Children with Encounters</div>
                <div className="kpi-value">
                  {transitions?.total_children ?? 0}
                </div>
              </div>
              <div className="card">
                <div className="kpi-label">Total Field Encounters</div>
                <div className="kpi-value">
                  {transitions?.total_encounters ?? 0}
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
                </div>
              </div>
            </div>

            <div className="card">
              <h3>Round-to-Round Zero-Dose Progression</h3>
              <table>
                <thead>
                  <tr>
                    <th>Transition</th>
                    <th>Zero-Dose Reached</th>
                    <th>Remaining Zero-Dose</th>
                    <th>Children Reached (Click to Inspect)</th>
                  </tr>
                </thead>
                <tbody>
                  {transitions?.transitions.map((tr) => (
                    <tr key={`${tr.from_round}-${tr.to_round}`}>
                      <td>
                        <strong>
                          {tr.from_round} → {tr.to_round}
                        </strong>
                      </td>
                      <td>{tr.transitioned_count}</td>
                      <td>{tr.remaining_zero_dose_count}</td>
                      <td>
                        <div className="form-row">
                          {tr.transitioned_children.map((ch) => (
                            <button
                              key={ch.child_id}
                              type="button"
                              className="tab"
                              onClick={() => void inspectChild(ch.child_id)}
                            >
                              {ch.child_id}
                              {ch.confirmation_method ===
                              "External (Vaccinated Elsewhere)"
                                ? " (External)"
                                : ""}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card">
              <h3>Child Multi-Round Timeline Inspector</h3>
              <div className="form-row" style={{ marginBottom: "1rem" }}>
                <select
                  value={selectedChildId}
                  onChange={(e) => void inspectChild(e.target.value)}
                >
                  <option value="">Select a child to inspect timeline...</option>
                  {beneficiaries.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.id} — {b.full_name} ({b.district})
                    </option>
                  ))}
                </select>
              </div>

              {timelineLoading && <p>Loading child timeline...</p>}

              {timeline && !timelineLoading && (
                <>
                  <p>
                    <strong>Child:</strong> {timeline.child_id}
                    {beneficiaryMap.get(timeline.child_id)
                      ? ` (${beneficiaryMap.get(timeline.child_id)?.full_name}, ${
                          beneficiaryMap.get(timeline.child_id)?.district
                        })`
                      : ""}{" "}
                    | <strong>Current Status:</strong>{" "}
                    {formatZeroDoseStatus(timeline.current_zero_dose)}
                    {timeline.confirmation_method
                      ? ` — ${timeline.confirmation_method}`
                      : ""}
                  </p>

                  <h4>Status by Round</h4>
                  <table style={{ marginBottom: "1rem" }}>
                    <thead>
                      <tr>
                        <th>Round</th>
                        <th>End-of-Round Status</th>
                        <th>Confirmation Method</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.values(timeline.round_states).map((rs) => (
                        <tr key={rs.round_id}>
                          <td>{rs.round_id}</td>
                          <td>{formatZeroDoseStatus(rs.zero_dose)}</td>
                          <td>{rs.confirmation_method ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <h4>Encounter Audit Trail ({timeline.audit_trail.length})</h4>
                  <table>
                    <thead>
                      <tr>
                        <th>Round</th>
                        <th>Recorded At</th>
                        <th>Type</th>
                        <th>Status After</th>
                        <th>Confirmation</th>
                        <th>Comment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {timeline.audit_trail.map((ev) => (
                        <tr key={ev.event_id}>
                          <td>{ev.round_id}</td>
                          <td>{new Date(ev.recorded_at).toLocaleString()}</td>
                          <td>{ev.type}</td>
                          <td>{formatZeroDoseStatus(ev.zero_dose_after)}</td>
                          <td>{ev.confirmation_method ?? "—"}</td>
                          <td>{ev.comment ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </>
              )}
            </div>
          </>
        )}

        {tab === "campaigns" && (
          <>
            {isAdmin && (
              <div className="card">
                <h3>Create Campaign (Admin Only)</h3>
                <form className="form-row" onSubmit={handleCreateCampaign}>
                  <input
                    placeholder="Campaign name"
                    value={campName}
                    onChange={(e) => setCampName(e.target.value)}
                    required
                  />
                  <input
                    placeholder="District"
                    value={campDistrict}
                    onChange={(e) => setCampDistrict(e.target.value)}
                    required
                  />
                  <input
                    type="number"
                    min={0}
                    placeholder="Target"
                    value={campTarget}
                    onChange={(e) => setCampTarget(e.target.value)}
                    required
                  />
                  <button type="submit">Create</button>
                </form>
              </div>
            )}

            <div className="card">
              <h3>All Campaigns</h3>
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>District</th>
                    <th>Target</th>
                    <th>Status</th>
                    <th>Created By</th>
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((c) => (
                    <tr key={c.id}>
                      <td>{c.name}</td>
                      <td>{c.district}</td>
                      <td>{c.target_beneficiaries}</td>
                      <td>{c.status}</td>
                      <td>{c.created_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {tab === "tracking" && (
          <>
            <div className="card">
              <h3>Log Field Encounter (Multi-Round Visit)</h3>
              <form className="form-row" onSubmit={handleLogEncounter}>
                <select
                  value={encChildId}
                  onChange={(e) => setEncChildId(e.target.value)}
                  required
                >
                  <option value="">Select child...</option>
                  {beneficiaries.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.id} — {b.full_name} ({b.district})
                    </option>
                  ))}
                </select>

                <select
                  value={encRoundId}
                  onChange={(e) => setEncRoundId(e.target.value)}
                  required
                >
                  <option value="">Select round...</option>
                  {rounds.map((r) => (
                    <option key={r.round_id} value={r.round_id}>
                      {r.round_id} ({r.name})
                    </option>
                  ))}
                </select>

                <select
                  value={encOutcome}
                  onChange={(e) =>
                    setEncOutcome(e.target.value as EncounterOutcome)
                  }
                  required
                >
                  <option value="campaign_vax">Vaccinated (Campaign)</option>
                  <option value="external_vax">
                    Vaccinated Elsewhere (External)
                  </option>
                  <option value="still_zero_dose">
                    Not Vaccinated (Still Zero-Dose / Correction)
                  </option>
                  <option value="not_home">
                    Child Unavailable / Not Home (No Status Change)
                  </option>
                </select>

                <input
                  placeholder="Field note (optional)"
                  value={encComment}
                  onChange={(e) => setEncComment(e.target.value)}
                />

                <button type="submit">Log Encounter</button>
              </form>
              {encSuccess && (
                <p style={{ color: "#15803d", marginTop: "0.75rem" }}>
                  {encSuccess}
                </p>
              )}
            </div>

            <div className="card">
              <h3>Register Zero-Dose Beneficiary</h3>
              <form className="form-row" onSubmit={handleCreateBeneficiary}>
                <select
                  value={benCampaignId}
                  onChange={(e) => setBenCampaignId(e.target.value)}
                  required
                >
                  <option value="">Select campaign...</option>
                  {campaigns.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} ({c.district})
                    </option>
                  ))}
                </select>
                <input
                  placeholder="Full name"
                  value={benName}
                  onChange={(e) => setBenName(e.target.value)}
                  required
                />
                <input
                  type="number"
                  min={0}
                  max={240}
                  placeholder="Age (months)"
                  value={benAge}
                  onChange={(e) => setBenAge(e.target.value)}
                  required
                />
                <input
                  placeholder="District"
                  value={benDistrict}
                  onChange={(e) => setBenDistrict(e.target.value)}
                  required
                />
                <button type="submit">Register</button>
              </form>
            </div>

            <div className="card">
              <h3>Log Vaccination Dose</h3>
              <form className="form-row" onSubmit={handleLogVaccination}>
                <select
                  value={vaxBenId}
                  onChange={(e) => {
                    const benId = e.target.value;
                    setVaxBenId(benId);
                    const currentMax = vaccinations
                      .filter(
                        (v) =>
                          v.beneficiary_id === benId &&
                          v.vaccine_name === vaxName
                      )
                      .reduce((max, v) => Math.max(max, v.dose_number), 0);
                    setVaxDose(String(Math.min(currentMax + 1, 3)));
                  }}
                  required
                >
                  <option value="">Select beneficiary...</option>
                  {beneficiaries.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.full_name} ({b.district})
                    </option>
                  ))}
                </select>
                <input
                  placeholder="Vaccine (e.g. DTP1)"
                  value={vaxName}
                  onChange={(e) => {
                    const nextVax = e.target.value;
                    setVaxName(nextVax);
                    const currentMax = vaccinations
                      .filter(
                        (v) =>
                          v.beneficiary_id === vaxBenId &&
                          v.vaccine_name === nextVax
                      )
                      .reduce((max, v) => Math.max(max, v.dose_number), 0);
                    setVaxDose(String(Math.min(currentMax + 1, 3)));
                  }}
                  required
                />
                <select
                  value={vaxDose}
                  onChange={(e) => setVaxDose(e.target.value)}
                  disabled={isSeriesComplete}
                  required
                >
                  {[1, 2, 3].map((d) => (
                    <option
                      key={d}
                      value={String(d)}
                      disabled={Boolean(vaxBenId) && d !== nextDose}
                    >
                      Dose {d}{" "}
                      {Boolean(vaxBenId) && d <= maxCompletedDose
                        ? "(Completed)"
                        : ""}
                    </option>
                  ))}
                </select>
                <button type="submit" disabled={isSeriesComplete}>
                  {isSeriesComplete
                    ? "All 3 Doses Complete"
                    : `Log Dose ${nextDose}`}
                </button>
              </form>
            </div>

            <div className="card">
              <h3>Recent Vaccinations ({vaccinations.length})</h3>
              <table>
                <thead>
                  <tr>
                    <th>Beneficiary ID</th>
                    <th>Vaccine</th>
                    <th>Dose</th>
                    <th>Administered By</th>
                  </tr>
                </thead>
                <tbody>
                  {vaccinations.map((v) => (
                    <tr key={v.id}>
                      <td>{v.beneficiary_id.slice(0, 8)}...</td>
                      <td>{v.vaccine_name}</td>
                      <td>{v.dose_number}</td>
                      <td>{v.administered_by}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>
    </>
  );
}
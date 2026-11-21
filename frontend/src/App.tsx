import { FormEvent, useEffect, useState } from "react";
import {
  AnalyticsSummary,
  api,
  Beneficiary,
  Campaign,
  DistrictMetric,
  Vaccination,
} from "./api/client";
import { getUsername, hasRole, keycloak } from "./auth/keycloak";

type Tab = "dashboard" | "campaigns" | "tracking";

export default function App() {
  const isAdmin = hasRole("admin");
  const username = getUsername();
  const roleLabel = isAdmin ? "admin" : "field_worker";

  const [tab, setTab] = useState<Tab>("dashboard");
  const [error, setError] = useState<string | null>(null);

  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [metrics, setMetrics] = useState<DistrictMetric[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>([]);
  const [vaccinations, setVaccinations] = useState<Vaccination[]>([]);

  // Form states
  const [campName, setCampName] = useState("");
  const [campDistrict, setCampDistrict] = useState("");
  const [campTarget, setCampTarget] = useState("500");

  const [benCampaignId, setBenCampaignId] = useState("");
  const [benName, setBenName] = useState("");
  const [benAge, setBenAge] = useState("12");
  const [benDistrict, setBenDistrict] = useState("");

  const [vaxBenId, setVaxBenId] = useState("");
  const [vaxName, setVaxName] = useState("DTP1");
  const [vaxDose, setVaxDose] = useState("1");

  async function refreshAll() {
    try {
      setError(null);
      const [s, c, b, v] = await Promise.all([
        api.getSummary(),
        api.listCampaigns(),
        api.listBeneficiaries(),
        api.listVaccinations(),
      ]);
      setSummary(s);
      setCampaigns(c);
      setBeneficiaries(b);
      setVaccinations(v);

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

  return (
    <>
      <header className="topbar">
        <h1>Zero-Dose Tracking Platform</h1>
        <div className="topbar-right">
          <span>{username}</span>
          <span className="badge">{roleLabel}</span>
          <button
            className="secondary"
            onClick={() => keycloak.logout({ redirectUri: window.location.origin })}
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
                <div className="kpi-value">{summary?.total_beneficiaries ?? 0}</div>
              </div>
              <div className="card">
                <div className="kpi-label">Doses Administered</div>
                <div className="kpi-value">{summary?.total_vaccinations ?? 0}</div>
              </div>
              <div className="card">
                <div className="kpi-label">Coverage</div>
                <div className="kpi-value">
                  {summary?.coverage_percentage ?? 0}%
                </div>
              </div>
            </div>

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
                  onChange={(e) => setVaxBenId(e.target.value)}
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
                  onChange={(e) => setVaxName(e.target.value)}
                  required
                />
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={vaxDose}
                  onChange={(e) => setVaxDose(e.target.value)}
                  required
                />
                <button type="submit">Log Dose</button>
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
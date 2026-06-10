import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Criteria, type JobDetail } from "../api/client";

type Editable = Omit<Criteria, "id" | "job_id">;

const EMPTY: Editable = {
  required_skills: [],
  preferred_skills: [],
  min_years: 0,
  must_haves: [],
  weights: { required_skills: 0.5, preferred_skills: 0.2, min_years: 0.15, must_haves: 0.15 },
};

const toText = (a: string[]) => a.join(", ");
const fromText = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function JobSetup() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const nav = useNavigate();

  const [job, setJob] = useState<JobDetail | null>(null);
  const [jd, setJd] = useState("");
  const [crit, setCrit] = useState<Editable>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    void (async () => {
      const j = await api.getJob(id);
      setJob(j);
      setJd(j.jd_text);
      if (j.criteria) {
        const { id: _i, job_id: _j, ...rest } = j.criteria;
        setCrit(rest);
      }
    })();
  }, [id]);

  async function extract() {
    setError(""); setInfo(""); setBusy(true);
    try {
      const c = await api.extractCriteria(id, jd);
      const { id: _i, job_id: _j, ...rest } = c;
      setCrit(rest);
      setInfo("Criteria extracted by AI — review and edit, then confirm.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setError(""); setInfo(""); setBusy(true);
    try {
      await api.updateCriteria(id, crit);
      nav(`/jobs/${id}/candidates`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!job) return <p className="muted">Loading…</p>;

  return (
    <div>
      <h2>{job.title} — Setup</h2>

      <div className="card">
        <label>Job description</label>
        <textarea value={jd} onChange={(e) => setJd(e.target.value)} />
        <div style={{ marginTop: 12 }} className="row">
          <button onClick={extract} disabled={busy || !jd.trim()}>
            {busy ? "Extracting…" : "✨ Extract criteria with AI"}
          </button>
          <span className="muted">Claude reads the JD and proposes screening criteria.</span>
        </div>
      </div>

      {info && <p style={{ color: "var(--good)" }}>{info}</p>}
      {error && <p className="error">{error}</p>}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Scoring criteria <span className="muted" style={{ fontSize: 13 }}>(editable)</span></h3>
        <label>Required skills (comma-separated)</label>
        <input value={toText(crit.required_skills)} onChange={(e) => setCrit({ ...crit, required_skills: fromText(e.target.value) })} />
        <label>Preferred skills</label>
        <input value={toText(crit.preferred_skills)} onChange={(e) => setCrit({ ...crit, preferred_skills: fromText(e.target.value) })} />
        <label>Must-have qualifications</label>
        <input value={toText(crit.must_haves)} onChange={(e) => setCrit({ ...crit, must_haves: fromText(e.target.value) })} />
        <label>Minimum years of experience</label>
        <input type="number" min={0} value={crit.min_years}
          onChange={(e) => setCrit({ ...crit, min_years: Number(e.target.value) })}
          style={{ width: 120 }} />
        <div style={{ marginTop: 16 }} className="row">
          <button onClick={confirm} disabled={busy}>Confirm criteria &amp; start screening →</button>
          <span className="muted">Saving marks the job ready to accept CVs.</span>
        </div>
      </div>
    </div>
  );
}

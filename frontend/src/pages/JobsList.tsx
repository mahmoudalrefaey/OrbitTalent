import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, type Job } from "../api/client";

export default function JobsList() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [title, setTitle] = useState("");
  const [jd, setJd] = useState("");
  const [error, setError] = useState("");
  const [llmEnabled, setLlmEnabled] = useState(true);
  const nav = useNavigate();

  async function load() {
    try {
      setJobs(await api.listJobs());
      const h = await api.health();
      setLlmEnabled(h.llm_enabled);
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => { void load(); }, []);

  async function create() {
    if (!title.trim()) return;
    try {
      const job = await api.createJob(title, jd);
      nav(`/jobs/${job.id}/setup`);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div>
      <h2>Job Postings</h2>
      {!llmEnabled && (
        <div className="card" style={{ borderColor: "var(--warn)" }}>
          <strong>AI scoring is disabled.</strong>{" "}
          <span className="muted">
            Set <code>ANTHROPIC_API_KEY</code> in the backend to enable JD criteria
            extraction and deep scoring. ATS-readiness and keyword matching still work.
          </span>
        </div>
      )}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>New job</h3>
        <label>Title</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Senior Backend Engineer" />
        <label>Job description (optional — paste now or later)</label>
        <textarea value={jd} onChange={(e) => setJd(e.target.value)} placeholder="Paste the full job description…" />
        <div style={{ marginTop: 12 }}>
          <button onClick={create} disabled={!title.trim()}>Create job</button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      {jobs.length === 0 ? (
        <div className="empty">No jobs yet. Create one above to start screening CVs.</div>
      ) : (
        <table>
          <thead>
            <tr><th>Title</th><th>Status</th><th>Candidates</th><th>Created</th></tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} style={{ cursor: "pointer" }} onClick={() => nav(`/jobs/${j.id}/candidates`)}>
                <td><Link to={`/jobs/${j.id}/setup`}>{j.title}</Link></td>
                <td>{j.status}</td>
                <td>{j.candidate_count}</td>
                <td className="muted">{new Date(j.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

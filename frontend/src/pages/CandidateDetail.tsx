import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type CandidateDetail as CD } from "../api/client";
import { KeywordChips, Meter, ScoreBadge, StageSelect, StatusTag } from "../components/common";

export default function CandidateDetail() {
  const { jobId, candidateId } = useParams();
  const [c, setC] = useState<CD | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      setC(await api.getCandidate(Number(candidateId)));
    } catch (e) {
      setError(String(e));
    }
  }
  useEffect(() => { void load(); }, [candidateId]);

  if (error) return <p className="error">{error}</p>;
  if (!c) return <p className="muted">Loading…</p>;

  return (
    <div>
      <Link to={`/jobs/${jobId}/candidates`}>← Back to candidates</Link>
      <div className="spread" style={{ marginTop: 12 }}>
        <h2 style={{ margin: 0 }}>{c.filename}</h2>
        <StageSelect value={c.stage} onChange={async (s) => {
          const updated = await api.updateStage(c.id, s);
          setC({ ...c, stage: updated.stage });
        }} />
      </div>
      <p><StatusTag status={c.score_status} /></p>
      {c.error && <p className="error">Error: {c.error}</p>}

      <div className="grid-2">
        <div className="card">
          <div className="muted">Overall score</div>
          <div className="score-big"><ScoreBadge score={c.overall_score} /></div>
          <div style={{ marginTop: 16 }}>
            <Meter value={c.job_match_pct} label="Job match (fit for this role)" />
          </div>
          <div style={{ marginTop: 12 }}>
            <Meter value={c.ats_score} label="ATS readiness (CV parse-ability)" />
          </div>
        </div>

        <div className="card">
          <div className="muted">AI reasoning</div>
          <p>{c.reasoning || <span className="muted">No reasoning available.</span>}</p>
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Matched keywords</h3>
          <KeywordChips items={c.matched_keywords} kind="good" />
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Missing keywords</h3>
          <KeywordChips items={c.missing_keywords} kind="bad" />
        </div>
      </div>

      {c.ats_issues.length > 0 && (
        <div className="card" style={{ borderColor: "var(--warn)" }}>
          <h3 style={{ marginTop: 0 }}>ATS issues</h3>
          <ul>{c.ats_issues.map((i) => <li key={i} className="muted">{i}</li>)}</ul>
        </div>
      )}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Extracted CV text</h3>
        <pre style={{ whiteSpace: "pre-wrap", color: "var(--muted)", fontSize: 13, maxHeight: 360, overflow: "auto" }}>
          {c.parsed_text || "(no text extracted)"}
        </pre>
      </div>
    </div>
  );
}

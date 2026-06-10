import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, type Candidate } from "../api/client";
import { Meter, ScoreBadge, StageSelect, StatusTag } from "../components/common";

export default function CandidatesDashboard() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const nav = useNavigate();

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [stageFilter, setStageFilter] = useState<string>("all");
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      setCandidates(await api.listCandidates(id));
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => { void load(); }, [id]);

  // Poll while any candidate is still being processed.
  useEffect(() => {
    const anyProcessing = candidates.some(
      (c) => c.score_status === "pending" || c.score_status === "processing"
    );
    if (!anyProcessing) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [candidates, id]);

  async function onUpload(files: FileList | null) {
    if (!files || !files.length) return;
    setUploading(true); setError("");
    try {
      await api.uploadCandidates(id, files);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function setStage(c: Candidate, stage: Candidate["stage"]) {
    const updated = await api.updateStage(c.id, stage);
    setCandidates((cs) => cs.map((x) => (x.id === c.id ? updated : x)));
  }

  const shown = candidates.filter((c) => stageFilter === "all" || c.stage === stageFilter);

  return (
    <div>
      <div className="spread">
        <h2>Candidates</h2>
        <div className="row">
          <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value)} style={{ width: "auto" }}>
            <option value="all">All stages</option>
            <option value="new">New</option>
            <option value="shortlisted">Shortlisted</option>
            <option value="interview">Interview</option>
            <option value="rejected">Rejected</option>
          </select>
          <button className="secondary" onClick={() => nav(`/jobs/${id}/analytics`)}>Analytics</button>
        </div>
      </div>

      <div className="card">
        <label>Upload CVs (PDF, DOCX, TXT — select multiple)</label>
        <input ref={fileRef} type="file" multiple accept=".pdf,.docx,.txt"
          onChange={(e) => onUpload(e.target.files)} disabled={uploading} />
        {uploading && <p className="muted">Uploading &amp; queuing for scoring…</p>}
      </div>

      {error && <p className="error">{error}</p>}

      {shown.length === 0 ? (
        <div className="empty">No candidates yet. Upload CVs above.</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>#</th><th>Candidate</th><th>Overall</th><th style={{ width: 160 }}>Job match</th>
              <th style={{ width: 160 }}>ATS</th><th>Status</th><th>Stage</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((c, i) => (
              <tr key={c.id} style={{ cursor: "pointer" }}
                  onClick={() => nav(`/jobs/${id}/candidates/${c.id}`)}>
                <td className="muted">{i + 1}</td>
                <td>{c.filename}</td>
                <td><ScoreBadge score={c.overall_score} /></td>
                <td><Meter value={c.job_match_pct} label="" /></td>
                <td><Meter value={c.ats_score} label="" /></td>
                <td><StatusTag status={c.score_status} /></td>
                <td><StageSelect value={c.stage} onChange={(s) => setStage(c, s)} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

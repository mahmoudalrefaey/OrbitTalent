import type { CandidateStage, ScoreStatus } from "../api/client";

export function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span className="muted">—</span>;
  const color = score >= 7 ? "var(--good)" : score >= 4 ? "var(--warn)" : "var(--bad)";
  return (
    <span className="badge" style={{ background: color, color: "#0f1419" }}>
      {score.toFixed(1)}/10
    </span>
  );
}

export function Meter({ value, label }: { value: number | null; label: string }) {
  const v = value ?? 0;
  const color = v >= 70 ? "var(--good)" : v >= 40 ? "var(--warn)" : "var(--bad)";
  return (
    <div>
      <div className="spread" style={{ fontSize: 13, marginBottom: 4 }}>
        <span className="muted">{label}</span>
        <span>{value == null ? "—" : `${Math.round(v)}%`}</span>
      </div>
      <div className="meter">
        <div style={{ width: `${v}%`, background: color }} />
      </div>
    </div>
  );
}

export function KeywordChips({ items, kind }: { items: string[]; kind: "good" | "bad" }) {
  if (!items.length) return <span className="muted">none</span>;
  return (
    <div className="tag-list">
      {items.map((k) => (
        <span key={k} className={`chip ${kind}`}>{k}</span>
      ))}
    </div>
  );
}

const STAGES: CandidateStage[] = ["new", "shortlisted", "interview", "rejected"];

export function StageSelect({
  value,
  onChange,
}: {
  value: CandidateStage;
  onChange: (s: CandidateStage) => void;
}) {
  return (
    <select
      value={value}
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => onChange(e.target.value as CandidateStage)}
      style={{ width: "auto" }}
    >
      {STAGES.map((s) => (
        <option key={s} value={s}>{s}</option>
      ))}
    </select>
  );
}

const STATUS_LABEL: Record<ScoreStatus, { text: string; color: string }> = {
  pending: { text: "Pending", color: "var(--muted)" },
  processing: { text: "Processing…", color: "var(--accent)" },
  scored: { text: "Scored", color: "var(--good)" },
  filtered_out: { text: "Filtered out", color: "var(--warn)" },
  failed: { text: "Failed", color: "var(--bad)" },
};

export function StatusTag({ status }: { status: ScoreStatus }) {
  const s = STATUS_LABEL[status];
  return <span style={{ color: s.color, fontSize: 13 }}>{s.text}</span>;
}

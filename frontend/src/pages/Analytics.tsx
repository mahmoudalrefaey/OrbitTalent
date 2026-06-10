import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, type Analytics as A } from "../api/client";

const STAGE_COLORS: Record<string, string> = {
  new: "#8b98a9",
  shortlisted: "#4f9cf9",
  interview: "#2ecc71",
  rejected: "#e74c3c",
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card" style={{ flex: 1, textAlign: "center" }}>
      <div className="muted" style={{ fontSize: 13 }}>{label}</div>
      <div className="score-big">{value}</div>
    </div>
  );
}

export default function Analytics() {
  const { jobId } = useParams();
  const [a, setA] = useState<A | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void api.analytics(Number(jobId)).then(setA).catch((e) => setError(String(e)));
  }, [jobId]);

  if (error) return <p className="error">{error}</p>;
  if (!a) return <p className="muted">Loading…</p>;

  const stageData = Object.entries(a.stage_counts).map(([name, value]) => ({ name, value }));
  const missingData = a.top_missing_keywords.map((m) => ({ name: m.keyword, count: m.count }));

  return (
    <div>
      <h2>Analytics</h2>

      <div className="row" style={{ alignItems: "stretch" }}>
        <Stat label="Total" value={a.total} />
        <Stat label="Scored" value={a.scored} />
        <Stat label="Filtered out" value={a.filtered_out} />
        <Stat label="Avg overall" value={a.avg_overall_score ?? "—"} />
        <Stat label="Avg job match" value={a.avg_job_match_pct != null ? `${a.avg_job_match_pct}%` : "—"} />
        <Stat label="Avg ATS" value={a.avg_ats_score != null ? `${a.avg_ats_score}%` : "—"} />
      </div>

      <div className="grid-2">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Pipeline stages</h3>
          {a.total === 0 ? <p className="muted">No data.</p> : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={stageData} dataKey="value" nameKey="name" outerRadius={90} label>
                  {stageData.map((d) => (
                    <Cell key={d.name} fill={STAGE_COLORS[d.name] ?? "#8b98a9"} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginTop: 0 }}>Top missing skills (skill gaps)</h3>
          {missingData.length === 0 ? <p className="muted">No data.</p> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={missingData} layout="vertical" margin={{ left: 20 }}>
                <XAxis type="number" stroke="#8b98a9" allowDecimals={false} />
                <YAxis type="category" dataKey="name" stroke="#8b98a9" width={120} />
                <Tooltip />
                <Bar dataKey="count" fill="#f5a623" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}

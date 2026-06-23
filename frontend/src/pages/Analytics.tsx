import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft } from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type Analytics as A } from "@/api/client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { formatUsd } from "@/lib/utils";

const MUTED = "hsl(var(--muted-foreground))";

const STAGE_COLORS: Record<string, string> = {
  new: "hsl(var(--muted-foreground))",
  shortlisted: "hsl(var(--primary))",
  interview: "hsl(var(--success))",
  rejected: "hsl(var(--danger))",
};

const TIER_LABELS: Record<string, string> = {
  "0": "Tier 0 (free)",
  "1": "Tier 1",
  "2": "Tier 2",
  "3": "Tier 3 (deep)",
};

const TIER_COLORS: Record<string, string> = {
  "0": "hsl(var(--success))",
  "1": "hsl(var(--primary))",
  "2": "hsl(var(--warning))",
  "3": "hsl(var(--danger))",
};

function Stat({
  label,
  value,
  i,
}: {
  label: string;
  value: string | number;
  i: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay: Math.min(i * 0.04, 0.3) }}
    >
      <Card>
        <CardContent className="p-4">
          <div className="text-xs text-muted-foreground">{label}</div>
          <div className="mt-1 text-2xl font-bold tracking-tight">{value}</div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

function EmptyChart() {
  return (
    <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
      No data yet.
    </div>
  );
}

export default function Analytics() {
  const { jobId } = useParams();
  const [a, setA] = useState<A | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void api
      .analytics(Number(jobId))
      .then(setA)
      .catch((e) => setError(String(e)));
  }, [jobId]);

  const backLink = `/app/jobs/${jobId}/candidates`;

  if (error) {
    return (
      <div className="space-y-4">
        <BackLink to={backLink} />
        <Card className="border-danger/40">
          <CardContent className="py-4 text-sm text-danger">{error}</CardContent>
        </Card>
      </div>
    );
  }

  if (!a) {
    return (
      <div className="space-y-6">
        <BackLink to={backLink} />
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-80 w-full rounded-lg" />
          <Skeleton className="h-80 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  const stageData = Object.entries(a.stage_counts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));
  // Prefer the richer skill_gaps (has pct); fall back to legacy keyword counts.
  const topGaps =
    a.skill_gaps.length > 0
      ? a.skill_gaps.slice(0, 8)
      : a.top_missing_keywords
          .slice(0, 8)
          .map((m) => ({ keyword: m.keyword, count: m.count, pct: 0, example_candidate_ids: [] }));
  const tierData = ["0", "1", "2", "3"].map((k) => ({
    name: TIER_LABELS[k],
    key: k,
    count: a.tier_distribution[k] ?? 0,
  }));
  const hasTierData = tierData.some((t) => t.count > 0);

  const stats: { label: string; value: string | number }[] = [
    { label: "Total", value: a.total },
    { label: "Scored", value: a.scored },
    { label: "Filtered out", value: a.filtered_out },
    { label: "Avg overall", value: a.avg_overall_score ?? "—" },
    {
      label: "Avg job match %",
      value: a.avg_job_match_pct != null ? `${a.avg_job_match_pct}%` : "—",
    },
    {
      label: "Avg ATS %",
      value: a.avg_ats_score != null ? `${a.avg_ats_score}%` : "—",
    },
    { label: "Est. total cost", value: formatUsd(a.est_total_cost_usd) },
    {
      label: "Cache hit rate",
      value: `${Math.round(a.cache_hit_rate * 100)}%`,
    },
  ];

  return (
    <div className="space-y-6">
      <BackLink to={backLink} />

      <div>
        <h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Pipeline health and cost breakdown for this job
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {stats.map((s, i) => (
          <Stat key={s.label} label={s.label} value={s.value} i={i} />
        ))}
      </div>

      {/* Pipeline + missing skills */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Pipeline stages</CardTitle>
            <CardDescription>Candidates by current stage</CardDescription>
          </CardHeader>
          <CardContent>
            {a.total === 0 || stageData.length === 0 ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <PieChart>
                  <Pie
                    data={stageData}
                    dataKey="value"
                    nameKey="name"
                    outerRadius={90}
                    label
                  >
                    {stageData.map((d) => (
                      <Cell
                        key={d.name}
                        fill={STAGE_COLORS[d.name] ?? MUTED}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-start justify-between space-y-0">
            <div>
              <CardTitle className="text-base">Top missing skills</CardTitle>
              <CardDescription>Most common skill gaps</CardDescription>
            </div>
            <Link
              to={`/app/jobs/${jobId}/skill-gaps`}
              className="shrink-0 text-sm text-primary hover:underline"
            >
              View all
            </Link>
          </CardHeader>
          <CardContent>
            {topGaps.length === 0 ? (
              <EmptyChart />
            ) : (
              <div className="space-y-2.5">
                {topGaps.map((g) => {
                  const max = topGaps[0]?.count || 1;
                  return (
                    <div key={g.keyword} className="space-y-1">
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <span className="truncate" title={g.keyword}>
                          {g.keyword}
                        </span>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {g.count}
                          {g.pct ? ` · ${g.pct}%` : ""}
                        </span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full rounded-full bg-warning"
                          style={{ width: `${Math.max((g.count / max) * 100, 4)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Funnel + conversions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Hiring funnel &amp; conversion</CardTitle>
          <CardDescription>
            Candidates reaching each stage, with stage-to-stage conversion.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {a.funnel.every((f) => f.count === 0) ? (
            <EmptyChart />
          ) : (
            <div className="space-y-1.5">
              {a.funnel.map((f) => {
                const max = Math.max(...a.funnel.map((x) => x.count), 1);
                return (
                  <div key={f.stage} className="flex items-center gap-3">
                    <span className="w-40 shrink-0 text-right text-xs capitalize text-muted-foreground">
                      {f.stage.replace(/_/g, " ")}
                    </span>
                    <div className="h-7 flex-1 overflow-hidden rounded bg-muted">
                      <div
                        className="flex h-full items-center justify-end rounded bg-primary px-2 text-xs font-medium text-primary-foreground transition-all"
                        style={{ width: `${Math.max((f.count / max) * 100, 6)}%` }}
                      >
                        {f.count}
                      </div>
                    </div>
                    <span className="w-12 shrink-0 text-xs text-muted-foreground">
                      {f.conversion_from_prev != null ? `${f.conversion_from_prev}%` : "—"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Score distribution + geography */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI score distribution</CardTitle>
            <CardDescription>Overall scores bucketed (1–10)</CardDescription>
          </CardHeader>
          <CardContent>
            {Object.values(a.score_distribution).every((v) => v === 0) ? (
              <EmptyChart />
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart
                  data={Object.entries(a.score_distribution).map(([name, count]) => ({
                    name,
                    count,
                  }))}
                >
                  <XAxis dataKey="name" stroke={MUTED} style={{ fontSize: 12 }} />
                  <YAxis stroke={MUTED} style={{ fontSize: 12 }} allowDecimals={false} />
                  <Tooltip
                    cursor={{ fill: "hsl(var(--muted))" }}
                    contentStyle={{
                      background: "hsl(var(--card))",
                      border: "1px solid hsl(var(--border))",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Candidates by country</CardTitle>
            <CardDescription>Geographic distribution</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.keys(a.by_country).length === 0 ? (
              <EmptyChart />
            ) : (
              Object.entries(a.by_country)
                .sort((x, y) => y[1] - x[1])
                .slice(0, 8)
                .map(([country, n]) => (
                  <div key={country} className="flex items-center justify-between text-sm">
                    <span>{country}</span>
                    <span className="text-muted-foreground">{n}</span>
                  </div>
                ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Cascade tier distribution */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cascade tier distribution</CardTitle>
          <CardDescription>
            Cheaper tiers resolve first — more candidates at lower tiers means
            lower total cost.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {a.total === 0 || !hasTierData ? (
            <EmptyChart />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={tierData} margin={{ top: 8 }}>
                <XAxis
                  dataKey="name"
                  stroke={MUTED}
                  style={{ fontSize: 12 }}
                />
                <YAxis
                  stroke={MUTED}
                  style={{ fontSize: 12 }}
                  allowDecimals={false}
                />
                <Tooltip
                  cursor={{ fill: "hsl(var(--muted))" }}
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {tierData.map((d) => (
                    <Cell key={d.key} fill={TIER_COLORS[d.key] ?? MUTED} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function BackLink({ to }: { to: string }) {
  return (
    <Link
      to={to}
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
    >
      <ArrowLeft className="h-4 w-4" />
      Back to candidates
    </Link>
  );
}

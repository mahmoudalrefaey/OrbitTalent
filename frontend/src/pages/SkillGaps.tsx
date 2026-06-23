import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  Treemap,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowDown, ArrowUp, Download, Table2, BarChart3, Grid3x3 } from "lucide-react";
import { api, type SkillGap } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { downloadCsv, toCsv } from "@/lib/csv";
import { cn } from "@/lib/utils";

type View = "table" | "bar" | "treemap";
type SortKey = "keyword" | "count" | "pct";

export default function SkillGaps() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const [view, setView] = useState<View>("table");
  const [sortKey, setSortKey] = useState<SortKey>("count");
  const [asc, setAsc] = useState(false);

  const { data: a, isLoading } = useQuery({
    queryKey: ["analytics", id],
    queryFn: () => api.analytics(id),
    enabled: !Number.isNaN(id),
  });

  const gaps = useMemo(() => {
    const rows = [...(a?.skill_gaps ?? [])];
    rows.sort((x, y) => {
      const dir = asc ? 1 : -1;
      if (sortKey === "keyword") return dir * x.keyword.localeCompare(y.keyword);
      return dir * (x[sortKey] - y[sortKey]);
    });
    return rows;
  }, [a, sortKey, asc]);

  if (isLoading || !a) {
    return <Skeleton className="h-96 w-full rounded-lg" />;
  }

  function sortBy(key: SortKey) {
    if (key === sortKey) setAsc((v) => !v);
    else {
      setSortKey(key);
      setAsc(key === "keyword");
    }
  }

  function exportCsv() {
    downloadCsv(
      `job-${id}-skill-gaps.csv`,
      toCsv(
        gaps.map((g) => ({ skill: g.keyword, affected: g.count, pct_missing: g.pct })),
        ["skill", "affected", "pct_missing"]
      )
    );
  }

  const barData = gaps.slice(0, 15).map((g) => ({ name: g.keyword, count: g.count }));
  const treeData = gaps.slice(0, 30).map((g) => ({ name: g.keyword, size: g.count }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Skill gaps</h1>
          <p className="text-sm text-muted-foreground">
            Skills most often missing across {a.total} candidates
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border border-border p-0.5">
            {([
              ["table", Table2],
              ["bar", BarChart3],
              ["treemap", Grid3x3],
            ] as const).map(([v, Icon]) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={cn(
                  "flex items-center gap-1.5 rounded px-2.5 py-1.5 text-sm capitalize transition-colors",
                  view === v
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" /> {v}
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={exportCsv}>
            <Download className="h-4 w-4" /> CSV
          </Button>
        </div>
      </div>

      {gaps.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-sm text-muted-foreground">
            No skill-gap data yet — score some candidates first.
          </CardContent>
        </Card>
      ) : view === "table" ? (
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <Th label="Skill" k="keyword" {...{ sortKey, asc, sortBy }} />
                  <Th label="# Affected" k="count" {...{ sortKey, asc, sortBy }} />
                  <Th label="% Missing" k="pct" {...{ sortKey, asc, sortBy }} />
                </tr>
              </thead>
              <tbody>
                {gaps.map((g) => (
                  <tr key={g.keyword} className="border-b border-border/60 last:border-0">
                    <td className="px-4 py-2.5 font-medium">{g.keyword}</td>
                    <td className="px-4 py-2.5">{g.count}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-primary"
                            style={{ width: `${g.pct}%` }}
                          />
                        </div>
                        <span className="text-muted-foreground">{g.pct}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      ) : view === "bar" ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top 15 missing skills</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(300, barData.length * 28)}>
              <BarChart data={barData} layout="vertical" margin={{ left: 24 }}>
                <XAxis type="number" stroke="hsl(var(--muted-foreground))" allowDecimals={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={200}
                  interval={0}
                  stroke="hsl(var(--muted-foreground))"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v: string) =>
                    v.length > 28 ? `${v.slice(0, 27)}…` : v
                  }
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Skill-gap treemap</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={360}>
              <Treemap
                data={treeData}
                dataKey="size"
                stroke="hsl(var(--background))"
                fill="hsl(var(--primary))"
              />
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Th({
  label,
  k,
  sortKey,
  asc,
  sortBy,
}: {
  label: string;
  k: SortKey;
  sortKey: SortKey;
  asc: boolean;
  sortBy: (k: SortKey) => void;
}) {
  return (
    <th className="px-4 py-2.5">
      <button
        onClick={() => sortBy(k)}
        className="flex items-center gap-1 hover:text-foreground"
      >
        {label}
        {sortKey === k &&
          (asc ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
      </button>
    </th>
  );
}

// Keep SkillGap type referenced for consumers.
export type { SkillGap };

import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Candidate } from "@/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { ScoreBadge, StageBadge, KeywordChips } from "@/components/common";

const ROWS: { label: string; render: (c: Candidate) => React.ReactNode }[] = [
  { label: "Overall", render: (c) => <ScoreBadge score={c.overall_score} /> },
  { label: "Job match", render: (c) => (c.job_match_pct != null ? `${c.job_match_pct}%` : "—") },
  { label: "ATS", render: (c) => (c.ats_score != null ? `${c.ats_score}%` : "—") },
  { label: "Stage", render: (c) => <StageBadge stage={c.stage} /> },
  { label: "Experience", render: (c) => (c.experience_years != null ? `${c.experience_years} yrs` : "—") },
  { label: "Education", render: (c) => c.education ?? "—" },
  { label: "Country", render: (c) => c.country ?? "—" },
  { label: "Certifications", render: (c) => c.certifications.join(", ") || "—" },
  { label: "Languages", render: (c) => c.languages.join(", ") || "—" },
  { label: "Matched", render: (c) => <KeywordChips items={c.matched_keywords} kind="good" /> },
  { label: "Missing", render: (c) => <KeywordChips items={c.missing_keywords} kind="bad" /> },
];

export default function Compare() {
  const [params] = useSearchParams();
  const ids = (params.get("ids") ?? "")
    .split(",")
    .map((s) => Number(s))
    .filter((n) => !Number.isNaN(n));

  const { data: cands = [], isLoading, error } = useQuery({
    queryKey: ["compare", ids],
    queryFn: () => api.compareCandidates(ids),
    enabled: ids.length >= 2,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Compare candidates</h1>
        <p className="text-sm text-muted-foreground">Side-by-side comparison</p>
      </div>

      {ids.length < 2 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            Select 2–4 candidates to compare (pass <code>?ids=1,2,3</code>).
          </CardContent>
        </Card>
      ) : isLoading ? (
        <Skeleton className="h-96 w-full rounded-lg" />
      ) : error ? (
        <Card className="border-danger/40">
          <CardContent className="py-4 text-sm text-danger">{String(error)}</CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="p-3 text-left text-xs uppercase text-muted-foreground">
                    Field
                  </th>
                  {cands.map((c) => (
                    <th key={c.id} className="min-w-[160px] p-3 text-left font-medium">
                      {c.filename}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr key={row.label} className="border-b border-border/60 last:border-0">
                    <td className="p-3 text-xs uppercase text-muted-foreground">
                      {row.label}
                    </td>
                    {cands.map((c) => (
                      <td key={c.id} className="p-3 align-top">
                        {row.render(c)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

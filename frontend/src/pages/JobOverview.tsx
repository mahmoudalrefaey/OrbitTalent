import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Users } from "lucide-react";
import { api } from "@/api/client";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { cn, formatUsd } from "@/lib/utils";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="text-xs text-muted-foreground">{label}</div>
        <div className="mt-1 text-2xl font-bold tracking-tight">{value}</div>
      </CardContent>
    </Card>
  );
}

export default function JobOverview() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const { data: a, isLoading } = useQuery({
    queryKey: ["analytics", id],
    queryFn: () => api.analytics(id),
    enabled: !Number.isNaN(id),
  });

  if (isLoading || !a) {
    return (
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  const hired = a.stage_counts["hired"] ?? 0;
  const rejected = a.stage_counts["rejected"] ?? 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Total candidates" value={a.total} />
        <Stat label="Scored" value={a.scored} />
        <Stat label="Hired" value={hired} />
        <Stat label="Rejected" value={rejected} />
        <Stat label="Avg overall" value={a.avg_overall_score ?? "—"} />
        <Stat label="Avg job match" value={a.avg_job_match_pct != null ? `${a.avg_job_match_pct}%` : "—"} />
        <Stat label="Avg ATS" value={a.avg_ats_score != null ? `${a.avg_ats_score}%` : "—"} />
        <Stat label="LLM cost" value={formatUsd(a.est_total_cost_usd)} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick actions</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            <Link to={`/app/jobs/${id}/candidates`} className={cn(buttonVariants())}>
              <Users className="h-4 w-4" /> View candidates
            </Link>
            <Link to={`/app/jobs/${id}/analytics`} className={cn(buttonVariants({ variant: "outline" }))}>
              Analytics <ArrowRight className="h-4 w-4" />
            </Link>
            <Link to={`/app/jobs/${id}/settings`} className={cn(buttonVariants({ variant: "outline" }))}>
              Edit criteria
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Top skill gaps</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {a.skill_gaps.length === 0 ? (
              <p className="text-sm text-muted-foreground">No data yet.</p>
            ) : (
              a.skill_gaps.slice(0, 6).map((s) => (
                <div key={s.keyword} className="flex items-center justify-between text-sm">
                  <span className="truncate">{s.keyword}</span>
                  <span className="text-muted-foreground">
                    {s.count} ({s.pct}%)
                  </span>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

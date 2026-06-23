import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Briefcase,
  CheckCircle2,
  Plus,
  Users,
  XCircle,
} from "lucide-react";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { ScoreBadge } from "@/components/common";
import { cn } from "@/lib/utils";

function Kpi({ label, value, icon: Icon, i }: {
  label: string; value: string | number;
  icon: React.ComponentType<{ className?: string }>; i: number;
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.05 }}>
      <Card>
        <CardContent className="flex items-center gap-4 p-5">
          <div className="rounded-lg bg-primary/10 p-2.5 text-primary">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <div className="text-2xl font-bold tracking-tight">{value}</div>
            <div className="text-xs text-muted-foreground">{label}</div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ["overview"],
    queryFn: () => api.overview(),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Organization-wide hiring overview
          </p>
        </div>
        <Link to="/onboarding" className={cn(buttonVariants())}>
          <Plus className="h-4 w-4" /> New job
        </Link>
      </div>

      {isLoading || !data ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Active jobs" value={`${data.active_jobs}/${data.total_jobs}`} icon={Briefcase} i={0} />
            <Kpi label="Candidates" value={data.total_candidates} icon={Users} i={1} />
            <Kpi label="Hired" value={data.total_hired} icon={CheckCircle2} i={2} />
            <Kpi label="Rejected" value={data.total_rejected} icon={XCircle} i={3} />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            {/* Jobs table */}
            <Card className="lg:col-span-2">
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <CardTitle className="text-base">Jobs</CardTitle>
                <Link to="/app/jobs" className="text-sm text-primary hover:underline">
                  View all
                </Link>
              </CardHeader>
              <CardContent className="p-0">
                {data.jobs.length === 0 ? (
                  <p className="px-6 pb-6 text-sm text-muted-foreground">
                    No jobs yet. Create your first job to start screening.
                  </p>
                ) : (
                  <div className="divide-y divide-border">
                    {data.jobs.map((j) => (
                      <Link
                        key={j.id}
                        to={`/app/jobs/${j.id}/overview`}
                        className="flex items-center justify-between px-6 py-3 transition-colors hover:bg-secondary/50"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="truncate font-medium">{j.title}</span>
                            <Badge variant="outline">{j.status}</Badge>
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {j.total_candidates} candidates · {j.hired} hired ·{" "}
                            {j.rejected} rejected
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <ScoreBadge score={j.avg_overall_score} />
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Top missing skills org-wide */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top skill gaps</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.top_missing_skills.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No data yet.</p>
                ) : (
                  data.top_missing_skills.slice(0, 8).map((s) => (
                    <div key={s.keyword} className="flex items-center justify-between text-sm">
                      <span className="truncate">{s.keyword}</span>
                      <span className="text-muted-foreground">{s.pct}%</span>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

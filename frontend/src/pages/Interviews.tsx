import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, type Candidate, type CandidateStage } from "@/api/client";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { ScoreBadge, StageBadge } from "@/components/common";

const INTERVIEW_STAGES: CandidateStage[] = [
  "interview_scheduled",
  "interview_passed",
  "final_review",
];

export default function Interviews() {
  const { jobId } = useParams();
  const id = Number(jobId);

  const { data: all = [], isLoading } = useQuery({
    queryKey: ["candidates", id],
    queryFn: () => api.listCandidates(id),
    enabled: !Number.isNaN(id),
  });

  const rows = all.filter((c: Candidate) => INTERVIEW_STAGES.includes(c.stage));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Interview pipeline</h1>
        <p className="text-sm text-muted-foreground">
          {rows.length} candidates in interview stages
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-40 w-full rounded-lg" />
      ) : rows.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-sm text-muted-foreground">
            No candidates in the interview pipeline yet.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {rows.map((c) => (
            <Link key={c.id} to={`/app/jobs/${id}/candidates/${c.id}`}>
              <Card className="transition-colors hover:border-primary/50">
                <CardContent className="flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{c.filename}</div>
                    <div className="pt-1">
                      <StageBadge stage={c.stage} />
                    </div>
                  </div>
                  <ScoreBadge score={c.overall_score} />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

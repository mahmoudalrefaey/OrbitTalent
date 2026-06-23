import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/misc";
import { ScoreBadge, REJECTION_LABELS } from "@/components/common";
import type { RejectionReason } from "@/api/client";

export default function Rejected() {
  const { jobId } = useParams();
  const id = Number(jobId);

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ["candidates", id, "rejected"],
    queryFn: () => api.listCandidates(id, "rejected"),
    enabled: !Number.isNaN(id),
  });
  const { data: a } = useQuery({
    queryKey: ["analytics", id],
    queryFn: () => api.analytics(id),
    enabled: !Number.isNaN(id),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Rejected candidates</h1>
        <p className="text-sm text-muted-foreground">
          {rows.length} rejected · with reasons
        </p>
      </div>

      {/* Rejection reason breakdown */}
      {a && Object.keys(a.rejection_reasons).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Rejection reasons</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {Object.entries(a.rejection_reasons).map(([reason, count]) => (
              <Badge key={reason} variant="secondary">
                {REJECTION_LABELS[reason as RejectionReason] ?? reason}: {count}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Skeleton className="h-40 w-full rounded-lg" />
      ) : rows.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-sm text-muted-foreground">
            No rejected candidates.
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
                    {c.rejection_reason && (
                      <Badge variant="danger" className="mt-1">
                        {REJECTION_LABELS[c.rejection_reason]}
                      </Badge>
                    )}
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

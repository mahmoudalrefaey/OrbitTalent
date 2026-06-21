import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { AlertTriangle, ArrowLeft, Sparkles } from "lucide-react";
import { api, type CandidateDetail as CD } from "@/api/client";
import {
  KeywordChips,
  Meter,
  ScoreBadge,
  StageSelect,
  StatusTag,
  TierBadge,
} from "@/components/common";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { formatUsd } from "@/lib/utils";

const fade = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
};

export default function CandidateDetail() {
  const { jobId, candidateId } = useParams();
  const [c, setC] = useState<CD | null>(null);
  const [error, setError] = useState("");

  async function load() {
    try {
      setC(await api.getCandidate(Number(candidateId)));
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidateId]);

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

  if (!c) {
    return (
      <div className="space-y-4">
        <BackLink to={backLink} />
        <Skeleton className="h-12 w-2/3 rounded-lg" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-48 w-full rounded-lg" />
          <Skeleton className="h-48 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  async function onStage(stage: CD["stage"]) {
    if (!c) return;
    const updated = await api.updateStage(c.id, stage);
    setC({ ...c, stage: updated.stage });
  }

  return (
    <div className="space-y-6">
      <BackLink to={backLink} />

      {/* Header */}
      <motion.div
        {...fade}
        transition={{ duration: 0.25 }}
        className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
      >
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-bold tracking-tight">
            {c.filename}
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <StatusTag status={c.score_status} />
            <TierBadge tier={c.tier_reached} />
            {c.cache_hit && <Badge variant="secondary">cached</Badge>}
            {c.est_cost_usd > 0 && (
              <span className="text-sm text-muted-foreground">
                {formatUsd(c.est_cost_usd)}
              </span>
            )}
          </div>
        </div>
        <StageSelect value={c.stage} onChange={onStage} />
      </motion.div>

      {c.error && (
        <Card className="border-danger/40">
          <CardContent className="py-4 text-sm text-danger">
            Error: {c.error}
          </CardContent>
        </Card>
      )}

      {/* Scores + reasoning */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Scores</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="flex items-center gap-3">
              <span className="text-sm text-muted-foreground">Overall</span>
              <ScoreBadge score={c.overall_score} />
            </div>
            <Meter
              value={c.job_match_pct}
              label="Job match (fit for this role)"
            />
            <Meter
              value={c.ats_score}
              label="ATS readiness (CV parse-ability)"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-primary" />
              AI reasoning
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
              {c.reasoning || (
                <span className="text-muted-foreground">
                  No reasoning available.
                </span>
              )}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Keywords */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Matched keywords</CardTitle>
          </CardHeader>
          <CardContent>
            <KeywordChips items={c.matched_keywords} kind="good" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Missing keywords</CardTitle>
          </CardHeader>
          <CardContent>
            <KeywordChips items={c.missing_keywords} kind="bad" />
          </CardContent>
        </Card>
      </div>

      {/* ATS issues */}
      {c.ats_issues.length > 0 && (
        <Card className="border-warning/40 bg-warning/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-warning">
              <AlertTriangle className="h-4 w-4" />
              ATS issues
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
              {c.ats_issues.map((i) => (
                <li key={i}>{i}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Extracted text */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Extracted CV text</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap rounded-md bg-muted/50 p-4 font-mono text-sm text-muted-foreground">
            {c.parsed_text || "(no text extracted)"}
          </pre>
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

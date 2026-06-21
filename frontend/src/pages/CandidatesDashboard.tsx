import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { BarChart3, ChevronRight, FileUp, Inbox, Loader2 } from "lucide-react";
import { api, type Candidate } from "@/api/client";
import {
  Meter,
  ScoreBadge,
  StageSelect,
  StatusTag,
  TierBadge,
} from "@/components/common";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { formatUsd } from "@/lib/utils";

const STAGE_FILTERS = [
  { value: "all", label: "All stages" },
  { value: "new", label: "New" },
  { value: "shortlisted", label: "Shortlisted" },
  { value: "interview", label: "Interview" },
  { value: "rejected", label: "Rejected" },
];

export default function CandidatesDashboard() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const nav = useNavigate();

  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [stageFilter, setStageFilter] = useState<string>("all");
  const fileRef = useRef<HTMLInputElement>(null);

  async function load() {
    try {
      setCandidates(await api.listCandidates(id));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    setLoading(true);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // Poll while any candidate is still being processed.
  useEffect(() => {
    const anyProcessing = candidates.some(
      (c) => c.score_status === "pending" || c.score_status === "processing"
    );
    if (!anyProcessing) return;
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candidates, id]);

  async function onUpload(files: FileList | null) {
    if (!files || !files.length) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadCandidates(id, files);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function setStage(c: Candidate, stage: Candidate["stage"]) {
    const updated = await api.updateStage(c.id, stage);
    setCandidates((cs) => cs.map((x) => (x.id === c.id ? updated : x)));
  }

  const shown = candidates.filter(
    (c) => stageFilter === "all" || c.stage === stageFilter
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Candidates</h1>
          <p className="text-sm text-muted-foreground">
            Ranked by overall fit · cost shown per candidate
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {STAGE_FILTERS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <Button
            variant="outline"
            onClick={() => nav(`/app/jobs/${id}/analytics`)}
          >
            <BarChart3 className="h-4 w-4" />
            Analytics
          </Button>
        </div>
      </div>

      {/* Upload dropzone */}
      <Card>
        <CardContent className="p-0">
          <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border px-6 py-8 text-center transition-colors hover:border-primary/50 hover:bg-secondary/40">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
              {uploading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <FileUp className="h-5 w-5" />
              )}
            </span>
            <span className="text-sm font-medium">
              {uploading
                ? "Uploading & queuing for scoring…"
                : "Upload CVs to score"}
            </span>
            <span className="text-xs text-muted-foreground">
              PDF, DOCX or TXT · select multiple
            </span>
            <input
              ref={fileRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              className="hidden"
              onChange={(e) => onUpload(e.target.files)}
              disabled={uploading}
            />
          </label>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-danger/40">
          <CardContent className="py-4 text-sm text-danger">{error}</CardContent>
        </Card>
      )}

      {/* List */}
      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : shown.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-secondary text-muted-foreground">
              <Inbox className="h-6 w-6" />
            </span>
            <div>
              <p className="font-medium">No candidates yet</p>
              <p className="text-sm text-muted-foreground">
                {candidates.length === 0
                  ? "Upload CVs above to start screening."
                  : "No candidates match this stage filter."}
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {shown.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, delay: Math.min(i * 0.03, 0.3) }}
            >
              <Card
                onClick={() => nav(`/app/jobs/${id}/candidates/${c.id}`)}
                className="cursor-pointer transition-colors hover:border-primary/50 hover:bg-secondary/30"
              >
                <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center">
                  {/* Rank + identity */}
                  <div className="flex min-w-0 flex-1 items-center gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-semibold text-muted-foreground">
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-medium">{c.filename}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        <StatusTag status={c.score_status} />
                        <TierBadge tier={c.tier_reached} />
                        {c.cache_hit && (
                          <span className="text-xs text-muted-foreground">
                            cached
                          </span>
                        )}
                        {c.est_cost_usd > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {formatUsd(c.est_cost_usd)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Meters */}
                  <div className="grid grid-cols-2 gap-3 lg:w-72 lg:shrink-0">
                    <Meter value={c.job_match_pct} label="Match" />
                    <Meter value={c.ats_score} label="ATS" />
                  </div>

                  {/* Score + stage + chevron */}
                  <div
                    className="flex items-center justify-between gap-2 lg:justify-end"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ScoreBadge score={c.overall_score} />
                    <StageSelect
                      value={c.stage}
                      onChange={(s) => setStage(c, s)}
                    />
                    <ChevronRight className="hidden h-4 w-4 shrink-0 text-muted-foreground lg:block" />
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}

import { useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { FileUp, Inbox, Loader2 } from "lucide-react";
import {
  api,
  type Candidate,
  type CandidateStage,
  type RejectionReason,
} from "@/api/client";
import {
  Meter,
  ScoreBadge,
  StageBadge,
  StageSelect,
  StatusTag,
  TierBadge,
} from "@/components/common";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { BulkActionBar } from "@/components/bulk-action-bar";
import { downloadCsv, toCsv } from "@/lib/csv";
import { formatUsd } from "@/lib/utils";

export default function CandidatesDashboard() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const nav = useNavigate();
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);

  const [stageFilter, setStageFilter] = useState<string>("all");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [uploadError, setUploadError] = useState("");

  const { data: candidates = [], isLoading } = useQuery({
    queryKey: ["candidates", id],
    queryFn: () => api.listCandidates(id),
    enabled: !Number.isNaN(id),
    // Poll while any candidate is still processing.
    refetchInterval: (q) =>
      (q.state.data ?? []).some(
        (c) => c.score_status === "pending" || c.score_status === "processing"
      )
        ? 2000
        : false,
  });

  const upload = useMutation({
    mutationFn: (files: FileList) => api.uploadCandidates(id, files),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["candidates", id] }),
    onError: (e) => setUploadError(String(e)),
    onSettled: () => {
      if (fileRef.current) fileRef.current.value = "";
    },
  });

  const setStage = useMutation({
    mutationFn: ({ c, stage }: { c: Candidate; stage: CandidateStage }) =>
      api.updateStage(c.id, stage),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["candidates", id] }),
  });

  const bulk = useMutation({
    mutationFn: (body: Parameters<typeof api.bulkAction>[0]) => api.bulkAction(body),
    onSuccess: (res) => {
      if (res.action === "export" && res.candidates) {
        downloadCsv(`job-${id}-selected.csv`, toCsv(res.candidates as never[]));
      }
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["candidates", id] });
    },
  });

  const shown = useMemo(
    () =>
      candidates.filter((c) => stageFilter === "all" || c.stage === stageFilter),
    [candidates, stageFilter]
  );

  function toggle(cid: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(cid) ? next.delete(cid) : next.add(cid);
      return next;
    });
  }
  const allShownSelected = shown.length > 0 && shown.every((c) => selected.has(c.id));
  function toggleAll() {
    setSelected(allShownSelected ? new Set() : new Set(shown.map((c) => c.id)));
  }

  const ids = [...selected];
  const runBulk = (
    action: "move_stage" | "reject" | "shortlist" | "export",
    extra?: { stage?: CandidateStage; rejection_reason?: RejectionReason }
  ) => bulk.mutate({ candidate_ids: ids, action, ...extra });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Candidates</h1>
          <p className="text-sm text-muted-foreground">
            Ranked by overall fit · select rows for bulk actions
          </p>
        </div>
        <select
          value={stageFilter}
          onChange={(e) => setStageFilter(e.target.value)}
          className="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <option value="all">All stages</option>
          {[...new Set(candidates.map((c) => c.stage))].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {/* Upload */}
      <Card>
        <CardContent className="p-0">
          <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border px-6 py-7 text-center transition-colors hover:border-primary/50 hover:bg-secondary/40">
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
              {upload.isPending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <FileUp className="h-5 w-5" />
              )}
            </span>
            <span className="text-sm font-medium">
              {upload.isPending ? "Uploading…" : "Upload CVs to score"}
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
              onChange={(e) => e.target.files && upload.mutate(e.target.files)}
              disabled={upload.isPending}
            />
          </label>
        </CardContent>
      </Card>

      {uploadError && (
        <Card className="border-danger/40">
          <CardContent className="py-3 text-sm text-danger">{uploadError}</CardContent>
        </Card>
      )}

      {/* List */}
      {isLoading ? (
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
            <p className="text-sm text-muted-foreground">
              {candidates.length === 0
                ? "Upload CVs above to start screening."
                : "No candidates match this filter."}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {/* Select-all */}
          <label className="flex items-center gap-2 px-1 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={allShownSelected}
              onChange={toggleAll}
              className="h-4 w-4 rounded border-input accent-primary"
            />
            Select all ({shown.length})
          </label>

          {shown.map((c, i) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: Math.min(i * 0.02, 0.25) }}
            >
              <Card className="transition-colors hover:border-primary/50">
                <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center">
                  <input
                    type="checkbox"
                    checked={selected.has(c.id)}
                    onChange={() => toggle(c.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="h-4 w-4 shrink-0 rounded border-input accent-primary"
                    aria-label={`Select ${c.filename}`}
                  />
                  <button
                    className="flex min-w-0 flex-1 items-center gap-3 text-left"
                    onClick={() => nav(`/app/jobs/${id}/candidates/${c.id}`)}
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-sm font-semibold text-muted-foreground">
                      {i + 1}
                    </span>
                    <div className="min-w-0">
                      <div className="truncate font-medium">{c.filename}</div>
                      <div className="flex flex-wrap items-center gap-1.5 pt-1">
                        <StatusTag status={c.score_status} />
                        <TierBadge tier={c.tier_reached} />
                        {c.est_cost_usd > 0 && (
                          <span className="text-xs text-muted-foreground">
                            {formatUsd(c.est_cost_usd)}
                          </span>
                        )}
                        {c.country && (
                          <span className="text-xs text-muted-foreground">
                            · {c.country}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>

                  <div className="grid w-full grid-cols-2 gap-3 lg:w-72">
                    <Meter value={c.job_match_pct} label="Match" />
                    <Meter value={c.ats_score} label="ATS" />
                  </div>

                  <div className="flex items-center gap-2 lg:w-40 lg:justify-end">
                    <ScoreBadge score={c.overall_score} />
                  </div>

                  <div onClick={(e) => e.stopPropagation()}>
                    {c.stage === "rejected" ? (
                      <StageBadge stage={c.stage} />
                    ) : (
                      <StageSelect
                        value={c.stage}
                        onChange={(stage) => setStage.mutate({ c, stage })}
                      />
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      <BulkActionBar
        count={selected.size}
        busy={bulk.isPending}
        onClear={() => setSelected(new Set())}
        onMoveStage={(stage) => runBulk("move_stage", { stage })}
        onReject={(rejection_reason) => runBulk("reject", { rejection_reason })}
        onShortlist={() => runBulk("shortlist")}
        onExport={() => runBulk("export")}
      />
    </div>
  );
}

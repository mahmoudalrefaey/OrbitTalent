import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Download, Loader2, Trash2, X } from "lucide-react";
import {
  CANDIDATE_STAGES,
  REJECTION_REASONS,
  type CandidateStage,
  type RejectionReason,
} from "@/api/client";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { STAGE_LABELS, REJECTION_LABELS } from "@/components/common";

interface Props {
  count: number;
  busy?: boolean;
  onClear: () => void;
  onMoveStage: (stage: CandidateStage) => void;
  onReject: (reason: RejectionReason) => void;
  onShortlist: () => void;
  onExport: () => void;
}

/** Floating toolbar shown when candidates are multi-selected. */
export function BulkActionBar({
  count,
  busy,
  onClear,
  onMoveStage,
  onReject,
  onShortlist,
  onExport,
}: Props) {
  const [stage, setStage] = useState<CandidateStage>("shortlisted");
  const [reason, setReason] = useState<RejectionReason>("recruiter_decision");

  return (
    <AnimatePresence>
      {count > 0 && (
        <motion.div
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 80, opacity: 0 }}
          className="fixed inset-x-0 bottom-4 z-40 mx-auto flex w-fit max-w-[95vw] flex-wrap items-center gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-lg"
        >
          <span className="text-sm font-medium">
            {count} selected
            {busy && <Loader2 className="ml-2 inline h-4 w-4 animate-spin" />}
          </span>

          <div className="flex items-center gap-1">
            <Select
              value={stage}
              onChange={(e) => setStage(e.target.value as CandidateStage)}
              className="h-9"
            >
              {CANDIDATE_STAGES.map((s) => (
                <option key={s} value={s}>
                  {STAGE_LABELS[s]}
                </option>
              ))}
            </Select>
            <Button size="sm" variant="secondary" disabled={busy}
              onClick={() => onMoveStage(stage)}>
              Move
            </Button>
          </div>

          <Button size="sm" variant="secondary" disabled={busy} onClick={onShortlist}>
            Shortlist
          </Button>

          <div className="flex items-center gap-1">
            <Select
              value={reason}
              onChange={(e) => setReason(e.target.value as RejectionReason)}
              className="h-9"
            >
              {REJECTION_REASONS.map((r) => (
                <option key={r} value={r}>
                  {REJECTION_LABELS[r]}
                </option>
              ))}
            </Select>
            <Button size="sm" variant="danger" disabled={busy}
              onClick={() => onReject(reason)}>
              <Trash2 className="h-4 w-4" /> Reject
            </Button>
          </div>

          <Button size="sm" variant="outline" disabled={busy} onClick={onExport}>
            <Download className="h-4 w-4" /> Export
          </Button>

          <Button size="icon" variant="ghost" onClick={onClear} aria-label="Clear selection">
            <X className="h-4 w-4" />
          </Button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

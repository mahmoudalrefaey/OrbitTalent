import type { CandidateStage, ScoreStatus } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/misc";
import { cn } from "@/lib/utils";

export function ScoreBadge({ score }: { score: number | null }) {
  if (score == null) return <span className="text-muted-foreground">—</span>;
  const variant = score >= 7 ? "success" : score >= 4 ? "warning" : "danger";
  return <Badge variant={variant}>{score.toFixed(1)}/10</Badge>;
}

export function Meter({ value, label }: { value: number | null; label: string }) {
  const v = value ?? 0;
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value == null ? "—" : `${Math.round(v)}%`}</span>
      </div>
      <Progress value={v} />
    </div>
  );
}

export function KeywordChips({ items, kind }: { items: string[]; kind: "good" | "bad" }) {
  if (!items.length) return <span className="text-sm text-muted-foreground">none</span>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((k) => (
        <span
          key={k}
          className={cn(
            "rounded-md px-2 py-0.5 text-xs font-medium",
            kind === "good"
              ? "bg-success/15 text-success"
              : "bg-danger/15 text-danger"
          )}
        >
          {k}
        </span>
      ))}
    </div>
  );
}

const STAGES: CandidateStage[] = ["new", "shortlisted", "interview", "rejected"];

export function StageSelect({
  value,
  onChange,
}: {
  value: CandidateStage;
  onChange: (s: CandidateStage) => void;
}) {
  return (
    <select
      value={value}
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => onChange(e.target.value as CandidateStage)}
      className="h-9 rounded-md border border-input bg-background px-2 text-sm capitalize focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {STAGES.map((s) => (
        <option key={s} value={s} className="capitalize">
          {s}
        </option>
      ))}
    </select>
  );
}

const STATUS_META: Record<
  ScoreStatus,
  { text: string; variant: "default" | "secondary" | "success" | "warning" | "danger" }
> = {
  pending: { text: "Pending", variant: "secondary" },
  processing: { text: "Processing…", variant: "default" },
  scored: { text: "Scored", variant: "success" },
  filtered_out: { text: "Filtered out", variant: "warning" },
  failed: { text: "Failed", variant: "danger" },
};

export function StatusTag({ status }: { status: ScoreStatus }) {
  const s = STATUS_META[status];
  return <Badge variant={s.variant}>{s.text}</Badge>;
}

const TIER_META: Record<number, { label: string; hint: string }> = {
  0: { label: "T0 · free", hint: "Resolved by deterministic rules (no LLM cost)" },
  1: { label: "T1 · embed", hint: "Filtered by embedding similarity" },
  2: { label: "T2 · cheap", hint: "Scored by the cheap model" },
  3: { label: "T3 · deep", hint: "Deep model — precise scoring" },
};

/** Shows which cascade tier produced a candidate's score (cost transparency). */
export function TierBadge({ tier }: { tier: number }) {
  const meta = TIER_META[tier] ?? TIER_META[0];
  const variant = tier >= 3 ? "default" : tier === 2 ? "secondary" : "outline";
  return (
    <Badge variant={variant} title={meta.hint}>
      {meta.label}
    </Badge>
  );
}

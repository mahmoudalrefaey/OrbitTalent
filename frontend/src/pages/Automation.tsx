import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Zap } from "lucide-react";
import { api, REJECTION_REASONS, type AutomationRule } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/misc";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { REJECTION_LABELS } from "@/components/common";

const FIELDS = [
  { value: "overall_score", label: "AI score" },
  { value: "experience_years", label: "Experience (yrs)" },
  { value: "country", label: "Country" },
  { value: "expected_salary", label: "Expected salary" },
];
const OPS = [
  { value: "lt", label: "<" },
  { value: "lte", label: "≤" },
  { value: "gt", label: ">" },
  { value: "gte", label: "≥" },
  { value: "eq", label: "=" },
  { value: "missing_count_gte", label: "missing skills ≥" },
];

export default function Automation() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const qc = useQueryClient();

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["automation", id],
    queryFn: () => api.listAutomationRules(id),
    enabled: !Number.isNaN(id),
  });

  const [name, setName] = useState("");
  const [field, setField] = useState("overall_score");
  const [op, setOp] = useState("lt");
  const [value, setValue] = useState("6");
  const [actionType, setActionType] = useState("reject");
  const [stage, setStage] = useState("shortlisted");
  const [reason, setReason] = useState("low_ai_score");

  const create = useMutation({
    mutationFn: () =>
      api.createAutomationRule({
        name: name || "Untitled rule",
        job_id: id,
        trigger_json: [
          {
            field,
            op,
            value: isNaN(Number(value)) ? value : Number(value),
          },
        ],
        action_json:
          actionType === "reject"
            ? { type: "reject", reason }
            : actionType === "move"
            ? { type: "move", stage }
            : { type: "shortlist" },
        enabled: true,
        priority: 0,
      }),
    onSuccess: () => {
      setName("");
      qc.invalidateQueries({ queryKey: ["automation", id] });
    },
  });

  const del = useMutation({
    mutationFn: (rid: number) => api.deleteAutomationRule(rid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["automation", id] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Automation rules</h1>
        <p className="text-sm text-muted-foreground">
          Auto-reject or auto-progress candidates when conditions match — applied
          right after AI scoring.
        </p>
      </div>

      {/* New rule */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">New rule</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label>Rule name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Reject low scorers" />
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <div>
              <Label>If</Label>
              <Select value={field} onChange={(e) => setField(e.target.value)}>
                {FIELDS.map((f) => (
                  <option key={f.value} value={f.value}>{f.label}</option>
                ))}
              </Select>
            </div>
            <Select value={op} onChange={(e) => setOp(e.target.value)}>
              {OPS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </Select>
            <div>
              <Label>Value</Label>
              <Input className="w-28" value={value}
                onChange={(e) => setValue(e.target.value)} />
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-2">
            <div>
              <Label>Then</Label>
              <Select value={actionType} onChange={(e) => setActionType(e.target.value)}>
                <option value="reject">Reject</option>
                <option value="move">Move to stage</option>
                <option value="shortlist">Shortlist</option>
              </Select>
            </div>
            {actionType === "reject" && (
              <div>
                <Label>Reason</Label>
                <Select value={reason} onChange={(e) => setReason(e.target.value)}>
                  {REJECTION_REASONS.map((r) => (
                    <option key={r} value={r}>{REJECTION_LABELS[r]}</option>
                  ))}
                </Select>
              </div>
            )}
            {actionType === "move" && (
              <div>
                <Label>Stage</Label>
                <Input value={stage} onChange={(e) => setStage(e.target.value)} />
              </div>
            )}
            <Button onClick={() => create.mutate()} disabled={create.isPending}>
              <Plus className="h-4 w-4" /> Add rule
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Existing rules */}
      {isLoading ? (
        <Skeleton className="h-32 w-full rounded-lg" />
      ) : rules.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No automation rules yet.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {rules.map((r: AutomationRule) => (
            <Card key={r.id}>
              <CardContent className="flex items-center justify-between gap-3 p-4">
                <div className="flex items-center gap-3">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Zap className="h-4 w-4" />
                  </span>
                  <div>
                    <div className="font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground">
                      {(r.trigger_json ?? [])
                        .map((c) => `${c.field} ${c.op} ${c.value}`)
                        .join(" AND ")}{" "}
                      → {JSON.stringify(r.action_json)}
                    </div>
                  </div>
                  {!r.enabled && <Badge variant="secondary">disabled</Badge>}
                </div>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => del.mutate(r.id)}
                  aria-label="Delete rule"
                >
                  <Trash2 className="h-4 w-4 text-danger" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

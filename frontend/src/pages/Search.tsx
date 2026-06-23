import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Search as SearchIcon, Loader2 } from "lucide-react";
import {
  api,
  CANDIDATE_STAGES,
  type Candidate,
  type CandidateSearchRequest,
  type CandidateStage,
} from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/misc";
import { Card, CardContent } from "@/components/ui/card";
import { ScoreBadge, StageBadge, STAGE_LABELS } from "@/components/common";

export default function SearchPage() {
  const [form, setForm] = useState<CandidateSearchRequest>({ query: "" });
  const [results, setResults] = useState<Candidate[]>([]);
  const [searched, setSearched] = useState(false);

  const search = useMutation({
    mutationFn: () => api.searchCandidates(form),
    onSuccess: (r) => {
      setResults(r.results);
      setSearched(true);
    },
  });

  const set = <K extends keyof CandidateSearchRequest>(
    k: K,
    v: CandidateSearchRequest[K]
  ) => setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Search candidates</h1>
        <p className="text-sm text-muted-foreground">
          Free-text ranking (BM25) + structured filters across all your jobs
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 p-5">
          <div className="flex gap-2">
            <Input
              placeholder='e.g. "senior backend engineer with Django and AWS"'
              value={form.query ?? ""}
              onChange={(e) => set("query", e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search.mutate()}
            />
            <Button onClick={() => search.mutate()} disabled={search.isPending}>
              {search.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <SearchIcon className="h-4 w-4" />
              )}
              Search
            </Button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <Label>Country</Label>
              <Input
                value={form.country ?? ""}
                onChange={(e) => set("country", e.target.value || null)}
              />
            </div>
            <div>
              <Label>Min experience (yrs)</Label>
              <Input
                type="number"
                value={form.min_experience ?? ""}
                onChange={(e) =>
                  set("min_experience", e.target.value ? Number(e.target.value) : null)
                }
              />
            </div>
            <div>
              <Label>Min score</Label>
              <Input
                type="number"
                value={form.min_score ?? ""}
                onChange={(e) =>
                  set("min_score", e.target.value ? Number(e.target.value) : null)
                }
              />
            </div>
            <div>
              <Label>Stage</Label>
              <Select
                value={form.stage ?? ""}
                onChange={(e) =>
                  set("stage", (e.target.value || null) as CandidateStage | null)
                }
                className="w-full"
              >
                <option value="">Any</option>
                {CANDIDATE_STAGES.map((s) => (
                  <option key={s} value={s}>
                    {STAGE_LABELS[s]}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {searched && (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{results.length} results</p>
          {results.map((c) => (
            <Link key={c.id} to={`/app/jobs/${c.job_id}/candidates/${c.id}`}>
              <Card className="transition-colors hover:border-primary/50">
                <CardContent className="flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{c.filename}</div>
                    <div className="flex items-center gap-2 pt-1 text-xs text-muted-foreground">
                      {c.country && <span>{c.country}</span>}
                      {c.experience_years != null && <span>· {c.experience_years}y</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StageBadge stage={c.stage} />
                    <ScoreBadge score={c.overall_score} />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

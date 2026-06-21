import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Briefcase,
  Plus,
  Rocket,
  Sparkles,
  Users,
} from "lucide-react";
import { api, type Job } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label, Skeleton } from "@/components/ui/misc";

const STATUS_VARIANT: Record<Job["status"], "secondary" | "success" | "outline"> = {
  draft: "secondary",
  ready: "success",
  archived: "outline",
};

export default function JobsList() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [title, setTitle] = useState("");
  const [jd, setJd] = useState("");
  const [error, setError] = useState("");
  const [llmEnabled, setLlmEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const nav = useNavigate();

  async function load() {
    try {
      setJobs(await api.listJobs());
      const h = await api.health();
      setLlmEnabled(h.llm_enabled);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);

  async function create() {
    if (!title.trim()) return;
    setError("");
    setCreating(true);
    try {
      const job = await api.createJob(title, jd);
      nav(`/app/jobs/${job.id}/setup`);
    } catch (e) {
      setError(String(e));
      setCreating(false);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Job Postings</h1>
        <p className="mt-1 text-muted-foreground">
          Create a role, extract screening criteria, and start ranking CVs.
        </p>
      </div>

      {!llmEnabled && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-3 rounded-lg border border-warning/40 bg-warning/10 p-4 text-sm"
        >
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
          <div>
            <p className="font-semibold text-foreground">AI scoring is disabled</p>
            <p className="mt-0.5 text-muted-foreground">
              Set <code className="rounded bg-muted px-1 py-0.5">LLM_API_KEY</code> in the
              backend to enable JD criteria extraction and deep scoring. ATS-readiness and
              keyword matching still work.
            </p>
          </div>
        </motion.div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-primary" /> New job
          </CardTitle>
          <CardDescription>Paste the job description now or add it later.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="job-title">Title</Label>
            <Input
              id="job-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Senior Backend Engineer"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="job-jd">Job description (optional)</Label>
            <Textarea
              id="job-jd"
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              placeholder="Paste the full job description…"
            />
          </div>
          <div>
            <Button onClick={create} disabled={!title.trim() || creating}>
              {creating ? "Creating…" : "Create job"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && <p className="text-sm text-danger">{error}</p>}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full rounded-lg" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <div className="rounded-full bg-primary/10 p-4">
              <Briefcase className="h-7 w-7 text-primary" />
            </div>
            <div>
              <p className="font-semibold">No jobs yet</p>
              <p className="text-sm text-muted-foreground">
                Create one above, or launch the guided wizard.
              </p>
            </div>
            <Button variant="outline" onClick={() => nav("/onboarding")}>
              <Rocket className="h-4 w-4" /> New job wizard
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((j, i) => (
            <motion.div
              key={j.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.25 }}
            >
              <Card
                onClick={() => nav(`/app/jobs/${j.id}/candidates`)}
                className="group cursor-pointer transition-all hover:border-primary/40 hover:shadow-md"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="line-clamp-2 group-hover:text-primary">
                      {j.title}
                    </CardTitle>
                    <Badge variant={STATUS_VARIANT[j.status]} className="capitalize">
                      {j.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex items-center justify-between text-sm text-muted-foreground">
                  <span className="inline-flex items-center gap-1.5">
                    <Users className="h-4 w-4" />
                    {j.candidate_count} candidate{j.candidate_count === 1 ? "" : "s"}
                  </span>
                  <span>{new Date(j.created_at).toLocaleDateString()}</span>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {jobs.length > 0 && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Sparkles className="h-4 w-4 text-primary" />
          Prefer a guided flow?{" "}
          <Link to="/onboarding" className="text-primary hover:underline">
            Open the new job wizard
          </Link>
        </div>
      )}
    </div>
  );
}

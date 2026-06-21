import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, ArrowRight, CheckCircle2, Sparkles } from "lucide-react";
import { api, type Criteria, type JobDetail } from "@/api/client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { Label, Skeleton } from "@/components/ui/misc";

type Editable = Omit<Criteria, "id" | "job_id">;

const EMPTY: Editable = {
  required_skills: [],
  preferred_skills: [],
  min_years: 0,
  must_haves: [],
  weights: { required_skills: 0.5, preferred_skills: 0.2, min_years: 0.15, must_haves: 0.15 },
};

const toText = (a: string[]) => a.join(", ");
const fromText = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);

export default function JobSetup() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const nav = useNavigate();

  const [job, setJob] = useState<JobDetail | null>(null);
  const [jd, setJd] = useState("");
  const [crit, setCrit] = useState<Editable>(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const j = await api.getJob(id);
        setJob(j);
        setJd(j.jd_text);
        if (j.criteria) {
          const { id: _i, job_id: _j, ...rest } = j.criteria;
          void _i;
          void _j;
          setCrit(rest);
        }
      } catch (e) {
        setError(String(e));
      }
    })();
  }, [id]);

  async function extract() {
    setError("");
    setInfo("");
    setBusy(true);
    try {
      const c = await api.extractCriteria(id, jd);
      const { id: _i, job_id: _j, ...rest } = c;
      void _i;
      void _j;
      setCrit(rest);
      setInfo("Criteria extracted by AI — review and edit, then confirm.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setError("");
    setInfo("");
    setBusy(true);
    try {
      await api.updateCriteria(id, crit);
      nav(`/app/jobs/${id}/candidates`);
    } catch (e) {
      setError(String(e));
      setBusy(false);
    }
  }

  if (!job) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/app"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Back to jobs
        </Link>
        <h1 className="mt-2 text-2xl font-bold tracking-tight sm:text-3xl">
          {job.title} — Setup
        </h1>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Job description</CardTitle>
            <CardDescription>
              The AI reads the JD and proposes screening criteria.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              className="min-h-[180px]"
              placeholder="Paste the full job description…"
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button onClick={extract} disabled={busy || !jd.trim()}>
                <Sparkles className="h-4 w-4" />
                {busy ? "Extracting…" : "Extract criteria with AI"}
              </Button>
              <span className="text-sm text-muted-foreground">
                Proposes required/preferred skills and must-haves.
              </span>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {info && (
        <div className="flex items-center gap-2 rounded-lg border border-success/40 bg-success/10 p-3 text-sm text-success">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {info}
        </div>
      )}
      {error && <p className="text-sm text-danger">{error}</p>}

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.05 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>
              Scoring criteria{" "}
              <span className="text-sm font-normal text-muted-foreground">(editable)</span>
            </CardTitle>
            <CardDescription>
              Comma-separate skill lists. Tune before you start screening.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="required">Required skills</Label>
              <Input
                id="required"
                value={toText(crit.required_skills)}
                onChange={(e) =>
                  setCrit({ ...crit, required_skills: fromText(e.target.value) })
                }
                placeholder="Python, FastAPI, PostgreSQL"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="preferred">Preferred skills</Label>
              <Input
                id="preferred"
                value={toText(crit.preferred_skills)}
                onChange={(e) =>
                  setCrit({ ...crit, preferred_skills: fromText(e.target.value) })
                }
                placeholder="Docker, AWS, Kubernetes"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="musthaves">Must-have qualifications</Label>
              <Input
                id="musthaves"
                value={toText(crit.must_haves)}
                onChange={(e) =>
                  setCrit({ ...crit, must_haves: fromText(e.target.value) })
                }
                placeholder="Bachelor's degree, work authorization"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="minyears">Minimum years of experience</Label>
              <Input
                id="minyears"
                type="number"
                min={0}
                value={crit.min_years}
                onChange={(e) =>
                  setCrit({ ...crit, min_years: Number(e.target.value) })
                }
                className="w-32"
              />
            </div>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Button onClick={confirm} disabled={busy}>
                {busy ? "Saving…" : "Confirm criteria & start screening"}
                <ArrowRight className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground">
                Saving marks the job ready to accept CVs.
              </span>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}

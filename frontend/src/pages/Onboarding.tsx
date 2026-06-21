import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Sparkles,
  UploadCloud,
  PartyPopper,
  Loader2,
  FileText,
} from "lucide-react";
import { api, type Criteria } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Label, Progress } from "@/components/ui/misc";
import { ThemeToggle } from "@/components/theme-toggle";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";

type Editable = Omit<Criteria, "id" | "job_id">;

const EMPTY: Editable = {
  required_skills: [],
  preferred_skills: [],
  min_years: 0,
  must_haves: [],
  weights: {
    required_skills: 0.5,
    preferred_skills: 0.2,
    min_years: 0.15,
    must_haves: 0.15,
  },
};

const toText = (a: string[]) => a.join(", ");
const fromText = (s: string) =>
  s
    .split(",")
    .map((x) => x.trim())
    .filter(Boolean);

const STEPS = ["Create job", "Extract criteria", "Upload CVs", "Done"];

export default function Onboarding() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Step 1
  const [title, setTitle] = useState("");
  const [jd, setJd] = useState("");
  const [jobId, setJobId] = useState<number | null>(null);

  // Step 2
  const [crit, setCrit] = useState<Editable>(EMPTY);
  const [llmEnabled, setLlmEnabled] = useState<boolean | null>(null);

  // Step 3
  const [uploaded, setUploaded] = useState<string[]>([]);

  useEffect(() => {
    void (async () => {
      try {
        const h = await api.health();
        setLlmEnabled(h.llm_enabled);
      } catch {
        setLlmEnabled(false);
      }
    })();
  }, []);

  async function handleCreateJob() {
    setError("");
    setBusy(true);
    try {
      const job = await api.createJob(title.trim(), jd);
      setJobId(job.id);
      setStep(1);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleExtract() {
    if (jobId == null) return;
    setError("");
    setBusy(true);
    try {
      const c = await api.extractCriteria(jobId, jd);
      const { id: _i, job_id: _j, ...rest } = c;
      setCrit(rest);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleConfirmCriteria() {
    if (jobId == null) return;
    setError("");
    setBusy(true);
    try {
      await api.updateCriteria(jobId, crit);
      setStep(2);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(files: FileList | null) {
    if (jobId == null || !files || files.length === 0) return;
    setError("");
    setBusy(true);
    try {
      const created = await api.uploadCandidates(jobId, files);
      setUploaded(created.map((c) => c.filename));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Minimal chrome */}
      <header className="border-b border-border">
        <div className="container flex h-16 items-center justify-between">
          <Link to="/app" className="flex items-center">
            <Logo variant="full" height={28} />
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="container flex flex-1 flex-col items-center py-12">
        <div className="w-full max-w-2xl">
          {/* Step indicator */}
          <div className="mb-8">
            <div className="mb-3 flex items-center justify-between">
              {STEPS.map((label, i) => (
                <div key={label} className="flex items-center gap-2">
                  <div
                    className={cn(
                      "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                      i < step
                        ? "bg-primary text-primary-foreground"
                        : i === step
                        ? "bg-primary text-primary-foreground ring-4 ring-primary/20"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {i < step ? <Check className="h-3.5 w-3.5" /> : i + 1}
                  </div>
                  <span
                    className={cn(
                      "hidden text-sm font-medium sm:inline",
                      i === step ? "text-foreground" : "text-muted-foreground"
                    )}
                  >
                    {label}
                  </span>
                </div>
              ))}
            </div>
            <Progress value={progress} tone="primary" />
          </div>

          {error && (
            <Card className="mb-6 border-danger/40 bg-danger/5">
              <CardContent className="flex items-center gap-2 py-4">
                <Badge variant="danger">Error</Badge>
                <span className="text-sm text-danger">{error}</span>
              </CardContent>
            </Card>
          )}

          <AnimatePresence mode="wait">
            {/* Step 1 — Create job */}
            {step === 0 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -30 }}
                transition={{ duration: 0.3 }}
              >
                <Card>
                  <CardContent className="space-y-5 p-6">
                    <div>
                      <h2 className="text-xl font-semibold">Create a job</h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Give your role a title and (optionally) paste the job
                        description to power AI criteria extraction.
                      </p>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="title">Job title</Label>
                      <Input
                        id="title"
                        placeholder="Senior Frontend Engineer"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        autoFocus
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="jd">Job description (optional)</Label>
                      <Textarea
                        id="jd"
                        placeholder="Paste the full job description here…"
                        value={jd}
                        onChange={(e) => setJd(e.target.value)}
                        className="min-h-[160px]"
                      />
                    </div>
                    <div className="flex justify-end">
                      <Button
                        onClick={handleCreateJob}
                        disabled={busy || !title.trim()}
                      >
                        {busy ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <ArrowRight className="h-4 w-4" />
                        )}
                        Next
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Step 2 — Extract criteria */}
            {step === 1 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -30 }}
                transition={{ duration: 0.3 }}
              >
                <Card>
                  <CardContent className="space-y-5 p-6">
                    <div>
                      <h2 className="text-xl font-semibold">Extract criteria</h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Let the AI read your job description and propose screening
                        criteria. Everything is editable.
                      </p>
                    </div>

                    {llmEnabled === false && (
                      <div className="rounded-md border border-warning/40 bg-warning/10 p-3 text-sm text-warning">
                        AI extraction is currently disabled. You can fill in the
                        criteria manually below.
                      </div>
                    )}

                    {llmEnabled !== false && (
                      <Button
                        variant="secondary"
                        onClick={handleExtract}
                        disabled={busy || !jd.trim()}
                      >
                        {busy ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Sparkles className="h-4 w-4" />
                        )}
                        Extract with AI
                      </Button>
                    )}
                    {llmEnabled !== false && !jd.trim() && (
                      <p className="text-xs text-muted-foreground">
                        No job description provided — fill the criteria manually.
                      </p>
                    )}

                    <div className="space-y-4">
                      <div className="space-y-2">
                        <Label>Required skills (comma-separated)</Label>
                        <Input
                          value={toText(crit.required_skills)}
                          onChange={(e) =>
                            setCrit({
                              ...crit,
                              required_skills: fromText(e.target.value),
                            })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Preferred skills</Label>
                        <Input
                          value={toText(crit.preferred_skills)}
                          onChange={(e) =>
                            setCrit({
                              ...crit,
                              preferred_skills: fromText(e.target.value),
                            })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Must-have qualifications</Label>
                        <Input
                          value={toText(crit.must_haves)}
                          onChange={(e) =>
                            setCrit({
                              ...crit,
                              must_haves: fromText(e.target.value),
                            })
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Minimum years of experience</Label>
                        <Input
                          type="number"
                          min={0}
                          value={crit.min_years}
                          onChange={(e) =>
                            setCrit({
                              ...crit,
                              min_years: Number(e.target.value),
                            })
                          }
                          className="w-32"
                        />
                      </div>
                    </div>

                    <div className="flex justify-between">
                      <Button variant="ghost" onClick={() => setStep(0)}>
                        <ArrowLeft className="h-4 w-4" />
                        Back
                      </Button>
                      <Button onClick={handleConfirmCriteria} disabled={busy}>
                        {busy ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <ArrowRight className="h-4 w-4" />
                        )}
                        Confirm &amp; continue
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Step 3 — Upload CVs */}
            {step === 2 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -30 }}
                transition={{ duration: 0.3 }}
              >
                <Card>
                  <CardContent className="space-y-5 p-6">
                    <div>
                      <h2 className="text-xl font-semibold">Upload CVs</h2>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Drop in résumés as PDF, DOCX or TXT. We'll score and rank
                        them with the cascade.
                      </p>
                    </div>

                    <label
                      htmlFor="cv-upload"
                      className={cn(
                        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-border bg-muted/30 px-6 py-12 text-center transition-colors hover:border-primary/50 hover:bg-primary/5",
                        busy && "pointer-events-none opacity-60"
                      )}
                    >
                      {busy ? (
                        <Loader2 className="h-8 w-8 animate-spin text-primary" />
                      ) : (
                        <UploadCloud className="h-8 w-8 text-muted-foreground" />
                      )}
                      <div>
                        <p className="text-sm font-medium">
                          Click to upload, or drag &amp; drop
                        </p>
                        <p className="text-xs text-muted-foreground">
                          PDF, DOCX or TXT — multiple files supported
                        </p>
                      </div>
                      <Input
                        id="cv-upload"
                        type="file"
                        multiple
                        accept=".pdf,.docx,.txt"
                        className="hidden"
                        onChange={(e) => void handleUpload(e.target.files)}
                      />
                    </label>

                    {uploaded.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-success">
                          {uploaded.length} file
                          {uploaded.length === 1 ? "" : "s"} uploaded
                        </p>
                        <ul className="space-y-1">
                          {uploaded.map((name) => (
                            <li
                              key={name}
                              className="flex items-center gap-2 text-sm text-muted-foreground"
                            >
                              <FileText className="h-4 w-4 shrink-0" />
                              <span className="truncate">{name}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="flex justify-between">
                      <Button variant="ghost" onClick={() => setStep(1)}>
                        <ArrowLeft className="h-4 w-4" />
                        Back
                      </Button>
                      <Button
                        onClick={() => setStep(3)}
                        disabled={uploaded.length === 0}
                      >
                        <ArrowRight className="h-4 w-4" />
                        Finish
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Step 4 — Done */}
            {step === 3 && (
              <motion.div
                key="step4"
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -30 }}
                transition={{ duration: 0.3 }}
              >
                <Card>
                  <CardContent className="flex flex-col items-center gap-5 p-10 text-center">
                    <motion.div
                      initial={{ scale: 0, rotate: -30 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{
                        type: "spring",
                        stiffness: 200,
                        damping: 12,
                      }}
                      className="flex h-16 w-16 items-center justify-center rounded-full bg-success/15 text-success"
                    >
                      <PartyPopper className="h-8 w-8" />
                    </motion.div>
                    <div>
                      <h2 className="text-2xl font-bold">You're all set!</h2>
                      <p className="mt-2 text-muted-foreground">
                        Your CVs are being scored. Head to the candidates
                        dashboard to watch the ranked shortlist come together.
                      </p>
                    </div>
                    {jobId != null && (
                      <Button onClick={() => nav(`/app/jobs/${jobId}/candidates`)}>
                        View ranked candidates
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    )}
                    <Link
                      to="/app"
                      className="text-sm text-muted-foreground underline-offset-4 hover:underline"
                    >
                      Go to dashboard
                    </Link>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

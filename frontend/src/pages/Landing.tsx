import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Rocket,
  Layers,
  Gauge,
  Brain,
  DollarSign,
  FileText,
  Sparkles,
  ListOrdered,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
  transition: { duration: 0.5 },
};

const features = [
  {
    icon: Layers,
    title: "Cost-optimized cascade",
    desc: "Cheap models triage every CV first. Only genuine contenders ever reach the deep, expensive model — so you pay for depth only where it matters.",
  },
  {
    icon: Gauge,
    title: "Two scores that matter",
    desc: "Every candidate gets an ATS-readiness score and a job-match percentage, so you see both résumé quality and fit at a glance.",
  },
  {
    icon: Brain,
    title: "Explainable results",
    desc: "Plain-language reasoning plus matched and missing keywords behind every ranking. No black box — defensible decisions.",
  },
  {
    icon: DollarSign,
    title: "Cost dashboard",
    desc: "Track spend per job in real time, watch the cascade keep costs low, and never get surprised by an AI bill again.",
  },
];

const steps = [
  {
    icon: FileText,
    title: "Paste the job description",
    desc: "Drop in your JD. No templates, no rigid forms — just the text you already have.",
  },
  {
    icon: Sparkles,
    title: "AI extracts the criteria",
    desc: "We pull out required skills, nice-to-haves, must-haves and experience — all editable.",
  },
  {
    icon: ListOrdered,
    title: "Upload CVs, get a ranked list",
    desc: "Bulk-upload résumés and receive a scored, sorted shortlist in seconds.",
  },
];

export default function Landing() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary/5 via-background to-background">
        <div
          className="pointer-events-none absolute inset-0 -z-10 bg-[linear-gradient(to_right,hsl(var(--border)/0.4)_1px,transparent_1px),linear-gradient(to_bottom,hsl(var(--border)/0.4)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_at_top,black,transparent_70%)]"
          aria-hidden
        />
        <div className="container flex flex-col items-center py-24 text-center sm:py-32">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Badge variant="secondary" className="mb-6 gap-1.5">
              <Rocket className="h-3.5 w-3.5" />
              AI CV screening, minus the AI bill
            </Badge>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="max-w-4xl text-4xl font-bold tracking-tight sm:text-6xl"
          >
            Rank every candidate in seconds, at a{" "}
            <span className="text-primary">fraction of the cost</span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="mt-6 max-w-2xl text-lg text-muted-foreground"
          >
            OrbitTalent screens résumés with a tiered cascade: cheap models handle
            the easy calls and only the strongest CVs reach the deep model. You get
            explainable, ranked shortlists without burning your budget.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="mt-10 flex flex-col gap-3 sm:flex-row"
          >
            <Link to="/onboarding" className={cn(buttonVariants({ size: "lg" }))}>
              Start screening free
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              to="/pricing"
              className={cn(buttonVariants({ variant: "outline", size: "lg" }))}
            >
              View pricing
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Capability strip */}
      <section className="border-y border-border bg-card/40">
        <div className="container py-10">
          <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-3 text-sm font-medium text-muted-foreground">
            <span>Explainable scoring</span>
            <span className="text-border">·</span>
            <span>Cost-optimized AI</span>
            <span className="text-border">·</span>
            <span>PDF, DOCX &amp; TXT</span>
            <span className="text-border">·</span>
            <span>Per-tenant isolation</span>
            <span className="text-border">·</span>
            <span>Funnel &amp; skill-gap analytics</span>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="container py-24">
        <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Everything you need to screen smarter
          </h2>
          <p className="mt-4 text-muted-foreground">
            Built for high-volume hiring where speed, transparency and cost all
            matter at once.
          </p>
        </motion.div>
        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: i * 0.05 }}
              whileHover={{ y: -4 }}
            >
              <Card className="h-full">
                <CardHeader>
                  <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <f.icon className="h-5 w-5" />
                  </div>
                  <CardTitle>{f.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{f.desc}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-border bg-card/40">
        <div className="container py-24">
          <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              From job description to shortlist in three steps
            </h2>
            <p className="mt-4 text-muted-foreground">
              No setup, no training data, no spreadsheets.
            </p>
          </motion.div>
          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {steps.map((s, i) => (
              <motion.div
                key={s.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="relative flex flex-col items-center text-center"
              >
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-md shadow-primary/20">
                  <s.icon className="h-6 w-6" />
                </div>
                <div className="mt-2 text-sm font-semibold text-primary">
                  Step {i + 1}
                </div>
                <h3 className="mt-2 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 max-w-xs text-sm text-muted-foreground">
                  {s.desc}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="container py-24">
        <motion.div
          {...fadeUp}
          className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-primary/10 via-card to-card px-8 py-16 text-center"
        >
          <h2 className="mx-auto max-w-2xl text-3xl font-bold tracking-tight sm:text-4xl">
            Start screening candidates today
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Spin up your first job, extract criteria with AI, and upload a batch of
            CVs in minutes.
          </p>
          <div className="mt-8 flex justify-center">
            <Link to="/onboarding" className={cn(buttonVariants({ size: "lg" }))}>
              Start screening free
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </motion.div>
      </section>
    </div>
  );
}

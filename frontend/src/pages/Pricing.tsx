import { motion } from "framer-motion";
import { Check } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true },
  transition: { duration: 0.5 },
};

interface Tier {
  name: string;
  price: string;
  period?: string;
  description: string;
  features: string[];
  cta: string;
}

// Planned tiers — shown as a preview only. Pricing is not live yet, so none of
// these have working CTAs.
const tiers: Tier[] = [
  {
    name: "Starter",
    price: "Free",
    description: "For trying it out and small one-off hiring rounds.",
    features: [
      "1 active job",
      "Cascade scoring (cheap tiers)",
      "ATS + job-match scores",
    ],
    cta: "Coming soon",
  },
  {
    name: "Pro",
    price: "—",
    description: "For recruiters screening at volume every week.",
    features: [
      "Unlimited jobs",
      "Full deep-model cascade",
      "Explainable reasoning & keywords",
      "Per-job cost dashboard",
    ],
    cta: "Coming soon",
  },
  {
    name: "Enterprise",
    price: "—",
    description: "For teams with high volume, SSO and compliance needs.",
    features: [
      "Everything in Pro",
      "SSO & role-based access",
      "Custom data retention",
    ],
    cta: "Coming soon",
  },
];

const faqs = [
  {
    q: "How does the cascade keep costs down?",
    a: "Most CVs are clearly a strong or weak fit and get resolved by cheap, fast models. Only borderline candidates are escalated to the deep model, so you pay premium rates only where they change the outcome.",
  },
  {
    q: "What are ATS and job-match scores?",
    a: "The ATS score reflects how well a résumé is structured and parseable, while the job-match percentage measures fit against the criteria extracted from your job description.",
  },
  {
    q: "Can I edit the AI-extracted criteria?",
    a: "Yes. After the AI proposes required skills, preferred skills and must-haves, you can edit everything before scoring begins.",
  },
  {
    q: "Is pricing available yet?",
    a: "Not yet. OrbitTalent is an early demo, so the tiers below are a preview of the planned structure rather than something you can buy today.",
  },
];

export default function Pricing() {
  return (
    <div className="container py-20 sm:py-28">
      <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
        <Badge variant="secondary" className="mb-4">
          Coming soon
        </Badge>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Pricing is on the way
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          OrbitTalent is an early demo. Here is a preview of the planned plans —
          nothing is for sale yet, and the whole app is free to try.
        </p>
      </motion.div>

      <div className="mx-auto mt-14 grid max-w-5xl gap-6 lg:grid-cols-3">
        {tiers.map((tier, i) => (
          <motion.div
            key={tier.name}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: i * 0.07 }}
            whileHover={{ y: -4 }}
          >
            <Card className="flex h-full flex-col">
              <CardHeader>
                <CardTitle className="text-xl">{tier.name}</CardTitle>
                <CardDescription>{tier.description}</CardDescription>
                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-4xl font-bold tracking-tight">
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span className="text-muted-foreground">{tier.period}</span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="flex-1">
                <ul className="space-y-3">
                  {tier.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2.5 text-sm">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                <button
                  type="button"
                  disabled
                  className={cn(
                    buttonVariants({ variant: "outline" }),
                    "w-full cursor-not-allowed opacity-60"
                  )}
                >
                  {tier.cta}
                </button>
              </CardFooter>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* FAQ */}
      <div className="mx-auto mt-24 max-w-3xl">
        <motion.h2
          {...fadeUp}
          className="text-center text-3xl font-bold tracking-tight"
        >
          Frequently asked questions
        </motion.h2>
        <div className="mt-10 grid gap-4">
          {faqs.map((faq, i) => (
            <motion.div
              key={faq.q}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.45, delay: i * 0.05 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{faq.q}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{faq.a}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

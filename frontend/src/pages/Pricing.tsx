import { Link } from "react-router-dom";
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
  to?: string;
  highlight?: boolean;
}

const tiers: Tier[] = [
  {
    name: "Starter",
    price: "Free",
    description: "For trying it out and small one-off hiring rounds.",
    features: [
      "1 active job",
      "Up to 50 CVs / month",
      "Cascade scoring (cheap tiers)",
      "ATS + job-match scores",
      "Community support",
    ],
    cta: "Get started",
    to: "/onboarding",
  },
  {
    name: "Pro",
    price: "$49",
    period: "/mo",
    description: "For recruiters screening at volume every week.",
    features: [
      "Unlimited jobs",
      "Up to 2,000 CVs / month",
      "Full deep-model cascade",
      "Explainable reasoning & keywords",
      "Per-job cost dashboard",
      "Priority email support",
    ],
    cta: "Start free trial",
    to: "/onboarding",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    description: "For teams with high volume, SSO and compliance needs.",
    features: [
      "Everything in Pro",
      "Unlimited CVs",
      "SSO & role-based access",
      "Custom data retention",
      "Dedicated success manager",
      "SLA & onboarding",
    ],
    cta: "Contact sales",
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
    q: "Is pricing final?",
    a: "Pricing shown here is illustrative for this demo. Reach out to sales for a quote tailored to your hiring volume.",
  },
];

export default function Pricing() {
  return (
    <div className="container py-20 sm:py-28">
      <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Simple, transparent pricing
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          Pay for depth only when it matters. Start free and scale as you hire.
        </p>
        <p className="mt-2 text-sm text-muted-foreground/70">
          Pricing below is illustrative.
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
            <Card
              className={cn(
                "relative flex h-full flex-col",
                tier.highlight && "ring-2 ring-primary shadow-lg shadow-primary/10"
              )}
            >
              {tier.highlight && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">
                  Most popular
                </Badge>
              )}
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
                {tier.to ? (
                  <Link
                    to={tier.to}
                    className={cn(
                      buttonVariants({
                        variant: tier.highlight ? "default" : "outline",
                      }),
                      "w-full"
                    )}
                  >
                    {tier.cta}
                  </Link>
                ) : (
                  <Link
                    to="/onboarding"
                    className={cn(buttonVariants({ variant: "outline" }), "w-full")}
                  >
                    {tier.cta}
                  </Link>
                )}
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

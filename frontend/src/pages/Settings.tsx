import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  Database,
  DollarSign,
  Layers,
  Moon,
  Zap,
} from "lucide-react";
import { api, type Health, type Usage } from "@/api/client";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label, Separator, Skeleton } from "@/components/ui/misc";
import { useTheme } from "@/components/theme-provider";
import { cn, formatUsd } from "@/lib/utils";

const TIER_LABELS: Record<string, string> = {
  "0": "Tier 0 · free rules",
  "1": "Tier 1 · embeddings",
  "2": "Tier 2 · cheap model",
  "3": "Tier 3 · deep model",
};

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 py-5">
        <div className="rounded-lg bg-primary/10 p-2.5 text-primary">{icon}</div>
        <div>
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-xl font-semibold tracking-tight">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function Settings() {
  const { theme, setTheme } = useTheme();
  const [health, setHealth] = useState<Health | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void (async () => {
      try {
        const [h, u] = await Promise.all([api.health(), api.usage()]);
        setHealth(h);
        setUsage(u);
      } catch (e) {
        setError(String(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const chartData =
    usage?.by_day.map((d) => ({
      date: new Date(d.date).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
      }),
      cost: d.cost_usd,
    })) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Appearance, LLM provider status, and your usage &amp; cost.
        </p>
      </div>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>Appearance</CardTitle>
          <CardDescription>Customize how OrbitTalent looks.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Moon className="h-5 w-5 text-muted-foreground" />
              <Label htmlFor="dark-mode">Dark mode</Label>
            </div>
            <Switch
              checked={theme === "dark"}
              onCheckedChange={(v) => setTheme(v ? "dark" : "light")}
              aria-label="Toggle dark mode"
            />
          </div>
        </CardContent>
      </Card>

      {/* LLM provider */}
      <Card>
        <CardHeader>
          <CardTitle>LLM provider</CardTitle>
          <CardDescription>Scoring engine configuration.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <Skeleton className="h-20 w-full rounded-lg" />
          ) : health ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Provider</span>
                <span className="font-medium">{health.provider || "—"}</span>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">AI scoring</span>
                <Badge variant={health.llm_enabled ? "success" : "danger"}>
                  {health.llm_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Cost today</span>
                <span className="font-medium">{formatUsd(health.today_cost_usd)}</span>
              </div>
              {!health.llm_enabled && (
                <p className="rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm text-muted-foreground">
                  Set <code className="rounded bg-muted px-1 py-0.5">LLM_API_KEY</code> in
                  the backend to enable AI criteria extraction and deep scoring.
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-danger">{error || "Unable to load provider info."}</p>
          )}
        </CardContent>
      </Card>

      {/* Usage & cost */}
      <Card>
        <CardHeader>
          <CardTitle>Usage &amp; cost</CardTitle>
          <CardDescription>
            The cascade routes most candidates through free and cheap tiers, so only the
            hard cases reach the deep model — keeping spend low.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {loading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full rounded-lg" />
              ))}
            </div>
          ) : usage ? (
            <>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  icon={<DollarSign className="h-5 w-5" />}
                  label="Cost today"
                  value={formatUsd(usage.today_cost_usd)}
                />
                <StatCard
                  icon={<Activity className="h-5 w-5" />}
                  label="Last 7 days"
                  value={formatUsd(usage.last_7_days_cost_usd)}
                />
                <StatCard
                  icon={<Zap className="h-5 w-5" />}
                  label="Total calls"
                  value={usage.total_calls.toLocaleString()}
                />
                <StatCard
                  icon={<Database className="h-5 w-5" />}
                  label="Cache hit rate"
                  value={`${Math.round(usage.cache_hit_rate * 100)}%`}
                />
              </div>

              <div>
                <p className="mb-3 text-sm font-medium">Cost over time</p>
                {chartData.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No usage recorded yet.</p>
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4 }}
                    className="h-64 w-full"
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                        <XAxis
                          dataKey="date"
                          tickLine={false}
                          axisLine={false}
                          style={{ fontSize: 12 }}
                          stroke="hsl(var(--muted-foreground))"
                        />
                        <YAxis
                          tickLine={false}
                          axisLine={false}
                          style={{ fontSize: 12 }}
                          stroke="hsl(var(--muted-foreground))"
                          tickFormatter={(v: number) => formatUsd(v)}
                        />
                        <Tooltip
                          cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }}
                          contentStyle={{
                            background: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: 8,
                            fontSize: 12,
                            color: "hsl(var(--foreground))",
                          }}
                          formatter={(v: number) => [formatUsd(v), "Cost"]}
                        />
                        <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
                          {chartData.map((_, i) => (
                            <Cell key={i} fill="hsl(var(--primary))" />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </motion.div>
                )}
              </div>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <div>
                  <p className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <Layers className="h-4 w-4 text-primary" /> By cascade tier
                  </p>
                  <BreakdownList
                    entries={Object.entries(usage.by_tier)}
                    labelFor={(k) => TIER_LABELS[k] ?? `Tier ${k}`}
                    suffix=" calls"
                  />
                </div>
                <div>
                  <p className="mb-3 flex items-center gap-2 text-sm font-medium">
                    <Zap className="h-4 w-4 text-primary" /> By model
                  </p>
                  <BreakdownList
                    entries={Object.entries(usage.by_model)}
                    labelFor={(k) => k}
                    suffix=" calls"
                  />
                </div>
              </div>
            </>
          ) : (
            <p className="text-sm text-danger">{error || "Unable to load usage."}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function BreakdownList({
  entries,
  labelFor,
  suffix,
}: {
  entries: [string, number][];
  labelFor: (key: string) => string;
  suffix: string;
}) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">No data yet.</p>;
  }
  const max = Math.max(...entries.map(([, v]) => v), 1);
  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="space-y-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{labelFor(key)}</span>
            <span className="font-medium tabular-nums">
              {value.toLocaleString()}
              {suffix}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
            <div
              className={cn("h-full rounded-full bg-primary transition-all")}
              style={{ width: `${(value / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

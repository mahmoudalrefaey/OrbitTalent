import { NavLink, Outlet, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart3,
  Briefcase,
  LayoutDashboard,
  Search,
  Settings,
  Users,
  XCircle,
  Zap,
} from "lucide-react";
import { api } from "@/api/client";
import { cn } from "@/lib/utils";

const TABS = [
  { to: "overview", label: "Overview", icon: LayoutDashboard },
  { to: "candidates", label: "Candidates", icon: Users },
  { to: "analytics", label: "Analytics", icon: BarChart3 },
  { to: "skill-gaps", label: "Skill Gaps", icon: Search },
  { to: "interviews", label: "Interviews", icon: Briefcase },
  { to: "rejected", label: "Rejected", icon: XCircle },
  { to: "automation", label: "Automation", icon: Zap },
  { to: "settings", label: "Settings", icon: Settings },
];

/** Tabbed shell for a single job workspace (nested under /app/jobs/:id). */
export function JobLayout() {
  const { jobId } = useParams();
  const id = Number(jobId);
  const { data: job } = useQuery({
    queryKey: ["job", id],
    queryFn: () => api.getJob(id),
    enabled: !Number.isNaN(id),
  });

  return (
    <div className="space-y-6">
      <div>
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Job workspace
        </div>
        <h1 className="text-2xl font-bold tracking-tight">
          {job?.title ?? "…"}
        </h1>
      </div>

      {/* Tab bar — horizontally scrollable on small screens. */}
      <div className="-mx-1 overflow-x-auto">
        <nav className="flex gap-1 border-b border-border px-1">
          {TABS.map((t) => (
            <NavLink
              key={t.to}
              to={`/app/jobs/${id}/${t.to}`}
              className={({ isActive }) =>
                cn(
                  "flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "border-primary text-primary"
                    : "border-transparent text-muted-foreground hover:text-foreground"
                )
              }
            >
              <t.icon className="h-4 w-4" />
              {t.label}
            </NavLink>
          ))}
        </nav>
      </div>

      <Outlet />
    </div>
  );
}

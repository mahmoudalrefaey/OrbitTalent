import { Route, Routes } from "react-router-dom";
import { MarketingLayout } from "@/components/marketing-layout";
import { AppLayout } from "@/components/app-layout";
import { JobLayout } from "@/components/job-layout";
import { RequireAuth } from "@/components/require-auth";
import Landing from "@/pages/Landing";
import Pricing from "@/pages/Pricing";
import Onboarding from "@/pages/Onboarding";
import SignIn from "@/pages/SignIn";
import SignUp from "@/pages/SignUp";
import Dashboard from "@/pages/Dashboard";
import JobsList from "@/pages/JobsList";
import JobSetup from "@/pages/JobSetup";
import JobOverview from "@/pages/JobOverview";
import CandidatesDashboard from "@/pages/CandidatesDashboard";
import CandidateDetail from "@/pages/CandidateDetail";
import Analytics from "@/pages/Analytics";
import SkillGaps from "@/pages/SkillGaps";
import Interviews from "@/pages/Interviews";
import Rejected from "@/pages/Rejected";
import Automation from "@/pages/Automation";
import SearchPage from "@/pages/Search";
import Compare from "@/pages/Compare";
import Settings from "@/pages/Settings";
import NotFound from "@/pages/NotFound";

export default function App() {
  return (
    <Routes>
      {/* Public marketing */}
      <Route element={<MarketingLayout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/pricing" element={<Pricing />} />
      </Route>

      {/* Public auth */}
      <Route path="/signin" element={<SignIn />} />
      <Route path="/signup" element={<SignUp />} />

      {/* Authenticated routes */}
      <Route element={<RequireAuth />}>
        {/* Standalone onboarding wizard (own chrome) */}
        <Route path="/onboarding" element={<Onboarding />} />

        <Route path="/app" element={<AppLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="jobs" element={<JobsList />} />
          <Route path="settings" element={<Settings />} />
          <Route path="search" element={<SearchPage />} />
          <Route path="compare" element={<Compare />} />

          {/* Candidate detail stands alone (full width, no tab chrome). */}
          <Route
            path="jobs/:jobId/candidates/:candidateId"
            element={<CandidateDetail />}
          />

          {/* Tabbed job workspace. */}
          <Route path="jobs/:jobId" element={<JobLayout />}>
            <Route index element={<JobOverview />} />
            <Route path="overview" element={<JobOverview />} />
            <Route path="candidates" element={<CandidatesDashboard />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="skill-gaps" element={<SkillGaps />} />
            <Route path="interviews" element={<Interviews />} />
            <Route path="rejected" element={<Rejected />} />
            <Route path="automation" element={<Automation />} />
            <Route path="settings" element={<JobSetup />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

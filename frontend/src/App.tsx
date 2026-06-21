import { Route, Routes } from "react-router-dom";
import { MarketingLayout } from "@/components/marketing-layout";
import { AppLayout } from "@/components/app-layout";
import { RequireAuth } from "@/components/require-auth";
import Landing from "@/pages/Landing";
import Pricing from "@/pages/Pricing";
import Onboarding from "@/pages/Onboarding";
import SignIn from "@/pages/SignIn";
import SignUp from "@/pages/SignUp";
import JobsList from "@/pages/JobsList";
import JobSetup from "@/pages/JobSetup";
import CandidatesDashboard from "@/pages/CandidatesDashboard";
import CandidateDetail from "@/pages/CandidateDetail";
import Analytics from "@/pages/Analytics";
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
          <Route index element={<JobsList />} />
          <Route path="settings" element={<Settings />} />
          <Route path="jobs/:jobId/setup" element={<JobSetup />} />
          <Route path="jobs/:jobId/candidates" element={<CandidatesDashboard />} />
          <Route
            path="jobs/:jobId/candidates/:candidateId"
            element={<CandidateDetail />}
          />
          <Route path="jobs/:jobId/analytics" element={<Analytics />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

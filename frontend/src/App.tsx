import { NavLink, Route, Routes, useParams } from "react-router-dom";
import JobsList from "./pages/JobsList";
import JobSetup from "./pages/JobSetup";
import CandidatesDashboard from "./pages/CandidatesDashboard";
import CandidateDetail from "./pages/CandidateDetail";
import Analytics from "./pages/Analytics";

// Per-job sub-nav lives in the sidebar when a job is selected.
function JobNav() {
  const { jobId } = useParams();
  if (!jobId) return null;
  return (
    <nav style={{ marginTop: 20, borderTop: "1px solid var(--border)", paddingTop: 16 }}>
      <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>THIS JOB</div>
      <NavLink to={`/jobs/${jobId}/setup`}>Setup &amp; criteria</NavLink>
      <NavLink to={`/jobs/${jobId}/candidates`}>Candidates</NavLink>
      <NavLink to={`/jobs/${jobId}/analytics`}>Analytics</NavLink>
    </nav>
  );
}

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <h1>🛰️ OrbitTalent</h1>
        <nav>
          <NavLink to="/" end>Jobs</NavLink>
        </nav>
        <Routes>
          <Route path="/jobs/:jobId/*" element={<JobNav />} />
        </Routes>
      </aside>
      <main className="main">
        <Routes>
          <Route path="/" element={<JobsList />} />
          <Route path="/jobs/:jobId/setup" element={<JobSetup />} />
          <Route path="/jobs/:jobId/candidates" element={<CandidatesDashboard />} />
          <Route path="/jobs/:jobId/candidates/:candidateId" element={<CandidateDetail />} />
          <Route path="/jobs/:jobId/analytics" element={<Analytics />} />
        </Routes>
      </main>
    </div>
  );
}

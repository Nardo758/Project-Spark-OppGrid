import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import RequireAuth from './components/RequireAuth'
import RequireTier from './components/RequireTier'
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Discover from './pages/Discover'
import IdeaEngine from './pages/IdeaEngine'
import Pricing from './pages/Pricing'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Services from './pages/Services'
import Network from './pages/Network'
import JoinNetwork from './pages/JoinNetwork'
import ExpertApplication from './pages/ExpertApplication'
import Leads from './pages/Leads'
import Funding from './pages/Funding'
import Tools from './pages/Tools'
import Learn from './pages/Learn'
import AIRoadmap from './pages/AIRoadmap'
import AIMatch from './pages/AIMatch'
import ExpertMarketplace from './pages/ExpertMarketplace'
import ExpertDashboard from './pages/ExpertDashboard'
import MyEngagements from './pages/MyEngagements'
import About from './pages/About'
import Blog from './pages/Blog'
import Contact from './pages/Contact'
import Terms from './pages/Terms'
import Privacy from './pages/Privacy'
import BrainDashboard from './pages/brain/BrainDashboard'
import AuthCallback from './pages/AuthCallback'
import OAuthCallback from './pages/OAuthCallback'
import MagicLinkCallback from './pages/MagicLinkCallback'
import Saved from './pages/Saved'
import OpportunityDetail from './pages/OpportunityDetail'
import ReportStudio from './pages/build/ReportStudio'
import ConsultantStudio from './pages/build/ConsultantStudio'
import ApiPortal from './pages/ApiPortal'
import Settings from './pages/Settings'
import SettingsApiKeys from './pages/SettingsApiKeys'
import Projects from './pages/Projects'
import MyWorkspaces from './pages/MyWorkspaces'
import WorkspacePage from './pages/Workspace'
import OpportunityHub from './pages/OpportunityHub'
import WorkHub from './pages/WorkHub'
import AdminMarketing from './pages/AdminMarketing'
import AdminExperts from './pages/AdminExperts'
import AdminAffiliateTools from './pages/AdminAffiliateTools'
import StripeArchitecture from './pages/StripeArchitecture'
import BillingReturn from './pages/BillingReturn'
import PublicReportViewer from './pages/PublicReportViewer'
import MapWorkspace from './pages/MapWorkspace'
import MyIdeas from './pages/MyIdeas'
import LifecycleDashboard from './pages/LifecycleDashboard'

function AdminRedirect() {
  window.location.href = '/admin.html';
  return null;
}

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <ErrorBoundary>
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={isAuthenticated ? <Dashboard /> : <Home />} />
        <Route path="welcome" element={<Home />} />
        <Route path="discover" element={<Discover />} />
        <Route path="idea-engine" element={<IdeaEngine />} />
        <Route path="services" element={<Services />} />
        <Route path="network" element={<Navigate to="/network/experts" />} />
        <Route path="pricing" element={<Pricing />} />
        <Route path="opportunity/:id" element={<OpportunityDetail />} />
        <Route
          path="opportunity/:id/hub"
          element={
            <RequireAuth>
              <WorkHub />
            </RequireAuth>
          }
        />
        <Route
          path="opportunity/:id/hub-legacy"
          element={
            <RequireAuth>
              <OpportunityHub />
            </RequireAuth>
          }
        />
        <Route
          path="opportunity/:opportunityId/map"
          element={
            <RequireAuth>
              <MapWorkspace />
            </RequireAuth>
          }
        />
        <Route
          path="map-workspace"
          element={
            <RequireAuth>
              <MapWorkspace />
            </RequireAuth>
          }
        />
        <Route path="login" element={<Login />} />
        <Route path="signup" element={<Signup />} />
        <Route path="leads" element={<Leads />} />
        <Route path="tools" element={<Tools />} />
        <Route path="learn" element={<Learn />} />
        <Route path="ai-roadmap" element={<AIRoadmap />} />
        <Route path="ai-match" element={<AIMatch />} />
        <Route path="developer" element={<ApiPortal />} />
        <Route path="about" element={<About />} />
        <Route path="blog" element={<Blog />} />
        <Route path="contact" element={<Contact />} />
        <Route path="terms" element={<Terms />} />
        <Route path="privacy" element={<Privacy />} />
        <Route
          path="saved"
          element={
            <RequireAuth>
              <Saved />
            </RequireAuth>
          }
        />
        <Route
          path="dashboard"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="brain"
          element={
            <RequireAuth>
              <BrainDashboard />
            </RequireAuth>
          }
        />
        <Route path="build/reports" element={<ReportStudio />} />
        <Route path="build/reports/:type" element={<ReportStudio />} />
        <Route path="build/business-plan" element={<ReportStudio />} />
        <Route path="build/financials" element={<ReportStudio />} />
        <Route path="build/pitch-deck" element={<ReportStudio />} />
        <Route path="build/consultant-studio" element={<ConsultantStudio />} />
        <Route
          path="build/experts"
          element={
            <RequireTier requiredTier="starter" featureName="Expert Marketplace">
              <ExpertMarketplace />
            </RequireTier>
          }
        />
        <Route
          path="expert/dashboard"
          element={
            <RequireAuth>
              <ExpertDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="expert/connect/complete"
          element={
            <RequireAuth>
              <ExpertDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="expert/connect/refresh"
          element={
            <RequireAuth>
              <ExpertDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="build/engagements"
          element={
            <RequireAuth>
              <MyEngagements />
            </RequireAuth>
          }
        />
        <Route
          path="build/funding"
          element={
            <RequireTier requiredTier="starter" featureName="Funding Discovery">
              <Funding />
            </RequireTier>
          }
        />
        <Route
          path="settings"
          element={
            <RequireAuth>
              <Settings />
            </RequireAuth>
          }
        />
        <Route
          path="settings/api"
          element={
            <RequireAuth>
              <SettingsApiKeys />
            </RequireAuth>
          }
        />
        <Route
          path="projects"
          element={
            <RequireAuth>
              <Projects />
            </RequireAuth>
          }
        />
        <Route
          path="workspaces"
          element={
            <RequireAuth>
              <MyWorkspaces />
            </RequireAuth>
          }
        />
        <Route
          path="workspace/:id"
          element={
            <RequireAuth>
              <WorkspacePage />
            </RequireAuth>
          }
        />
        <Route path="network/:tab" element={<Network />} />
        <Route path="join-network/:role" element={<JoinNetwork />} />
        <Route path="expert/apply" element={<ExpertApplication />} />
        <Route path="auth/callback" element={<AuthCallback />} />
        <Route path="auth/oauth-callback" element={<OAuthCallback />} />
        <Route path="auth/magic" element={<MagicLinkCallback />} />
        <Route path="billing/return" element={<BillingReturn />} />
        <Route path="reports/view/:reportId" element={<PublicReportViewer />} />
        <Route path="admin" element={<RequireAuth><AdminRedirect /></RequireAuth>} />
        <Route path="admin/marketing" element={<AdminMarketing />} />
        <Route path="admin/experts" element={<AdminExperts />} />
        <Route path="admin/affiliate-tools" element={<AdminAffiliateTools />} />
        <Route path="architecture/stripe" element={<StripeArchitecture />} />
        <Route
          path="my-ideas"
          element={
            <RequireAuth>
              <MyIdeas />
            </RequireAuth>
          }
        />
        <Route
          path="lifecycle"
          element={
            <RequireAuth>
              <LifecycleDashboard />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Route>
    </Routes>
    </ErrorBoundary>
  )
}

export default App

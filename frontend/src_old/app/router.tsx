import { Routes, Route, Navigate } from 'react-router-dom'
import AppShell from './layout/AppShell'
import LoginPage from '../pages/auth/LoginPage'
import DashboardPage from '../pages/dashboard/DashboardPage'
import ScansPage from '../pages/scans/ScansPage'
import IncidentsPage from '../pages/incidents/IncidentsPage'
import TimelinePage from '../pages/timeline/TimelinePage'
import SessionsPage from '../pages/sessions/SessionsPage'
import PoliciesPage from '../pages/policies/PoliciesPage'
import RulesPage from '../pages/rules/RulesPage'
import TenantsPage from '../pages/tenants/TenantsPage'
import ApiKeysPage from '../pages/apiKeys/ApiKeysPage'
import ReportsPage from '../pages/reports/ReportsPage'
import UnauthorizedPage from '../pages/system/UnauthorizedPage'
import NotFoundPage from '../pages/system/NotFoundPage'
import { useAuth } from '../hooks/useAuth'

const PrivateRoute = ({ children }: { children: JSX.Element }) => {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? children : <Navigate to="/login" />
}

const AppRouter = () => {
  return (
	<Routes>
	  <Route path="/" element={<Navigate to="/dashboard" />} />
	  <Route path="/dashboard" element={<DashboardPage />} />
	  <Route path="/scans" element={<ScansPage />} />
	  <Route path="/incidents" element={<IncidentsPage />} />
	  <Route path="/timeline" element={<TimelinePage />} />
	  <Route path="/sessions" element={<SessionsPage />} />
	  <Route path="/policies" element={<PoliciesPage />} />
	  <Route path="/rules" element={<RulesPage />} />
	  <Route path="/tenants" element={<TenantsPage />} />
	  <Route path="/api-keys" element={<ApiKeysPage />} />
	  <Route path="/reports" element={<ReportsPage />} />
	</Routes>
  )
}

export default AppRouter

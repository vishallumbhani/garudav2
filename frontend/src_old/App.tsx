import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import DashboardPage from './pages/dashboard/DashboardPage'
import ScansPage from './pages/scans/ScansPage'
import IncidentsPage from './pages/incidents/IncidentsPage'
import TimelinePage from './pages/timeline/TimelinePage'
import SessionsPage from './pages/sessions/SessionsPage'
import PoliciesPage from './pages/policies/PoliciesPage'
import RulesPage from './pages/rules/RulesPage'
import TenantsPage from './pages/tenants/TenantsPage'
import ApiKeysPage from './pages/apiKeys/ApiKeysPage'
import ReportsPage from './pages/reports/ReportsPage'
import AlertsPage from './pages/alerts/AlertsPage'
import UsersPage from './pages/admin/UsersPage'
import LoginPage from './pages/auth/LoginPage'
import Sidebar from './components/layout/Sidebar'
import Topbar from './components/layout/Topbar'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

function PrivateRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { isAuthenticated, isLoading, hasRole } = useAuth()
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (roles && !hasRole(roles)) return <Navigate to="/unauthorized" replace />
  return <>{children}</>
}

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-gray-950">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  )
}

function AppRoutes() {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route
          path="/login"
          element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />}
        />

        {/* Protected */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={
          <PrivateRoute><Layout><DashboardPage /></Layout></PrivateRoute>
        } />
        <Route path="/scans" element={
          <PrivateRoute><Layout><ScansPage /></Layout></PrivateRoute>
        } />
        <Route path="/incidents" element={
          <PrivateRoute><Layout><IncidentsPage /></Layout></PrivateRoute>
        } />
        <Route path="/timeline" element={
          <PrivateRoute><Layout><TimelinePage /></Layout></PrivateRoute>
        } />
        <Route path="/sessions" element={
          <PrivateRoute><Layout><SessionsPage /></Layout></PrivateRoute>
        } />
        <Route path="/policies" element={
          <PrivateRoute roles={['admin', 'operator']}><Layout><PoliciesPage /></Layout></PrivateRoute>
        } />
        <Route path="/rules" element={
          <PrivateRoute roles={['admin', 'operator']}><Layout><RulesPage /></Layout></PrivateRoute>
        } />
        <Route path="/tenants" element={
          <PrivateRoute roles={['admin']}><Layout><TenantsPage /></Layout></PrivateRoute>
        } />
        <Route path="/api-keys" element={
          <PrivateRoute roles={['admin']}><Layout><ApiKeysPage /></Layout></PrivateRoute>
        } />
        <Route path="/reports" element={
          <PrivateRoute><Layout><ReportsPage /></Layout></PrivateRoute>
        } />
        <Route path="/alerts" element={
          <PrivateRoute><Layout><AlertsPage /></Layout></PrivateRoute>
        } />
        <Route path="/admin/users" element={
          <PrivateRoute roles={['admin']}><Layout><UsersPage /></Layout></PrivateRoute>
        } />
        <Route path="/unauthorized" element={
          <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white">
            <div className="text-center">
              <h1 className="text-4xl font-bold mb-2">403</h1>
              <p className="text-gray-400">You don't have permission to access this page.</p>
            </div>
          </div>
        } />
        <Route path="*" element={
          <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white">
            <div className="text-center">
              <h1 className="text-4xl font-bold mb-2">404</h1>
              <p className="text-gray-400">Page not found.</p>
            </div>
          </div>
        } />
      </Routes>
    </BrowserRouter>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App

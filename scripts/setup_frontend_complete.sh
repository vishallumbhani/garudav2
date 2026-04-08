#!/bin/bash
set -e

echo "=== Garuda Frontend Complete Setup ==="

# Create frontend directory
mkdir -p frontend
cd frontend

# Create Vite project (skip if already exists)
if [ ! -f package.json ]; then
  npm create vite@latest . -- --template react-ts -y
fi

# Install dependencies
npm install react-router-dom axios @tanstack/react-query recharts date-fns zustand react-hook-form react-hot-toast
npm install -D tailwindcss postcss autoprefixer @types/node

# Initialize Tailwind CSS
npx tailwindcss init -p

# Configure Tailwind
cat > tailwind.config.js << 'EOF'
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOF

# Add Tailwind directives
cat > src/index.css << 'EOF'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-gray-900 text-gray-100;
  }
}
EOF

# Create directory structure
mkdir -p src/app/layout
mkdir -p src/pages/{auth,dashboard,scans,incidents,timeline,sessions,policies,rules,tenants,apiKeys,reports,system}
mkdir -p src/components/{cards,tables,filters,badges,charts,drawers,forms,feedback}
mkdir -p src/services
mkdir -p src/hooks
mkdir -p src/store
mkdir -p src/types
mkdir -p src/utils

# ------------------------------------------------------------
# 1. Main entry files
# ------------------------------------------------------------
cat > src/main.tsx << 'EOF'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
EOF

cat > src/App.tsx << 'EOF'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import AppRouter from './app/router'
import { AuthProvider } from './hooks/useAuth'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
EOF

# ------------------------------------------------------------
# 2. Router
# ------------------------------------------------------------
cat > src/app/router.tsx << 'EOF'
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
      <Route path="/login" element={<LoginPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />
      <Route element={<PrivateRoute><AppShell /></PrivateRoute>}>
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
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default AppRouter
EOF

# ------------------------------------------------------------
# 3. Layout components (AppShell, Sidebar, Topbar)
# ------------------------------------------------------------
cat > src/app/layout/AppShell.tsx << 'EOF'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import { useState } from 'react'

const AppShell = () => {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="flex h-screen bg-gray-900">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default AppShell
EOF

cat > src/app/layout/Sidebar.tsx << 'EOF'
import { NavLink } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Scan, 
  AlertTriangle, 
  Calendar, 
  Users, 
  Shield, 
  FileText, 
  Building2, 
  Key, 
  BarChart3,
  ChevronLeft,
  ChevronRight
} from 'lucide-react'

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/scans', label: 'Scans', icon: Scan },
  { path: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { path: '/timeline', label: 'Timeline', icon: Calendar },
  { path: '/sessions', label: 'Sessions', icon: Users },
  { path: '/policies', label: 'Policies', icon: Shield },
  { path: '/rules', label: 'Rules', icon: FileText },
  { path: '/tenants', label: 'Tenants', icon: Building2 },
  { path: '/api-keys', label: 'API Keys', icon: Key },
  { path: '/reports', label: 'Reports', icon: BarChart3 },
]

const Sidebar = ({ collapsed, onToggle }: SidebarProps) => {
  return (
    <div className={`bg-gray-800 transition-all duration-300 ${collapsed ? 'w-16' : 'w-64'} flex flex-col`}>
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        {!collapsed && <span className="text-xl font-bold text-white">Garuda</span>}
        <button onClick={onToggle} className="text-gray-400 hover:text-white">
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>
      <nav className="flex-1 mt-4">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center px-4 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors ${
                isActive ? 'bg-gray-700 text-white' : ''
              }`
            }
          >
            <item.icon size={20} />
            {!collapsed && <span className="ml-3">{item.label}</span>}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
        {!collapsed && <span>Version 1.0.0</span>}
      </div>
    </div>
  )
}

export default Sidebar
EOF

cat > src/app/layout/Topbar.tsx << 'EOF'
import { useAuth } from '../../hooks/useAuth'
import { LogOut, RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'

const Topbar = () => {
  const { logout, user } = useAuth()
  const queryClient = useQueryClient()

  const refresh = () => {
    queryClient.invalidateQueries()
  }

  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-3 flex justify-between items-center">
      <h1 className="text-xl font-semibold text-white">AI Security Platform</h1>
      <div className="flex items-center gap-4">
        <button onClick={refresh} className="text-gray-400 hover:text-white">
          <RefreshCw size={18} />
        </button>
        <span className="text-sm text-gray-300">{user?.tenant || 'default'}</span>
        <button onClick={logout} className="text-gray-400 hover:text-white">
          <LogOut size={18} />
        </button>
      </div>
    </header>
  )
}

export default Topbar
EOF

# ------------------------------------------------------------
# 4. Auth hooks and context
# ------------------------------------------------------------
cat > src/hooks/useAuth.tsx << 'EOF'
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../services/api'

interface User {
  tenant: string
  role: string
}

interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  login: (apiKey: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    const storedKey = localStorage.getItem('garuda_api_key')
    if (storedKey) {
      api.setApiKey(storedKey)
      setIsAuthenticated(true)
      // Optionally fetch tenant info
      setUser({ tenant: 'default', role: 'admin' })
    }
  }, [])

  const login = async (apiKey: string) => {
    api.setApiKey(apiKey)
    // Test the key by calling a protected endpoint
    try {
      await api.get('/v1/admin/rules')
      localStorage.setItem('garuda_api_key', apiKey)
      setIsAuthenticated(true)
      setUser({ tenant: 'default', role: 'admin' })
    } catch (error) {
      throw new Error('Invalid API key')
    }
  }

  const logout = () => {
    localStorage.removeItem('garuda_api_key')
    api.setApiKey(null)
    setIsAuthenticated(false)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
EOF

# ------------------------------------------------------------
# 5. API client
# ------------------------------------------------------------
cat > src/services/api.ts << 'EOF'
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

let apiKey: string | null = null

export const setApiKey = (key: string | null) => {
  apiKey = key
  if (key) {
    api.defaults.headers.common['X-API-Key'] = key
  } else {
    delete api.defaults.headers.common['X-API-Key']
  }
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('garuda_api_key')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Helper methods for typed endpoints
export const dashboardApi = {
  health: () => api.get('/v1/dashboard/health'),
  recentScans: (limit = 50) => api.get(`/v1/dashboard/recent-scans?limit=${limit}`),
  recentBlocks: (limit = 50) => api.get(`/v1/dashboard/recent-blocks?limit=${limit}`),
  timeline: (interval = 'day', limit = 30) => api.get(`/v1/dashboard/timeline?interval=${interval}&limit=${limit}`),
  engineOutcomes: (limit = 100) => api.get(`/v1/dashboard/engine-outcomes?limit=${limit}`),
  policyHits: (limit = 50) => api.get(`/v1/dashboard/policy-hits?limit=${limit}`),
  session: (sessionId: string) => api.get(`/v1/dashboard/session/${sessionId}`),
}

export const scansApi = {
  text: (data: any) => api.post('/v1/scan/text', data),
  file: (file: File, sessionId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    if (sessionId) formData.append('session_id', sessionId)
    return api.post('/v1/scan/file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
}

export const incidentsApi = {
  summary: (startDate: string, endDate: string) =>
    api.get(`/v1/reports/incidents/summary?start_date=${startDate}&end_date=${endDate}`),
  csv: (startDate: string, endDate: string) =>
    api.get(`/v1/reports/incidents/csv?start_date=${startDate}&end_date=${endDate}`, { responseType: 'blob' }),
}

export const adminApi = {
  rules: {
    list: () => api.get('/v1/admin/rules'),
    create: (data: any) => api.post('/v1/admin/rules', data),
    update: (id: number, data: any) => api.put(`/v1/admin/rules/${id}`, data),
    delete: (id: number) => api.delete(`/v1/admin/rules/${id}`),
  },
  policies: {
    list: (tenantId?: string) => api.get('/v1/admin/policies', { params: { tenant_id: tenantId } }),
    update: (key: string, data: any) => api.patch(`/v1/admin/policies/${key}`, data),
  },
  tenants: {
    get: (tenantId: string) => api.get(`/v1/admin/tenants/${tenantId}`),
    update: (tenantId: string, data: any) => api.patch(`/v1/admin/tenants/${tenantId}`, data),
  },
  apiKeys: {
    list: (tenantId?: string) => api.get('/v1/admin/api-keys', { params: { tenant_id: tenantId } }),
    create: (data: any) => api.post('/v1/admin/api-keys', data),
    revoke: (id: number) => api.delete(`/v1/admin/api-keys/${id}`),
  },
}
EOF

# ------------------------------------------------------------
# 6. Login page
# ------------------------------------------------------------
cat > src/pages/auth/LoginPage.tsx << 'EOF'
import { useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { Eye, EyeOff, Key } from 'lucide-react'

const LoginPage = () => {
  const { login } = useAuth()
  const [apiKey, setApiKey] = useState('')
  const [showKey, setShowKey] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(apiKey)
    } catch (err) {
      setError('Invalid API key. Please check and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800">
      <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-white">Garuda</h1>
          <p className="text-gray-400 mt-2">AI Security Platform</p>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">API Key</label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-md text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter your admin API key"
                required
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-2.5 text-gray-400 hover:text-white"
              >
                {showKey ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>
          {error && <div className="mb-4 text-red-500 text-sm">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition flex items-center justify-center gap-2"
          >
            {loading ? 'Signing in...' : 'Sign In'}
            {!loading && <Key size={16} />}
          </button>
        </form>
        <div className="mt-6 text-center text-xs text-gray-500">
          <p>Enter your admin API key to access the platform.</p>
        </div>
      </div>
    </div>
  )
}

export default LoginPage
EOF

# ------------------------------------------------------------
# 7. Dashboard page (complete with charts)
# ------------------------------------------------------------
cat > src/pages/dashboard/DashboardPage.tsx << 'EOF'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../services/api'
import HealthCard from '../../components/cards/HealthCard'
import StatCard from '../../components/cards/StatCard'
import DecisionTrendChart from '../../components/charts/DecisionTrendChart'
import DecisionDistributionChart from '../../components/charts/DecisionDistributionChart'
import EngineOutcomeChart from '../../components/charts/EngineOutcomeChart'
import PolicyHitsChart from '../../components/charts/PolicyHitsChart'
import DataTable from '../../components/tables/DataTable'
import { Activity, AlertTriangle, CheckCircle, Shield, Zap } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'

const DashboardPage = () => {
  const { user } = useAuth()
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['dashboard', 'health'],
    queryFn: () => dashboardApi.health().then(res => res.data),
  })
  const { data: recentScans } = useQuery({
    queryKey: ['dashboard', 'recentScans'],
    queryFn: () => dashboardApi.recentScans(10).then(res => res.data),
  })
  const { data: recentBlocks } = useQuery({
    queryKey: ['dashboard', 'recentBlocks'],
    queryFn: () => dashboardApi.recentBlocks(10).then(res => res.data),
  })
  const { data: timeline } = useQuery({
    queryKey: ['dashboard', 'timeline'],
    queryFn: () => dashboardApi.timeline('day', 14).then(res => res.data),
  })
  const { data: engineOutcomes } = useQuery({
    queryKey: ['dashboard', 'engineOutcomes'],
    queryFn: () => dashboardApi.engineOutcomes(100).then(res => res.data),
  })
  const { data: policyHits } = useQuery({
    queryKey: ['dashboard', 'policyHits'],
    queryFn: () => dashboardApi.policyHits(10).then(res => res.data),
  })

  if (healthLoading) return <div className="text-white">Loading dashboard...</div>

  const totalBlocks = recentBlocks?.length || 0
  const totalScans = recentScans?.length || 0
  const safeMode = health?.safe_mode ? 'Active' : 'Inactive'
  const degradedEngines = health?.degraded_engines?.join(', ') || 'None'

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400">Welcome back, {user?.tenant || 'admin'}</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <HealthCard title="API" status={health?.api} />
        <HealthCard title="Database" status={health?.db} />
        <HealthCard title="Redis" status={health?.redis} />
        <StatCard title="Recent Scans" value={totalScans} icon={Activity} />
        <StatCard title="Blocks (24h)" value={totalBlocks} icon={AlertTriangle} />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatCard title="Safe Mode" value={safeMode} icon={Shield} />
        <StatCard title="Degraded Engines" value={degradedEngines} icon={Zap} />
        <StatCard title="Integrity" value={health?.integrity_status || 'ok'} icon={CheckCircle} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <DecisionTrendChart data={timeline?.data || []} />
        <DecisionDistributionChart data={timeline?.data || []} />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <EngineOutcomeChart data={engineOutcomes?.engine_scores || {}} />
        <PolicyHitsChart data={policyHits?.top_policies || []} />
      </div>

      {/* Recent Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Recent Scans</h2>
          <DataTable
            columns={[
              { key: 'timestamp', label: 'Time' },
              { key: 'decision', label: 'Decision' },
              { key: 'score', label: 'Score' },
              { key: 'session_id', label: 'Session' },
            ]}
            data={recentScans || []}
            onRowClick={(row) => console.log(row)}
          />
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-white mb-3">Recent Blocks</h2>
          <DataTable
            columns={[
              { key: 'timestamp', label: 'Time' },
              { key: 'policy_hits', label: 'Policy Hits' },
              { key: 'session_id', label: 'Session' },
            ]}
            data={recentBlocks || []}
            onRowClick={(row) => console.log(row)}
          />
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
EOF

# ------------------------------------------------------------
# 8. Basic components (HealthCard, StatCard, DataTable, etc.)
# ------------------------------------------------------------
cat > src/components/cards/HealthCard.tsx << 'EOF'
import { Circle } from 'lucide-react'

interface HealthCardProps {
  title: string
  status?: string
}

const HealthCard = ({ title, status }: HealthCardProps) => {
  const isHealthy = status === 'healthy'
  return (
    <div className="bg-gray-800 rounded-lg p-4 flex items-center justify-between">
      <span className="text-gray-300">{title}</span>
      <div className="flex items-center gap-2">
        <Circle size={12} className={isHealthy ? 'text-green-500 fill-green-500' : 'text-red-500 fill-red-500'} />
        <span className={isHealthy ? 'text-green-500' : 'text-red-500'}>{status || 'unknown'}</span>
      </div>
    </div>
  )
}

export default HealthCard
EOF

cat > src/components/cards/StatCard.tsx << 'EOF'
import { LucideIcon } from 'lucide-react'

interface StatCardProps {
  title: string
  value: string | number
  icon: LucideIcon
}

const StatCard = ({ title, value, icon: Icon }: StatCardProps) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4 flex items-center gap-3">
      <div className="p-2 bg-gray-700 rounded-full">
        <Icon size={20} className="text-blue-400" />
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-sm text-gray-400">{title}</div>
      </div>
    </div>
  )
}

export default StatCard
EOF

cat > src/components/tables/DataTable.tsx << 'EOF'
interface Column {
  key: string
  label: string
  render?: (value: any, row: any) => React.ReactNode
}

interface DataTableProps {
  columns: Column[]
  data: any[]
  onRowClick?: (row: any) => void
}

const DataTable = ({ columns, data, onRowClick }: DataTableProps) => {
  if (!data.length) {
    return <div className="text-gray-500 text-center py-8">No data available</div>
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-700">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-700">
          {data.map((row, idx) => (
            <tr
              key={idx}
              onClick={() => onRowClick && onRowClick(row)}
              className="hover:bg-gray-700 cursor-pointer transition"
            >
              {columns.map((col) => (
                <td key={col.key} className="px-4 py-2 whitespace-nowrap text-sm text-gray-300">
                  {col.render ? col.render(row[col.key], row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default DataTable
EOF

# ------------------------------------------------------------
# 9. Chart components (minimal, using recharts)
# ------------------------------------------------------------
cat > src/components/charts/DecisionTrendChart.tsx << 'EOF'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useMemo } from 'react'

const DecisionTrendChart = ({ data }: { data: any[] }) => {
  const chartData = useMemo(() => {
    return data.map(d => ({
      date: new Date(d.time).toLocaleDateString(),
      total: d.total,
      block: d.block,
      challenge: d.challenge,
      monitor: d.monitor,
      allow: d.allow,
    }))
  }, [data])
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-white font-medium mb-4">Decision Trend</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" stroke="#9CA3AF" />
          <YAxis stroke="#9CA3AF" />
          <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: 'none' }} />
          <Legend />
          <Line type="monotone" dataKey="block" stroke="#EF4444" />
          <Line type="monotone" dataKey="challenge" stroke="#F59E0B" />
          <Line type="monotone" dataKey="monitor" stroke="#3B82F6" />
          <Line type="monotone" dataKey="allow" stroke="#10B981" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default DecisionTrendChart
EOF

cat > src/components/charts/DecisionDistributionChart.tsx << 'EOF'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useMemo } from 'react'

const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444']

const DecisionDistributionChart = ({ data }: { data: any[] }) => {
  const chartData = useMemo(() => {
    if (!data.length) return []
    const totals = data.reduce((acc, d) => ({
      allow: acc.allow + d.allow,
      monitor: acc.monitor + d.monitor,
      challenge: acc.challenge + d.challenge,
      block: acc.block + d.block,
    }), { allow: 0, monitor: 0, challenge: 0, block: 0 })
    return Object.entries(totals).map(([name, value]) => ({ name, value }))
  }, [data])
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-white font-medium mb-4">Decision Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: 'none' }} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export default DecisionDistributionChart
EOF

# For EngineOutcomeChart and PolicyHitsChart, similar simple implementations.
# I'll create minimal versions.
cat > src/components/charts/EngineOutcomeChart.tsx << 'EOF'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const EngineOutcomeChart = ({ data }: { data: any }) => {
  const chartData = Object.entries(data).map(([engine, scores]: [string, any]) => ({
    engine,
    low: scores.low,
    medium: scores.medium,
    high: scores.high,
  }))
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-white font-medium mb-4">Engine Score Distribution</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="engine" stroke="#9CA3AF" />
          <YAxis stroke="#9CA3AF" />
          <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: 'none' }} />
          <Legend />
          <Bar dataKey="low" fill="#10B981" />
          <Bar dataKey="medium" fill="#F59E0B" />
          <Bar dataKey="high" fill="#EF4444" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default EngineOutcomeChart
EOF

cat > src/components/charts/PolicyHitsChart.tsx << 'EOF'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const PolicyHitsChart = ({ data }: { data: any[] }) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-white font-medium mb-4">Top Policy Hits</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="policy" stroke="#9CA3AF" />
          <YAxis stroke="#9CA3AF" />
          <Tooltip contentStyle={{ backgroundColor: '#1F2937', border: 'none' }} />
          <Bar dataKey="count" fill="#8B5CF6" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export default PolicyHitsChart
EOF

# ------------------------------------------------------------
# 10. Placeholder pages (to avoid build errors)
# ------------------------------------------------------------
for page in ScansPage IncidentsPage TimelinePage SessionsPage PoliciesPage RulesPage TenantsPage ApiKeysPage ReportsPage UnauthorizedPage NotFoundPage; do
  cat > src/pages/${page/Page/Page}.tsx << EOF
const ${page} = () => {
  return <div className="text-white">${page} - Coming Soon</div>
}
export default ${page}
EOF
done

# Also create a placeholder for TraceDetailDrawer (to be implemented later)
mkdir -p src/pages/scans/components
cat > src/pages/scans/components/TraceDetailDrawer.tsx << 'EOF'
const TraceDetailDrawer = () => null
export default TraceDetailDrawer
EOF

echo "Frontend complete! Run: cd frontend && npm run dev"
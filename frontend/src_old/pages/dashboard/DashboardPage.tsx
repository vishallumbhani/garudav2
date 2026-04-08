import { useQuery, useQueryClient } from '@tanstack/react-query'
import { dashboardApi, alertsApi } from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import { useLiveFeed } from '../../hooks/useWebSocket'
import {
  Activity, AlertTriangle, Shield, Database, Server, CheckCircle,
  Zap, Bell, TrendingUp, Radio
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, AreaChart, Area
} from 'recharts'
import DataTable from '../../components/tables/DataTable'
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const COLORS = ['#10B981', '#3B82F6', '#F59E0B', '#EF4444']

interface StatCardProps {
  title: string
  value: any
  icon: any
  color?: string
  subtitle?: string
  onClick?: () => void
}

const StatCard = ({ title, value, icon: Icon, color = 'blue', subtitle, onClick }: StatCardProps) => (
  <div
    onClick={onClick}
    className={`bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4 ${onClick ? 'cursor-pointer hover:border-gray-600 transition' : ''}`}
  >
    <div className={`p-2.5 bg-gray-800 rounded-xl text-${color}-400 shrink-0`}>
      <Icon size={20} />
    </div>
    <div>
      <p className="text-2xl font-bold text-white leading-none">{value ?? '—'}</p>
      <p className="text-xs text-gray-500 mt-0.5">{title}</p>
      {subtitle && <p className="text-xs text-gray-600 mt-0.5">{subtitle}</p>}
    </div>
  </div>
)

const decisionColors: Record<string, string> = {
  block: '#EF4444',
  challenge: '#F59E0B',
  monitor: '#3B82F6',
  allow: '#10B981',
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: <span className="font-semibold">{p.value}</span>
        </p>
      ))}
    </div>
  )
}

const LiveBadge = ({ connected }: { connected: boolean }) => (
  <div className={`flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border ${
    connected
      ? 'bg-green-950 border-green-800 text-green-400'
      : 'bg-gray-800 border-gray-700 text-gray-500'
  }`}>
    <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`} />
    {connected ? 'Live' : 'Offline'}
  </div>
)

const DashboardPage = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [liveEvents, setLiveEvents] = useState<any[]>([])

  const handleLiveScan = useCallback((event: any) => {
    setLiveEvents(prev => [event, ...prev].slice(0, 50))
    queryClient.invalidateQueries({ queryKey: ['recentScans'] })
  }, [queryClient])

  const handleLiveAlert = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['alertStats'] })
  }, [queryClient])

  const { connected } = useLiveFeed(handleLiveScan, handleLiveAlert)

  const { data: health } = useQuery({ queryKey: ['health'], queryFn: () => dashboardApi.health().then(r => r.data) })
  const { data: recentScans } = useQuery({ queryKey: ['recentScans'], queryFn: () => dashboardApi.recentScans(15).then(r => r.data) })
  const { data: recentBlocks } = useQuery({ queryKey: ['recentBlocks'], queryFn: () => dashboardApi.recentBlocks(15).then(r => r.data) })
  const { data: timeline } = useQuery({ queryKey: ['timeline', 'day', 14], queryFn: () => dashboardApi.timeline('day', 14).then(r => r.data) })
  const { data: engineOutcomes } = useQuery({ queryKey: ['engineOutcomes'], queryFn: () => dashboardApi.engineOutcomes(100).then(r => r.data) })
  const { data: policyHits } = useQuery({ queryKey: ['policyHits'], queryFn: () => dashboardApi.policyHits(10).then(r => r.data) })
  const { data: alertStats } = useQuery({ queryKey: ['alertStats'], queryFn: () => alertsApi.stats().then(r => r.data), refetchInterval: 30_000 })

  const timelineData = timeline?.data?.map((d: any) => ({
    date: new Date(d.time).toLocaleDateString('en-GB', { month: 'short', day: 'numeric' }),
    Block: d.block,
    Challenge: d.challenge,
    Monitor: d.monitor,
    Allow: d.allow,
    Total: d.total,
  })).reverse() || []

  const pieData = timelineData.length
    ? [
        { name: 'Allow',     value: timelineData.reduce((a: number, b: any) => a + b.Allow, 0) },
        { name: 'Monitor',   value: timelineData.reduce((a: number, b: any) => a + b.Monitor, 0) },
        { name: 'Challenge', value: timelineData.reduce((a: number, b: any) => a + b.Challenge, 0) },
        { name: 'Block',     value: timelineData.reduce((a: number, b: any) => a + b.Block, 0) },
      ].filter(d => d.value > 0)
    : []

  // Engine outcomes bar data
  const engineBarData = engineOutcomes?.engine_scores
    ? Object.entries(engineOutcomes.engine_scores).map(([engine, counts]: any) => ({
        engine: engine.charAt(0).toUpperCase() + engine.slice(1),
        Low: counts.low,
        Medium: counts.medium,
        High: counts.high,
      }))
    : []

  // Policy hits bar
  const policyBarData = policyHits?.top_policies?.slice(0, 8) || []

  const scanColumns = [
    { key: 'timestamp', label: 'Time', render: (v: string) => <span className="text-xs text-gray-400">{new Date(v).toLocaleTimeString()}</span> },
    {
      key: 'decision', label: 'Decision',
      render: (v: string) => (
        <span className={`text-xs font-semibold uppercase px-2 py-0.5 rounded-full ${
          v === 'block' ? 'bg-red-950 text-red-400 border border-red-800' :
          v === 'challenge' ? 'bg-yellow-950 text-yellow-400 border border-yellow-800' :
          v === 'monitor' ? 'bg-blue-950 text-blue-400 border border-blue-800' :
          'bg-green-950 text-green-400 border border-green-800'
        }`}>{v}</span>
      )
    },
    { key: 'score', label: 'Score', render: (v: number) => <span className="text-gray-400">{v}</span> },
    { key: 'session_id', label: 'Session', render: (v: string) => <span className="font-mono text-xs text-gray-500 truncate">{v?.slice(0, 8) || '—'}</span> },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-0.5">Welcome back, {user?.username}</p>
        </div>
        <LiveBadge connected={connected} />
      </div>

      {/* Health + Alert stats */}
      {health && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard title="API" value={health.api} icon={Activity} color="green" />
          <StatCard title="Database" value={health.db} icon={Database} color="blue" />
          <StatCard title="Redis" value={health.redis} icon={Server} color="purple" />
          <StatCard title="Safe Mode" value={health.safe_mode ? 'Active' : 'Off'} icon={Shield} color={health.safe_mode ? 'red' : 'green'} />
          <StatCard
            title="Active Alerts"
            value={alertStats?.active ?? 0}
            icon={Bell}
            color={alertStats?.critical > 0 ? 'red' : alertStats?.active > 0 ? 'orange' : 'gray'}
            onClick={() => navigate('/alerts')}
          />
          <StatCard
            title="Critical Alerts"
            value={alertStats?.critical ?? 0}
            icon={AlertTriangle}
            color={alertStats?.critical > 0 ? 'red' : 'gray'}
            onClick={() => navigate('/alerts')}
          />
        </div>
      )}

      {/* Engine/Integrity status */}
      {health && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
          <StatCard
            title="Degraded Engines"
            value={health.degraded_engines?.length > 0 ? health.degraded_engines.join(', ') : 'None'}
            icon={Zap}
            color={health.degraded_engines?.length > 0 ? 'orange' : 'green'}
          />
          <StatCard title="Integrity" value={health.integrity_status} icon={CheckCircle} color="blue" />
          <StatCard title="Recent Blocks" value={recentBlocks?.length ?? 0} icon={AlertTriangle} color="red" />
        </div>
      )}

      {/* Charts row 1: Timeline + Pie */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <TrendingUp size={16} className="text-blue-400" />
            Decision Trend (14 days)
          </h3>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={timelineData}>
              <defs>
                {Object.entries(decisionColors).map(([key, color]) => (
                  <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={color} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" stroke="#4B5563" tick={{ fontSize: 11 }} />
              <YAxis stroke="#4B5563" tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Area type="monotone" dataKey="Block" stroke="#EF4444" fill="url(#grad-block)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="Challenge" stroke="#F59E0B" fill="url(#grad-challenge)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="Monitor" stroke="#3B82F6" fill="url(#grad-monitor)" strokeWidth={2} dot={false} />
              <Area type="monotone" dataKey="Allow" stroke="#10B981" fill="url(#grad-allow)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-white font-semibold mb-4">Decision Mix</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="45%" outerRadius={85} innerRadius={40} paddingAngle={3}>
                  {pieData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-gray-600 text-sm">No data</div>
          )}
        </div>
      </div>

      {/* Charts row 2: Engine outcomes + Policy hits */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-white font-semibold mb-4">Engine Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={engineBarData} barSize={18}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="engine" stroke="#4B5563" tick={{ fontSize: 11 }} />
              <YAxis stroke="#4B5563" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="Low" fill="#10B981" radius={[3, 3, 0, 0]} />
              <Bar dataKey="Medium" fill="#F59E0B" radius={[3, 3, 0, 0]} />
              <Bar dataKey="High" fill="#EF4444" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <h3 className="text-white font-semibold mb-4">Top Policy Hits</h3>
          {policyBarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={policyBarData} layout="vertical" barSize={14}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                <XAxis type="number" stroke="#4B5563" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="policy" stroke="#4B5563" tick={{ fontSize: 10 }} width={120} />
                <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" fill="#3B82F6" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-56 flex items-center justify-center text-gray-600 text-sm">No policy hits</div>
          )}
        </div>
      </div>

      {/* Tables row: Recent scans + Recent blocks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <Radio size={15} className="text-blue-400" />
              Recent Scans
            </h3>
            <button onClick={() => navigate('/scans')} className="text-xs text-blue-400 hover:text-blue-300 transition">View all →</button>
          </div>
          <DataTable columns={scanColumns} data={recentScans || []} onRowClick={() => navigate('/scans')} emptyMessage="No recent scans" />
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold flex items-center gap-2">
              <AlertTriangle size={15} className="text-red-400" />
              Recent Blocks
            </h3>
            <button onClick={() => navigate('/incidents')} className="text-xs text-blue-400 hover:text-blue-300 transition">View all →</button>
          </div>
          <DataTable
            columns={[
              { key: 'timestamp', label: 'Time', render: (v: string) => <span className="text-xs text-gray-400">{new Date(v).toLocaleTimeString()}</span> },
              { key: 'event_id', label: 'Event', render: (v: string) => <span className="font-mono text-xs text-gray-500">{v?.slice(0, 8)}</span> },
              { key: 'policy_hits', label: 'Policies', render: (v: string[]) => <span className="text-xs text-orange-400">{v?.join(', ') || '—'}</span> },
            ]}
            data={recentBlocks || []}
            onRowClick={() => navigate('/incidents')}
            emptyMessage="No recent blocks"
          />
        </div>
      </div>
    </div>
  )
}

export default DashboardPage

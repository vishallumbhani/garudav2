import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { alertsApi } from '../../services/api'
import { useState } from 'react'
import { AlertTriangle, AlertCircle, Info, CheckCircle, Check, X, RefreshCw, Bell } from 'lucide-react'

const severityConfig: Record<string, { icon: any; color: string; bg: string; border: string }> = {
  critical: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-950/50', border: 'border-red-800' },
  high:     { icon: AlertCircle,  color: 'text-orange-400', bg: 'bg-orange-950/50', border: 'border-orange-800' },
  medium:   { icon: AlertCircle,  color: 'text-yellow-400', bg: 'bg-yellow-950/50', border: 'border-yellow-800' },
  low:      { icon: Info,         color: 'text-blue-400', bg: 'bg-blue-950/50', border: 'border-blue-800' },
}

const AlertsPage = () => {
  const queryClient = useQueryClient()
  const [showResolved, setShowResolved] = useState(false)
  const [tab, setTab] = useState<'active' | 'history'>('active')

  const { data: alerts = [], isLoading, refetch } = useQuery({
    queryKey: ['alerts', tab],
    queryFn: () => alertsApi.list(tab === 'history').then(r => r.data),
    refetchInterval: 15_000,
  })

  const { data: stats } = useQuery({
    queryKey: ['alertStats'],
    queryFn: () => alertsApi.stats().then(r => r.data),
    refetchInterval: 15_000,
  })

  const ackMutation = useMutation({
    mutationFn: (id: string) => alertsApi.acknowledge(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alertStats'] })
    },
  })

  const resolveMutation = useMutation({
    mutationFn: (id: string) => alertsApi.resolve(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alertStats'] })
    },
  })

  const activeAlerts = tab === 'active'
    ? alerts.filter((a: any) => !a.resolved_at)
    : alerts.filter((a: any) => a.resolved_at)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-white">Alerts</h1>
          <p className="text-gray-500 text-sm mt-0.5">Security events requiring attention</p>
        </div>
        <button onClick={() => refetch()} className="flex items-center gap-2 text-gray-400 hover:text-white text-sm px-3 py-2 bg-gray-800 rounded-lg border border-gray-700 transition">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Active', value: stats.active, color: 'text-white' },
            { label: 'Critical', value: stats.critical, color: 'text-red-400' },
            { label: 'High', value: stats.high, color: 'text-orange-400' },
            { label: 'Acknowledged', value: stats.acknowledged, color: 'text-green-400' },
          ].map(s => (
            <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <p className={`text-2xl font-bold ${s.color}`}>{s.value ?? 0}</p>
              <p className="text-gray-500 text-xs mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 w-fit">
        {(['active', 'history'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium capitalize transition ${
              tab === t ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="space-y-2">
        {isLoading ? (
          <div className="text-center py-10 text-gray-500">Loading alerts…</div>
        ) : activeAlerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-gray-600">
            <CheckCircle size={40} className="mb-3 text-green-700" />
            <p className="font-medium text-gray-500">No {tab === 'active' ? 'active' : 'resolved'} alerts</p>
            <p className="text-sm mt-1">
              {tab === 'active' ? 'All clear — no security events require attention.' : 'No historical alerts found.'}
            </p>
          </div>
        ) : (
          activeAlerts.map((alert: any) => {
            const cfg = severityConfig[alert.severity] || severityConfig.low
            const Icon = cfg.icon
            return (
              <div key={alert.id} className={`${cfg.bg} border ${cfg.border} rounded-xl p-4 flex items-start gap-4`}>
                <Icon size={18} className={`${cfg.color} shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-xs font-bold uppercase tracking-wide ${cfg.color}`}>{alert.severity}</span>
                    <span className="text-white font-medium text-sm">{alert.title}</span>
                    {alert.acknowledged && (
                      <span className="text-xs bg-green-900/50 text-green-400 border border-green-800 px-2 py-0.5 rounded-full">Acknowledged</span>
                    )}
                    {alert.resolved_at && (
                      <span className="text-xs bg-gray-800 text-gray-400 border border-gray-700 px-2 py-0.5 rounded-full">Resolved</span>
                    )}
                  </div>
                  {alert.description && (
                    <p className="text-gray-400 text-sm mt-1">{alert.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-600">
                    <span>{new Date(alert.created_at).toLocaleString()}</span>
                    {alert.tenant_id && <span>Tenant: {alert.tenant_id}</span>}
                    {alert.acknowledged_by && <span>Acked by: {alert.acknowledged_by}</span>}
                  </div>
                  {alert.context && (
                    <details className="mt-2">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">Show context</summary>
                      <pre className="mt-1 text-xs text-gray-400 bg-black/30 rounded p-2 overflow-auto max-h-40">
                        {JSON.stringify(alert.context, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
                {tab === 'active' && (
                  <div className="flex gap-2 shrink-0">
                    {!alert.acknowledged && (
                      <button
                        onClick={() => ackMutation.mutate(alert.id)}
                        title="Acknowledge"
                        className="p-1.5 bg-gray-800 hover:bg-green-900 text-gray-400 hover:text-green-300 rounded-lg border border-gray-700 transition"
                      >
                        <Check size={14} />
                      </button>
                    )}
                    <button
                      onClick={() => resolveMutation.mutate(alert.id)}
                      title="Resolve"
                      className="p-1.5 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white rounded-lg border border-gray-700 transition"
                    >
                      <X size={14} />
                    </button>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default AlertsPage

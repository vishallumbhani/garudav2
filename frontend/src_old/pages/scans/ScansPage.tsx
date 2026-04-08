import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../services/api'
import DataTable from '../../components/tables/DataTable'
import TraceDetailDrawer from './components/TraceDetailDrawer'

const ScansPage = () => {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const { data: scans, isLoading } = useQuery({
    queryKey: ['recentScans', 100],
    queryFn: () => dashboardApi.recentScans(100).then(r => r.data)
  })

  if (isLoading) return <div className="text-white">Loading scans...</div>

  const columns = [
    { key: 'timestamp', label: 'Time', render: (v: string) => new Date(v).toLocaleString() },
    { key: 'event_id', label: 'Event ID' },
    { key: 'decision', label: 'Decision' },
    { key: 'score', label: 'Score' },
    { key: 'session_id', label: 'Session' },
    { key: 'endpoint', label: 'Endpoint' }
  ]

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Scans</h1>
      <div className="bg-gray-800 rounded-lg p-4">
        <DataTable columns={columns} data={scans || []} onRowClick={(row) => setSelectedEventId(row.event_id)} />
      </div>
      <TraceDetailDrawer eventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
    </div>
  )
}
export default ScansPage
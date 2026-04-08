import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../services/api'
import DataTable from '../../components/tables/DataTable'

const IncidentsPage = () => {
  const { data: blocks, isLoading } = useQuery({
    queryKey: ['recentBlocks', 100],
    queryFn: () => dashboardApi.recentBlocks(100).then(r => r.data)
  })
  if (isLoading) return <div className="text-white">Loading incidents...</div>
  const columns = [
    { key: 'timestamp', label: 'Time', render: (v: string) => new Date(v).toLocaleString() },
    { key: 'event_id', label: 'Event ID' },
    { key: 'session_id', label: 'Session' },
    { key: 'policy_hits', label: 'Policy Hits', render: (v: string[]) => v?.join(', ') },
    { key: 'top_signals', label: 'Top Signals', render: (v: any) => JSON.stringify(v) }
  ]
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Incidents (Blocks & Challenges)</h1>
      <div className="bg-gray-800 rounded-lg p-4">
        <DataTable columns={columns} data={blocks || []} />
      </div>
    </div>
  )
}
export default IncidentsPage
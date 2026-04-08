import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../services/api'
import DataTable from '../../components/tables/DataTable'

const SessionsPage = () => {
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const { data: scans } = useQuery({
    queryKey: ['recentScans', 500],
    queryFn: () => dashboardApi.recentScans(500).then(r => r.data)
  })
  const sessionMap = new Map()
  scans?.forEach((s: any) => {
    if (s.session_id) {
      if (!sessionMap.has(s.session_id)) sessionMap.set(s.session_id, { count: 0, decisions: {}, lastSeen: s.timestamp })
      const sess = sessionMap.get(s.session_id)
      sess.count++
      sess.decisions[s.decision] = (sess.decisions[s.decision] || 0) + 1
      if (new Date(s.timestamp) > new Date(sess.lastSeen)) sess.lastSeen = s.timestamp
    }
  })
  const sessions = Array.from(sessionMap.entries()).map(([id, data]) => ({ session_id: id, ...data }))
  const columns = [
    { key: 'session_id', label: 'Session ID' },
    { key: 'count', label: 'Requests' },
    { key: 'decisions', label: 'Decisions', render: (v: any) => JSON.stringify(v) },
    { key: 'lastSeen', label: 'Last Seen', render: (v: string) => new Date(v).toLocaleString() }
  ]
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Sessions</h1>
      <div className="bg-gray-800 rounded-lg p-4">
        <DataTable columns={columns} data={sessions} onRowClick={(row) => setSelectedSession(row.session_id)} />
      </div>
      {selectedSession && (
        <div className="fixed inset-y-0 right-0 w-96 bg-gray-800 shadow-xl p-4 overflow-y-auto">
          <button onClick={() => setSelectedSession(null)} className="float-right text-gray-400">Close</button>
          <h2 className="text-xl font-bold text-white mb-4">Session {selectedSession}</h2>
          <pre className="text-gray-300 text-sm">{JSON.stringify(sessionMap.get(selectedSession), null, 2)}</pre>
        </div>
      )}
    </div>
  )
}
export default SessionsPage
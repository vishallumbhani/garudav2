import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '../../services/api'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import DataTable from '../../components/tables/DataTable'

const TimelinePage = () => {
  const [interval, setInterval] = useState<'day' | 'week'>('day')
  const { data: timeline } = useQuery({
    queryKey: ['timeline', interval],
    queryFn: () => dashboardApi.timeline(interval, 30).then(r => r.data)
  })
  const { data: scans } = useQuery({
    queryKey: ['recentScans', 200],
    queryFn: () => dashboardApi.recentScans(200).then(r => r.data)
  })
  const timelineData = timeline?.data?.map((d: any) => ({ date: new Date(d.time).toLocaleDateString(), total: d.total, block: d.block, challenge: d.challenge, monitor: d.monitor, allow: d.allow })) || []
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white">Timeline</h1>
        <div className="space-x-2">
          <button onClick={() => setInterval('day')} className={`px-3 py-1 rounded ${interval === 'day' ? 'bg-blue-600' : 'bg-gray-700'}`}>Day</button>
          <button onClick={() => setInterval('week')} className={`px-3 py-1 rounded ${interval === 'week' ? 'bg-blue-600' : 'bg-gray-700'}`}>Week</button>
        </div>
      </div>
      <div className="bg-gray-800 rounded-lg p-4">
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={timelineData}>
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
      <div className="bg-gray-800 rounded-lg p-4">
        <h2 className="text-white font-medium mb-4">Recent Events</h2>
        <DataTable columns={[
          { key: 'timestamp', label: 'Time', render: (v: string) => new Date(v).toLocaleString() },
          { key: 'decision', label: 'Decision' },
          { key: 'session_id', label: 'Session' }
        ]} data={scans?.slice(0, 50) || []} />
      </div>
    </div>
  )
}
export default TimelinePage
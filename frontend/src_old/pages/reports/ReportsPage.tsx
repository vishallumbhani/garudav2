import { useState } from 'react'
import { incidentsApi } from '../../services/api'
import { saveAs } from 'file-saver'

const ReportsPage = () => {
  const [startDate, setStartDate] = useState('2026-04-01')
  const [endDate, setEndDate] = useState('2026-04-05')
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchSummary = async () => {
    setLoading(true)
    try {
      const res = await incidentsApi.summary(startDate, endDate)
      setSummary(res.data)
    } finally { setLoading(false) }
  }
  const exportCSV = async () => {
    const res = await incidentsApi.csv(startDate, endDate)
    const blob = new Blob([res.data], { type: 'text/csv' })
    saveAs(blob, `incidents_${startDate}_to_${endDate}.csv`)
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Reports</h1>
      <div className="bg-gray-800 rounded-lg p-4 space-y-4">
        <div className="flex gap-4">
          <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="bg-gray-700 text-white p-2 rounded" />
          <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="bg-gray-700 text-white p-2 rounded" />
          <button onClick={fetchSummary} className="bg-blue-600 px-4 py-2 rounded">Load Summary</button>
          <button onClick={exportCSV} className="bg-green-600 px-4 py-2 rounded">Export CSV</button>
        </div>
        {loading && <div>Loading...</div>}
        {summary && <pre className="text-gray-300">{JSON.stringify(summary, null, 2)}</pre>}
      </div>
    </div>
  )
}
export default ReportsPage
// src/pages/scans/components/TraceDetailDrawer.tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '../../../services/api'
import { X } from 'lucide-react'

const TraceDetailDrawer = ({ eventId, onClose }: { eventId: string | null; onClose: () => void }) => {
  const { data: traceData } = useQuery({
    queryKey: ['trace', eventId],
    queryFn: () => api.get(`/v1/dashboard/trace/${eventId}`).then(r => r.data),
    enabled: !!eventId
  })

  if (!eventId) return null

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-1/2 lg:w-2/5 bg-gray-800 shadow-xl z-50 overflow-y-auto">
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-xl font-bold text-white">Trace: {eventId}</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24} /></button>
      </div>
      <div className="p-4">
        <pre className="text-gray-300 text-sm whitespace-pre-wrap">{JSON.stringify(traceData, null, 2)}</pre>
      </div>
    </div>
  )
}
export default TraceDetailDrawer
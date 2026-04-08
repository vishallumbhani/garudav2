import { X } from 'lucide-react'

interface TraceDetailDrawerProps {
  trace: any
  eventId: string
  onClose: () => void
}

const TraceDetailDrawer = ({ trace, eventId, onClose }: TraceDetailDrawerProps) => {
  if (!trace) return null

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-gray-800 shadow-xl z-50 overflow-y-auto">
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-white">Trace: {eventId}</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white">
          <X size={20} />
        </button>
      </div>
      <div className="p-4">
        <pre className="text-xs text-gray-300 whitespace-pre-wrap">
          {JSON.stringify(trace, null, 2)}
        </pre>
      </div>
    </div>
  )
}

export default TraceDetailDrawer

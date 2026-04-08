import { X } from 'lucide-react'
import { useState } from 'react'
import { adminApi } from '../../../services/api'

const PolicyEditDrawer = ({ policy, onClose, onUpdate }: any) => {
  const [enabled, setEnabled] = useState(policy?.enabled || false)
  const [loading, setLoading] = useState(false)

  const handleToggle = async () => {
    setLoading(true)
    try {
      await adminApi.policies.update(policy.policy_key, { enabled: !enabled })
      setEnabled(!enabled)
      if (onUpdate) onUpdate()
    } catch (err) { console.error(err) } finally { setLoading(false) }
  }

  if (!policy) return null
  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-gray-800 shadow-xl z-50 overflow-y-auto">
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h2 className="text-lg font-semibold text-white">Edit Policy: {policy.policy_key}</h2>
        <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={20} /></button>
      </div>
      <div className="p-4">
        <div className="mb-4 flex justify-between items-center">
          <span className="text-white">Enabled</span>
          <button onClick={handleToggle} disabled={loading} className="px-3 py-1 bg-blue-600 rounded">
            {enabled ? 'Disable' : 'Enable'}
          </button>
        </div>
        <pre className="text-xs text-gray-300">{JSON.stringify(policy, null, 2)}</pre>
      </div>
    </div>
  )
}
export default PolicyEditDrawer

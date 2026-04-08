import { X } from 'lucide-react'
import { useState } from 'react'
import { adminApi } from '../../../services/api'

const CreateApiKeyModal = ({ onClose, onCreated }: any) => {
  const [tenantId, setTenantId] = useState('11111111-1111-1111-1111-111111111111')
  const [loading, setLoading] = useState(false)
  const [newKey, setNewKey] = useState('')

  const handleCreate = async () => {
    setLoading(true)
    try {
      const res = await adminApi.apiKeys.create({ tenant_id: tenantId })
      setNewKey(res.data.api_key)
      if (onCreated) onCreated()
    } catch (err) { console.error(err) } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg w-full max-w-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-white">Create API Key</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={20} /></button>
        </div>
        {newKey ? (
          <div>
            <p className="text-green-400 mb-2">Key created (copy now, it won't be shown again):</p>
            <code className="block bg-gray-900 p-2 rounded text-sm break-all">{newKey}</code>
            <button onClick={onClose} className="mt-4 w-full bg-blue-600 py-2 rounded">Close</button>
          </div>
        ) : (
          <>
            <input type="text" value={tenantId} onChange={e => setTenantId(e.target.value)} className="w-full bg-gray-700 border border-gray-600 rounded p-2 mb-4 text-white" placeholder="Tenant ID" />
            <button onClick={handleCreate} disabled={loading} className="w-full bg-blue-600 py-2 rounded">Generate</button>
          </>
        )}
      </div>
    </div>
  )
}
export default CreateApiKeyModal

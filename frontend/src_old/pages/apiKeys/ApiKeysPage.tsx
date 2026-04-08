import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/api'
import DataTable from '../../components/tables/DataTable'
import { useState } from 'react'

const ApiKeysPage = () => {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [newKeyTenant, setNewKeyTenant] = useState('default')
  const [newKeyResult, setNewKeyResult] = useState('')
  const { data: keys } = useQuery({ queryKey: ['apiKeys'], queryFn: () => adminApi.apiKeys.list().then(r => r.data) })
  const createMutation = useMutation({
    mutationFn: (data: any) => adminApi.apiKeys.create(data),
    onSuccess: (res) => { setNewKeyResult(res.data.api_key); queryClient.invalidateQueries({ queryKey: ['apiKeys'] }) }
  })
  const revokeMutation = useMutation({
    mutationFn: (id: number) => adminApi.apiKeys.revoke(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['apiKeys'] })
  })
  const columns = [
    { key: 'key_prefix', label: 'Prefix' },
    { key: 'tenant_id', label: 'Tenant' },
    { key: 'created_at', label: 'Created', render: (v: string) => new Date(v).toLocaleString() },
    { key: 'enabled', label: 'Enabled', render: (v: boolean) => v ? 'Yes' : 'No' }
  ]
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">API Keys</h1>
      <button onClick={() => setShowCreate(true)} className="bg-green-600 px-4 py-2 rounded">Create New Key</button>
      <div className="bg-gray-800 rounded-lg p-4">
        <DataTable columns={columns} data={keys || []} onRowClick={(row) => revokeMutation.mutate(row.id)} />
      </div>
      {showCreate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-800 p-6 rounded-lg w-96">
            <h2 className="text-xl font-bold text-white mb-4">Create API Key</h2>
            <input type="text" placeholder="Tenant ID" value={newKeyTenant} onChange={e => setNewKeyTenant(e.target.value)} className="w-full bg-gray-700 text-white p-2 rounded mb-4" />
            <button onClick={() => createMutation.mutate({ tenant_id: newKeyTenant })} className="bg-blue-600 px-4 py-2 rounded w-full">Generate</button>
            {newKeyResult && <div className="mt-4 p-2 bg-gray-900 rounded"><code className="text-green-400">{newKeyResult}</code><p className="text-xs text-gray-400">Copy this key now, it won't be shown again.</p></div>}
            <button onClick={() => { setShowCreate(false); setNewKeyResult('') }} className="mt-4 text-gray-400">Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
export default ApiKeysPage
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/api'
import DataTable from '../../components/tables/DataTable'
import { useState } from 'react'

const PoliciesPage = () => {
  const queryClient = useQueryClient()
  const [editingPolicy, setEditingPolicy] = useState<any>(null)
  const { data: policies } = useQuery({ queryKey: ['policies'], queryFn: () => adminApi.policies.list().then(r => r.data) })
  const updateMutation = useMutation({
    mutationFn: ({ key, data }: any) => adminApi.policies.update(key, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['policies'] })
  })
  const columns = [
    { key: 'policy_key', label: 'Key' },
    { key: 'action', label: 'Action' },
    { key: 'enabled', label: 'Enabled', render: (v: boolean) => v ? 'Yes' : 'No' },
    { key: 'policy_level', label: 'Level' }
  ]
  const handleToggle = (policy: any) => {
    updateMutation.mutate({ key: policy.policy_key, data: { enabled: !policy.enabled } })
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Policies</h1>
      <div className="bg-gray-800 rounded-lg p-4">
        <DataTable columns={columns} data={policies || []} onRowClick={(row) => setEditingPolicy(row)} />
      </div>
      {editingPolicy && (
        <div className="fixed inset-y-0 right-0 w-96 bg-gray-800 shadow-xl p-4">
          <button onClick={() => setEditingPolicy(null)} className="float-right text-gray-400">Close</button>
          <h2 className="text-xl font-bold text-white mb-4">Edit {editingPolicy.policy_key}</h2>
          <button onClick={() => handleToggle(editingPolicy)} className="bg-blue-600 px-4 py-2 rounded">Toggle Enabled</button>
        </div>
      )}
    </div>
  )
}
export default PoliciesPage
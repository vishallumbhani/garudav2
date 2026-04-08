import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/api'
import DataTable from '../../components/tables/DataTable'
import { useState } from 'react'

const TenantsPage = () => {
  const queryClient = useQueryClient()
  const [selectedTenant, setSelectedTenant] = useState<string>('default')
  const { data: tenantConfig } = useQuery({ queryKey: ['tenant', selectedTenant], queryFn: () => adminApi.tenants.get(selectedTenant).then(r => r.data) })
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: any) => adminApi.tenants.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tenant', selectedTenant] })
  })
  const handleToggleStrict = () => {
    updateMutation.mutate({ id: selectedTenant, data: { strict_mode: !tenantConfig?.strict_mode } })
  }
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-white">Tenants</h1>
      <div className="bg-gray-800 rounded-lg p-4">
        <label className="text-white mr-2">Tenant ID:</label>
        <input type="text" value={selectedTenant} onChange={e => setSelectedTenant(e.target.value)} className="bg-gray-700 text-white p-1 rounded" />
        <button onClick={handleToggleStrict} className="ml-4 bg-blue-600 px-4 py-1 rounded">Toggle Strict Mode</button>
        <pre className="mt-4 text-gray-300">{JSON.stringify(tenantConfig, null, 2)}</pre>
      </div>
    </div>
  )
}
export default TenantsPage